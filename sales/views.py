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
from datetime import datetime
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
        cart, created = Order.objects.get_or_create(
            customer=request.user, 
            status='PENDING',
            defaults={'total_price': 0}
        )
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

# --- VISTA DE PRUEBA PARA SIMULAR EL WEBHOOK MANUALMENTE ---
class ManualOrderCompletionView(views.APIView):
    """
    [SOLO PARA DESARROLLO]
    Endpoint para forzar la finalización de la orden pendiente de un usuario.
    Simula el comportamiento del webhook de Stripe.
    """
    permission_classes = [permissions.IsAdminUser] # Protegido para que solo un admin pueda usarlo

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
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = OrderSerializer
    filterset_class = OrderFilter
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]

    def get_queryset(self):
        """
        Filtra las órdenes para devolver solo las que tienen el estado 'COMPLETED'.
        """
        return Order.objects.filter(status='COMPLETED').order_by('-updated_at')

# --- VISTA PARA GENERAR COMPROBANTES EN PDF ---
class GenerateOrderReceiptPDF(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, order_id):
        try:
            # 1. Buscamos la orden completada
            order = Order.objects.get(id=order_id, status='COMPLETED')
        except Order.DoesNotExist:
            return response.Response({'error': 'Completed order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Creamos una respuesta HTTP de tipo PDF
        response_pdf = HttpResponse(content_type='application/pdf')
        response_pdf['Content-Disposition'] = f'attachment; filename="receipt_order_{order.id}.pdf"'

        # 3. Creamos el lienzo del PDF
        p = canvas.Canvas(response_pdf, pagesize=letter)
        width, height = letter

        # --- DIBUJAMOS EL CONTENIDO DEL PDF ---
        p.setFont("Helvetica-Bold", 16)
        p.drawString(72, height - 72, "Nota de Venta / Comprobante")

        p.setFont("Helvetica", 12)
        p.drawString(72, height - 108, f"Orden N°: {order.id}")
        p.drawString(72, height - 126, f"Fecha: {order.updated_at.strftime('%d/%m/%Y %H:%M')}")

        p.drawString(width - 250, height - 108, "Cliente:")
        p.setFont("Helvetica-Bold", 12)
        p.drawString(width - 250, height - 126, f"{order.customer.first_name} {order.customer.last_name}")
        p.setFont("Helvetica", 12)
        p.drawString(width - 250, height - 144, f"(@{order.customer.username})")

        p.line(72, height - 160, width - 72, height - 160) # Línea divisoria

        # 4. Creamos la tabla de productos
        table_data = [['Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
        for item in order.items.all():
            subtotal = item.quantity * item.price
            table_data.append([
                item.product.name,
                str(item.quantity),
                f"${item.price:.2f} USD",
                f"${subtotal:.2f} USD"
            ])

        table = Table(table_data, colWidths=[3.5 * inch, 0.8 * inch, 1.2 * inch, 1.2 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A222E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        table_height = table.wrap(width, height)[1]
        table.drawOn(p, 72, height - 200 - table_height)

        # 5. Dibujamos el total al final
        p.setFont("Helvetica-Bold", 14)
        p.drawRightString(width - 72, height - 220 - table_height, f"Total: ${order.total_price:.2f} USD")

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
        # Obtenemos todas las órdenes del usuario
        queryset = Order.objects.filter(customer=user)
        # --- CAMBIO AQUÍ: Excluimos las que son PENDING y no tienen items ---
        queryset = queryset.exclude(status='PENDING', items__isnull=True)
        # -----------------------------------------------------------------
        # Ordenamos por fecha, las más recientes primero
        return queryset.order_by('-created_at')

# ============================================================================
# NUEVAS VISTAS PARA REPORTES DINÁMICOS
# ============================================================================

from django.http import HttpResponse
from .prompt_parser import parse_prompt
from .report_generator import generate_report
from .excel_exporter import export_to_excel

class DynamicReportView(views.APIView):
    """
    Endpoint para generar reportes dinámicos basados en prompts de texto.
    
    Acepta POST con:
    {
        "prompt": "Reporte de ventas del mes de octubre en PDF"
    }
    
    Retorna el reporte en el formato solicitado (JSON, PDF o Excel).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """
        Procesa el prompt y genera el reporte solicitado.
        """
        prompt = request.data.get('prompt', '')
        
        if not prompt:
            return response.Response(
                {'error': 'Se requiere un prompt para generar el reporte.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 1. Parsear el prompt
            params = parse_prompt(prompt)
            
            # 2. Generar el reporte
            report_data = generate_report(params)
            
            # 3. Retornar según el formato solicitado
            format_type = params.get('format', 'screen')
            
            if format_type == 'pdf':
                return self._generate_pdf_response(report_data)
            elif format_type == 'excel':
                return self._generate_excel_response(report_data)
            else:
                # Retornar JSON para mostrar en pantalla
                return response.Response({
                    'success': True,
                    'prompt': prompt,
                    'params': params,
                    'data': report_data
                })
        
        except Exception as e:
            return response.Response(
                {
                    'error': 'Error al generar el reporte.',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_pdf_response(self, report_data):
        """
        Genera y retorna un PDF del reporte.
        """
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        # Crear respuesta HTTP de tipo PDF
        response_pdf = HttpResponse(content_type='application/pdf')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reporte_{timestamp}.pdf'
        response_pdf['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Crear el documento PDF
        doc = SimpleDocTemplate(response_pdf, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Estilo para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1A222E'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Estilo para el subtítulo
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        # Añadir título
        title = Paragraph(report_data.get('title', 'Reporte'), title_style)
        elements.append(title)
        
        # Añadir subtítulo
        if report_data.get('subtitle'):
            subtitle = Paragraph(report_data.get('subtitle', ''), subtitle_style)
            elements.append(subtitle)
        
        elements.append(Spacer(1, 0.2*inch))
        
        # Crear tabla de datos
        table_data = [report_data.get('headers', [])]
        table_data.extend(report_data.get('rows', []))
        
        if table_data:
            # Calcular anchos de columna
            num_columns = len(table_data[0])
            col_widths = [letter[0] / num_columns * 0.9] * num_columns
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                # Estilo del header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A222E')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Estilo de las filas de datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                
                # Bordes
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Alternar colores en las filas
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.beige]),
            ]))
            
            elements.append(table)
        
        # Añadir totales si existen
        if report_data.get('totals'):
            elements.append(Spacer(1, 0.3*inch))
            
            totals_data = []
            for key, value in report_data['totals'].items():
                label = key.replace('_', ' ').title()
                totals_data.append([f"{label}:", str(value)])
            
            totals_table = Table(totals_data, colWidths=[3*inch, 2*inch])
            totals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E2E8F0')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            
            elements.append(totals_table)
        
        # Añadir timestamp
        elements.append(Spacer(1, 0.3*inch))
        timestamp_text = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        timestamp_para = Paragraph(timestamp_text, styles['Normal'])
        elements.append(timestamp_para)
        
        # Construir el PDF
        doc.build(elements)
        
        return response_pdf
    
    def _generate_excel_response(self, report_data):
        """
        Genera y retorna un Excel del reporte.
        """
        excel_file = export_to_excel(report_data)
        
        response_excel = HttpResponse(
            excel_file.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'reporte_{timestamp}.xlsx'
        response_excel['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response_excel