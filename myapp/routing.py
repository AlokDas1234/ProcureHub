# # myapp/routing.py
#
# from django.urls import re_path
# from . import consumers
#
# websocket_urlpatterns = [
#     re_path(r'ws/somepath/$', consumers.MyConsumer.as_asgi()),
# ]
# myapp/routing.py



from django.urls import re_path
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[^/]+)/$', ChatConsumer.as_asgi()),
]
