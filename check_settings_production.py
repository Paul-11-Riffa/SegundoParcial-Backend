"""
Script para verificar la configuración de Django en producción.
Ejecutar: python check_settings_production.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings

print("=" * 80)
print("VERIFICACIÓN DE CONFIGURACIÓN DE PRODUCCIÓN")
print("=" * 80)

print(f"\n1. DEBUG = {settings.DEBUG}")

print(f"\n2. INSTALLED_APPS con Cloudinary:")
cloudinary_apps = [app for app in settings.INSTALLED_APPS if 'cloudinary' in app.lower()]
for app in cloudinary_apps:
    print(f"   ✅ {app}")

print(f"\n3. DEFAULT_FILE_STORAGE:")
storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'NO CONFIGURADO')
print(f"   {storage}")

if 'cloudinary' in storage.lower():
    print("   ✅ Apunta a Cloudinary")
else:
    print("   ❌ NO apunta a Cloudinary")

print(f"\n4. CLOUDINARY_STORAGE:")
if hasattr(settings, 'CLOUDINARY_STORAGE'):
    print(f"   CLOUD_NAME: {settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', 'NO CONFIGURADO')}")
    print(f"   API_KEY: {settings.CLOUDINARY_STORAGE.get('API_KEY', 'NO CONFIGURADO')}")
    api_secret = settings.CLOUDINARY_STORAGE.get('API_SECRET', '')
    if api_secret:
        print(f"   API_SECRET: {api_secret[:4]}...{api_secret[-4:]}")
    else:
        print(f"   API_SECRET: NO CONFIGURADO")
else:
    print("   ❌ CLOUDINARY_STORAGE no existe")

print(f"\n5. Variables de entorno:")
print(f"   CLOUDINARY_CLOUD_NAME: {os.getenv('CLOUDINARY_CLOUD_NAME', 'NO CONFIGURADO')}")
print(f"   CLOUDINARY_API_KEY: {os.getenv('CLOUDINARY_API_KEY', 'NO CONFIGURADO')}")
api_secret_env = os.getenv('CLOUDINARY_API_SECRET', '')
if api_secret_env:
    print(f"   CLOUDINARY_API_SECRET: {api_secret_env[:4]}...{api_secret_env[-4:]}")
else:
    print(f"   CLOUDINARY_API_SECRET: NO CONFIGURADO")

print("\n" + "=" * 80)

# Intentar subir un archivo de prueba
if not settings.DEBUG and 'cloudinary' in storage.lower():
    print("\n🧪 PRUEBA DE SUBIDA A CLOUDINARY:")
    print("=" * 80)
    try:
        import cloudinary.uploader
        from io import BytesIO
        from PIL import Image
        
        # Crear imagen de prueba
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Intentar subir
        result = cloudinary.uploader.upload(
            img_io,
            folder="test",
            public_id="django_test_image"
        )
        
        print(f"✅ SUBIDA EXITOSA!")
        print(f"   URL: {result.get('secure_url', result.get('url'))}")
        print(f"   Public ID: {result.get('public_id')}")
        
        # Eliminar imagen de prueba
        cloudinary.uploader.destroy(result.get('public_id'))
        print(f"✅ Imagen de prueba eliminada correctamente")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
