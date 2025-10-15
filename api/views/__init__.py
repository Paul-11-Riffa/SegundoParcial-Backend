# api/views/__init__.py
from .auth import register_view, login_view, LogoutView, UserProfileView
from .user import UserListView, UserDetailView