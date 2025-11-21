import os
from django.core.asgi import get_asgi_application

# 1. Configurar settings primero
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# 2. ¡CRUCIAL! Inicializar Django ANTES de importar nada de tu aplicación
# Esto carga los modelos y apps para que estén listos.
django_asgi_app = get_asgi_application()

# 3. AHORA sí es seguro importar las rutas y middleware
from channels.routing import ProtocolTypeRouter, URLRouter
from chat.middleware import TokenAuthMiddleware
import chat.routing

application = ProtocolTypeRouter({
    # 4. Manejar HTTP con la app de Django ya iniciada
    "http": django_asgi_app,
    
    # 5. Manejar WebSockets
    "websocket": TokenAuthMiddleware(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})