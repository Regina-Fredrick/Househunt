from django.urls import path
from . import api_views

urlpatterns = [
    path('csrf/', api_views.csrf_view, name='api_csrf'),
    path('login/', api_views.login_view, name='api_login'),
    path('logout/', api_views.logout_view, name='api_logout'),
    path('me/', api_views.current_user_view, name='api_current_user'),
    path('register/', api_views.register_view, name='api_register'),
    path('google-login/', api_views.google_login_view, name='api_google_login'),
]