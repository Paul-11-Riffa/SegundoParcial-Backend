# api/urls.py
from django.urls import path
from .views import register_view, login_view, LogoutView, UserProfileView

urlpatterns = [

    # Endpoint para el registro
    path('register/', register_view, name='register'),

    # Endpoint para el login
    path('login/', login_view, name='login'),

    # Endpoint para el logout
    path('logout/', LogoutView.as_view(), name='logout'),

    # Endpoint para ver/gestionar el perfil
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]