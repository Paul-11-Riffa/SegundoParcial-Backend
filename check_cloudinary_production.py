"""
Script de diagnóstico para verificar configuración de Cloudinary en producción.
Ejecutar con: python manage.py shell < check_cloudinary_production.py
"""

import os
import sys

print("=" * 80)
print("🔍 DIAGNÓSTICO DE CLOUDINARY EN PRODUCCIÓN")
print("=" * 80)

# 1. Verificar variables de entorno
print("\n1️⃣ VARIABLES DE ENTORNO:")
print("-" * 80)

env_vars = {
    'DEBUG': os.environ.get('DEBUG'),
    'CLOUDINARY_CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'CLOUDINARY_API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'CLOUDINARY_API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
    'CLOUDINARY_URL': os.environ.get('CLOUDINARY_URL'),
}

for key, value in env_vars.items():
    if key == 'CLOUDINARY_API_SECRET':
        display_value = f"{value[:4]}...{value[-4:]}" if value else "❌ NO CONFIGURADA"
    elif value:
        display_value = f"✅ {value}"
    else:
        display_value = "❌ NO CONFIGURADA"
    
    print(f"{key:30} = {display_value}")

# 2. Verificar configuración de Django
print("\n2️⃣ CONFIGURACIÓN DE DJANGO:")
print("-" * 80)

from django.conf import settings

print(f"DEBUG = {settings.DEBUG}")
print(f"DEFAULT_FILE_STORAGE = {getattr(settings, 'DEFAULT_FILE_STORAGE', 'NO CONFIGURADO')}")

if hasattr(settings, 'CLOUDINARY_STORAGE'):
    print(f"CLOUDINARY_STORAGE = {settings.CLOUDINARY_STORAGE}")
else:
    print("❌ CLOUDINARY_STORAGE NO EXISTE")

# 3. Verificar si Cloudinary está instalado
print("\n3️⃣ MÓDULOS INSTALADOS:")
print("-" * 80)

try:
    import cloudinary
    print(f"✅ cloudinary instalado - versión: {cloudinary.__version__}")
except ImportError as e:
    print(f"❌ cloudinary NO instalado: {e}")

try:
    import cloudinary_storage
    print(f"✅ cloudinary_storage instalado")
except ImportError as e:
    print(f"❌ cloudinary_storage NO instalado: {e}")

# 4. Verificar INSTALLED_APPS
print("\n4️⃣ INSTALLED_APPS:")
print("-" * 80)

cloudinary_apps = [app for app in settings.INSTALLED_APPS if 'cloudinary' in app.lower()]
if cloudinary_apps:
    for app in cloudinary_apps:
        print(f"✅ {app}")
else:
    print("❌ No hay apps de Cloudinary en INSTALLED_APPS")

# 5. Probar conexión a Cloudinary
print("\n5️⃣ PRUEBA DE CONEXIÓN:")
print("-" * 80)

if os.environ.get('CLOUDINARY_CLOUD_NAME'):
    try:
        import cloudinary
        cloudinary.config(
            cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key=os.environ.get('CLOUDINARY_API_KEY'),
            api_secret=os.environ.get('CLOUDINARY_API_SECRET')
        )
        
        # Intentar listar recursos
        result = cloudinary.api.ping()
        print(f"✅ CONEXIÓN EXITOSA: {result}")
    except Exception as e:
        print(f"❌ ERROR DE CONEXIÓN: {e}")
else:
    print("❌ No se puede probar la conexión - faltan variables de entorno")

# 6. Verificar el problema real
print("\n6️⃣ DIAGNÓSTICO DEL PROBLEMA:")
print("-" * 80)

issues = []

if settings.DEBUG:
    issues.append("⚠️  DEBUG=True (debería ser False en producción)")

if not os.environ.get('CLOUDINARY_CLOUD_NAME'):
    issues.append("❌ CLOUDINARY_CLOUD_NAME no está configurada en Render")

if not os.environ.get('CLOUDINARY_API_KEY'):
    issues.append("❌ CLOUDINARY_API_KEY no está configurada en Render")

if not os.environ.get('CLOUDINARY_API_SECRET'):
    issues.append("❌ CLOUDINARY_API_SECRET no está configurada en Render")

if not os.environ.get('CLOUDINARY_URL'):
    issues.append("❌ CLOUDINARY_URL no está configurada en Render")

storage = getattr(settings, 'DEFAULT_FILE_STORAGE', '')
if 'cloudinary' not in storage.lower():
    issues.append(f"❌ DEFAULT_FILE_STORAGE no apunta a Cloudinary: {storage}")

if issues:
    print("❌ PROBLEMAS ENCONTRADOS:")
    for issue in issues:
        print(f"   {issue}")
else:
    print("✅ Todo parece estar configurado correctamente")

print("\n" + "=" * 80)
print("📋 RESUMEN:")
print("=" * 80)

if not issues:
    print("✅ La configuración parece correcta.")
    print("   Si aún no funciona, intenta:")
    print("   1. Hacer un 'Clear Build Cache' en Render")
    print("   2. Hacer un 'Manual Deploy'")
else:
    print("❌ Se encontraron problemas. Debes:")
    if any('DEBUG' in issue for issue in issues):
        print("   1. Verificar que DEBUG=False en las variables de Render")
    if any('CLOUDINARY' in issue and 'no está configurada' in issue for issue in issues):
        print("   2. Agregar las 4 variables de Cloudinary en Render Dashboard")
    if any('DEFAULT_FILE_STORAGE' in issue for issue in issues):
        print("   3. Verificar que el código de settings.py esté correcto")

print("=" * 80)
