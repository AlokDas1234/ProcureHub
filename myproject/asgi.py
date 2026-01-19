# # myproject/asgi.py
#
# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from myapp import routing
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
#
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             routing.websocket_urlpatterns
#         )
#     ),
# })

import os
import django  # ✅ Add this

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# ✅ Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# ✅ Initialize Django before anything else
django.setup()

from myapp import routing  # Safe to import after django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})

# myproject/asgi.py

# import os
# import django
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.sessions import SessionMiddlewareStack
# from django.core.asgi import get_asgi_application
#
# # ✅ Set Django settings module BEFORE importing routing or models
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
#
# # ✅ Initialize Django
# django.setup()
#
# from myapp import routing  # Import AFTER setup
#
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": SessionMiddlewareStack(
#         URLRouter(routing.websocket_urlpatterns)
#     ),
# })
