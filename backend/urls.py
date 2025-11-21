from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from api.views import CustomVerifyEmailView, CustomRegisterView
from django.shortcuts import redirect
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/register/', CustomRegisterView.as_view(), name='custom_register'),
    re_path(r'^api/auth/register/account-confirm-email/(?P<key>[-:\w]+)/$',
            CustomVerifyEmailView.as_view(), name='account_confirm_email'),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/register/', include('dj_rest_auth.registration.urls')),
    
    re_path(r'^password-reset/confirm/(?P<uidb64>.*)/(?P<token>.*)/$', 
        lambda request, uidb64, token: redirect(f'{os.environ.get("FRONTEND_URL", "http://localhost:5173")}/password-reset/confirm?uid={uidb64}&token={token}'), 
        name='password_reset_confirm'),
]

# Servir archivos media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
