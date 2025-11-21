from rest_framework import serializers
from .models import Profile, Folder, Document, Tag, DocumentPermission, TranslationHistory


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo de Perfil.
    """
    class Meta:
        model = Profile
        fields = ['language_preference', 'subscription_plan', 'preferred_translation_api']

class RecursiveFolderSerializer(serializers.Serializer):
    """Un serializer simple para mostrar hijos de forma recursiva."""
    def to_representation(self, value):
        # Llama al serializer principal (FolderSerializer) para renderizar el hijo
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class FolderSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Folder."""
    owner = serializers.ReadOnlyField(source='owner.username')
    
    # ¡ESTA ES LA LÍNEA CLAVE!
    # Le dice a Django que use el serializer recursivo para el campo 'subfolders'
    subfolders = RecursiveFolderSerializer(many=True, read_only=True)

    class Meta:
        model = Folder
        # ¡AÑADIR 'subfolders' A LOS CAMPOS!
        fields = ['id', 'name', 'owner', 'parent', 'created_at', 'subfolders']

class DocumentSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Document."""
    owner = serializers.ReadOnlyField(source='owner.username')
    file_url = serializers.SerializerMethodField(read_only=True)
    preview_url = serializers.SerializerMethodField(read_only=True)
    permission_level = serializers.SerializerMethodField()
    is_shared = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'owner', 'folder', 'file', 'file_url',
                  'preview_url', 'uploaded_at', 'tags',
                  'extracted_content', 
                  'permission_level', 
                  'is_shared','modified_at']
        read_only_fields = [
            'uploaded_at', 'owner', 'file_url', 
            'preview_url', 'permission_level', 'is_shared','modified_at'
        ]

    # --- INICIO DE LAS FUNCIONES QUE FALTABAN ---
    def get_file_url(self, obj):
        request = self.context.get('request', None)
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_preview_url(self, obj):
        request = self.context.get('request', None)
        if request and obj.preview:
            return request.build_absolute_uri(obj.preview.url)
        return None
    # --- FIN DE LAS FUNCIONES QUE FALTABAN ---

    def get_permission_level(self, obj):
        request = self.context.get('request', None)
        if not request or not request.user.is_authenticated:
            return None
        if obj.owner == request.user:
            return "PROPIETARIO"
        try:
            permission = DocumentPermission.objects.get(document=obj, user=request.user)
            if permission.permission_level == 'edit':
                return "EDITOR"
            else:
                return "LECTOR"
        except DocumentPermission.DoesNotExist:
            return None

    def get_is_shared(self, obj):
        """
        Comprueba si el propietario ha compartido este documento con alguien.
        """
        request = self.context.get('request', None)
        if not request or not request.user.is_authenticated:
            return False
        
        if obj.owner == request.user:
            return DocumentPermission.objects.filter(document=obj).exists()
        
        return False

class TagSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Tag."""
    class Meta:
        model = Tag
        fields = ['id', 'name']

class TranslationHistorySerializer(serializers.ModelSerializer):
    """
    UC-20: Serializer para el historial de traducciones.
    """
    # Usamos ReadOnlyField para mostrar información del usuario y documento sin permitir su modificación
    user = serializers.ReadOnlyField(source='user.username')
    original_document_name = serializers.ReadOnlyField(source='original_document.file.name')

    class Meta:
        model = TranslationHistory
        fields = [
            'id',
            'user',
            'original_document',
            'original_document_name',
            'source_language',
            'target_language',
            'translated_content',
            'translated_at'
        ]


class DocumentPermissionSerializer(serializers.ModelSerializer):
    """Serializer para gestionar los permisos de un documento."""
    # Hacemos que el campo 'user' sea de solo lectura por su ID para la entrada,
    # pero muestre el username en la salida.
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = DocumentPermission
        fields = ['id', 'user', 'user_id', 'permission_level']
