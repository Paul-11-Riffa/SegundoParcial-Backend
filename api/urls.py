# api/urls.py
from django.urls import path
from .views import (
    register_view,
    login_view,
    LogoutView,
    UserProfileView,
    UserListView,
    UserDetailView
)

urlpatterns = [
    # --- Autenticación ---
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # --- Perfil de Usuario (para el usuario logueado) ---
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # --- Gestión de Usuarios (SOLO ADMINS) ---
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]