"""
Filtros para el sistema de reclamaciones
"""
import django_filters
from .models import Claim


class ClaimFilter(django_filters.FilterSet):
    """
    Filtros para búsqueda y filtrado de reclamos
    """
    
    # Filtros por campos exactos
    status = django_filters.ChoiceFilter(choices=Claim.ClaimStatus.choices)
    priority = django_filters.ChoiceFilter(choices=Claim.Priority.choices)
    damage_type = django_filters.ChoiceFilter(choices=Claim.DamageType.choices)
    resolution_type = django_filters.ChoiceFilter(choices=Claim.Resolution.choices)
    
    # Filtros por rango de fechas
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Creado después de'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Creado antes de'
    )
    
    # Filtros de búsqueda
    ticket_number = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Número de ticket'
    )
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Título'
    )
    description = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Descripción'
    )
    
    # Filtros por relaciones
    customer_username = django_filters.CharFilter(
        field_name='customer__username',
        lookup_expr='icontains',
        label='Usuario del cliente'
    )
    product_name = django_filters.CharFilter(
        field_name='product__name',
        lookup_expr='icontains',
        label='Nombre del producto'
    )
    assigned_to = django_filters.NumberFilter(
        field_name='assigned_to__id',
        label='Asignado a (ID de usuario)'
    )
    
    # Filtros booleanos
    is_resolved = django_filters.BooleanFilter(
        method='filter_is_resolved',
        label='Está resuelto'
    )
    has_rating = django_filters.BooleanFilter(
        method='filter_has_rating',
        label='Tiene calificación'
    )
    
    # Filtro por días abiertos
    days_open_min = django_filters.NumberFilter(
        method='filter_days_open_min',
        label='Días abiertos (mínimo)'
    )
    days_open_max = django_filters.NumberFilter(
        method='filter_days_open_max',
        label='Días abiertos (máximo)'
    )
    
    class Meta:
        model = Claim
        fields = [
            'status',
            'priority',
            'damage_type',
            'resolution_type',
            'ticket_number',
            'title',
            'customer_username',
            'product_name',
            'assigned_to'
        ]
    
    def filter_is_resolved(self, queryset, name, value):
        """Filtrar por reclamos resueltos o no"""
        if value:
            return queryset.filter(
                status__in=[Claim.ClaimStatus.RESOLVED, Claim.ClaimStatus.CLOSED]
            )
        else:
            return queryset.exclude(
                status__in=[Claim.ClaimStatus.RESOLVED, Claim.ClaimStatus.CLOSED]
            )
    
    def filter_has_rating(self, queryset, name, value):
        """Filtrar por reclamos con o sin calificación"""
        if value:
            return queryset.filter(customer_rating__isnull=False)
        else:
            return queryset.filter(customer_rating__isnull=True)
    
    def filter_days_open_min(self, queryset, name, value):
        """Filtrar por días mínimos abiertos"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=value)
        return queryset.filter(created_at__lte=cutoff_date)
    
    def filter_days_open_max(self, queryset, name, value):
        """Filtrar por días máximos abiertos"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=value)
        return queryset.filter(created_at__gte=cutoff_date)
