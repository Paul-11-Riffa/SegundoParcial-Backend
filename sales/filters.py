import django_filters
from .models import Order

class OrderFilter(django_filters.FilterSet):
    """
    Filtro para las Órdenes.
    Permite filtrar por rango de fechas usando 'created_at'.
    """
    # Filtro para la fecha de inicio (mayor o igual que)
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    # Filtro para la fecha de fin (menor o igual que)
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Order
        # Definimos los campos por los que se puede filtrar directamente
        # (En este caso, añadimos start_date y end_date, pero podrías añadir 'customer' si quisieras filtrar por ID de cliente)
        fields = ['start_date', 'end_date']