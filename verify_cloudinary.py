"""
Script para verificar la configuración de Cloudinary en Render
Ejecuta esto DESPUÉS de agregar las variables en Render Environment
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from decouple import config

print("=" * 70)
print("🔍 VERIFICACIÓN DE CONFIGURACIÓN DE CLOUDINARY")
print("=" * 70)
print()

# 1. Verificar que Cloudinary esté instalado
try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    print("✅ Cloudinary instalado correctamente")
except ImportError as e:
    print(f"❌ Error: Cloudinary no está instalado: {e}")
    print("   Ejecuta: pip install cloudinary django-cloudinary-storage")
    sys.exit(1)

# 2. Verificar variables de entorno
print("\n📋 Variables de entorno:")
print("-" * 70)

cloud_name = config('CLOUDINARY_CLOUD_NAME', default='')
api_key = config('CLOUDINARY_API_KEY', default='')
api_secret = config('CLOUDINARY_API_SECRET', default='')
cloudinary_url = config('CLOUDINARY_URL', default='')

if cloud_name:
    print(f"✅ CLOUDINARY_CLOUD_NAME = {cloud_name}")
else:
    print("❌ CLOUDINARY_CLOUD_NAME = NO CONFIGURADA")

if api_key:
    print(f"✅ CLOUDINARY_API_KEY = {api_key[:4]}...{api_key[-4:]}")
else:
    print("❌ CLOUDINARY_API_KEY = NO CONFIGURADA")

if api_secret:
    print(f"✅ CLOUDINARY_API_SECRET = {api_secret[:4]}...{api_secret[-4:]}")
else:
    print("❌ CLOUDINARY_API_SECRET = NO CONFIGURADA")

if cloudinary_url:
    print(f"✅ CLOUDINARY_URL = cloudinary://...")
else:
    print("❌ CLOUDINARY_URL = NO CONFIGURADA")

# 3. Verificar configuración de Django
print("\n⚙️  Configuración de Django:")
print("-" * 70)

print(f"DEBUG = {settings.DEBUG}")

if hasattr(settings, 'DEFAULT_FILE_STORAGE'):
    print(f"✅ DEFAULT_FILE_STORAGE = {settings.DEFAULT_FILE_STORAGE}")
    if 'cloudinary' in settings.DEFAULT_FILE_STORAGE.lower():
        print("   ✅ Cloudinary está configurado como storage backend")
    else:
        print("   ⚠️  Cloudinary NO está configurado como storage backend")
else:
    print("⚠️  DEFAULT_FILE_STORAGE no está definido")

print(f"MEDIA_URL = {settings.MEDIA_URL}")
print(f"MEDIA_ROOT = {settings.MEDIA_ROOT}")

# 4. Verificar apps instaladas
print("\n📦 Apps instaladas:")
print("-" * 70)

if 'cloudinary' in settings.INSTALLED_APPS:
    print("✅ 'cloudinary' en INSTALLED_APPS")
else:
    print("❌ 'cloudinary' NO está en INSTALLED_APPS")

if 'cloudinary_storage' in settings.INSTALLED_APPS:
    print("✅ 'cloudinary_storage' en INSTALLED_APPS")
else:
    print("❌ 'cloudinary_storage' NO está en INSTALLED_APPS")

# 5. Test de conexión (solo si todas las variables están)
print("\n🔗 Test de conexión:")
print("-" * 70)

if cloud_name and api_key and api_secret:
    try:
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
        
        # Intentar obtener info de la cuenta
        result = cloudinary.api.ping()
        print(f"✅ Conexión exitosa a Cloudinary!")
        print(f"   Status: {result.get('status', 'OK')}")
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
else:
    print("⚠️  No se puede probar conexión (faltan variables de entorno)")

# Resumen final
print("\n" + "=" * 70)
print("📊 RESUMEN")
print("=" * 70)

all_ok = all([
    cloud_name,
    api_key,
    api_secret,
    cloudinary_url,
    'cloudinary' in settings.INSTALLED_APPS,
    'cloudinary_storage' in settings.INSTALLED_APPS,
])

if all_ok and not settings.DEBUG:
    print("✅ ¡TODO CONFIGURADO CORRECTAMENTE PARA PRODUCCIÓN!")
    print("\n📝 Próximos pasos:")
    print("   1. Hacer deploy en Render")
    print("   2. Subir imágenes desde el admin")
    print("   3. Las imágenes se guardarán automáticamente en Cloudinary")
elif settings.DEBUG:
    print("⚠️  Estás en modo DEBUG (desarrollo)")
    print("   Las imágenes se guardarán localmente, no en Cloudinary")
else:
    print("❌ CONFIGURACIÓN INCOMPLETA")
    print("\n🔧 Tareas pendientes:")
    if not cloud_name:
        print("   - Agregar CLOUDINARY_CLOUD_NAME en .env o Render")
    if not api_key:
        print("   - Agregar CLOUDINARY_API_KEY en .env o Render")
    if not api_secret:
        print("   - Agregar CLOUDINARY_API_SECRET en .env o Render")
    if not cloudinary_url:
        print("   - Agregar CLOUDINARY_URL en .env o Render")
    if 'cloudinary' not in settings.INSTALLED_APPS:
        print("   - Agregar 'cloudinary' a INSTALLED_APPS")
    if 'cloudinary_storage' not in settings.INSTALLED_APPS:
        print("   - Agregar 'cloudinary_storage' a INSTALLED_APPS")

print("=" * 70)
