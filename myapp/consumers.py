import asyncio
from sys import exception

from django.contrib.auth.models import User
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import *
from asgiref.sync import async_to_sync, sync_to_async
import pandas as pd

class ChatConsumer(AsyncWebsocketConsumer):
    auction_end_status=False
    async def connect(self):
        print("Connecting WebSocket...")
        if self.scope['user'].is_authenticated:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            username = self.scope['user'].username

            if not self.scope['user'].is_superuser:
                bid_group_data = await self.get_all_bid_group(username)
                await self.send(text_data=json.dumps({
                    'type': 'grouped_bid',
                    'bid_group_data': bid_group_data
                }))

            if self.scope['user'].is_superuser:
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
                print("Users:",users)
                await self.send(text_data=json.dumps({
                    "type": "normal_user",
                    "users": [user["username"] for user in users]
                }))


                # general_access = await self.get_general_access()
                # if general_access:
                #     await self.send(text_data=json.dumps({
                #         "type": "normal_user",
                #         "users": [user["username"] for user in users]
                #     }))


            @sync_to_async
            def req_view_access(user):
                '''This function is used to see whether the normal user or bidder has the access of  seeing the requirements or no'''
                user = User.objects.get(username=user.username)
                access, created = UserAccess.objects.get_or_create(user=user)

                return access, created

            def get_all_requirements():
                return list(Requirements.objects.all().values(
                    'id', 'loading_point', 'unloading_point','loading_point_full_address', 'unloading_point_full_address','truck_type', 'qty', 'product','no_of_trucks','notes','drum_type_no_of_drums','weight_per_drum','types'
                ))

            access, created = await req_view_access(self.scope['user'])
            # general_access,minutes,end_time= await self.get_general_access()
            # print("General Access from con:",general_access)
            # import time
            # from datetime import datetime, date
            #
            #
            # today = date.today()
            # current_tim = datetime.now().time()
            # # If end_time is a time object already:
            # current_dt = datetime.combine(today, current_tim)
            # end_dt = datetime.combine(today, end_time)
            # remaining = end_dt - current_dt
            #
            # current_tim = time.strftime("%H:%M")
            #
            # print("Auction  End Time: ", end_time)
            # print("Auction  End Time  type: ",type( end_time))
            # current_time = datetime.strptime(current_tim, "%H:%M").time()
            # auction_end_status=False
            #
            # print("Remaining:",remaining)
            # if current_time >= end_time:
            #     print("Auction Ended")
            #     auction_end_status=True
            from django.utils import timezone
            from datetime import datetime
            """If auction ends requirements will not be shows"""
            general_access, minutes, start_time = await self.get_general_access()
            print("General Access from connect:", general_access)
            print("General Access minutes from connect:", minutes)
            print("General Access end_time from connect:", start_time)


            auction_end_status = False
            # if now_dt >= end_dt:
            #     print("Auction Ended")
            #     auction_end_status = True

            if auction_end_status==False:
                if self.scope['user'].is_superuser:
                    self.timer_task=asyncio.create_task(self.send_remaining_time())

                if access.can_view_requirements  and general_access == True :

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


                        }
                    )


            else:


                if hasattr(self, "timer_task") and not self.timer_task.done():
                    self.timer_task.cancel()
                    try:
                        await self.timer_task
                    except asyncio.CancelledError:
                        print("Cancelled timer task")
                print("Auction Ended")



        else:
            await self.send(text_data=json.dumps({"message": "Login"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')
        user = self.scope['user']

        if text_data_json.get("type") == "submit_bid":
            req_id = text_data_json.get("req_id")
            bid_amt = text_data_json.get("bid_amt")
            requirement = await sync_to_async(Requirements.objects.get)(id=req_id)
            # general_access,minutes,end_time = await self.get_general_access()
            # print("Received Bid amount:",bid_amt)
            # print("Bid Req Id:",req_id)
            # existing_bids = await sync_to_async(Bid.objects.filter(user=user, req=requirement).count)()
            # print("Existing_bids:",existing_bids)
            # print("General Access to save data to server:",general_access)
            #
            # #Start
            # import time
            # from datetime import datetime, date
            #
            # today = date.today()
            # current_tim = datetime.now().time()
            # # If end_time is a time object already:
            # current_dt = datetime.combine(today, current_tim)
            # end_dt = datetime.combine(today, end_time)
            # remaining = end_dt - current_dt
            #
            # current_tim = time.strftime("%H:%M")
            #
            # print("Auction  End Time: ", end_time)
            # print("Auction  End Time  type: ", type(end_time))
            # current_time = datetime.strptime(current_tim, "%H:%M").time()
            # #end
            #
            # print("Remaining:", remaining)
            # if not  current_time >= end_time:
            #     if existing_bids < 5 and general_access == True:
            #         bid_instance = await sync_to_async(Bid.objects.create)(
            #             user=user,
            #             req=requirement,
            #             rate=bid_amt
            #         )
            from django.utils import timezone
            from datetime import datetime

            general_access, minutes, start_time = await self.get_general_access()
            print("Received Bid amount:", bid_amt)
            print("Bid Req Id:", req_id)

            existing_bids = await sync_to_async(
                Bid.objects.filter(user=user, req=requirement).count
            )()
            print("Existing_bids:", existing_bids)
            print("General Access to save data to server:", general_access)

            # --- Timezone-safe auction end check ---
            now_dt = timezone.localtime()
            today = timezone.localdate()

            # Combine today's date with the end_time from DB
            end_dt = datetime.combine(today, end_time)

            # Make timezone-aware
            end_dt = timezone.make_aware(end_dt, timezone.get_current_timezone())

            remaining = end_dt - now_dt

            print("Auction End Time:", end_time)
            print("Auction End Time type:", type(end_time))
            print("Current Time:", now_dt.time())
            print("Remaining:", remaining)

            # Only allow bid if current time < end time
            if now_dt < end_dt:
                if existing_bids < 5 and general_access:
                    bid_instance = await sync_to_async(Bid.objects.create)(
                        user=user,
                        req=requirement,
                        rate=bid_amt
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
                            'unloading_point_full_address':requirement.unloading_point_full_address,
                            'truck_type': requirement.truck_type,
                            'no_of_trucks': requirement.no_of_trucks,
                            'qty': requirement.qty,
                            'notes': requirement.notes,
                            'drum_type_no_of_drums': requirement.drum_type_no_of_drums,
                            'product': requirement.product,
                            'weight_per_drum': requirement.weight_per_drum,
                            'types': requirement.types,
                        },
                        'bid_rate': bid_amt
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You can only place up to 5 bids for the same requirement.'
                }))
            return
        if not self.scope['user'].is_superuser:
            bid_group_data = await self.get_all_bid_group(user.username)
            await self.send(text_data=json.dumps({
                'type': 'grouped_bid',
                'bid_group_data': bid_group_data
            }))

        #Load the requirement upon admin button click
        # if text_data_json.get("action") == "load_requirements":
            #
            # def get_all_requirements():
            #     return list(Requirements.objects.all().values(
            #         'id', 'loading_point', 'unloading_point', 'loading_point_full_address', 'unloading_point_full_address',
            #         'truck_type', 'qty', 'product', 'no_of_trucks', 'notes', 'drum_type_no_of_drums', 'weight_per_drum',
            #         'types'
            #     ))
            #
            # reqs = await sync_to_async(get_all_requirements)()
            #
            # await self.channel_layer.group_send(
            #     self.room_group_name,
            #     {
            #         'type': 'load_requirements',
            #         'requirements': reqs,
            #         'len_reqs': len(reqs)
            #     }
            # )



    async def load_requirements(self, event):
        await self.send(text_data=json.dumps({
            'type': 'requirements',
            'data': event['requirements'],
            'len_reqs': event['len_reqs']

        }))

    async def bids_per_requirement(self, event):
        await self.send(text_data=json.dumps({
            'type': 'bids_per_requirement',
            'bid_id': event['bid_id'],
            'bids_by': event['bids_by'],
            'bid_req': event['requirement'],
            'bid_rate': event['bid_rate']
        }))

    @sync_to_async
    def get_bid_users(self):
        return list(User.objects.filter(is_superuser=False, is_staff=False).values("username"))
    from .models import GeneralAccess
    @sync_to_async
    def get_general_access(self):
        try:
            general_access=GeneralAccess.objects.get(pk=1)
            return general_access.general_access,general_access.minutes,general_access.start_time
        except Exception as e:
            print("General Access eException:",e)






    # async def bid_end_time(self,event):
    #     message=event["message"]
    #     print("Bid End Time from consumers:",message)
    #     await self.send(text_data=json.dumps({
    #         "type":"bid_end_time",
    #         "message":message
    #     }))






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
                        'qty': bid.req.qty,
                        'product': bid.req.product,
                        'notes': bid.req.notes,
                        'drum_type_no_of_drums': bid.req.drum_type_no_of_drums,
                        'weight_per_drum': bid.req.weight_per_drum,
                        'types': bid.req.types,
                    },
                    'bid_rate': bid.rate
                })
        return result

    # @sync_to_async
    # def get_all_bid_group(self, username):
    #     print(f"get_all_bid_group called by: {username}")
    #     result = []
    #     user = User.objects.get(username=username)
    #     bids = Bid.objects.select_related('user', 'req').all().order_by('req__id', 'rate')
    #     rank_bid = []
    #
    #     for bid in bids:
    #         rank_bid.append({"bid_id": bid.req.id, "bid_by": bid.user.username, "bid_rate": bid.rate})
    #
    #     if rank_bid:
    #         df = pd.DataFrame(rank_bid)
    #         df['rank'] = df.groupby('bid_id')['bid_rate'].rank(method='dense').astype(int)
    #
    #         user_rank_df = df[df['bid_by'] == username]
    #         user_rank_df = user_rank_df.loc[user_rank_df.groupby('bid_id')['bid_rate'].idxmin()]
    #         user_result = user_rank_df[['bid_id', 'bid_rate', 'rank']].to_dict(orient='records')
    #     else:
    #         user_result = []
    #
    #     user_bids = Bid.objects.filter(user=user)
    #     for bid in user_bids:
    #         result.append({
    #             "id": bid.req.id,
    #             "rate": bid.rate
    #         })
    #
    #     return {
    #         "bids": result,
    #         "user_ranks": user_result
    #     }
    @sync_to_async
    def get_all_bid_group(self, username):
        print(f"get_all_bid_group called by: {username}")
        result = []
        user = User.objects.get(username=username)

        # Order by req_id, then rate, then created_at so earlier bids get priority
        bids = Bid.objects.select_related('user', 'req') \
            .all() \
            .order_by('req__id', 'rate', 'created_at')

        rank_bid = []
        for bid in bids:
            rank_bid.append({
                "bid_id": bid.req.id,
                "bid_by": bid.user.username,
                "bid_rate": bid.rate,
                "bid_time": bid.created_at  # assuming you have a timestamp
            })

        if rank_bid:
            import pandas as pd
            df = pd.DataFrame(rank_bid)

            # Sort by rate and time to break ties
            df = df.sort_values(['bid_id', 'bid_rate', 'bid_time'], ascending=[True, True, True])

            # Assign rank based on sorted position
            df['rank'] = df.groupby('bid_id').cumcount() + 1

            # Get the current user's best rank per requirement
            user_rank_df = df[df['bid_by'] == username]
            user_rank_df = user_rank_df.loc[user_rank_df.groupby('bid_id')['bid_rate'].idxmin()]
            user_result = user_rank_df[['bid_id', 'bid_rate', 'rank']].to_dict(orient='records')
        else:
            user_result = []

        # Gather all user's bids for display
        user_bids = Bid.objects.filter(user=user)
        for bid in user_bids:
            result.append({
                "id": bid.req.id,
                "rate": bid.rate
            })

        return {
            "bids": result,
            "user_ranks": user_result
        }

    # async def send_remaining_time(self):
    #     import asyncio
    #     from datetime import datetime, date
    #     while True:
    #         general_access, minutes, end_time = await self.get_general_access()
    #         today = date.today()
    #         now_dt = datetime.now()
    #         end_dt = datetime.combine(today, end_time)
    #         remaining = end_dt - now_dt
    #         # If auction ended, stop the loop
    #         if remaining.total_seconds() <= 0:
    #             print("Auction time reached, stopping timer.")
    #             break
    #
    #         # Send only the time update
    #         await self.channel_layer.group_send(
    #             self.room_group_name,
    #             {
    #                 'type': 'timer_update',
    #                 'minutes': str(remaining),
    #
    #                 'end_time': str(end_time)
    #             }
    #         )
    #         await asyncio.sleep(1)  # Update every minute
    #
    async def timer_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'timer_update',
            'minutes': event['minutes'],
            'end_time': event['end_time']
        }))

    async def send_remaining_time(self):
        from django.utils import timezone
        from datetime import datetime

        import asyncio

        while True:
            general_access, minutes, start_time = await self.get_general_access()
            from datetime import datetime, timedelta
            import pytz

            get_india = pytz.timezone('Asia/Kolkata')
            clt = datetime.now(get_india)
            print("Current Local  Time:", clt)
            print("Current Local  Time Type:", type(clt))
            print("Start_time Type:", type(start_time))
            print("Start_time Type:", start_time)
            print("Minutes:",minutes)



            minute = timedelta(minutes=minutes)
            end_times = start_time + minute
            print("End Time:", end_times)
            print("End Time Type:", type(end_times))

            remaining = end_times- clt
            print("Remaining:", remaining)
            print("Remaining type:", type(remaining))

            # If auction ended, stop the loop
            if remaining.total_seconds() <= 0:
                print("Auction time reached, stopping timer.")
                break

            # Send only the time update
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'timer_update',
                    'minutes': str(remaining),
                    'end_time': str(end_times)
                }
            )

            await asyncio.sleep(1)  # update every second
