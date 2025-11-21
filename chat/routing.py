from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # CAMBIO: Cambiamos \w+ por [^/]+ para aceptar guiones y otros símbolos
    re_path(r'^ws/chat/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
]