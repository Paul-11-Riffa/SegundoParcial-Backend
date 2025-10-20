from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .filters import ProductFilter
from api.permissions import IsAdminUser # Reutilizamos el permiso de administrador que ya creamos

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar categorías.
    - Listar y ver es para cualquier usuario.
    - Crear, editar y eliminar es solo para administradores.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug' # Permite buscar categorías por 'slug' en la URL en lugar de por ID

    def get_permissions(self):
        """
        Asigna permisos basados en la acción.
        """
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()


class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint que permite ver o editar productos.
    - Listar y ver es para cualquier usuario.
    - Crear, editar y eliminar es solo para administradores.
    - Incluye filtros avanzados por categoría, precio, stock y búsqueda.
    
    Ejemplos de uso:
    - /api/products/?name=laptop (buscar por nombre)
    - /api/products/?category_slug=electronics (filtrar por categoría)
    - /api/products/?price_min=100&price_max=500 (rango de precio)
    - /api/products/?in_stock=true (solo productos disponibles)
    - /api/products/?ordering=-price (ordenar por precio descendente)
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name', 'stock']
    ordering = ['-created_at']  # Orden por defecto

    def get_permissions(self):
        """
        Asigna permisos basados en la acción.
        """
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()