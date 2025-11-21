import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.utils import timezone

from api.models import Profile 
from api.translation import translate_text


class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        # Obtenemos el nombre de la sala desde la URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Obtenemos el usuario. Gracias a AuthMiddlewareStack en asgi.py
        self.user = self.scope['user']

        # Rechazar conexiÃ³n si el usuario no estÃ¡ autenticado
        if not self.user.is_authenticated:
            await self.close()
            return

        # 1. Unirse al grupo de la sala
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # 2. Aceptar la conexiÃ³n WebSocket
        await self.accept()
        print(f"Usuario {self.user.username} conectado a la sala: {self.room_name}")


    async def disconnect(self, close_code):
        # Salir del grupo de la sala
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"Usuario {self.user.username} desconectado de la sala: {self.room_name}")


    # 3. Esta funciÃ³n se llama cuando recibimos un mensaje del cliente (Frontend)
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        can_send = await self.check_message_limit(self.user)
        if not can_send:
            await self.send(text_data=json.dumps({
                'message': "Límite diario alcanzado (10 msgs). Actualiza tu Plan a Premium para continuar.",
                'username': "Sistema"
            }))
            return
        
        # Obtenemos el idioma de origen del usuario que envÃ­a
        source_language = await self.get_user_language(self.user)

        # Enviar el mensaje al grupo (esto llamarÃ¡ a la funciÃ³n 'chat_message')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message', # Llama a la funciÃ³n chat_message
                'message': message,
                'username': self.user.username,
                'source_lang': source_language
            }
        )

    @sync_to_async
    def check_message_limit(self, user):
        try:
            profile = user.profile
            today = timezone.now().date()
            
            # Resetear si es otro dÃ­a
            if profile.last_message_date != today:
                profile.daily_messages_count = 0
                profile.last_message_date = today
            
            # Validar
            limit = 10 # Demo limit
            if profile.subscription_plan == 'free' and profile.daily_messages_count >= limit:
                profile.save()
                return False
            
            # Contar
            profile.daily_messages_count += 1
            profile.save()
            return True
        except:
            return True

    # 4. Esta funciÃ³n se llama en CADA consumidor (usuario) del grupo
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        source_lang = event['source_lang']
        
        # Obtenemos el idioma de destino de ESTE usuario (el receptor)
        target_language = await self.get_user_language(self.scope['user'])

        translated_text = message
        
        # 5. Usamos sync_to_async para la traducciÃ³n si los idiomas son diferentes
        if source_lang != target_language:
            # Â¡AquÃ­ ocurre la magia!
            translation_result = await self.perform_translation(message, target_language, source_lang)
            
            if 'error' not in translation_result:
                translated_text = translation_result['translated_text']
            else:
                print(f"Error de traducción: {translation_result['error']}")
                translated_text = f"Error al traducir: {message}" # Enviar error al cliente

        # 6. Enviar el mensaje (traducido o no) de vuelta al frontend de este usuario
        await self.send(text_data=json.dumps({
            'message': translated_text,
            'username': username
        }))

    # --- Funciones de Ayuda ---

    @sync_to_async
    def get_user_language(self, user):
        """
        Obtiene la preferencia de idioma del perfil del usuario (acceso a BBDD).
        """
        try:
            # Usamos el modelo Profile que ya tenÃ­as
            return user.profile.language_preference
        except Profile.DoesNotExist:
            return 'es' # Idioma por defecto si no tiene perfil

    @sync_to_async
    def perform_translation(self, text, target_lang, source_lang):
        """
        Ejecuta la traducciÃ³n sÃ­ncrona (de translation.py) en un hilo separado.
        """
        # Usamos la funciÃ³n que ya tenÃ­as
        return translate_text(text, target_lang, source_lang)