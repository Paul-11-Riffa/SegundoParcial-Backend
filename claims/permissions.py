"""
Permisos personalizados para el sistema de reclamaciones
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsClaimOwnerOrAdmin(BasePermission):
    """
    Permiso personalizado para permitir que:
    - Los clientes solo puedan ver y editar sus propios reclamos
    - Los administradores puedan ver y editar todos los reclamos
    """
    
    def has_permission(self, request, view):
        # El usuario debe estar autenticado
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Los administradores tienen acceso total
        if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return True
        
        # Los clientes solo pueden acceder a sus propios reclamos
        return obj.customer == request.user


class IsAdminOrReadOnly(BasePermission):
    """
    Permiso que permite lectura a todos los usuarios autenticados,
    pero solo los administradores pueden crear, editar o eliminar.
    """
    
    def has_permission(self, request, view):
        # Debe estar autenticado
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Permitir lectura a todos
        if request.method in SAFE_METHODS:
            return True
        
        # Escritura solo para admins
        return hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'


class IsAdminUser(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol de 'Admin'.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'


class IsCustomerUser(BasePermission):
    """
    Permite el acceso solo a usuarios con el rol de 'Cliente'.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return hasattr(request.user, 'profile') and request.user.profile.role == 'CLIENT'
