from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Claim, ClaimImage, ClaimHistory
from sales.models import Order, OrderItem
from products.models import Product
from products.serializers import ProductSerializer
from api.serializers import UserSerializer


class ClaimImageSerializer(serializers.ModelSerializer):
    """
    Serializer para imágenes de evidencia de reclamos
    """
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClaimImage
        fields = ['id', 'image', 'image_url', 'description', 'uploaded_at']
        read_only_fields = ['uploaded_at']
    
    def get_image_url(self, obj):
        """Devuelve la URL completa de la imagen"""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def validate_image(self, value):
        """Validar tamaño de imagen (máx 5MB)"""
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "La imagen no puede ser mayor a 5MB."
            )
        return value


class ClaimHistorySerializer(serializers.ModelSerializer):
    """
    Serializer para el historial de cambios de un reclamo
    """
    user = UserSerializer(read_only=True)
    old_status_display = serializers.CharField(
        source='get_old_status_display',
        read_only=True
    )
    new_status_display = serializers.CharField(
        source='get_new_status_display',
        read_only=True
    )
    
    class Meta:
        model = ClaimHistory
        fields = [
            'id',
            'user',
            'action',
            'old_status',
            'old_status_display',
            'new_status',
            'new_status_display',
            'notes',
            'timestamp'
        ]
        read_only_fields = ['timestamp']


class ClaimListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listado de reclamos
    Usado en vistas de lista para optimizar performance
    """
    customer = UserSerializer(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    damage_type_display = serializers.CharField(source='get_damage_type_display', read_only=True)
    images_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Claim
        fields = [
            'id',
            'ticket_number',
            'customer',
            'product_name',
            'title',
            'damage_type',
            'damage_type_display',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'images_count',
            'created_at',
            'days_open'
        ]
    
    def get_images_count(self, obj):
        """Retorna el número de imágenes del reclamo"""
        return obj.images.count()


class ClaimDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para detalle de reclamo
    Incluye toda la información y relaciones
    """
    customer = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    images = ClaimImageSerializer(many=True, read_only=True)
    history = ClaimHistorySerializer(many=True, read_only=True)
    
    # Displays para choices
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    damage_type_display = serializers.CharField(source='get_damage_type_display', read_only=True)
    resolution_type_display = serializers.CharField(source='get_resolution_type_display', read_only=True)
    
    # Información de la orden
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_total = serializers.DecimalField(
        source='order.total_price',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    
    class Meta:
        model = Claim
        fields = [
            'id',
            'ticket_number',
            'customer',
            'order_id',
            'order_total',
            'product',
            'order_item',
            'title',
            'description',
            'damage_type',
            'damage_type_display',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'resolution_type',
            'resolution_type_display',
            'resolution_notes',
            'admin_response',
            'internal_notes',
            'assigned_to',
            'customer_rating',
            'customer_feedback',
            'images',
            'history',
            'created_at',
            'updated_at',
            'resolved_at',
            'closed_at',
            'is_resolved',
            'days_open'
        ]
        read_only_fields = [
            'ticket_number',
            'customer',
            'created_at',
            'updated_at',
            'resolved_at',
            'closed_at',
            'is_resolved',
            'days_open'
        ]


class ClaimCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear nuevos reclamos (usado por clientes)
    Maneja la carga de múltiples imágenes
    """
    # Campo para recibir múltiples imágenes
    images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False),
        write_only=True,
        required=False,
        help_text="Lista de imágenes de evidencia del daño"
    )
    
    # Campos para mostrar en la respuesta
    product = ProductSerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    
    # IDs para crear la relación
    product_id = serializers.IntegerField(write_only=True)
    order_id = serializers.IntegerField(write_only=True)
    order_item_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Claim
        fields = [
            'id',
            'ticket_number',
            'customer',
            'order_id',
            'product_id',
            'product',
            'order_item_id',
            'title',
            'description',
            'damage_type',
            'priority',
            'images',
            'created_at'
        ]
        read_only_fields = ['ticket_number', 'customer', 'created_at']
    
    def validate_product_id(self, value):
        """Validar que el producto exista"""
        try:
            Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("El producto no existe.")
        return value
    
    def validate_order_id(self, value):
        """Validar que la orden exista"""
        try:
            Order.objects.get(id=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("La orden no existe.")
        return value
    
    def validate(self, data):
        """
        Validaciones a nivel de objeto completo
        """
        # Obtener el usuario del contexto
        user = self.context['request'].user
        
        # Validar que la orden pertenezca al usuario
        try:
            order = Order.objects.get(id=data['order_id'])
        except Order.DoesNotExist:
            raise serializers.ValidationError({
                'order_id': "La orden no existe."
            })
        
        if order.customer != user:
            raise serializers.ValidationError({
                'order_id': "No puedes crear un reclamo sobre una orden que no te pertenece."
            })
        
        # Validar que la orden esté completada
        if order.status != Order.OrderStatus.COMPLETED:
            raise serializers.ValidationError({
                'order_id': "Solo puedes crear reclamos sobre órdenes completadas."
            })
        
        # Validar que el producto pertenezca a la orden
        try:
            product = Product.objects.get(id=data['product_id'])
        except Product.DoesNotExist:
            raise serializers.ValidationError({
                'product_id': "El producto no existe."
            })
        
        if not order.items.filter(product=product).exists():
            raise serializers.ValidationError({
                'product_id': "El producto no pertenece a la orden seleccionada."
            })
        
        # Si se especifica order_item_id, validar que pertenezca a la orden y al producto
        if 'order_item_id' in data and data['order_item_id']:
            try:
                order_item = OrderItem.objects.get(id=data['order_item_id'])
                if order_item.order != order or order_item.product != product:
                    raise serializers.ValidationError({
                        'order_item_id': "El item de la orden no corresponde a la orden y producto especificados."
                    })
            except OrderItem.DoesNotExist:
                raise serializers.ValidationError({
                    'order_item_id': "El item de la orden no existe."
                })
        
        # Validar que el título no esté vacío
        if not data.get('title', '').strip():
            raise serializers.ValidationError({
                'title': "El título no puede estar vacío."
            })
        
        # Validar que la descripción no esté vacía
        if not data.get('description', '').strip():
            raise serializers.ValidationError({
                'description': "La descripción no puede estar vacía."
            })
        
        return data
    
    def create(self, validated_data):
        """
        Crear el reclamo y sus imágenes
        """
        # Extraer las imágenes del validated_data
        images_data = validated_data.pop('images', [])
        
        # Extraer los IDs y obtener los objetos
        product_id = validated_data.pop('product_id')
        order_id = validated_data.pop('order_id')
        order_item_id = validated_data.pop('order_item_id', None)
        
        # Obtener los objetos
        product = Product.objects.get(id=product_id)
        order = Order.objects.get(id=order_id)
        order_item = OrderItem.objects.get(id=order_item_id) if order_item_id else None
        
        # Crear el reclamo
        claim = Claim.objects.create(
            customer=self.context['request'].user,
            order=order,
            product=product,
            order_item=order_item,
            **validated_data
        )
        
        # Crear las imágenes
        for image in images_data:
            ClaimImage.objects.create(
                claim=claim,
                image=image
            )
        
        return claim


class ClaimUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar reclamos (usado por administradores)
    """
    assigned_to_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Claim
        fields = [
            'status',
            'priority',
            'resolution_type',
            'resolution_notes',
            'admin_response',
            'internal_notes',
            'assigned_to_id'
        ]
    
    def validate_assigned_to_id(self, value):
        """Validar que el usuario asignado exista y sea admin"""
        if value is not None:
            try:
                user = User.objects.get(id=value)
                if not user.is_staff:
                    raise serializers.ValidationError(
                        "Solo se puede asignar a usuarios administradores."
                    )
            except User.DoesNotExist:
                raise serializers.ValidationError("El usuario no existe.")
        return value
    
    def update(self, instance, validated_data):
        """
        Actualizar el reclamo y registrar en el historial
        """
        # Guardar estado anterior para el historial
        old_status = instance.status
        
        # Guardar assigned_to anterior para las señales
        old_assigned_to = instance.assigned_to
        
        # Manejar assigned_to_id
        assigned_to_id = validated_data.pop('assigned_to_id', None)
        if assigned_to_id is not None:
            new_assigned_to = User.objects.get(id=assigned_to_id)
            instance.assigned_to = new_assigned_to
            # Guardar en el instance para la señal
            instance._old_assigned_to = old_assigned_to
        elif 'assigned_to_id' in self.initial_data and self.initial_data['assigned_to_id'] is None:
            instance.assigned_to = None
            instance._old_assigned_to = old_assigned_to
        
        # Actualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Registrar en el historial si cambió el estado
        if old_status != instance.status:
            # Obtener display names de los estados
            old_status_display = dict(Claim.ClaimStatus.choices).get(old_status, old_status)
            new_status_display = instance.get_status_display()
            
            ClaimHistory.objects.create(
                claim=instance,
                user=self.context['request'].user,
                action=f"Cambio de estado por administrador",
                old_status=old_status,
                new_status=instance.status,
                notes=f"Estado cambiado de {old_status_display} a {new_status_display}"
            )
        
        return instance


class ClaimCustomerFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializer para que el cliente califique y dé feedback sobre la resolución
    """
    class Meta:
        model = Claim
        fields = ['customer_rating', 'customer_feedback']
    
    def validate_customer_rating(self, value):
        """Validar que la calificación esté entre 1 y 5"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError(
                "La calificación debe estar entre 1 y 5."
            )
        return value
    
    def validate(self, data):
        """Validar que el reclamo esté resuelto antes de calificar"""
        claim = self.instance
        if not claim.is_resolved:
            raise serializers.ValidationError(
                "Solo puedes calificar reclamos que estén resueltos o cerrados."
            )
        return data
    
    def update(self, instance, validated_data):
        """Actualizar feedback del cliente"""
        instance.customer_rating = validated_data.get('customer_rating', instance.customer_rating)
        instance.customer_feedback = validated_data.get('customer_feedback', instance.customer_feedback)
        instance.save()
        
        # Registrar en el historial
        ClaimHistory.objects.create(
            claim=instance,
            user=self.context['request'].user,
            action="Cliente proporcionó feedback",
            notes=f"Calificación: {instance.customer_rating}/5"
        )
        
        return instance
