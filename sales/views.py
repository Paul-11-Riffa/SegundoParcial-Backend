from rest_framework import views, response, status, permissions
from .models import Order, OrderItem, Product
from .serializers import OrderSerializer

class CartView(views.APIView):
    """
    Vista para gestionar el carrito de compras del usuario.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Obtiene o crea el carrito de compras actual (en estado 'PENDING') del usuario.
        """
        # Busca una orden 'PENDING' para el usuario, o la crea si no existe.
        cart, created = Order.objects.get_or_create(customer=request.user, status='PENDING')
        serializer = OrderSerializer(cart)
        return response.Response(serializer.data)

    def post(self, request):
        """
        Añade un producto al carrito.
        Espera recibir: { "product_id": <id>, "quantity": <cantidad> }
        """
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        if not product_id:
            return response.Response({'error': 'Product ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return response.Response({'error': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart, _ = Order.objects.get_or_create(customer=request.user, status='PENDING')

        # Si el producto ya está en el carrito, actualiza la cantidad. Si no, lo crea.
        order_item, created = OrderItem.objects.get_or_create(order=cart, product=product, defaults={'price': product.price})

        if not created:
            order_item.quantity += quantity
        else:
            order_item.quantity = quantity

        # Valida que haya suficiente stock
        if order_item.quantity > product.stock:
            return response.Response({'error': 'Not enough stock available.'}, status=status.HTTP_400_BAD_REQUEST)

        order_item.save()

        # Recalcula el precio total del carrito
        cart.total_price = sum(item.price * item.quantity for item in cart.items.all())
        cart.save()

        serializer = OrderSerializer(cart)
        return response.Response(serializer.data, status=status.HTTP_200_OK)


class CartItemView(views.APIView):
    """
    Vista para actualizar o eliminar un artículo específico del carrito.
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, item_id):
        """
        Actualiza la cantidad de un artículo en el carrito.
        Espera recibir: { "quantity": <nueva_cantidad> }
        """
        quantity = int(request.data.get('quantity', 1))

        try:
            order_item = OrderItem.objects.get(id=item_id, order__customer=request.user)
        except OrderItem.DoesNotExist:
            return response.Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

        if quantity > 0:
            if quantity > order_item.product.stock:
                return response.Response({'error': 'Not enough stock available.'}, status=status.HTTP_400_BAD_REQUEST)
            order_item.quantity = quantity
            order_item.save()
        else: # Si la cantidad es 0, elimina el artículo
            order_item.delete()

        # Recalcula el precio total
        cart = order_item.order
        cart.total_price = sum(item.price * item.quantity for item in cart.items.all())
        cart.save()

        serializer = OrderSerializer(cart)
        return response.Response(serializer.data)

    def delete(self, request, item_id):
        """
        Elimina un artículo del carrito.
        """
        try:
            order_item = OrderItem.objects.get(id=item_id, order__customer=request.user)
        except OrderItem.DoesNotExist:
            return response.Response({'error': 'Cart item not found.'}, status=status.HTTP_404_NOT_FOUND)

        cart = order_item.order
        order_item.delete()

        # Recalcula el precio total
        cart.total_price = sum(item.price * item.quantity for item in cart.items.all())
        cart.save()

        serializer = OrderSerializer(cart)
        return response.Response(serializer.data)