import asyncio

from django.http import HttpResponse
from django.utils.timezone import localtime
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import *
from asgiref.sync import async_to_sync, sync_to_async
from datetime import datetime, timedelta
import pytz
import io
import base64
import matplotlib
matplotlib.use("Agg")   # important if server has no GUI (prevents Tkinter errors)
import matplotlib.pyplot as plt
import pandas as pd

class ChatConsumer(AsyncWebsocketConsumer):
    auction_end_status = False
    async def connect(self):
        # print("Connecting WebSocket...")
        if self.scope['user'].is_authenticated:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'

            # await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            # await self.accept()
            username = self.scope['user'].username

            """Timer canView  access"""
            user = self.scope['user']
            user_access_obj = await sync_to_async(UserAccess.objects.get)(user=user)

            if user_access_obj.can_view_requirements:
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
            else:
                # reject the connection or just don't add them to the group
                await self.close()
            """Timer Access end"""

            general_access, minutes, start_time,g_access,use_cel,dec_val_vi= await self.get_general_access()
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


            """Auction Started"""
            if  auction_start  and auction_end_status == False and  not self.scope['user'].is_superuser :
                '''Normal users is subscribed to this channel'''
                bid_group_data = await self.get_all_bid_group(username)
                # print("bid_group_data in connect:",bid_group_data)

                await self.send(text_data=json.dumps({
                    'type': 'grouped_bid',
                    'bid_group_data': bid_group_data

                }))

            if  self.scope['user'].is_superuser:
                '''Only admin is subscribed to this channel'''
                ranked_bids = await self.get_ranked_bids()
                for item in ranked_bids:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "bids_per_requirement",
                            "bid_req": item["requirement"],
                            "top_bidders": [
                                {
                                    "username": bidder["username"],
                                    "rate": bidder["rate"],
                                    "rank": bidder["rank"],
                                }
                                for bidder in item["top_bidders"]
                            ]
                        }
                    )
                # bid_data = await self.get_all_bid_data(dec_val_vi)
                # for item in bid_data:
                #     await self.channel_layer.group_send(
                #         self.room_group_name,
                #         {
                #             "type": "bids_per_requirement",
                #             'bid_id': item['bid_id'],
                #             'bids_by': item['bid_by'],
                #             'bid_req': item['requirement'],
                #             'bid_rate': item['bid_rate']
                #         }
                #     )




            if self.scope['user'].is_superuser:
                '''This is used to get all users except superuser only admins subscribed to this '''
                users = await self.get_bid_users()
                # print("Users:", users)
                await self.send(text_data=json.dumps({
                    "type": "normal_user",
                    "users": [user["username"] for user in users]
                }))

            # if self.scope['user'].is_superuser:
            #     report= await self.get_bid_report()
            #     print("Report:", report)
                # await self.send(text_data=json.dumps({
                #     "type": "report",
                #     "report": ""
                # }))

                # if self.scope['user'].is_superuser:
                #     image_base64 = await self.get_bid_report_plot()
                #     await self.channel_layer.group_send(
                #        self.room_group_name,
                #         {
                #             "type": "send_bid_graph",
                #             "graph": image_base64
                #         }
                #     )

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
            general_access, minutes, start_time,g_access,use_cel,dec_val_vi = await self.get_general_access()
            # print("General Access from connect:", general_access)
            # print("General Access minutes from connect:", minutes)
            # print("General Access end_time from connect:", start_time)
            # print("Decremental Value:", dec_val_vi)
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
                # print("Auction Not Started can view req:",access.can_view_requirements)

                self.timer_task = asyncio.create_task(self.send_remaining_time())
                reqs = await sync_to_async(get_all_requirements)()
                # print("dec_val_vi:", dec_val_vi)
                if not dec_val_vi:
                    # print("not dec val visibility executed 1")
                    for r in reqs:  # loop through all requirements
                        r['min_dec_val'] = 0
                    # reqs[0].update({'min_dec_val': 0})
                # print("Reqs1:",reqs)

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
                    # print("dec_val_vi2:", dec_val_vi)
                    if  not dec_val_vi:
                        # print("not dec val visibility executed 2")
                        for r in reqs:  # loop through all requirements
                            r['min_dec_val'] = 0
                        # print("Reqs2 inside if:", reqs)
                    # print("Reqs2:",reqs)
                    """After Ending the auction still sending requirements so bidder can view their req"""
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'load_requirements',
                            'requirements': reqs,
                            'len_reqs': len(reqs),
                            "auction_start_status": auction_start,

                        }
                    )
                    """After Ending the auction still sending the following so bidder can view their bids"""

                    bid_group_data = await self.get_all_bid_group(username)
                    # print("bid_group_data in connect:",bid_group_data)

                    await self.send(text_data=json.dumps({
                        'type': 'grouped_bid',
                        'bid_group_data': bid_group_data

                    }))
            else:

                # print("Auction Ended")
                auction_start=False
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

                bid_group_data = await self.get_all_bid_group(username)
                # print("bid_group_data in connect:",bid_group_data)

                await self.send(text_data=json.dumps({
                    'type': 'grouped_bid',
                    'bid_group_data': bid_group_data

                }))
                if hasattr(self, "timer_task") and not self.timer_task.done():
                    self.timer_task.cancel()
                    try:
                        await self.timer_task
                    except asyncio.CancelledError:
                        print("Cancelled timer task")

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
            valid_bid = True
            if float(bid_amt) <= 0:  # Reject 0 and negative values
                valid_bid = False
                await self.send(text_data=json.dumps({
                    'type': 'valid_bid',
                    'valid_bid': "0 and negative values are not accepted"
                }))
                return  #  VERY IMPORTANT — stop executing the rest of the function

            requirement = await sync_to_async(Requirements.objects.get)(id=req_id)

            general_access, minutes, start_time,g_access,use_cel,dec_val_vi = await self.get_general_access()
            clt,start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
            # existing_bids = await sync_to_async(
            #     Bid.objects.filter(user=user, req=requirement).count
            # )()



            from django.utils import timezone
            import pytz
            kolkata_tz = pytz.timezone("Asia/Kolkata")
            # Convert everything to Kolkata time
            clt_kolkata = clt.astimezone(kolkata_tz)
            start_time_kolkata = start_time.astimezone(kolkata_tz)
            end_times_kolkata = end_times.astimezone(kolkata_tz)

            # print("clt_kolkata:", clt_kolkata)
            # print("start_time_kolkata:", start_time_kolkata)
            # print("end_times_kolkata:", end_times_kolkata)
            # print("remaining:", remaining)

            auction_end_status = False
            if clt_kolkata >= end_times_kolkata:
                print("Auction Ended")
                auction_end_status = True
            if clt_kolkata <= start_time_kolkata:
                print("Auction Not Started")
                auction_end_status = True

            if auction_end_status==False:
                last_minute = timedelta(minutes=1)
                if bid_amt and remaining <= last_minute:
                    # print("User submitted  the bid last minute")
                    g_access.minutes += 2
                    await sync_to_async(g_access.save)()
                    # GeneralAccess.save()

                    general_access, minutes, start_time, g_access, use_cel, dec_val_vi = await self.get_general_access()

                    clt, start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
                    # print("end_times:", end_times)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'valid_bid',
                     'valid_bid': " Auction Ended.",
                }))
                return  #


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
                    return  #



            '''This is for getting  the lowest bid price than the previous one'''
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
                return  #

            valid_bid_dec_val = True
            if user_bid:  # make sure it's not empty
                last_bid = user_bid[-1].rate


                # print("last_bid from receive:", last_bid)
                if last_bid and int(req_.min_dec_val != 0):
                    # print("Bid dec val inside if:", valid_bid_dec_val)
                    # print("Last_Bid inside if:", last_bid)
                    # print("Decremental val is called:")
                    decremental_value = int(last_bid) - int(req_.min_dec_val)
                    # print("decremental_value:", decremental_value)

                    if decremental_value <= int(bid_amt):
                        print("decremental_value inside loop:", decremental_value)
                        print("Bid Amount:", int(bid_amt))

                        if dec_val_vi:
                            valid_bid_dec_val = False
                            await self.send(text_data=json.dumps({
                                'type': 'valid_bid',
                                'valid_bid': "Enter amount lower than the minimal decremental value {}".format(
                                    req_.min_dec_val),
                            }))
                            return  #
                        if not dec_val_vi:
                            valid_bid_dec_val = False
                            await self.send(text_data=json.dumps({
                                'type': 'valid_bid',
                                'valid_bid': "Decrease the bidding price more to compete",
                            }))
                            return  #
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
                        return  #
            try:
                user_exist = await sync_to_async(UserAccess.objects.get)(user=user_)
                user_access = user_exist.can_view_requirements
            except UserAccess.DoesNotExist:
                user_access = False


            # print("auction_end_status outside:",auction_end_status)
            # ✅ Only use user_access (boolean), don’t check user_exist == True
            if auction_end_status==False:
                # print("auction_end_status inside :", auction_end_status)

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
                        # print("Auction_end_status before saving:", auction_end_status)
                        # print("Bid Amount:", bid_amt)

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
                    # print("dec_val_vi3:", dec_val_vi)
                    if not dec_val_vi:
                        # reqs[0].update({'min_dec_val': 0})
                        for r in reqs:  # loop through all requirements
                            r['min_dec_val'] = 0
                    auction_start=True
                    # print("reqs3:",reqs)

                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'load_requirements',
                            'requirements': reqs,
                            'len_reqs': len(reqs),
                            "auction_start_status": auction_start,
                        }
                    )

                    ranked_bids = await self.get_ranked_bids()
                    for item in ranked_bids:
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "bids_per_requirement",
                                "bid_req": item["requirement"],
                                "top_bidders": [
                                    {
                                        "username": bidder["username"],
                                        "rate": bidder["rate"],
                                        "rank": bidder["rank"],
                                    }
                                    for bidder in item["top_bidders"]
                                ]
                            }
                        )
                else:
                    # bid_group_data = await self.get_all_bid_group(username)
                    # # print("bid_group_data in connect:",bid_group_data)
                    #
                    # await self.send(text_data=json.dumps({
                    #     'type': 'grouped_bid',
                    #     'bid_group_data': bid_group_data
                    #
                    # }))
                    # await self.channel_layer.group_send(
                    #     self.room_group_name,
                    #     {
                    #         "type": "send_grouped_bid"
                    #     }
                    # )

                    # ❌ Send error if auction closed or too many bids
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Auction ended.'
                    }))



            # image_base64 = await self.get_bid_report_plot()
            # await self.channel_layer.group_send(
            #     self.room_group_name,
            #     {
            #         "type": "send_bid_graph",
            #         "graph": image_base64
            #     }
            # )





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

    # async def bids_per_requirement(self, event):
    #     await self.send(text_data=json.dumps({
    #         'type': 'bids_per_requirement',
    #         'bid_id': event['bid_id'],
    #         'bids_by': event['bids_by'],
    #         'bid_req': event['bid_req'],
    #         'bid_rate': event['bid_rate']
    #     }))
    async def bids_per_requirement(self, event):
        await self.send(text_data=json.dumps({
            "type": "bids_per_requirement",
            "bid_req": event["bid_req"],
            "top_bidders": event["top_bidders"],
        }))

    async def send_bid_graph(self, event):
        await self.send(text_data=json.dumps({
            "type": "bid_report_graph",
            "graph": event["graph"]
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

    # @sync_to_async
    # def get_requirements_except_min_dec_val(self):
    #     return list(Requirements.objects.all().values(
    #         'id', 'loading_point', 'unloading_point', 'loading_point_full_address',
    #         'unloading_point_full_address', 'truck_type', 'product', 'no_of_trucks', 'notes',
    #         'drum_type_no_of_drums', 'weight_per_drum', 'approx_mat_mt', 'types', 'cel_price'
    #     ))


    @sync_to_async
    def get_bid_users(self):
        return list(User.objects.filter(is_superuser=False, is_staff=False).values("username"))

    # @sync_to_async
    # def get_bid_report(self):
    #     import pandas as pd
    #     all_bids = Bid.objects.all().values(
    #         "id", "user__username", "req__id", "req__loading_point", "req__unloading_point", "req__product",
    #         "req__truck_type", "rate", "created_at"
    #     )
    #     rank_df = pd.DataFrame(list(all_bids))  # ✅ now it's
    #     # Pick the lowest rate per user per requirement
    #     lowest_bids = rank_df.sort_values("rate").groupby(
    #         ["req__id", "user__username"], as_index=False
    #     ).first()
    #     # Rank them within each requirement
    #     lowest_bids["Rank"] = lowest_bids.groupby("req__id")["rate"].rank(
    #         ascending=True, method="dense"
    #     )
    #
    #     # Keep only ranks 1 to 4
    #     rank_df = lowest_bids[lowest_bids["Rank"].between(1, 4)]
    #     return rank_df
    @sync_to_async
    def get_bid_report_plot(self):
        import pandas as pd
        import matplotlib
        matplotlib.use("Agg")  # server-safe backend
        import matplotlib.pyplot as plt
        import io, base64

        # ---- Fetch bids ----
        all_bids = Bid.objects.all().values(
            "id", "user__username", "req__id",
            "req__loading_point", "req__unloading_point",
            "req__product", "req__truck_type",
            "rate", "created_at"
        )

        if not all_bids.exists():
            return None  # no data yet

        # ---- Convert to DataFrame ----
        df = pd.DataFrame(list(all_bids))

        # ---- Pick lowest rate per user per requirement ----
        lowest_bids = (
            df.sort_values("rate")
            .groupby(["req__id", "user__username"], as_index=False)
            .first()
        )

        # ---- Rank bids per requirement ----
        lowest_bids["Rank"] = (
            lowest_bids.groupby("req__id")["rate"]
            .rank(ascending=True, method="dense")
        )
        # ---- Keep only top 4 per requirement ----
        rank_df = lowest_bids[lowest_bids["Rank"].between(1, 4)]

        # ---- Prepare for grouped bar chart ----
        requirements = sorted(rank_df["req__id"].unique())
        users = rank_df["user__username"].unique()
        num_users = len(users)
        bar_width = 0.2  # width of each bar

        fig, ax = plt.subplots(figsize=(8, 5))

        # assign colors per user
        colors = {user: plt.cm.tab10(i % 10) for i, user in enumerate(users)}

        # plot bars per user
        for i, user in enumerate(users):
            user_data = rank_df[rank_df["user__username"] == user]
            # align bars per requirement id
            x_positions = [requirements.index(req) + i * bar_width for req in user_data["req__id"]]
            ax.bar(
                x_positions,
                user_data["rate"],
                width=bar_width,
                color=colors[user],
                label=user
            )
            # annotate bars with rank and rate
            for x, rate, rank in zip(x_positions, user_data["rate"], user_data["Rank"]):
                ax.text(x, rate + 0.01 * max(rank_df["rate"]), f"{int(rank)} | {rate}", ha="center", va="bottom",
                        fontsize=8)

        # ---- X-axis ticks in the middle of grouped bars ----
        mid_positions = [i + (num_users - 1) * bar_width / 2 for i in range(len(requirements))]
        ax.set_xticks(mid_positions)
        ax.set_xticklabels(requirements)

        # ---- Labels and title ----
        ax.set_xlabel("Requirement ID")
        ax.set_ylabel("Bid Rate")
        ax.set_title("Top 4 Bids per Requirement")
        ax.legend(title="Bidders")
        plt.tight_layout()

        # ---- Convert figure to base64 ----
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)

        return image_base64

    from .models import GeneralAccess
    @sync_to_async
    def get_general_access(self):
        try:
            general_access = GeneralAccess.objects.get(pk=1)
            return general_access.general_access, general_access.minutes, general_access.start_time,general_access,general_access.use_cel,general_access.dec_val_vi
        except Exception as e:
            print("General Access Exception:", e)

    @sync_to_async
    def get_all_bid_data(self,dec_val_vi):
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
    #
    # @ async_to_sync
    # def users_bis_history(self):
    #     all_bids = Bid.objects.all().values(
    #         # "id", "user__username", "req__id",
    #         # "req__loading_point", "req__unloading_point",
    #         # "req__product", "req__truck_type",
    #         # "rate", "created_at"
    #         "id", "user__username", "req__id",
    #         "req__loading_point", "req__unloading_point",
    #         "req__product", "req__truck_type", "req__no_of_trucks", "req__notes", "req__drum_type_no_of_drums",
    #         "req__approx_mat_mt", "req__weight_per_drum",
    #         "rate", "created_at"
    #     )
    #     rank_df = pd.DataFrame(list(all_bids))
    #
    #     # make sure created_at is datetime
    #     rank_df["created_at"] = pd.to_datetime(rank_df["created_at"])
    #
    #     # Pick the lowest rate per user per requirement, tie-break by earliest created_at
    #     lowest_bids = rank_df.sort_values(["req__id", "rate", "created_at"]).groupby(
    #         ["req__id", "user__username"], as_index=False
    #     ).first()
    #
    #     # Rank them within each requirement (rate first, created_at as tiebreaker)
    #     lowest_bids = lowest_bids.sort_values(["req__id", "rate", "created_at"])
    #     lowest_bids["Rank"] = lowest_bids.groupby("req__id").cumcount() + 1
    #
    #     # Keep only ranks 1 to 4
    #     rank_df = lowest_bids[lowest_bids["Rank"].between(1, 4)]
    #     return rank_df

    @sync_to_async
    def get_ranked_bids(self):
        """This get_rank_bids is for super user"""
        # 1️⃣ Fetch all bids
        all_bids = Bid.objects.select_related("req", "user").values(
            "id",
            "user__username",
            "req__id",
            "req__loading_point",
            "req__unloading_point",
            "req__product",
            "req__truck_type",
            "req__no_of_trucks",
            "req__notes",
            "req__drum_type_no_of_drums",
            "req__approx_mat_mt",
            "req__weight_per_drum",
            "rate",
            "created_at"
        )

        if not all_bids:
            return []

        df = pd.DataFrame(list(all_bids))
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["rate"] = df["rate"].astype(float)

        # 2️⃣ Collect all bids per user + req, keep order by created_at
        df = df.sort_values(["req__id", "user__username", "created_at"])
        all_bids_per_user = (
            df.groupby(["req__id", "user__username"])
            .agg({
                "rate": lambda x: " >> ".join(str(r) for r in x.tolist()),
                "created_at": "first",  # first bid time
                "req__loading_point": "first",
                "req__unloading_point": "first",
                # "req__product": "first",
                # "req__truck_type": "first",
                # "req__no_of_trucks": "first",
                # "req__notes": "first",
                # "req__drum_type_no_of_drums": "first",
                # "req__approx_mat_mt": "first",
                # "req__weight_per_drum": "first",
            })
            .reset_index()
        )

        # 3️⃣ Extract lowest bid (first number from ">>")
        all_bids_per_user["lowest_rate"] = all_bids_per_user["rate"].apply(
            lambda s: min(float(r) for r in s.split(" >> "))

        )

        # 4️⃣ Rank bidders within each requirement
        all_bids_per_user = all_bids_per_user.sort_values(
            ["req__id", "lowest_rate", "created_at"]
        )
        all_bids_per_user["rank"] = (
                all_bids_per_user.groupby("req__id").cumcount() + 1
        )

        # 5️⃣ Keep only top 4
        top4 = all_bids_per_user[all_bids_per_user["rank"] <= 4]

        # 6️⃣ Build response
        result = []
        for req_id, group in top4.groupby("req__id"):
            req = group.iloc[0]
            result.append({
                "requirement": {
                    "id": str(req["req__id"]),
                    "loading_point": str(req["req__loading_point"]),
                    "unloading_point": str(req["req__unloading_point"]),
                    # "product": str(req["req__product"]),
                    # "truck_type": str(req["req__truck_type"]),
                    # "no_of_trucks": str(req["req__no_of_trucks"]),
                    # "notes": str(req["req__notes"]),
                    # "drum_type_no_of_drums": str(req["req__drum_type_no_of_drums"]),
                    # "approx_mat_mt": str(req["req__approx_mat_mt"]),
                    # "weight_per_drum": str(req["req__weight_per_drum"]),
                },
                "top_bidders": [
                    {
                        "username": str(row["user__username"]),
                        "rate": str(row["rate"]),  # e.g. "1500 >> 1400 >> 1350"
                        "rank": str(row["rank"]),
                    }
                    for _, row in group.iterrows()
                ]
            })

        return result


    @sync_to_async
    def get_all_bid_group(self, username):
        from django.contrib.auth.models import User
        user = User.objects.get(username=username)
        # Build rows for all bids (any user), then compute ranks per user per req
        bids = Bid.objects.select_related("user", "req").all().order_by("req__id", "rate", "created_at")
        len_bids=len(bids)

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
            "user_ranks": user_ranks,  # one unique rank per req for this user
            "len_bids":len_bids
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

        user = self.scope['user']
        # print("has2:",user)
        user_access_obj = await sync_to_async(UserAccess.objects.get)(user=user)
        has_access = user_access_obj.can_view_requirements
        # print("Has_access:",has_access)
        if has_access:
            while True:
                general_access, minutes, start_time,g_access,use_cel,dec_val_vi = await self.get_general_access()
                """From get_general_access to time_calculation """
                # print("start_time:",start_time)

                clt,start_time, end_times, remaining = await self.time_calculation(general_access, minutes, start_time)
                # print("Remaining:", remaining.seconds)
                # print("Remaining type :", type(remaining.seconds))
                # print("Remaining Seconds:",remaining.total_seconds())
                if remaining.total_seconds() <= 0:
                    # print("Auction time reached, stopping timer.")
                    break


                # Send only the time update
                if clt <= start_time:
                    # print("Auction Not Started")
                    auction_start = False
                else:
                    auction_start = True
                auction_end_status = False
                if clt >= end_times:
                    # print("Auction Ended")
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



