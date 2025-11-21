from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

def user_directory_path(instance, filename):
    """Genera la ruta de archivo para nuevos documentos: MEDIA_ROOT/user_<id>/<filename>"""
    return f'user_{instance.owner.id}/{filename}'

def user_preview_directory_path(instance, filename):
    """Genera la ruta de archivo para las vistas previas: MEDIA_ROOT/user_<id>/previews/<filename>"""
    return f'user_{instance.owner.id}/previews/{filename}'

# Create your models here.


class Profile(models.Model):
    """
    Modelo que extiende el usuario de Django para añadir campos adicionales.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    language_preference = models.CharField(
        max_length=10, default='es', help_text="Preferencia de idioma (ej: 'es', 'en')")
    subscription_plan = models.CharField(
        max_length=20, default='free', help_text="Plan de suscripción del usuario (ej: 'free', 'premium')")
    
    # --- CAMPO AÑADIDO PARA UC-21 ---
    preferred_translation_api = models.CharField(
        max_length=50, default='google_translate', help_text="API de traducción preferida")
    # --- FIN DEL CAMPO AÑADIDO ---

    daily_messages_count = models.IntegerField(default=0, help_text="Mensajes enviados hoy")
    last_message_date = models.DateField(default=timezone.now)

    # 2. Límites de IA
    daily_ai_requests_count = models.IntegerField(default=0, help_text="Peticiones a la IA hoy")
    last_ai_request_date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Perfil de {self.user.username} ({self.subscription_plan})"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Crea un perfil automáticamente cuando se crea un nuevo usuario.
    """
    if created:
        Profile.objects.create(user=instance)


class Folder(models.Model):
    """Modelo para organizar documentos en carpetas."""
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subfolders')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Evita carpetas con el mismo nombre dentro del mismo directorio padre para un usuario
        unique_together = ('owner', 'name', 'parent')

    def __str__(self):
        return f"Carpeta '{self.name}' de {self.owner.username}"


class Document(models.Model):
    """Modelo para representar un archivo subido."""
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='documents')
    folder = models.ForeignKey(
        Folder, on_delete=models.SET_NULL, related_name='documents', null=True, blank=True)
    file = models.FileField(upload_to=user_directory_path)
    # UC-12: Campo para la vista previa
    preview = models.ImageField(
        upload_to=user_preview_directory_path, null=True, blank=True)
    # UC-15: Campo para el contenido extraído para búsqueda
    extracted_content = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(
        'Tag', blank=True, related_name='documents')


    def __str__(self):
        return f"Documento '{self.file.name}' de {self.owner.username}"


class Tag(models.Model):
    """Modelo para etiquetar documentos."""
    name = models.CharField(max_length=50)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='tags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('owner', 'name')

    def __str__(self):
        return self.name


class DocumentPermission(models.Model):
    """Modelo para gestionar los permisos de un documento compartido."""
    PERMISSION_CHOICES = [
        ('view', 'Ver'),
        ('edit', 'Editar'),
    ]

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='permissions')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='document_permissions')
    permission_level = models.CharField(
        max_length=10, choices=PERMISSION_CHOICES, default='view')

    class Meta:
        # Un usuario solo puede tener un tipo de permiso por documento
        unique_together = ('document', 'user')

    def __str__(self):
        return f"Permiso de '{self.permission_level}' para {self.user.username} en {self.document.file.name}"


# --- NUEVO MODELO AÑADIDO PARA UC-20 ---
class TranslationHistory(models.Model):
    """
    Almacena un registro de cada traducción realizada.
    """
    original_document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name='translations')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='translation_history')
    source_language = models.CharField(
        max_length=10, help_text="Idioma de origen (ej: 'es')")
    target_language = models.CharField(
        max_length=10, help_text="Idioma de destino (ej: 'en')")
    translated_content = models.TextField(
        blank=True, help_text="Contenido del documento traducido.")
    translated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-translated_at'] # Muestra los más recientes primero

    def __str__(self):
        return f"Traducción de {self.original_document.file.name} a {self.target_language} por {self.user.username}"
