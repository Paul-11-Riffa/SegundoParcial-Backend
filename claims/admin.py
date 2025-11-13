from django.contrib import admin
from .models import Claim, ClaimImage, ClaimHistory


class ClaimImageInline(admin.TabularInline):
    model = ClaimImage
    extra = 1
    fields = ('image', 'description', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


class ClaimHistoryInline(admin.TabularInline):
    model = ClaimHistory
    extra = 0
    fields = ('user', 'action', 'old_status', 'new_status', 'timestamp')
    readonly_fields = ('user', 'action', 'old_status', 'new_status', 'timestamp')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number', 
        'customer', 
        'product', 
        'damage_type',
        'status', 
        'priority',
        'created_at',
        'days_open'
    )
    list_filter = (
        'status', 
        'priority', 
        'damage_type', 
        'resolution_type',
        'created_at'
    )
    search_fields = (
        'ticket_number', 
        'customer__username', 
        'product__name',
        'title',
        'description'
    )
    readonly_fields = (
        'ticket_number', 
        'created_at', 
        'updated_at',
        'resolved_at',
        'closed_at',
        'days_open'
    )
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'ticket_number',
                'customer',
                'order',
                'product',
                'order_item'
            )
        }),
        ('Detalles del Reclamo', {
            'fields': (
                'title',
                'description',
                'damage_type',
                'status',
                'priority'
            )
        }),
        ('Gestión Administrativa', {
            'fields': (
                'assigned_to',
                'admin_response',
                'internal_notes'
            )
        }),
        ('Resolución', {
            'fields': (
                'resolution_type',
                'resolution_notes',
                'resolved_at',
                'closed_at'
            )
        }),
        ('Feedback del Cliente', {
            'fields': (
                'customer_rating',
                'customer_feedback'
            )
        }),
        ('Fechas', {
            'fields': (
                'created_at',
                'updated_at',
                'days_open'
            )
        }),
    )
    
    inlines = [ClaimImageInline, ClaimHistoryInline]
    
    def save_model(self, request, obj, form, change):
        """Registrar cambios en el historial"""
        if change:
            # Obtener el objeto original
            original = Claim.objects.get(pk=obj.pk)
            
            # Si cambió el estado, registrarlo
            if original.status != obj.status:
                ClaimHistory.objects.create(
                    claim=obj,
                    user=request.user,
                    action=f"Cambio de estado",
                    old_status=original.status,
                    new_status=obj.status,
                    notes=f"Estado cambiado de {original.get_status_display()} a {obj.get_status_display()}"
                )
        else:
            # Registro de creación
            super().save_model(request, obj, form, change)
            ClaimHistory.objects.create(
                claim=obj,
                user=request.user,
                action="Reclamo creado",
                new_status=obj.status
            )
            return
        
        super().save_model(request, obj, form, change)


@admin.register(ClaimImage)
class ClaimImageAdmin(admin.ModelAdmin):
    list_display = ('claim', 'description', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('claim__ticket_number', 'description')
    readonly_fields = ('uploaded_at',)


@admin.register(ClaimHistory)
class ClaimHistoryAdmin(admin.ModelAdmin):
    list_display = ('claim', 'user', 'action', 'old_status', 'new_status', 'timestamp')
    list_filter = ('timestamp', 'old_status', 'new_status')
    search_fields = ('claim__ticket_number', 'action', 'notes')
    readonly_fields = ('claim', 'user', 'action', 'old_status', 'new_status', 'timestamp')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
