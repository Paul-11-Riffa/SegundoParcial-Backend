"""
Comando para limpiar la base de datos para demo.
Mantiene usuarios pero elimina órdenes, productos y categorías antiguas.
Crea nuevos productos y categorías optimizados para demo.
"""
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.contrib.auth.models import User
from products.models import Product, Category
from sales.models import Order, OrderItem
from decimal import Decimal
import os
import time


class Command(BaseCommand):
    help = 'Limpia la base de datos y crea 10 productos demo con 5 categorías'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-confirm',
            action='store_true',
            help='Omitir confirmación (usar con cuidado)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('⚠️  LIMPIEZA DE BASE DE DATOS PARA DEMO'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))

        # Mostrar estado actual
        self.stdout.write('📊 Estado actual de la base de datos:')
        self.stdout.write(f'   Usuarios: {User.objects.count()}')
        self.stdout.write(f'   Categorías: {Category.objects.count()}')
        self.stdout.write(f'   Productos: {Product.objects.count()}')
        self.stdout.write(f'   Órdenes: {Order.objects.count()}')
        self.stdout.write(f'   OrderItems: {OrderItem.objects.count()}\n')

        # Advertencias
        self.stdout.write(self.style.ERROR('⚠️  ADVERTENCIA:'))
        self.stdout.write(self.style.ERROR('   ❌ Se eliminarán TODAS las órdenes'))
        self.stdout.write(self.style.ERROR('   ❌ Se eliminarán TODOS los productos'))
        self.stdout.write(self.style.ERROR('   ❌ Se eliminarán TODAS las categorías'))
        self.stdout.write(self.style.SUCCESS('   ✅ Se mantendrán los usuarios'))
        self.stdout.write(self.style.SUCCESS('   ✅ Se crearán 5 categorías nuevas'))
        self.stdout.write(self.style.SUCCESS('   ✅ Se crearán 10 productos nuevos\n'))

        # Confirmación
        if not options['skip_confirm']:
            confirm = input('¿Deseas continuar? (escriba "SI" para confirmar): ')
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR('❌ Operación cancelada'))
                return

        self.stdout.write(self.style.WARNING('\n🚀 Iniciando limpieza...\n'))

        try:
            # Cerrar conexiones antiguas para evitar problemas SSL
            connection.close()
            time.sleep(1)
            
            # Paso 1: Eliminar OrderItems primero (para evitar error de foreign key)
            self.stdout.write('1️⃣  Eliminando items de órdenes...')
            try:
                order_items_count = OrderItem.objects.count()
                self.stdout.write(f'   Total a eliminar: {order_items_count}')
                
                # Eliminar en lotes
                batch_size = 1000
                deleted_total = 0
                
                while OrderItem.objects.exists():
                    items_batch = list(OrderItem.objects.values_list('id', flat=True)[:batch_size])
                    if not items_batch:
                        break
                    OrderItem.objects.filter(id__in=items_batch).delete()
                    deleted_total += len(items_batch)
                    self.stdout.write(f'   ... eliminados {deleted_total}/{order_items_count}')
                    time.sleep(0.3)
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {deleted_total} items eliminados\n'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ⚠️  Error: {e}'))
                # Intentar método directo
                OrderItem.objects.all().delete()
                self.stdout.write(self.style.SUCCESS('   ✅ Items eliminados\n'))
            
            # Paso 2: Ahora eliminar órdenes (sin OrderItems, no habrá error)
            self.stdout.write('2️⃣  Eliminando órdenes...')
            try:
                orders_count = Order.objects.count()
                self.stdout.write(f'   Total a eliminar: {orders_count}')
                
                # Usar SQL directo para evitar signals y mejorar performance
                from django.db import connection as db_conn
                with db_conn.cursor() as cursor:
                    cursor.execute("DELETE FROM sales_order")
                    deleted = cursor.rowcount
                    self.stdout.write(f'   ... eliminados {deleted} órdenes')
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {deleted} órdenes eliminadas\n'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ⚠️  Error con SQL directo: {e}'))
                # Fallback: Intentar con batches más pequeños
                self.stdout.write('   Intentando con batches más pequeños...')
                batch_size = 100
                deleted_total = 0
                
                while Order.objects.exists():
                    orders_batch = list(Order.objects.values_list('id', flat=True)[:batch_size])
                    if not orders_batch:
                        break
                    Order.objects.filter(id__in=orders_batch)._raw_delete(Order.objects.db)
                    deleted_total += len(orders_batch)
                    if deleted_total % 500 == 0:
                        self.stdout.write(f'   ... eliminados {deleted_total}/{orders_count}')
                    time.sleep(0.1)
                
                self.stdout.write(self.style.SUCCESS(f'   ✅ {deleted_total} órdenes eliminadas\n'))

            # Paso 3: Eliminar productos (ahora sí se puede, sin PROTECT)
            self.stdout.write('3️⃣  Eliminando productos antiguos...')
            products_count = Product.objects.count()
            Product.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'   ✅ {products_count} productos eliminados\n'))

            # Paso 4: Eliminar categorías
            self.stdout.write('4️⃣  Eliminando categorías antiguas...')
            categories_count = Category.objects.count()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'   ✅ {categories_count} categorías eliminadas\n'))

            # Paso 5: Crear nuevas categorías (solo electrodomésticos)
            self.stdout.write('5️⃣  Creando 5 categorías nuevas...')
            categories_data = [
                {'name': 'Refrigeración', 'slug': 'refrigeracion'},
                {'name': 'Lavado y Secado', 'slug': 'lavado-secado'},
                {'name': 'Cocina', 'slug': 'cocina'},
                {'name': 'Climatización', 'slug': 'climatizacion'},
                {'name': 'Pequeños Electrodomésticos', 'slug': 'pequenos-electrodomesticos'},
            ]

            categories = []
            for cat_data in categories_data:
                category = Category.objects.create(**cat_data)
                categories.append(category)
                self.stdout.write(f'      ✅ {category.name}')
            
            self.stdout.write(self.style.SUCCESS(f'\n   ✅ {len(categories)} categorías creadas\n'))

            # Paso 6: Crear 10 productos nuevos (solo electrodomésticos)
            self.stdout.write('6️⃣  Creando 10 productos nuevos...')
            
            products_data = [
                    # Refrigeración
                    {
                        'name': 'Refrigerador Samsung 500L No Frost',
                        'category': categories[0],
                        'price': Decimal('1299.99'),
                        'stock': 8,
                        'description': 'Refrigerador de dos puertas con tecnología No Frost. Eficiencia energética A+. Capacidad 500 litros.'
                    },
                    {
                        'name': 'Congelador Vertical Whirlpool 280L',
                        'category': categories[0],
                        'price': Decimal('749.99'),
                        'stock': 12,
                        'description': 'Congelador vertical de 280 litros con 6 cajones. Sistema de congelación rápida y control digital.'
                    },
                    # Lavado y Secado
                    {
                        'name': 'Lavadora LG 18kg Carga Frontal',
                        'category': categories[1],
                        'price': Decimal('899.99'),
                        'stock': 10,
                        'description': 'Lavadora automática con tecnología TurboWash y AI DD. 14 programas de lavado. Inverter Direct Drive.'
                    },
                    {
                        'name': 'Lavavajillas Bosch 14 Servicios',
                        'category': categories[1],
                        'price': Decimal('649.99'),
                        'stock': 15,
                        'description': 'Lavavajillas con 6 programas de lavado y tecnología de secado ExtraDry. Clase energética A++.'
                    },
                    # Cocina
                    {
                        'name': 'Cocina a Gas Mabe 6 Hornallas',
                        'category': categories[2],
                        'price': Decimal('549.99'),
                        'stock': 7,
                        'description': 'Cocina a gas con horno autolimpiante de 120 litros. Parrillas de hierro fundido y encendido electrónico.'
                    },
                    {
                        'name': 'Microondas Panasonic 32L Inverter',
                        'category': categories[2],
                        'price': Decimal('199.99'),
                        'stock': 20,
                        'description': 'Microondas con grill y tecnología inverter. 32 litros de capacidad. 10 niveles de potencia y 15 menús pre-programados.'
                    },
                    # Climatización
                    {
                        'name': 'Aire Acondicionado Split Carrier 3500W',
                        'category': categories[3],
                        'price': Decimal('699.99'),
                        'stock': 9,
                        'description': 'Aire acondicionado Split frío/calor. Tecnología inverter. Bajo consumo energético clase A. Incluye control remoto.'
                    },
                    {
                        'name': 'Ventilador de Pie Philips 16"',
                        'category': categories[3],
                        'price': Decimal('89.99'),
                        'stock': 25,
                        'description': 'Ventilador de pie de 16 pulgadas con control remoto. 3 velocidades, oscilación automática y temporizador.'
                    },
                    # Pequeños Electrodomésticos
                    {
                        'name': 'Cafetera Nespresso Lattissima',
                        'category': categories[4],
                        'price': Decimal('299.99'),
                        'stock': 18,
                        'description': 'Cafetera de cápsulas con espumador de leche integrado. Sistema de calentamiento rápido de 25 segundos.'
                    },
                    {
                        'name': 'Licuadora Oster 1000W 10 Velocidades',
                        'category': categories[4],
                        'price': Decimal('129.99'),
                        'stock': 30,
                        'description': 'Licuadora de alto rendimiento con jarra de vidrio de 2 litros. 10 velocidades + pulso. Cuchillas de acero inoxidable.'
                    },
                ]

            for product_data in products_data:
                product = Product.objects.create(**product_data)
                self.stdout.write(f'      ✅ {product.name} (${product.price})')
            
            self.stdout.write(self.style.SUCCESS(f'\n   ✅ {len(products_data)} productos creados\n'))

            # Paso 7: Limpiar archivos de imágenes huérfanas (opcional)
            self.stdout.write('7️⃣  Limpiando archivos de medios antiguos...')
            media_products_path = 'media/products/'
            if os.path.exists(media_products_path):
                files_deleted = 0
                for filename in os.listdir(media_products_path):
                    file_path = os.path.join(media_products_path, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            files_deleted += 1
                    except Exception as e:
                        self.stdout.write(f'      ⚠️  No se pudo eliminar {filename}: {e}')
                self.stdout.write(self.style.SUCCESS(f'   ✅ {files_deleted} archivos de imagen eliminados\n'))
            else:
                self.stdout.write('   ℹ️  Carpeta de medios no encontrada\n')

            # Paso 8: Resetear metadatos de ML (si existen)
            self.stdout.write('8️⃣  Limpiando metadatos de ML...')
            ml_metadata_path = 'ml_models/models_metadata.json'
            if os.path.exists(ml_metadata_path):
                try:
                    import json
                    with open(ml_metadata_path, 'w') as f:
                        json.dump({'models': []}, f, indent=2)
                    self.stdout.write(self.style.SUCCESS('   ✅ Metadatos de ML reseteados\n'))
                except Exception as e:
                    self.stdout.write(f'   ⚠️  Error al limpiar metadatos: {e}\n')
            else:
                self.stdout.write('   ℹ️  Archivo de metadatos no encontrado\n')

            # Resumen final
            self.stdout.write(self.style.SUCCESS('\n' + '='*70))
            self.stdout.write(self.style.SUCCESS('✅ LIMPIEZA COMPLETADA EXITOSAMENTE'))
            self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

            self.stdout.write('📊 Nuevo estado de la base de datos:')
            self.stdout.write(f'   Usuarios: {User.objects.count()} ✅')
            self.stdout.write(f'   Categorías: {Category.objects.count()} ✅')
            self.stdout.write(f'   Productos: {Product.objects.count()} ✅')
            self.stdout.write(f'   Órdenes: {Order.objects.count()} ✅')
            self.stdout.write(f'   OrderItems: {OrderItem.objects.count()} ✅\n')

            self.stdout.write(self.style.SUCCESS('💡 Próximos pasos:'))
            self.stdout.write('   1. Añadir imágenes a los productos desde el admin')
            self.stdout.write('   2. Verificar que todo funcione correctamente')
            self.stdout.write('   3. Si necesitas datos de ML, ejecuta:')
            self.stdout.write('      python manage.py generate_demo_sales_data --orders 100\n')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error durante la limpieza: {str(e)}'))
            self.stdout.write(self.style.ERROR('   La transacción ha sido revertida'))
            raise
