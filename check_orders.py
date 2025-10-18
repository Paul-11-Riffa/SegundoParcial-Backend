import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from sales.models import Order

# Ver últimas 5 órdenes completadas
print("=== ÓRDENES COMPLETADAS ===")
orders = Order.objects.filter(status='COMPLETED').order_by('-updated_at')[:5]
if orders:
    for o in orders:
        print(f"Orden {o.id}: {o.status} - Total: ${o.total_price} - Cliente: {o.customer.username} - Fecha: {o.updated_at}")
else:
    print("No hay órdenes completadas")

print("\n=== ÓRDENES PENDIENTES ===")
pending = Order.objects.filter(status='PENDING').order_by('-updated_at')[:5]
if pending:
    for o in pending:
        items_count = o.items.count()
        print(f"Orden {o.id}: {o.status} - Items: {items_count} - Total: ${o.total_price} - Cliente: {o.customer.username}")
else:
    print("No hay órdenes pendientes")