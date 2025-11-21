from rest_framework import permissions
from .models import DocumentPermission


class IsOwnerOrHasPermission(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso solo a los propietarios
    o a usuarios con permisos explícitos sobre el documento.
    """

    def has_object_permission(self, request, view, obj):
        # Los permisos de lectura (GET, HEAD, OPTIONS) son permitidos
        # si el usuario es el propietario o tiene cualquier permiso sobre el documento.
        if request.method in permissions.SAFE_METHODS:
            return obj.owner == request.user or \
                DocumentPermission.objects.filter(
                    document=obj, user=request.user).exists()

        # Los permisos de escritura (PUT, PATCH, DELETE) solo son permitidos
        # si el usuario es el propietario o tiene permiso de 'edición'.
        return obj.owner == request.user or \
            DocumentPermission.objects.filter(
                document=obj,
                user=request.user,
                permission_level='edit'
            ).exists()
