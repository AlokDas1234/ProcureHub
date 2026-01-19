# myapp/tasks.py
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils.timezone import localtime
from myapp.utils.timer_utils import time_calculation, get_general_access  # ✅ correct import

@shared_task
def broadcast_remaining_time():
    general_access, minutes, start_time, g_access, use_cel, dec_val_vi, interval = get_general_access()
    clt, start_time, end_times, remaining, remaining_interval = time_calculation(
        general_access, minutes, start_time, interval
    )

    auction_start = clt > start_time
    auction_end_status = clt >= end_times

    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        "auction_room",
        {
            "type": "timer_update",
            "minutes": str(remaining),
            "end_time": str(localtime(end_times)),
            "seconds": remaining.seconds,
            "auction_started": auction_start,
            "auction_end_status": auction_end_status,
            "clt": str(clt),
            "start_time": str(localtime(start_time)),
        },
    )
