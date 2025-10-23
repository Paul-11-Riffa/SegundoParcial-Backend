import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from products.models import Product
from django.core.files.storage import default_storage

print("🔍 Revisando productos y sus imágenes...\n")

products = Product.objects.all()

for product in products:
    if product.image:
        # Verificar si el archivo existe
        if not default_storage.exists(product.image.name):
            print(f"❌ {product.name} - Imagen no existe: {product.image.name}")
            # Limpiar la referencia de imagen
            product.image = None
            product.save()
            print(f"   ✅ Campo de imagen limpiado para {product.name}")
        else:
            print(f"✅ {product.name} - Imagen OK: {product.image.name}")
    else:
        print(f"⚠️  {product.name} - Sin imagen asignada")

print("\n✅ Proceso completado!")
