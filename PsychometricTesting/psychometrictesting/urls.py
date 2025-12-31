# project/urls.py

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from authentication.views import OTPView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path('testing/', include(('testing.urls', 'testing'), namespace='testing')),
    path('payment/', include(('payment.urls', 'payment'), namespace='payment')),
    path('admin/', admin.site.urls),
    path('otp/', OTPView.as_view(), name='otp'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('blog/', include('blog.urls')),
    path('rating/', include('rating.urls')),
    path('reportgeneration/', include('reportgeneration.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

