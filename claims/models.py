from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from sales.models import Order, OrderItem
from products.models import Product


class Claim(models.Model):
    """
    Modelo para gestionar reclamos de clientes sobre productos defectuosos
    """
    class ClaimStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        IN_REVIEW = 'IN_REVIEW', 'En Revisión'
        REQUIRES_INFO = 'REQUIRES_INFO', 'Requiere Información'
        APPROVED = 'APPROVED', 'Aprobado'
        REJECTED = 'REJECTED', 'Rechazado'
        RESOLVED = 'RESOLVED', 'Resuelto'
        CLOSED = 'CLOSED', 'Cerrado'

    class DamageType(models.TextChoices):
        FACTORY_DEFECT = 'FACTORY_DEFECT', 'Defecto de Fábrica'
        SHIPPING_DAMAGE = 'SHIPPING_DAMAGE', 'Daño en Envío'
        WRONG_PRODUCT = 'WRONG_PRODUCT', 'Producto Incorrecto'
        MISSING_PARTS = 'MISSING_PARTS', 'Piezas Faltantes'
        NOT_AS_DESCRIBED = 'NOT_AS_DESCRIBED', 'No Coincide con Descripción'
        OTHER = 'OTHER', 'Otro'

    class Resolution(models.TextChoices):
        FULL_REFUND = 'FULL_REFUND', 'Reembolso Total'
        PARTIAL_REFUND = 'PARTIAL_REFUND', 'Reembolso Parcial'
        REPLACEMENT = 'REPLACEMENT', 'Reemplazo del Producto'
        REPAIR = 'REPAIR', 'Reparación'
        NONE = 'NONE', 'Sin Resolución'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Baja'
        MEDIUM = 'MEDIUM', 'Media'
        HIGH = 'HIGH', 'Alta'
        URGENT = 'URGENT', 'Urgente'

    # Relaciones
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='claims',
        help_text="Cliente que realiza el reclamo"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='claims',
        help_text="Orden asociada al reclamo"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='claims',
        help_text="Producto sobre el que se reclama"
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.PROTECT,
        related_name='claims',
        null=True,
        blank=True,
        help_text="Item específico de la orden"
    )

    # Información del reclamo
    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Número único de ticket generado automáticamente"
    )
    title = models.CharField(
        max_length=255,
        help_text="Título breve del reclamo"
    )
    description = models.TextField(
        help_text="Descripción detallada del problema"
    )
    damage_type = models.CharField(
        max_length=50,
        choices=DamageType.choices,
        default=DamageType.OTHER
    )

    # Estados y seguimiento
    status = models.CharField(
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.PENDING
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    # Resolución
    resolution_type = models.CharField(
        max_length=50,
        choices=Resolution.choices,
        default=Resolution.NONE,
        blank=True
    )
    resolution_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notas sobre la resolución del reclamo"
    )
    admin_response = models.TextField(
        blank=True,
        null=True,
        help_text="Respuesta del administrador al cliente"
    )
    internal_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notas internas (no visibles para el cliente)"
    )

    # Usuario que gestiona el reclamo
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_claims',
        help_text="Administrador asignado al reclamo"
    )

    # Calificación del servicio (1-5 estrellas)
    customer_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Calificación del cliente sobre la resolución (1-5)"
    )
    customer_feedback = models.TextField(
        blank=True,
        null=True,
        help_text="Comentarios del cliente sobre la resolución"
    )

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha en que se resolvió el reclamo"
    )
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha en que se cerró el reclamo"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Reclamo'
        verbose_name_plural = 'Reclamos'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['ticket_number']),
        ]

    def __str__(self):
        return f"Reclamo #{self.ticket_number} - {self.customer.username} - {self.status}"

    def save(self, *args, **kwargs):
        # Generar número de ticket si no existe
        if not self.ticket_number:
            self.ticket_number = self._generate_ticket_number()
        
        # Auto-calcular prioridad basada en tipo de daño
        if not self.pk:  # Solo al crear
            if self.damage_type in [self.DamageType.FACTORY_DEFECT, self.DamageType.WRONG_PRODUCT]:
                self.priority = self.Priority.HIGH
        
        super().save(*args, **kwargs)

    def _generate_ticket_number(self):
        """Genera un número único de ticket"""
        from django.utils import timezone
        import random
        
        date_str = timezone.now().strftime('%Y%m%d')
        random_num = random.randint(1000, 9999)
        
        # Formato: CLM-YYYYMMDD-XXXX (ej: CLM-20251111-1234)
        ticket = f"CLM-{date_str}-{random_num}"
        
        # Verificar que sea único
        while Claim.objects.filter(ticket_number=ticket).exists():
            random_num = random.randint(1000, 9999)
            ticket = f"CLM-{date_str}-{random_num}"
        
        return ticket

    def clean(self):
        """Validaciones personalizadas"""
        super().clean()
        
        # Validar que el producto pertenezca a la orden
        if self.order and self.product:
            if not self.order.items.filter(product=self.product).exists():
                raise ValidationError({
                    'product': 'El producto no pertenece a la orden seleccionada.'
                })
        
        # Validar que el cliente sea el dueño de la orden
        if self.order and self.customer:
            if self.order.customer != self.customer:
                raise ValidationError({
                    'order': 'No puedes crear un reclamo sobre una orden que no te pertenece.'
                })
        
        # Validar que la orden esté completada
        if self.order and self.order.status != Order.OrderStatus.COMPLETED:
            raise ValidationError({
                'order': 'Solo puedes crear reclamos sobre órdenes completadas.'
            })
        
        # Validar calificación (1-5)
        if self.customer_rating is not None:
            if self.customer_rating < 1 or self.customer_rating > 5:
                raise ValidationError({
                    'customer_rating': 'La calificación debe estar entre 1 y 5.'
                })

    @property
    def is_resolved(self):
        """Verifica si el reclamo está resuelto"""
        return self.status in [self.ClaimStatus.RESOLVED, self.ClaimStatus.CLOSED]

    @property
    def days_open(self):
        """Calcula cuántos días lleva abierto el reclamo"""
        from django.utils import timezone
        if self.resolved_at:
            return (self.resolved_at - self.created_at).days
        return (timezone.now() - self.created_at).days


class ClaimImage(models.Model):
    """
    Modelo para almacenar múltiples imágenes de evidencia de un reclamo
    """
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='claims/%Y/%m/%d/',
        help_text="Imagen de evidencia del daño"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Descripción de la imagen"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = 'Imagen de Reclamo'
        verbose_name_plural = 'Imágenes de Reclamos'

    def __str__(self):
        return f"Imagen para reclamo #{self.claim.ticket_number}"

    def clean(self):
        """Validar que la imagen no sea muy grande"""
        if self.image and self.image.size > 5 * 1024 * 1024:  # 5MB
            raise ValidationError({
                'image': 'La imagen no puede ser mayor a 5MB.'
            })


class ClaimHistory(models.Model):
    """
    Modelo para registrar el historial de cambios en un reclamo (auditoría)
    """
    claim = models.ForeignKey(
        Claim,
        on_delete=models.CASCADE,
        related_name='history'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Usuario que realizó el cambio"
    )
    action = models.CharField(
        max_length=255,
        help_text="Descripción de la acción realizada"
    )
    old_status = models.CharField(
        max_length=20,
        choices=Claim.ClaimStatus.choices,
        null=True,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Claim.ClaimStatus.choices,
        null=True,
        blank=True
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notas adicionales sobre el cambio"
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Historial de Reclamo'
        verbose_name_plural = 'Historial de Reclamos'

    def __str__(self):
        return f"{self.claim.ticket_number} - {self.action} - {self.timestamp}"
