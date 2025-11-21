# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import test_endpoint, ProfileDetailView, FolderViewSet, DocumentViewSet, TagViewSet, TranslationHistoryViewSet, ai_assistant, upgrade_to_premium

# Creamos un router y registramos nuestros viewsets
router = DefaultRouter()
router.register(r'folders', FolderViewSet, basename='folder')
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'translation-history', TranslationHistoryViewSet, basename='translation-history')

urlpatterns = [
    path('test/', test_endpoint, name='test_endpoint'),
    path('profile/', ProfileDetailView.as_view(), name='profile-detail'),
    path('ai-assistant/', ai_assistant, name='ai-assistant'),
    path('upgrade-premium/', upgrade_to_premium, name='upgrade-premium'),
    # Las URLs para la API de documentos y carpetas son generadas por el router
    path('', include(router.urls)),
]
