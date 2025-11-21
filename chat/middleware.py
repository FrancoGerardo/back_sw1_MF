from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from urllib.parse import parse_qs

@database_sync_to_async
def get_user(token_key):
    try:
        token = Token.objects.get(key=token_key)
        print(f"✅ Middleware: Usuario encontrado: {token.user.username}")
        return token.user
    except Token.DoesNotExist:
        print(f"❌ Middleware: Token {token_key} no existe en la base de datos.")
        return AnonymousUser()

class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Obtener la query string
        query_string = scope.get("query_string", b"").decode("utf-8")
        print(f"🔍 Middleware: Query string recibida: {query_string}")
        
        query_params = parse_qs(query_string)
        token_key = query_params.get("token", [None])[0]

        if token_key:
            print(f"🔑 Middleware: Token extraído: {token_key}")
            scope["user"] = await get_user(token_key)
        else:
            print("⚠️ Middleware: No se encontró el parámetro 'token' en la URL.")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)