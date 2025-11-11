from rest_framework import serializers
from .models import Order, OrderItem
from products.serializers import ProductSerializer
from api.serializers import UserSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializador para los artículos dentro de una orden (carrito).
    """
    # Usamos un serializador anidado para mostrar la información completa del producto.
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializador para la Orden/Venta (el carrito de compras).
    """
    # 'items' será una lista de todos los artículos en el carrito.
    items = OrderItemSerializer(many=True, read_only=True)
    customer = UserSerializer(read_only=True)
    
    # Campos calculados
    total_items = serializers.SerializerMethodField()
    
    def get_total_items(self, obj):
        """Retorna la cantidad total de productos en el carrito"""
        return sum(item.quantity for item in obj.items.all())

    class Meta:
        model = Order
        fields = ['id', 'customer', 'status', 'total_price', 'total_items', 'created_at', 'items']
        read_only_fields = ['customer', 'status', 'total_price', 'created_at']