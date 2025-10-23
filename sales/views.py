import django_filters
from rest_framework import views, response, status, permissions, generics
from .models import Order, OrderItem, Product
from .serializers import OrderSerializer
from django.conf import settings
import stripe
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
from .filters import OrderFilter
from datetime import datetime, timedelta
from django.utils import timezone
import re
from api.permissions import IsAdminUser  # Importar permiso personalizado
class CartView(views.APIView):
    """
    Vista para gestionar el carrito de compras del usuario.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Obtiene o crea el carrito de compras actual (en estado 'PENDING') del usuario.
        """
        # ✅ OPTIMIZADO: prefetch_related para traer items y productos en una consulta
        cart = Order.objects.filter(
            customer=request.user, 
            status='PENDING'
        ).prefetch_related('items__product__category').first()
        
        if not cart:
            cart = Order.objects.create(customer=request.user, status='PENDING', total_price=0.00)
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

class StripeCheckoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Crea una sesión de pago en Stripe con los artículos del carrito.
        """
        # Asigna la clave secreta de Stripe desde la configuración
        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            # 1. Obtiene el carrito del usuario
            cart = Order.objects.get(customer=request.user, status='PENDING')
            if not cart.items.exists():
                return response.Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Prepara la lista de productos para Stripe
            line_items = []
            for item in cart.items.all():
                line_items.append({
                    'price_data': {
                        'currency': 'usd', # Puedes cambiarlo a tu moneda local (ej. 'bob')
                        'product_data': {
                            'name': item.product.name,
                        },
                        'unit_amount': int(item.product.price * 100), # Stripe necesita el precio en centavos
                    },
                    'quantity': item.quantity,
                })

            # 3. Define las URLs de éxito y cancelación
            # (Estas son las páginas a las que Stripe redirigirá al usuario después del pago)
            frontend_base_url = "http://localhost:3000"
            success_url = f"{frontend_base_url}/order/success?session_id={{CHECKOUT_SESSION_ID}}"  # Pasamos el ID de sesión para verificación opcional
            cancel_url = f"{frontend_base_url}/order/cancel"

            # 4. Crea la sesión de checkout en Stripe
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                # Guarda el ID de nuestra orden en los metadatos de Stripe
                # ¡Esto es crucial para saber qué orden se pagó!
                metadata={
                    'order_id': cart.id,
                    'user_id': request.user.id
                }
            )

            # 5. IMPORTANTE: Cambia el estado del carrito a PROCESSING inmediatamente
            # Esto evita que el usuario vea el carrito mientras el pago está en proceso
            cart.status = 'PROCESSING'
            cart.save()

            # 6. Devuelve la URL de la sesión de pago al frontend
            return response.Response({'checkout_url': checkout_session.url})

        except Order.DoesNotExist:
            return response.Response({'error': 'You do not have an active cart.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StripeWebhookView(views.APIView):
    """
    Escucha los eventos de Stripe, específicamente cuando un pago es exitoso.
    """
    permission_classes = [permissions.AllowAny] # Debe ser accesible públicamente para Stripe

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        event = None

        try:
            # 1. Verifica que el evento realmente venga de Stripe
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            # Payload inválido
            return response.Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            # Firma inválida
            return response.Response(status=status.HTTP_400_BAD_REQUEST)

        # 2. Maneja el evento específico de "pago completado"
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']

            # Obtiene el ID de nuestra orden que guardamos en los metadatos
            order_id = session.get('metadata', {}).get('order_id')

            if order_id is None:
                return response.Response({'error': 'Missing order_id in Stripe metadata'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # 3. Encuentra la orden y actualiza su estado
                order = Order.objects.get(id=order_id, status='PROCESSING')
                order.status = 'COMPLETED'
                order.save()

                # 4. Reduce el stock de los productos vendidos
                for item in order.items.all():
                    product = item.product
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        product.save()
                    else:
                        # Manejar el caso de que no haya suficiente stock (raro, pero posible)
                        print(f"Alerta: Stock insuficiente para el producto {product.id} en la orden {order.id}")
                        # Aquí podrías enviar un email de alerta al administrador

            except Order.DoesNotExist:
                return response.Response({'error': f'Order with ID {order_id} not found or already processed.'}, status=status.HTTP_404_NOT_FOUND)

        # Si es otro tipo de evento, simplemente lo ignoramos por ahora
        else:
            print(f"Evento no manejado: {event['type']}")

        # 5. Responde a Stripe para confirmar que recibimos el evento
        return response.Response(status=status.HTTP_200_OK)

# --- VISTA PARA COMPLETAR LA ORDEN DEL USUARIO AUTENTICADO ---
class CompleteOrderView(views.APIView):
    """
    Endpoint para completar la orden pendiente del usuario autenticado.
    Se llama desde el frontend después de un pago exitoso en Stripe.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # 1. Buscar orden en PROCESSING (después del checkout en Stripe)
            cart = Order.objects.filter(customer=request.user, status='PROCESSING').first()
            
            if not cart:
                # Si no hay orden en PROCESSING, buscar en PENDING (por compatibilidad)
                cart = Order.objects.filter(customer=request.user, status='PENDING').first()
            
            if not cart:
                return response.Response({
                    'error': 'No order found to complete'
                }, status=status.HTTP_404_NOT_FOUND)

            # 2. Cambia el estado a COMPLETADO
            cart.status = 'COMPLETED'
            cart.save()

            # 3. Reduce el stock de los productos
            for item in cart.items.all():
                product = item.product
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                    product.save()
                else:
                    print(f"Alerta de Stock: Stock insuficiente para el producto {product.id}")

            # 4. ✅ CREAR NUEVO CARRITO VACÍO PARA EL USUARIO
            Order.objects.create(customer=request.user, status='PENDING', total_price=0.00)

            return response.Response({
                'success': True,
                'message': 'Order completed successfully',
                'order_id': cart.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return response.Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- VISTA DE PRUEBA PARA SIMULAR EL WEBHOOK MANUALMENTE ---
class ManualOrderCompletionView(views.APIView):
    """
    [SOLO PARA DESARROLLO]
    Endpoint para forzar la finalización de la orden pendiente de un usuario.
    Simula el comportamiento del webhook de Stripe.
    """
    permission_classes = [IsAdminUser] # Protegido para que solo un admin pueda usarlo

    def post(self, request):
        user_id = request.data.get('user_id')
        if not user_id:
            return response.Response({'error': 'user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. Encuentra la orden PENDIENTE del cliente especificado
            order = Order.objects.get(customer_id=user_id, status='PENDING')

            # 2. Cambia el estado a COMPLETADO
            order.status = 'COMPLETED'
            order.save()

            # 3. Reduce el stock de los productos
            for item in order.items.all():
                product = item.product
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                    product.save()
                else:
                    print(f"Alerta de Stock (Debug): Stock insuficiente para el producto {product.id}")

            return response.Response({'success': f'Order {order.id} for user {user_id} has been marked as COMPLETED.'}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return response.Response({'error': f'No pending order found for user {user_id}.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CompleteUserOrderView(views.APIView):
    """
    [DESARROLLO] Endpoint para completar la orden en PROCESSING del usuario autenticado.
    Se llama cuando el usuario regresa de Stripe exitosamente.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Busca la orden en estado PROCESSING del usuario
            order = Order.objects.get(customer=request.user, status='PROCESSING')
            
            # Cambia el estado a COMPLETED
            order.status = 'COMPLETED'
            order.save()
            
            # Reduce el stock de los productos
            for item in order.items.all():
                product = item.product
                if product.stock >= item.quantity:
                    product.stock -= item.quantity
                    product.save()
                else:
                    print(f"Alerta: Stock insuficiente para el producto {product.id} en la orden {order.id}")
            
            return response.Response({
                'success': True,
                'message': 'Orden completada exitosamente',
                'order_id': order.id
            }, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return response.Response({
                'success': False,
                'message': 'No se encontró una orden en proceso'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return response.Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- NUEVA VISTA PARA EL HISTORIAL DE VENTAS (SOLO ADMINS) ---
class SalesHistoryView(generics.ListAPIView):
    """
    Endpoint para que los administradores vean todas las órdenes completadas.
    Incluye filtros avanzados por fecha, cliente, monto y más.
    
    Ejemplos de uso:
    - /api/sales/sales-history/ (todas las ventas completadas)
    - /api/sales/sales-history/?start_date=2024-01-01&end_date=2024-12-31
    - /api/sales/sales-history/?customer_username=johndoe
    - /api/sales/sales-history/?total_min=50&total_max=500
    - /api/sales/sales-history/?ordering=-total_price
    """
    permission_classes = [IsAdminUser]
    serializer_class = OrderSerializer
    filterset_class = OrderFilter
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        """
        Filtra las órdenes para devolver solo las que tienen el estado 'COMPLETED'.
        """
        return Order.objects.filter(status='COMPLETED').select_related('customer').prefetch_related('items__product').order_by('-updated_at')


class SalesHistoryDetailView(generics.RetrieveAPIView):
    """
    Endpoint para ver el detalle de una orden completada específica.
    Solo administradores pueden ver el detalle completo.
    """
    permission_classes = [IsAdminUser]
    serializer_class = OrderSerializer
    lookup_field = 'pk'

    def get_queryset(self):
        """
        Filtra las órdenes para devolver solo las que tienen el estado 'COMPLETED'.
        """
        return Order.objects.filter(status='COMPLETED').select_related('customer').prefetch_related('items__product__category')

# --- VISTA PARA GENERAR COMPROBANTES EN PDF (ADMIN) ---
class GenerateOrderReceiptPDF(views.APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, order_id):
        try:
            # 1. Buscamos la orden completada
            # ✅ OPTIMIZADO: prefetch_related para traer items y productos
            order = Order.objects.select_related('customer').prefetch_related(
                'items__product__category'
            ).get(id=order_id, status='COMPLETED')
        except Order.DoesNotExist:
            return response.Response({'error': 'Completed order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Creamos una respuesta HTTP de tipo PDF
        response_pdf = HttpResponse(content_type='application/pdf')
        response_pdf['Content-Disposition'] = f'attachment; filename="comprobante_venta_{order.id}.pdf"'

        # 3. Creamos el lienzo del PDF
        p = canvas.Canvas(response_pdf, pagesize=letter)
        width, height = letter

        # --- ENCABEZADO CON LOGO Y EMPRESA ---
        # Nombre de la empresa grande y destacado
        p.setFont("Helvetica-Bold", 32)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawCentredString(width / 2, height - 60, "SMARTSALES365")
        
        # Línea decorativa bajo el nombre
        p.setStrokeColor(colors.HexColor('#764ba2'))
        p.setLineWidth(3)
        p.line(72, height - 75, width - 72, height - 75)
        
        # Subtítulo de la empresa
        p.setFont("Helvetica", 11)
        p.setFillColor(colors.HexColor('#495057'))
        p.drawCentredString(width / 2, height - 95, "Sistema Inteligente de Gestión Comercial")
        
        # --- INFORMACIÓN DEL COMPROBANTE ---
        p.setFont("Helvetica-Bold", 18)
        p.setFillColor(colors.HexColor('#1a222e'))
        p.drawCentredString(width / 2, height - 130, "COMPROBANTE DE VENTA")
        
        # Recuadro con información de la orden
        p.setStrokeColor(colors.HexColor('#667eea'))
        p.setLineWidth(1.5)
        p.rect(72, height - 200, (width - 144) / 2 - 10, 50, stroke=1, fill=0)
        p.rect(width / 2 + 10, height - 200, (width - 144) / 2 - 10, 50, stroke=1, fill=0)
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawString(82, height - 160, "N° DE ORDEN:")
        p.drawString(width / 2 + 20, height - 160, "FECHA DE EMISIÓN:")
        
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.black)
        p.drawString(82, height - 180, f"#{order.id:05d}")
        p.setFont("Helvetica-Bold", 12)
        p.drawString(width / 2 + 20, height - 180, order.updated_at.strftime('%d/%m/%Y %H:%M'))

        # --- INFORMACIÓN DEL CLIENTE ---
        p.setStrokeColor(colors.HexColor('#667eea'))
        p.rect(72, height - 260, width - 144, 45, stroke=1, fill=0)
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawString(82, height - 225, "CLIENTE:")
        
        customer_name = f"{order.customer.first_name} {order.customer.last_name}".strip()
        if not customer_name:
            customer_name = order.customer.username
        
        p.setFont("Helvetica-Bold", 13)
        p.setFillColor(colors.black)
        p.drawString(82, height - 243, customer_name)
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#6c757d'))
        p.drawString(82, height - 255, f"Email: {order.customer.email}")

        # --- TABLA DE PRODUCTOS ---
        table_data = [['PRODUCTO', 'CANT.', 'PRECIO UNIT.', 'SUBTOTAL']]
        for item in order.items.all():
            subtotal = item.quantity * item.price
            table_data.append([
                item.product.name,
                str(item.quantity),
                f"${item.price:.2f}",
                f"${subtotal:.2f}"
            ])

        table = Table(table_data, colWidths=[3.5 * inch, 0.8 * inch, 1.2 * inch, 1.3 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#e9ecef')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        table_height = table.wrap(width, height)[1]
        table.drawOn(p, 72, height - 290 - table_height)

        # --- TOTAL ---
        # Recuadro para el total
        total_y = height - 310 - table_height
        p.setFillColor(colors.HexColor('#667eea'))
        p.rect(width - 252, total_y - 45, 180, 40, stroke=0, fill=1)
        
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(colors.white)
        p.drawString(width - 240, total_y - 20, "TOTAL A PAGAR:")
        p.setFont("Helvetica-Bold", 18)
        p.drawString(width - 240, total_y - 38, f"${order.total_price:.2f} USD")

        # --- PIE DE PÁGINA ---
        footer_y = 100
        p.setFont("Helvetica", 9)
        p.setFillColor(colors.HexColor('#6c757d'))
        p.drawCentredString(width / 2, footer_y, "Gracias por su compra - SmartSales365")
        p.drawCentredString(width / 2, footer_y - 15, "www.smartsales365.com | contacto@smartsales365.com")
        
        # Línea decorativa en el pie
        p.setStrokeColor(colors.HexColor('#764ba2'))
        p.setLineWidth(2)
        p.line(72, footer_y - 30, width - 72, footer_y - 30)

        p.showPage()
        p.save()

        return response_pdf


# --- VISTA PARA GENERAR COMPROBANTES EN PDF (CLIENTE) ---
class GenerateMyOrderReceiptPDF(views.APIView):
    """
    Endpoint para que un cliente genere el comprobante de su propia orden.
    Solo puede acceder a sus propias órdenes completadas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        try:
            # 1. Buscamos la orden completada que pertenezca al usuario actual
            order = Order.objects.get(id=order_id, status='COMPLETED', customer=request.user)
        except Order.DoesNotExist:
            return response.Response({'error': 'Orden completada no encontrada o no tienes acceso a ella.'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Creamos una respuesta HTTP de tipo PDF
        response_pdf = HttpResponse(content_type='application/pdf')
        response_pdf['Content-Disposition'] = f'attachment; filename="comprobante_orden_{order.id}.pdf"'

        # 3. Creamos el lienzo del PDF
        p = canvas.Canvas(response_pdf, pagesize=letter)
        width, height = letter

        # --- ENCABEZADO CON LOGO Y EMPRESA ---
        # Nombre de la empresa grande y destacado
        p.setFont("Helvetica-Bold", 32)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawCentredString(width / 2, height - 60, "SMARTSALES365")
        
        # Línea decorativa bajo el nombre
        p.setStrokeColor(colors.HexColor('#764ba2'))
        p.setLineWidth(3)
        p.line(72, height - 75, width - 72, height - 75)
        
        # Subtítulo de la empresa
        p.setFont("Helvetica", 11)
        p.setFillColor(colors.HexColor('#495057'))
        p.drawCentredString(width / 2, height - 95, "Sistema Inteligente de Gestión Comercial")
        
        # --- INFORMACIÓN DEL COMPROBANTE ---
        p.setFont("Helvetica-Bold", 18)
        p.setFillColor(colors.HexColor('#1a222e'))
        p.drawCentredString(width / 2, height - 130, "COMPROBANTE DE COMPRA")
        
        # Recuadro con información de la orden
        p.setStrokeColor(colors.HexColor('#667eea'))
        p.setLineWidth(1.5)
        p.rect(72, height - 200, (width - 144) / 2 - 10, 50, stroke=1, fill=0)
        p.rect(width / 2 + 10, height - 200, (width - 144) / 2 - 10, 50, stroke=1, fill=0)
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawString(82, height - 160, "N° DE ORDEN:")
        p.drawString(width / 2 + 20, height - 160, "FECHA DE COMPRA:")
        
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.black)
        p.drawString(82, height - 180, f"#{order.id:05d}")
        p.setFont("Helvetica-Bold", 12)
        p.drawString(width / 2 + 20, height - 180, order.updated_at.strftime('%d/%m/%Y %H:%M'))

        # --- INFORMACIÓN DEL CLIENTE ---
        p.setStrokeColor(colors.HexColor('#667eea'))
        p.rect(72, height - 260, width - 144, 45, stroke=1, fill=0)
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#667eea'))
        p.drawString(82, height - 225, "DATOS DEL CLIENTE:")
        
        customer_name = f"{order.customer.first_name} {order.customer.last_name}".strip()
        if not customer_name:
            customer_name = order.customer.username
        
        p.setFont("Helvetica-Bold", 13)
        p.setFillColor(colors.black)
        p.drawString(82, height - 243, customer_name)
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor('#6c757d'))
        p.drawString(82, height - 255, f"Email: {order.customer.email}")

        # --- TABLA DE PRODUCTOS ---
        table_data = [['PRODUCTO', 'CANT.', 'PRECIO UNIT.', 'SUBTOTAL']]
        for item in order.items.all():
            subtotal = item.quantity * item.price
            table_data.append([
                item.product.name,
                str(item.quantity),
                f"${item.price:.2f}",
                f"${subtotal:.2f}"
            ])

        table = Table(table_data, colWidths=[3.5 * inch, 0.8 * inch, 1.2 * inch, 1.3 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#e9ecef')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        table_height = table.wrap(width, height)[1]
        table.drawOn(p, 72, height - 290 - table_height)

        # --- TOTAL ---
        # Recuadro para el total
        total_y = height - 310 - table_height
        p.setFillColor(colors.HexColor('#667eea'))
        p.rect(width - 252, total_y - 45, 180, 40, stroke=0, fill=1)
        
        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(colors.white)
        p.drawString(width - 240, total_y - 20, "TOTAL PAGADO:")
        p.setFont("Helvetica-Bold", 18)
        p.drawString(width - 240, total_y - 38, f"${order.total_price:.2f} USD")

        # --- PIE DE PÁGINA ---
        footer_y = 100
        p.setFont("Helvetica", 9)
        p.setFillColor(colors.HexColor('#6c757d'))
        p.drawCentredString(width / 2, footer_y, "¡Gracias por su compra! - SmartSales365")
        p.drawCentredString(width / 2, footer_y - 15, "www.smartsales365.com | contacto@smartsales365.com")
        p.drawCentredString(width / 2, footer_y - 30, "Este documento es un comprobante válido de su compra")
        
        # Línea decorativa en el pie
        p.setStrokeColor(colors.HexColor('#764ba2'))
        p.setLineWidth(2)
        p.line(72, footer_y - 45, width - 72, footer_y - 45)

        p.showPage()
        p.save()

        return response_pdf

# --- NUEVA VISTA PARA LAS ÓRDENES DEL CLIENTE LOGUEADO ---
class MyOrderListView(generics.ListAPIView):
    """
    Endpoint para que un cliente vea su propio historial de órdenes
    (incluyendo carritos pendientes y ventas completadas).
    """
    permission_classes = [permissions.IsAuthenticated] # Solo usuarios logueados
    serializer_class = OrderSerializer

    def get_queryset(self):
        """
        Filtra las órdenes para devolver solo las del usuario actual,
        excluyendo carritos pendientes Y vacíos.
        """
        user = self.request.user
        # Obtenemos todas las órdenes del usuario que NO sean PENDING
        # (solo mostramos las COMPLETED y CANCELLED, no el carrito activo)
        queryset = Order.objects.filter(customer=user).exclude(status='PENDING')
        # Ordenamos por fecha, las más recientes primero
        return queryset.order_by('-created_at')


# ============================================================
# ❌ ELIMINADO: GenerateDynamicReportView (CÓDIGO DUPLICADO)
# ============================================================
# Esta vista fue reemplazada por el Sistema Unificado de Reportes Inteligentes
# Ubicación: sales/views_unified_reports.py -> UnifiedIntelligentReportView
# 
# ✅ NUEVO ENDPOINT: POST /api/sales/reports/unified/generate/
# 
# El sistema unificado incluye:
# - Parsing inteligente de comandos (intelligent_report_router.py)
# - Parser de prompts centralizado (prompt_parser.py)
# - Generador de reportes modular (report_generator.py)
# - Integración con comandos de voz (voice_commands)
# - Soporte para ML y reportes avanzados
# 
# Ventajas del sistema unificado:
# ✅ Código modular y reutilizable
# ✅ Sin duplicación de lógica
# ✅ Mejor interpretación de lenguaje natural
# ✅ Soporte para múltiples tipos de reportes
# ✅ Integración completa con voice_commands
# ============================================================
