from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from api.models import Profile, Folder, Document, Tag, DocumentPermission

# --- Personalización del Admin de Usuarios ---

# Primero, desregistramos el admin de User por defecto
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    """
    Personalización del panel de admin para el modelo User.
    """
    # Añadimos 'id' al principio de la lista de campos a mostrar
    list_display = ('id', 'username', 'email', 'first_name',
                    'last_name', 'is_staff', 'date_joined')
    list_display_links = ('id', 'username')


# --- Registro de los otros modelos de la app 'api' ---

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'language_preference', 'subscription_plan')
    search_fields = ('user__username',)


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'parent', 'created_at')
    list_filter = ('owner',)
    search_fields = ('name', 'owner__username')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'owner', 'folder', 'uploaded_at')
    list_filter = ('owner', 'folder', 'tags')
    search_fields = ('file', 'owner__username')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner')
    search_fields = ('name', 'owner__username')


@admin.register(DocumentPermission)
class DocumentPermissionAdmin(admin.ModelAdmin):
    list_display = ('document', 'user', 'permission_level')
    search_fields = ('document__file', 'user__username')
