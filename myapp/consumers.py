import asyncio
from django.utils.timezone import localtime
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import *
from asgiref.sync import async_to_sync, sync_to_async
from datetime import datetime, timedelta
import pytz


class ChatConsumer(AsyncWebsocketConsumer):
    auction_end_status = False

    async def connect(self):
        # print("Connecting WebSocket...")
        if self.scope['user'].is_authenticated:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            username = self.scope['user'].username
            #

            general_access, minutes, start_time,g_access,use_cel= await self.get_general_access()
            clt, start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)

            auction_start = True

            if clt <= start_time:
                '''Auction not started'''
                # print("Auction Not Started")
                auction_start = False

            auction_end_status = False
            if clt >= end_times:
                """Auction Ended"""
                # print("Auction Ended")
                auction_end_status = True

            if  auction_start  and auction_end_status == False and  not self.scope['user'].is_superuser :
                '''Normal users is subscribed to this channel'''
                bid_group_data = await self.get_all_bid_group(username)
                await self.send(text_data=json.dumps({
                    'type': 'grouped_bid',
                    'bid_group_data': bid_group_data
                }))


            if  self.scope['user'].is_superuser:
                '''Only admin is subscribed to this channel'''
                bid_data = await self.get_all_bid_data()
                for item in bid_data:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'bids_per_requirement',
                            'bid_id': item['bid_id'],
                            'bids_by': item['bid_by'],
                            'requirement': item['requirement'],
                            'bid_rate': item['bid_rate']
                        }
                    )

            if self.scope['user'].is_superuser:
                '''This is used to get all users except superuser but admin can do it'''
                users = await self.get_bid_users()
                # print("Users:", users)
                await self.send(text_data=json.dumps({
                    "type": "normal_user",
                    "users": [user["username"] for user in users]
                }))

            @sync_to_async
            def req_view_access(user):
                '''This function is used to see whether the normal user or bidder has the access of  seeing the requirements or no'''
                user = User.objects.get(username=user.username)
                access, created = UserAccess.objects.get_or_create(user=user)
                return access, created

            def get_all_requirements():
                return list(Requirements.objects.all().values(
                    'id', 'loading_point', 'unloading_point', 'loading_point_full_address',
                    'unloading_point_full_address', 'truck_type', 'product', 'no_of_trucks', 'notes',
                    'drum_type_no_of_drums', 'weight_per_drum','approx_mat_mt', 'types','cel_price','min_dec_val'
                ))

            access, created = await req_view_access(self.scope['user'])

            from django.utils import timezone
            from datetime import datetime
            """If auction ends requirements will not be shows"""
            general_access, minutes, start_time,g_access,use_cel = await self.get_general_access()
            # print("General Access from connect:", general_access)
            # print("General Access minutes from connect:", minutes)
            # print("General Access end_time from connect:", start_time)

            clt,start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)

            auction_start = True
            if clt <= start_time:
                # print("Auction Not Started")
                auction_start = False

            auction_end_status = False
            if clt >= end_times:
                # print("Auction Ended")
                auction_end_status = True
            if auction_start==False and access.can_view_requirements and general_access == True:
                print("Auction Not Started can view req:",access.can_view_requirements)

                self.timer_task = asyncio.create_task(self.send_remaining_time())
                reqs = await sync_to_async(get_all_requirements)()

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'load_requirements',
                        'requirements': reqs,
                        'len_reqs': len(reqs),
                        "auction_start_status": auction_start,
                    }
                )
            elif auction_end_status == False:

                # # print("auction_end_status False: executed")
                if self.scope['user'].is_superuser:
                    self.timer_task = asyncio.create_task(self.send_remaining_time())

                if access.can_view_requirements and general_access == True:
                    user = self.scope['user']
                    # print("Access granted for: ", user.username)
                    # print("General Access minutes: ", minutes)
                    # print("General Access end_time: ", end_time)
                    reqs = await sync_to_async(get_all_requirements)()

                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'load_requirements',
                            'requirements': reqs,
                            'len_reqs': len(reqs),
                            "auction_start_status": auction_start,

                        }
                    )


            else:

                if hasattr(self, "timer_task") and not self.timer_task.done():
                    self.timer_task.cancel()
                    try:
                        await self.timer_task
                    except asyncio.CancelledError:
                        print("Cancelled timer task")
                # print("Auction Ended")



        else:
            await self.send(text_data=json.dumps({"message": "Login"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        user = self.scope['user']

        if text_data_json.get("type") == "submit_bid":
            req_id = text_data_json.get("req_id")
            bid_amt = text_data_json.get("bid_amt")

            requirement = await sync_to_async(Requirements.objects.get)(id=req_id)

            general_access, minutes, start_time,g_access,use_cel = await self.get_general_access()
            clt,start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
            existing_bids = await sync_to_async(
                Bid.objects.filter(user=user, req=requirement).count
            )()


            last_minute = timedelta(minutes=1)
            if bid_amt and remaining <= last_minute:
                # print("User submitted  the bid last minute")
                g_access.minutes += 2
                await sync_to_async(g_access.save)()
                # GeneralAccess.save()

                general_access, minutes, start_time,g_access,use_cel = await self.get_general_access()
                clt, start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)

            auction_end_status = False
            if clt >= end_times:
                """Auction Ended"""
                # print("Auction Ended")
                auction_end_status = True
            if clt <= start_time:
                """Auction not started"""
                # print("Auction Not Started")
                auction_end_status = True

            # print("User:",user)
            # print("User Name:",user.username)
            user_ = await sync_to_async(User.objects.get)(username=user.username)
            '''All the user previous bids in user_bid'''
            user_bid = await sync_to_async(list)(Bid.objects.filter(user=user_, req=requirement.id))
            req_ = await sync_to_async(Requirements.objects.get)(id=requirement.id)
            # print("User Bid :",user_bid)
            # print("Req :",req_)

            # min_dec_val
            ''' To place  a bid,Bid amount must be lower than the ceiling price or 0'''
            # print("Req ceiling price:",req_.cel_price)

            valid_bid_cel_price = True
            if use_cel:
                valid_bid_cel_price = False
                # print("req_.cel_price:",req_.cel_price)
                # print("req_.cel_price type:",type(req_.cel_price))
                # print("user_bid :",user_bid)
                # print("user_bid type:",type(user_bid))
                # print("user_bid  amt:",bid_amt)
                # print("user_bid amt type:",type(bid_amt))
                if (int(bid_amt) < req_.cel_price) or req_.cel_price == 0:
                    valid_bid_cel_price = True

                if not valid_bid_cel_price:
                    await self.send(text_data=json.dumps({
                        'type': 'valid_bid',
                        'valid_bid': "Place lowest bid price than ceiling price {}".format(req_.cel_price),
                    }))



            '''This is for getting taking the lowest bid price than the previous one'''
            valid_bid = True
            for rate in user_bid:
                # print("Submitted Rate", rate.rate)
                # print("Submitted Rate Type", type(rate.rate))
                if int(bid_amt)< rate.rate:
                    valid_bid=True
                else:
                    valid_bid=False

            if not valid_bid:
                await self.send(text_data=json.dumps({
                    'type': 'valid_bid',
                    'valid_bid':"Enter lowest bid amount than the previous one.",
                }))

            valid_bid_dec_val = True
            if user_bid:  # make sure it's not empty
                last_bid = user_bid[-1].rate
                # print("last_bid from receive:", last_bid)
                if last_bid and int(req_.min_dec_val != 0):
                    # print("Decremental val is called:")
                    decremental_value = int(last_bid) - int(req_.min_dec_val)
                    # print("decremental_value:", decremental_value)

                    if decremental_value <= int(bid_amt):
                        # print("decremental_value inside loop:", decremental_value)
                        # print("Bid Amount:", int(bid_amt))

                        valid_bid_dec_val = False
                        await self.send(text_data=json.dumps({
                            'type': 'valid_bid',
                            'valid_bid': "Enter amount lower than the minimal decremental value {}".format(
                                req_.min_dec_val),
                        }))
                # print("Valid Bid dec status:", valid_bid_dec_val)
                # print("Last_Bid:", last_bid)


            else:
                last_bid = 0
                if req_.cel_price:
                    minimum_amt=req_.cel_price-int(req_.min_dec_val)
                    if not int(bid_amt)<minimum_amt:
                        valid_bid_dec_val = False
                        await self.send(text_data=json.dumps({
                             'type': 'valid_bid',
                             'valid_bid': "Enter amount lower than the minimal decremental value {}".format(
                                 req_.min_dec_val),
                        }))

            try:
                user_exist = await sync_to_async(UserAccess.objects.get)(user=user_)
                user_access = user_exist.can_view_requirements
            except UserAccess.DoesNotExist:
                user_access = False


            # ✅ Only use user_access (boolean), don’t check user_exist == True
            if (
                    auction_end_status is False
                    # and existing_bids < 5
                    and general_access
                    and user_access  # True/False
                    and valid_bid
                    and valid_bid_cel_price
                    and valid_bid_dec_val
            ):
                if use_cel and valid_bid_cel_price:
                    """Updating ceiling price"""
                    await self.update_req_cel_price(req_, bid_amt)

                bid_instance = await sync_to_async(Bid.objects.create)(
                    user=user,
                    req=requirement,
                    rate=bid_amt
                )


                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_grouped_bid"
                    }
                )

                reqs=await self. get_all_requirements()
                auction_start=True

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'load_requirements',
                        'requirements': reqs,
                        'len_reqs': len(reqs),
                        "auction_start_status": auction_start,

                    }
                )



                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'bids_per_requirement',
                        'bid_id': bid_instance.id,
                        'bids_by': user.username,
                        'requirement': {
                            'id': requirement.id,
                            'loading_point': requirement.loading_point,
                            'unloading_point': requirement.unloading_point,
                            'loading_point_full_address': requirement.loading_point_full_address,
                            'unloading_point_full_address': requirement.unloading_point_full_address,
                            'truck_type': requirement.truck_type,
                            'no_of_trucks': requirement.no_of_trucks,
                            # 'qty': requirement.qty,
                            'notes': requirement.notes,
                            'drum_type_no_of_drums': requirement.drum_type_no_of_drums,
                            'product': requirement.product,
                            'weight_per_drum': requirement.weight_per_drum,
                            'approx_mat_mt': requirement.approx_mat_mt,
                            'types': requirement.types,
                            'cel_price': requirement.cel_price,
                        },
                        'bid_rate': bid_amt
                    }
                )

            else:
                # ❌ Send error if auction closed or too many bids
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You can only place up to 5 bids for the same requirement or auction ended.'
                }))



    async def time_calculation(self, general_access, minutes, start_time):


        # return access, created
        if general_access:
            get_india = pytz.timezone('Asia/Kolkata')
            clt = datetime.now(get_india)

            # Auction duration
            minute = timedelta(minutes=minutes)
            end_times = start_time + minute

            # Remaining time calculation
            if clt <= start_time:
                remaining = start_time - clt  # auction not started yet
            elif clt <= end_times:
                remaining = end_times - clt  # auction running
            else:
                remaining = timedelta(seconds=0)  # auction ended


            return clt, start_time, end_times, remaining

    async def load_requirements(self, event):
        await self.send(text_data=json.dumps({
            'type': 'requirements',
            'data': event['requirements'],
            'len_reqs': event['len_reqs'],
            'auction_start_status': event['auction_start_status']


        }))

    async def bids_per_requirement(self, event):
        await self.send(text_data=json.dumps({
            'type': 'bids_per_requirement',
            'bid_id': event['bid_id'],
            'bids_by': event['bids_by'],
            'bid_req': event['requirement'],
            'bid_rate': event['bid_rate']
        }))

    async def send_grouped_bid(self, event):
        user = self.scope['user']
        if not user.is_superuser:
            bid_group_data = await self.get_all_bid_group(user.username)
            await self.send(text_data=json.dumps({
                "type": "grouped_bid",
                "bid_group_data": bid_group_data
            }))



    @sync_to_async
    def get_all_requirements(self):
        return list(Requirements.objects.all().values(
            'id', 'loading_point', 'unloading_point', 'loading_point_full_address',
            'unloading_point_full_address', 'truck_type', 'product', 'no_of_trucks', 'notes',
            'drum_type_no_of_drums', 'weight_per_drum','approx_mat_mt', 'types', 'cel_price','min_dec_val'
        ))


    @sync_to_async
    def get_bid_users(self):
        return list(User.objects.filter(is_superuser=False, is_staff=False).values("username"))

    from .models import GeneralAccess
    @sync_to_async
    def get_general_access(self):
        try:
            general_access = GeneralAccess.objects.get(pk=1)
            return general_access.general_access, general_access.minutes, general_access.start_time,general_access,general_access.use_cel
        except Exception as e:
            print("General Access Exception:", e)

    @sync_to_async
    def get_all_bid_data(self):
        result = []
        requirements = Requirements.objects.prefetch_related('bid_req__user')
        for req in requirements:
            for bid in req.bid_req.all():
                result.append({
                    'bid_id': bid.id,
                    'bid_by': bid.user.username,
                    'requirement': {
                        'id': bid.req.id,
                        'loading_point': bid.req.loading_point,
                        'unloading_point': bid.req.unloading_point,
                        'loading_point_full_address': bid.req.loading_point_full_address,
                        'unloading_point_full_address': bid.req.unloading_point_full_address,
                        'truck_type': bid.req.truck_type,
                        'no_of_trucks': bid.req.no_of_trucks,
                        # 'qty': bid.req.qty,
                        'product': bid.req.product,
                        'notes': bid.req.notes,
                        'drum_type_no_of_drums': bid.req.drum_type_no_of_drums,
                        'weight_per_drum': bid.req.weight_per_drum,
                        'approx_mat_mt': bid.req.approx_mat_mt,
                        'types': bid.req.types,
                        'cel_price': bid.req.cel_price,
                    },
                    'bid_rate': bid.rate
                })
        return result


    @sync_to_async
    def get_all_bid_group(self, username):
        from django.contrib.auth.models import User
        user = User.objects.get(username=username)

        # Build rows for all bids (any user), then compute ranks per user per req
        bids = Bid.objects.select_related("user", "req").all().order_by("req__id", "rate", "created_at")

        rows = []
        for b in bids:
            rows.append({
                "bid_id": b.req.id,  # requirement id
                "bid_by": b.user.username,  # user
                "bid_rate": b.rate,  # rate
                "bid_time": b.created_at,  # timestamp
            })

        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)

            # --- Step 1: each (req, user) keeps only their BEST bid ---
            # Best = lowest rate; if tie on rate for same user, earlier time wins
            best_per_user = (
                df.sort_values(["bid_id", "bid_by", "bid_rate", "bid_time"])
                .drop_duplicates(subset=["bid_id", "bid_by"], keep="first")
            )

            # --- Step 2: rank USERS per requirement using those best bids ---
            best_per_user = best_per_user.sort_values(["bid_id", "bid_rate", "bid_time"])
            best_per_user["rank"] = best_per_user.groupby("bid_id").cumcount() + 1

            # Only return the current user's ranks (one row per req where they bid)
            me = best_per_user[best_per_user["bid_by"] == username][["bid_id", "bid_rate", "rank"]]
            user_ranks = me.to_dict(orient="records")
        else:
            user_ranks = []

        # Return ONLY this user's own bids (if you want to show their own history)
        my_bids_qs = (
            Bid.objects.filter(user=user)
            .values("req_id", "rate")
            .order_by("req_id", "created_at")
        )
        my_bids = [{"id": r["req_id"], "rate": r["rate"]} for r in my_bids_qs]
        # print("my_bids:",my_bids)
        # print("user_ranks:",user_ranks)
        '''
        my_bids: [{'id': 2550, 'rate': 1000}]
        user_ranks: [{'bid_id': 2550, 'bid_rate': 1000, 'rank': 1}]

        '''
        return {
            "bids": my_bids,  # these are ONLY this user's bids
            "user_ranks": user_ranks  # one unique rank per req for this user
        }

    async def timer_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'timer_update',
            'minutes': event['minutes'],
            'seconds': event['seconds'],
            'end_time': event['end_time'],
            'auction_started': event['auction_started'],
            'auction_end_status': event['auction_end_status'],
            'clt': event['clt'],
            'start_time': event['start_time']
        }))

    from channels.db import database_sync_to_async
    @database_sync_to_async
    def update_req_cel_price(self,req, bid_amt):
        req.cel_price = bid_amt
        req.save()
        return req

    async def send_remaining_time(self):
        from django.utils import timezone
        from datetime import datetime
        import asyncio

        while True:
            general_access, minutes, start_time,g_access,use_cel = await self.get_general_access()
            """From get_general_access to time_calculation """
            # print("start_time:",start_time)

            clt,start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
            # print("Remaining:", remaining.seconds)
            # print("Remaining type :", type(remaining.seconds))
            # print("Remaining Seconds:",remaining.total_seconds())
            if remaining.total_seconds() <= 0:
                print("Auction time reached, stopping timer.")
                break

            # Send only the time update
            if clt <= start_time:
                print("Auction Not Started")
                auction_start = False
            else:
                auction_start = True
            auction_end_status = False
            if clt >= end_times:
                print("Auction Ended")
                auction_end_status = True
            # Make it timezone-aware in Asia/Kolkata
            start_time = localtime(start_time)
            end_times = localtime(end_times)
            # print("start_time:",start_time)
            # print('auction_end_status:', auction_end_status)


            # print("auction_started status:", auction_start)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'timer_update',
                    'minutes': str(remaining),
                    'end_time': str(end_times),
                    'seconds': remaining.seconds,
                    'auction_started': auction_start,
                    'auction_end_status': auction_end_status,
                    "clt":str(clt),
                    "start_time":str(start_time)
                }
            )
            await asyncio.sleep(1)  # update every second

    # async def send_remaining_time(self):
    #     from django.utils import timezone
    #     from datetime import datetime
    #     import asyncio
    #     user = self.scope['user']
    #     # Fetch user's access once
    #     try:
    #         user_access_obj = await sync_to_async(UserAccess.objects.get)(user=user.username)
    #         has_access = user_access_obj.can_view_requirements
    #     except UserAccess.DoesNotExist:
    #         has_access = False
    #
    #     if not has_access:
    #         # User doesn't have access → exit immediately
    #         return
    #
    #     if has_access:
    #         while True:
    #             general_access, minutes, start_time, g_access, use_cel = await self.get_general_access()
    #             clt, start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
    #
    #             if remaining.total_seconds() <= 0:
    #                 break
    #
    #             auction_start=True
    #             if clt <= start_time:
    #                 auction_start = False
    #             else:
    #                 auction_start = True
    #
    #             auction_end_status = False
    #             if clt >= end_times:
    #                 print("Auction Ended")
    #                 auction_end_status = True
    #
    #             # Send timer update **only to this user**
    #             await self.send(text_data=json.dumps({
    #                 'type': 'timer_update',
    #                 'minutes': str(remaining),
    #                 'seconds': remaining.seconds,
    #                 'end_time': str(localtime(end_times)),
    #                 'auction_started': auction_start,
    #                 'auction_end_status': auction_end_status,
    #                 'clt': str(clt),
    #                 'start_time': str(localtime(start_time)),
    #             }))
    #
    #             await asyncio.sleep(1)


