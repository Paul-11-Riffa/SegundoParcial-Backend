import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    """
    Filtro para las Órdenes.
    Permite filtrar por rango de fechas usando 'created_at' y por cliente.
    """
    # Filtro para la fecha de inicio (mayor o igual que)
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    # Filtro para la fecha de fin (menor o igual que)
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    # Filtro por cliente (ID del usuario)
    customer = django_filters.NumberFilter(field_name='customer__id')
    # Filtro por nombre de cliente (búsqueda parcial insensible a mayúsculas)
    customer_name = django_filters.CharFilter(field_name='customer__username', lookup_expr='icontains')

    class Meta:
        model = Order
        fields = ['start_date', 'end_date', 'customer', 'customer_name']