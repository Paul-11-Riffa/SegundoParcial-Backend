from django.core.management.base import BaseCommand
from sales.models import Order, OrderItem
from django.db.models import Count

class Command(BaseCommand):
    help = 'Elimina carritos duplicados (órdenes PENDING) manteniendo el más reciente'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🔍 Buscando carritos duplicados...\n'))
        
        # Encontrar usuarios con múltiples carritos PENDING
        users_with_duplicates = Order.objects.filter(status='PENDING').values('customer').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if not users_with_duplicates:
            self.stdout.write(self.style.SUCCESS('✅ No se encontraron carritos duplicados\n'))
            return
        
        total_deleted = 0
        
        for user_data in users_with_duplicates:
            user_id = user_data['customer']
            count = user_data['count']
            
            self.stdout.write(f'   Usuario ID {user_id}: {count} carritos PENDING')
            
            # Obtener todos los carritos del usuario ordenados por fecha (más reciente primero)
            carts = Order.objects.filter(
                customer_id=user_id, 
                status='PENDING'
            ).order_by('-created_at')
            
            # Mantener el más reciente (primero), eliminar los demás
            carts_to_delete = list(carts)[1:]
            
            for cart in carts_to_delete:
                items_count = cart.items.count()
                self.stdout.write(f'      Eliminando carrito ID {cart.id} ({items_count} items)')
                cart.delete()
                total_deleted += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Se eliminaron {total_deleted} carritos duplicados\n'))
        
        # Verificar que ya no haya duplicados
        remaining_duplicates = Order.objects.filter(status='PENDING').values('customer').annotate(
            count=Count('id')
        ).filter(count__gt=1).count()
        
        if remaining_duplicates == 0:
            self.stdout.write(self.style.SUCCESS('✅ Todos los carritos duplicados fueron eliminados\n'))
        else:
            self.stdout.write(self.style.ERROR(f'⚠️  Aún quedan {remaining_duplicates} usuarios con carritos duplicados\n'))
