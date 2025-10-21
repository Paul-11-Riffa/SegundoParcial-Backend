from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from .filters import ProductFilter
from api.permissions import IsAdminUser # Reutilizamos el permiso de administrador que ya creamos

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite VER categorías (solo lectura para todos).
    Para crear/editar/eliminar, usar el admin de Django.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
    # ✅ PERMISOS: Acceso público total para lectura
    permission_classes = [permissions.AllowAny]
    
    # ✅ Sin autenticación requerida
    authentication_classes = []
    
    # ✅ Cache de 5 minutos para reducir carga
    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint que permite VER productos (solo lectura para todos).
    Para crear/editar/eliminar productos, usar el admin de Django.
    
    Incluye filtros avanzados por categoría, precio, stock y búsqueda.
    
    Ejemplos de uso:
    - /api/shop/products/?name=laptop (buscar por nombre)
    - /api/shop/products/?category_slug=electronics (filtrar por categoría)
    - /api/shop/products/?price_min=100&price_max=500 (rango de precio)
    - /api/shop/products/?in_stock=true (solo productos disponibles)
    - /api/shop/products/?ordering=-price (ordenar por precio descendente)
    """
    # ✅ OPTIMIZADO: select_related para traer la categoría en una sola consulta
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'created_at', 'name', 'stock']
    ordering = ['-created_at']  # Orden por defecto
    
    # ✅ PERMISOS: Acceso público total para lectura
    permission_classes = [permissions.AllowAny]
    
    # ✅ Sin autenticación requerida
    authentication_classes = []
    
    # ✅ Cache de 2 minutos para reducir carga (menos que categorías porque cambian más)
    @method_decorator(cache_page(60 * 2))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
