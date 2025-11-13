# sales/specific_report_generator.py
"""
🎯 Generadores de Reportes Ultra-Específicos
Crea reportes personalizados según entidades detectadas (clientes, productos, etc.)
"""

from django.db.models import Sum, Count, Avg, F, Q, Max, Min
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from .models import Order, OrderItem
from products.models import Product, Category


class SpecificReportGenerator:
    """
    Generador de reportes específicos basado en filtros granulares.
    """
    
    def __init__(self, report_type, filters):
        """
        Inicializa el generador.
        
        Args:
            report_type (str): Tipo de reporte a generar
            filters (dict): Filtros aplicados (customer_id, product_id, etc.)
        """
        self.report_type = report_type
        self.filters = filters
        self.report_data = {
            'title': '',
            'subtitle': '',
            'headers': [],
            'rows': [],
            'totals': {},
            'metadata': {},
            'charts': []  # Datos para gráficos
        }
    
    def generate(self):
        """
        Genera el reporte según el tipo especificado.
        
        Returns:
            dict: Datos del reporte generado
        """
        if self.report_type == 'compras_cliente':
            return self._compras_cliente()
        elif self.report_type == 'productos_comprados_por_cliente':
            return self._productos_comprados_por_cliente()
        elif self.report_type == 'analisis_comportamiento_cliente':
            return self._analisis_comportamiento_cliente()
        elif self.report_type == 'timeline_compras_cliente':
            return self._timeline_compras_cliente()
        elif self.report_type == 'clientes_que_compraron_producto':
            return self._clientes_que_compraron_producto()
        elif self.report_type == 'ventas_producto_especifico':
            return self._ventas_producto_especifico()
        elif self.report_type == 'ventas_por_rango_precio':
            return self._ventas_por_rango_precio()
        elif self.report_type == 'productos_mas_caros_vendidos':
            return self._productos_mas_caros_vendidos()
        elif self.report_type == 'comparativa_clientes':
            return self._comparativa_clientes()
        elif self.report_type == 'comparativa_productos':
            return self._comparativa_productos()
        else:
            # Fallback
            return self._ventas_general()
    
    # ========== REPORTES ESPECÍFICOS DE CLIENTES ==========
    
    def _compras_cliente(self):
        """
        Reporte completo de compras de un cliente específico.
        Muestra: Fecha, Productos comprados, Cantidad, Precio unitario, Subtotal, Total de la orden
        """
        customer_id = self.filters.get('customer_id')
        if not customer_id:
            return {'error': 'Se requiere customer_id'}
        
        try:
            customer = User.objects.get(id=customer_id)
        except User.DoesNotExist:
            return {'error': 'Cliente no encontrado'}
        
        # Título personalizado
        customer_name = f"{customer.first_name} {customer.last_name}".strip() or customer.username
        self.report_data['title'] = f'Historial de Compras - {customer_name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        # Headers detallados
        self.report_data['headers'] = [
            'Orden #',
            'Fecha',
            'Producto',
            'Cantidad',
            'Precio Unit.',
            'Subtotal',
            'Total Orden',
            'Estado'
        ]
        
        # Obtener órdenes del cliente
        orders_query = Order.objects.filter(customer=customer, status='COMPLETED')
        
        # Aplicar filtro de fechas si existe
        if self.filters.get('start_date'):
            orders_query = orders_query.filter(updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            orders_query = orders_query.filter(updated_at__lte=self.filters['end_date'])
        
        orders = orders_query.prefetch_related('items__product').order_by('-updated_at')
        
        # Construir filas
        total_spent = 0.0
        total_orders = 0
        total_items = 0
        
        for order in orders:
            order_items = order.items.all()
            first_item = True
            
            for item in order_items:
                subtotal = float(item.price * item.quantity)
                
                row = [
                    f"#{order.id}" if first_item else "",
                    order.updated_at.strftime('%d/%m/%Y %H:%M') if first_item else "",
                    item.product.name,
                    item.quantity,
                    f"${float(item.price):.2f}",
                    f"${subtotal:.2f}",
                    f"${float(order.total_price):.2f}" if first_item else "",
                    order.status if first_item else ""
                ]
                
                self.report_data['rows'].append(row)
                
                if first_item:
                    total_spent += float(order.total_price)
                    total_orders += 1
                first_item = False
                
                total_items += item.quantity
        
        # Totales
        avg_ticket = total_spent / total_orders if total_orders > 0 else 0
        
        self.report_data['totals'] = {
            'total_ordenes': total_orders,
            'total_productos': total_items,
            'total_gastado': f"${total_spent:.2f}",
            'ticket_promedio': f"${avg_ticket:.2f}"
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'cliente': {
                'id': customer.id,
                'username': customer.username,
                'nombre': customer_name,
                'email': customer.email
            },
            'generado_en': timezone.now().strftime('%d/%m/%Y %H:%M:%S'),
            'periodo': self.filters.get('period_text', 'Histórico completo')
        }
        
        return self.report_data
    
    def _productos_comprados_por_cliente(self):
        """
        Lista agrupada de productos que ha comprado un cliente.
        Muestra: Producto, Veces comprado, Cantidad total, Gasto total
        """
        customer_id = self.filters.get('customer_id')
        if not customer_id:
            return {'error': 'Se requiere customer_id'}
        
        try:
            customer = User.objects.get(id=customer_id)
        except User.DoesNotExist:
            return {'error': 'Cliente no encontrado'}
        
        customer_name = f"{customer.first_name} {customer.last_name}".strip() or customer.username
        self.report_data['title'] = f'Productos Comprados - {customer_name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        self.report_data['headers'] = [
            'Producto',
            'Categoría',
            'Veces Comprado',
            'Cantidad Total',
            'Precio Promedio',
            'Gasto Total',
            'Última Compra'
        ]
        
        # Obtener items del cliente
        items_query = OrderItem.objects.filter(
            order__customer=customer,
            order__status='COMPLETED'
        )
        
        # Aplicar filtros de fecha
        if self.filters.get('start_date'):
            items_query = items_query.filter(order__updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            items_query = items_query.filter(order__updated_at__lte=self.filters['end_date'])
        
        # Agrupar por producto
        products_stats = items_query.values(
            'product__id',
            'product__name',
            'product__category__name'
        ).annotate(
            veces_comprado=Count('order', distinct=True),
            cantidad_total=Sum('quantity'),
            precio_promedio=Avg('price'),
            gasto_total=Sum(F('price') * F('quantity')),
            ultima_compra=Max('order__updated_at')
        ).order_by('-gasto_total')
        
        # Construir filas
        total_products = 0
        total_spent = 0.0
        
        for stats in products_stats:
            self.report_data['rows'].append([
                stats['product__name'],
                stats['product__category__name'] or 'Sin categoría',
                stats['veces_comprado'],
                stats['cantidad_total'],
                f"${float(stats['precio_promedio']):.2f}",
                f"${float(stats['gasto_total']):.2f}",
                stats['ultima_compra'].strftime('%d/%m/%Y')
            ])
            
            total_products += 1
            total_spent += float(stats['gasto_total'])
        
        # Totales
        self.report_data['totals'] = {
            'productos_diferentes': total_products,
            'gasto_total': f"${total_spent:.2f}"
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'cliente': {
                'id': customer.id,
                'username': customer.username,
                'nombre': customer_name,
                'email': customer.email
            },
            'generado_en': timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return self.report_data
    
    def _analisis_comportamiento_cliente(self):
        """
        Análisis profundo del patrón de compra de un cliente.
        Incluye: Frecuencia, promedio de gasto, categorías preferidas, horarios, etc.
        """
        customer_id = self.filters.get('customer_id')
        if not customer_id:
            return {'error': 'Se requiere customer_id'}
        
        try:
            customer = User.objects.get(id=customer_id)
        except User.DoesNotExist:
            return {'error': 'Cliente no encontrado'}
        
        customer_name = f"{customer.first_name} {customer.last_name}".strip() or customer.username
        self.report_data['title'] = f'Análisis de Comportamiento - {customer_name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        # Obtener órdenes
        orders_query = Order.objects.filter(customer=customer, status='COMPLETED')
        
        if self.filters.get('start_date'):
            orders_query = orders_query.filter(updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            orders_query = orders_query.filter(updated_at__lte=self.filters['end_date'])
        
        orders = orders_query.prefetch_related('items__product__category')
        
        # Métricas generales
        total_orders = orders.count()
        total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
        avg_ticket = float(total_spent) / total_orders if total_orders > 0 else 0
        
        # Primera y última compra
        first_order = orders.order_by('updated_at').first()
        last_order = orders.order_by('-updated_at').first()
        
        # Categorías preferidas
        items = OrderItem.objects.filter(order__in=orders)
        categories_stats = items.values(
            'product__category__name'
        ).annotate(
            cantidad=Sum('quantity'),
            gasto=Sum(F('price') * F('quantity'))
        ).order_by('-gasto')[:5]
        
        # Producto más comprado
        top_product = items.values(
            'product__name'
        ).annotate(
            cantidad=Sum('quantity')
        ).order_by('-cantidad').first()
        
        # Headers para tabla de categorías
        self.report_data['headers'] = [
            'Categoría',
            'Cantidad Productos',
            'Gasto Total',
            '% del Total'
        ]
        
        # Filas de categorías
        for cat_stat in categories_stats:
            porcentaje = (float(cat_stat['gasto']) / float(total_spent) * 100) if total_spent > 0 else 0
            self.report_data['rows'].append([
                cat_stat['product__category__name'] or 'Sin categoría',
                cat_stat['cantidad'],
                f"${float(cat_stat['gasto']):.2f}",
                f"{porcentaje:.1f}%"
            ])
        
        # Totales y análisis
        days_between = (last_order.updated_at - first_order.updated_at).days if first_order and last_order else 0
        frequency_days = days_between / total_orders if total_orders > 1 else 0
        
        self.report_data['totals'] = {
            'total_ordenes': total_orders,
            'gasto_total': f"${float(total_spent):.2f}",
            'ticket_promedio': f"${avg_ticket:.2f}",
            'primera_compra': first_order.updated_at.strftime('%d/%m/%Y') if first_order else 'N/A',
            'ultima_compra': last_order.updated_at.strftime('%d/%m/%Y') if last_order else 'N/A',
            'frecuencia_compra_dias': f"{frequency_days:.0f}" if frequency_days > 0 else 'N/A',
            'producto_favorito': top_product['product__name'] if top_product else 'N/A',
            'categoria_favorita': categories_stats[0]['product__category__name'] if categories_stats else 'N/A'
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'cliente': {
                'id': customer.id,
                'username': customer.username,
                'nombre': customer_name,
                'email': customer.email
            },
            'analisis_generado': timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return self.report_data
    
    def _timeline_compras_cliente(self):
        """
        Línea de tiempo cronológica de las compras de un cliente.
        """
        customer_id = self.filters.get('customer_id')
        if not customer_id:
            return {'error': 'Se requiere customer_id'}
        
        try:
            customer = User.objects.get(id=customer_id)
        except User.DoesNotExist:
            return {'error': 'Cliente no encontrado'}
        
        customer_name = f"{customer.first_name} {customer.last_name}".strip() or customer.username
        self.report_data['title'] = f'Timeline de Compras - {customer_name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        self.report_data['headers'] = [
            'Fecha',
            'Orden #',
            'Productos',
            'Total',
            'Días desde Anterior',
            'Estado'
        ]
        
        # Obtener órdenes cronológicamente
        orders_query = Order.objects.filter(customer=customer, status='COMPLETED')
        
        if self.filters.get('start_date'):
            orders_query = orders_query.filter(updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            orders_query = orders_query.filter(updated_at__lte=self.filters['end_date'])
        
        orders = orders_query.prefetch_related('items__product').order_by('updated_at')
        
        previous_date = None
        for order in orders:
            # Calcular días desde compra anterior
            days_since_last = ''
            if previous_date:
                delta = order.updated_at - previous_date
                days_since_last = f"{delta.days} días"
            
            # Contar productos
            product_count = order.items.aggregate(total=Sum('quantity'))['total'] or 0
            
            self.report_data['rows'].append([
                order.updated_at.strftime('%d/%m/%Y %H:%M'),
                f"#{order.id}",
                f"{product_count} producto(s)",
                f"${float(order.total_price):.2f}",
                days_since_last,
                order.status
            ])
            
            previous_date = order.updated_at
        
        # Totales
        total_orders = orders.count()
        total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        self.report_data['totals'] = {
            'total_compras': total_orders,
            'total_gastado': f"${float(total_spent):.2f}"
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'cliente': {
                'id': customer.id,
                'username': customer.username,
                'nombre': customer_name
            },
            'generado_en': timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return self.report_data
    
    # ========== REPORTES ESPECÍFICOS DE PRODUCTOS ==========
    
    def _clientes_que_compraron_producto(self):
        """
        Lista de clientes que compraron un producto específico.
        """
        product_id = self.filters.get('product_id')
        if not product_id:
            return {'error': 'Se requiere product_id'}
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return {'error': 'Producto no encontrado'}
        
        self.report_data['title'] = f'Clientes que compraron: {product.name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        self.report_data['headers'] = [
            'Cliente',
            'Email',
            'Veces Comprado',
            'Cantidad Total',
            'Gasto Total',
            'Última Compra'
        ]
        
        # Obtener items de este producto (FIX: usar order_items en lugar de orderitem)
        items_query = OrderItem.objects.filter(
            product=product,
            order__status='COMPLETED'
        )
        
        if self.filters.get('start_date'):
            items_query = items_query.filter(order__updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            items_query = items_query.filter(order__updated_at__lte=self.filters['end_date'])
        
        # Agrupar por cliente
        clients_stats = items_query.values(
            'order__customer__id',
            'order__customer__username',
            'order__customer__first_name',
            'order__customer__last_name',
            'order__customer__email'
        ).annotate(
            veces_comprado=Count('order', distinct=True),
            cantidad_total=Sum('quantity'),
            gasto_total=Sum(F('price') * F('quantity')),
            ultima_compra=Max('order__updated_at')
        ).order_by('-gasto_total')
        
        # Construir filas
        total_clients = 0
        total_quantity = 0
        total_revenue = 0.0
        
        for stats in clients_stats:
            full_name = f"{stats['order__customer__first_name']} {stats['order__customer__last_name']}".strip()
            if not full_name:
                full_name = stats['order__customer__username']
            
            self.report_data['rows'].append([
                full_name,
                stats['order__customer__email'],
                stats['veces_comprado'],
                stats['cantidad_total'],
                f"${float(stats['gasto_total']):.2f}",
                stats['ultima_compra'].strftime('%d/%m/%Y')
            ])
            
            total_clients += 1
            total_quantity += stats['cantidad_total']
            total_revenue += float(stats['gasto_total'])
        
        # Totales
        self.report_data['totals'] = {
            'clientes_diferentes': total_clients,
            'unidades_vendidas': total_quantity,
            'ingresos_totales': f"${total_revenue:.2f}"
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'producto': {
                'id': product.id,
                'nombre': product.name,
                'precio_actual': f"${float(product.price):.2f}"
            },
            'generado_en': timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return self.report_data
    
    def _ventas_producto_especifico(self):
        """
        Historial de ventas de un producto específico.
        """
        product_id = self.filters.get('product_id')
        if not product_id:
            return {'error': 'Se requiere product_id'}
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return {'error': 'Producto no encontrado'}
        
        self.report_data['title'] = f'Historial de Ventas: {product.name}'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        self.report_data['headers'] = [
            'Fecha',
            'Cliente',
            'Cantidad',
            'Precio Unitario',
            'Subtotal',
            'Orden #'
        ]
        
        # Obtener ventas del producto
        items_query = OrderItem.objects.filter(
            product=product,
            order__status='COMPLETED'
        ).select_related('order__customer')
        
        if self.filters.get('start_date'):
            items_query = items_query.filter(order__updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            items_query = items_query.filter(order__updated_at__lte=self.filters['end_date'])
        
        items = items_query.order_by('-order__updated_at')
        
        # Construir filas
        total_quantity = 0
        total_revenue = 0.0
        
        for item in items:
            customer = item.order.customer
            customer_name = f"{customer.first_name} {customer.last_name}".strip() or customer.username
            
            subtotal = float(item.price * item.quantity)
            
            self.report_data['rows'].append([
                item.order.updated_at.strftime('%d/%m/%Y %H:%M'),
                customer_name,
                item.quantity,
                f"${float(item.price):.2f}",
                f"${subtotal:.2f}",
                f"#{item.order.id}"
            ])
            
            total_quantity += item.quantity
            total_revenue += subtotal
        
        # Totales
        avg_price = total_revenue / total_quantity if total_quantity > 0 else 0
        
        self.report_data['totals'] = {
            'unidades_vendidas': total_quantity,
            'ingresos_totales': f"${total_revenue:.2f}",
            'precio_promedio': f"${avg_price:.2f}"
        }
        
        # Metadata
        self.report_data['metadata'] = {
            'producto': {
                'id': product.id,
                'nombre': product.name,
                'precio_actual': f"${float(product.price):.2f}",
                'stock_actual': product.stock
            },
            'generado_en': timezone.now().strftime('%d/%m/%Y %H:%M:%S')
        }
        
        return self.report_data
    
    # ========== REPORTES POR PRECIO ==========
    
    def _ventas_por_rango_precio(self):
        """
        Ventas filtradas por rango de precio.
        """
        self.report_data['title'] = 'Ventas por Rango de Precio'
        
        price_desc = []
        if self.filters.get('price_min'):
            price_desc.append(f"Mínimo: ${self.filters['price_min']}")
        if self.filters.get('price_max'):
            price_desc.append(f"Máximo: ${self.filters['price_max']}")
        
        self.report_data['subtitle'] = ' | '.join(price_desc) if price_desc else 'Todos los precios'
        
        self.report_data['headers'] = [
            'Producto',
            'Categoría',
            'Precio',
            'Unidades Vendidas',
            'Ingresos'
        ]
        
        # Filtrar items por rango de precio
        items_query = OrderItem.objects.filter(order__status='COMPLETED')
        
        if self.filters.get('price_min'):
            items_query = items_query.filter(price__gte=self.filters['price_min'])
        if self.filters.get('price_max'):
            items_query = items_query.filter(price__lte=self.filters['price_max'])
        
        if self.filters.get('start_date'):
            items_query = items_query.filter(order__updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            items_query = items_query.filter(order__updated_at__lte=self.filters['end_date'])
        
        # Agrupar por producto
        products_stats = items_query.values(
            'product__name',
            'product__category__name',
            'price'
        ).annotate(
            cantidad=Sum('quantity'),
            ingresos=Sum(F('price') * F('quantity'))
        ).order_by('-ingresos')
        
        # Construir filas
        total_units = 0
        total_revenue = 0.0
        
        for stats in products_stats:
            self.report_data['rows'].append([
                stats['product__name'],
                stats['product__category__name'] or 'Sin categoría',
                f"${float(stats['price']):.2f}",
                stats['cantidad'],
                f"${float(stats['ingresos']):.2f}"
            ])
            
            total_units += stats['cantidad']
            total_revenue += float(stats['ingresos'])
        
        # Totales
        self.report_data['totals'] = {
            'productos_diferentes': len(products_stats),
            'unidades_vendidas': total_units,
            'ingresos_totales': f"${total_revenue:.2f}"
        }
        
        return self.report_data
    
    def _productos_mas_caros_vendidos(self):
        """
        Top productos de mayor precio vendidos.
        """
        self.report_data['title'] = 'Productos Más Caros Vendidos'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        self.report_data['headers'] = [
            'Producto',
            'Categoría',
            'Precio',
            'Unidades Vendidas',
            'Clientes',
            'Ingresos'
        ]
        
        # Obtener items ordenados por precio
        items_query = OrderItem.objects.filter(order__status='COMPLETED')
        
        if self.filters.get('start_date'):
            items_query = items_query.filter(order__updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            items_query = items_query.filter(order__updated_at__lte=self.filters['end_date'])
        
        # Agrupar por producto y ordenar por precio
        products_stats = items_query.values(
            'product__name',
            'product__category__name',
            'price'
        ).annotate(
            cantidad=Sum('quantity'),
            clientes=Count('order__customer', distinct=True),
            ingresos=Sum(F('price') * F('quantity'))
        ).order_by('-price')[:20]  # Top 20
        
        # Construir filas
        for stats in products_stats:
            self.report_data['rows'].append([
                stats['product__name'],
                stats['product__category__name'] or 'Sin categoría',
                f"${float(stats['price']):.2f}",
                stats['cantidad'],
                stats['clientes'],
                f"${float(stats['ingresos']):.2f}"
            ])
        
        return self.report_data
    
    # ========== REPORTES COMPARATIVOS ==========
    
    def _comparativa_clientes(self):
        """
        Compara comportamiento de múltiples clientes.
        """
        # TODO: Implementar comparativa de clientes
        self.report_data['title'] = 'Comparativa de Clientes'
        self.report_data['subtitle'] = 'Funcionalidad en desarrollo'
        return self.report_data
    
    def _comparativa_productos(self):
        """
        Compara ventas de múltiples productos.
        """
        # TODO: Implementar comparativa de productos
        self.report_data['title'] = 'Comparativa de Productos'
        self.report_data['subtitle'] = 'Funcionalidad en desarrollo'
        return self.report_data
    
    # ========== FALLBACK ==========
    
    def _ventas_general(self):
        """
        Reporte general de ventas (fallback).
        """
        self.report_data['title'] = 'Reporte General de Ventas'
        self.report_data['subtitle'] = self._get_period_subtitle()
        
        # Obtener órdenes
        orders_query = Order.objects.filter(status='COMPLETED')
        
        if self.filters.get('start_date'):
            orders_query = orders_query.filter(updated_at__gte=self.filters['start_date'])
        if self.filters.get('end_date'):
            orders_query = orders_query.filter(updated_at__lte=self.filters['end_date'])
        
        total_orders = orders_query.count()
        total_revenue = orders_query.aggregate(total=Sum('total_price'))['total'] or 0
        
        self.report_data['totals'] = {
            'total_ordenes': total_orders,
            'ingresos_totales': f"${float(total_revenue):.2f}"
        }
        
        return self.report_data
    
    # ========== HELPERS ==========
    
    def _get_period_subtitle(self):
        """
        Genera subtítulo descriptivo del período.
        """
        if self.filters.get('period_text'):
            return f"Período: {self.filters['period_text']}"
        elif self.filters.get('start_date') and self.filters.get('end_date'):
            start_str = self.filters['start_date'].strftime('%d/%m/%Y')
            end_str = self.filters['end_date'].strftime('%d/%m/%Y')
            return f"Período: {start_str} - {end_str}"
        else:
            return "Período: Histórico completo"
