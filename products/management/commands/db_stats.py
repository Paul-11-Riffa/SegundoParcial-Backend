"""
Comando para mostrar estadísticas detalladas de la base de datos.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.db import connection
from products.models import Product, Category
from sales.models import Order, OrderItem


class Command(BaseCommand):
    help = 'Muestra estadísticas detalladas de la base de datos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('📊 ESTADÍSTICAS DE LA BASE DE DATOS'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))

        # Información de la base de datos
        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']
        
        if 'postgresql' in db_engine:
            self.stdout.write(f'💾 Motor: PostgreSQL')
            self.stdout.write(f'   Base de datos: {db_settings.get("NAME")}')
            self.stdout.write(f'   Host: {db_settings.get("HOST")}:{db_settings.get("PORT")}\n')
            
            # Intentar obtener tamaño de la base de datos en PostgreSQL
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """)
                    db_size = cursor.fetchone()[0]
                    self.stdout.write(f'💾 Tamaño: {db_size}\n')
            except:
                self.stdout.write(f'💾 Tamaño: No disponible\n')
        elif 'sqlite' in db_engine:
            import os
            db_file = db_settings['NAME']
            if os.path.exists(db_file):
                db_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                self.stdout.write(f'💾 Tamaño del archivo: {db_size:.2f} MB\n')
        
        # Usuarios
        self.stdout.write(self.style.SUCCESS('👥 USUARIOS:'))
        users_count = User.objects.count()
        admins_count = User.objects.filter(is_superuser=True).count()
        staff_count = User.objects.filter(is_staff=True, is_superuser=False).count()
        regular_count = users_count - admins_count - staff_count
        
        self.stdout.write(f'   Total: {users_count}')
        self.stdout.write(f'   ├─ Administradores: {admins_count}')
        self.stdout.write(f'   ├─ Staff: {staff_count}')
        self.stdout.write(f'   └─ Regulares: {regular_count}\n')

        # Categorías
        self.stdout.write(self.style.SUCCESS('📂 CATEGORÍAS:'))
        categories_count = Category.objects.count()
        self.stdout.write(f'   Total: {categories_count}')
        
        if categories_count > 0:
            for cat in Category.objects.all()[:10]:
                products_in_cat = cat.products.count()
                self.stdout.write(f'   ├─ {cat.name}: {products_in_cat} productos')
        self.stdout.write('')

        # Productos
        self.stdout.write(self.style.SUCCESS('📦 PRODUCTOS:'))
        products_count = Product.objects.count()
        active_products = Product.objects.filter(is_active=True).count()
        inactive_products = products_count - active_products
        products_with_stock = Product.objects.filter(stock__gt=0).count()
        products_without_stock = products_count - products_with_stock
        
        self.stdout.write(f'   Total: {products_count}')
        self.stdout.write(f'   ├─ Activos: {active_products}')
        self.stdout.write(f'   ├─ Inactivos: {inactive_products}')
        self.stdout.write(f'   ├─ Con stock: {products_with_stock}')
        self.stdout.write(f'   └─ Sin stock: {products_without_stock}\n')

        # Órdenes
        self.stdout.write(self.style.SUCCESS('🛒 ÓRDENES:'))
        orders_count = Order.objects.count()
        pending_orders = Order.objects.filter(status='PENDING').count()
        processing_orders = Order.objects.filter(status='PROCESSING').count()
        completed_orders = Order.objects.filter(status='COMPLETED').count()
        cancelled_orders = Order.objects.filter(status='CANCELLED').count()
        
        self.stdout.write(f'   Total: {orders_count}')
        self.stdout.write(f'   ├─ Pendientes (Carritos): {pending_orders}')
        self.stdout.write(f'   ├─ En proceso: {processing_orders}')
        self.stdout.write(f'   ├─ Completadas: {completed_orders}')
        self.stdout.write(f'   └─ Canceladas: {cancelled_orders}\n')

        # OrderItems
        self.stdout.write(self.style.SUCCESS('📋 ITEMS EN ÓRDENES:'))
        order_items_count = OrderItem.objects.count()
        self.stdout.write(f'   Total: {order_items_count}\n')

        # Análisis de rendimiento
        if orders_count > 5000:
            self.stdout.write(self.style.ERROR('⚠️  ADVERTENCIA DE RENDIMIENTO:'))
            self.stdout.write(self.style.ERROR(f'   Tienes {orders_count} órdenes en la base de datos.'))
            self.stdout.write(self.style.ERROR('   Esto puede causar lentitud en las queries.'))
            self.stdout.write(self.style.WARNING('   💡 Considera ejecutar: python manage.py clean_database_for_demo\n'))
        elif orders_count > 1000:
            self.stdout.write(self.style.WARNING('⚠️  Base de datos con muchos datos:'))
            self.stdout.write(self.style.WARNING(f'   Tienes {orders_count} órdenes.'))
            self.stdout.write(self.style.WARNING('   Para una demo, considera reducir la cantidad.\n'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ Base de datos en buen estado\n'))

        self.stdout.write('\n' + '='*70 + '\n')
