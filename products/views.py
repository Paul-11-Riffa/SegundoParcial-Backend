from rest_framework import viewsets, permissions
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
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
    """
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer

    def get_permissions(self):
        """
        Asigna permisos basados en la acción.
        """
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [permissions.AllowAny]
        else:
            self.permission_classes = [permissions.IsAdminUser]
        return super().get_permissions()