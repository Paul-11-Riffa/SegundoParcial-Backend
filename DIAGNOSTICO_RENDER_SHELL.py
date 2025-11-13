"""
INSTRUCCIONES PARA DIAGNOSTICAR CLOUDINARY EN RENDER
=====================================================

1. Ve a tu servicio en Render Dashboard
2. Click en "Shell" en el menú lateral izquierdo
3. Espera a que cargue la terminal
4. Copia y pega este código línea por línea:

"""

# ===== COPIAR DESDE AQUÍ =====

import os
from django.conf import settings

print("\n" + "="*60)
print("DIAGNÓSTICO DE CLOUDINARY")
print("="*60)

# 1. Verificar DEBUG
print(f"\n1. DEBUG = {settings.DEBUG}")
if settings.DEBUG:
    print("   ⚠️  PROBLEMA: DEBUG debería ser False en producción")
else:
    print("   ✅ Correcto")

# 2. Verificar variables de entorno
print(f"\n2. Variables de entorno Cloudinary:")
vars_cloudinary = {
    'CLOUDINARY_CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'CLOUDINARY_API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'CLOUDINARY_API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
    'CLOUDINARY_URL': os.getenv('CLOUDINARY_URL'),
}

missing = []
for key, val in vars_cloudinary.items():
    if val:
        if 'SECRET' in key:
            print(f"   ✅ {key} = {val[:4]}...{val[-4:]}")
        else:
            print(f"   ✅ {key} = {val}")
    else:
        print(f"   ❌ {key} = NO CONFIGURADA")
        missing.append(key)

# 3. Verificar DEFAULT_FILE_STORAGE
print(f"\n3. DEFAULT_FILE_STORAGE:")
storage = getattr(settings, 'DEFAULT_FILE_STORAGE', 'NO CONFIGURADO')
print(f"   {storage}")

if 'cloudinary' in storage.lower():
    print("   ✅ Apunta a Cloudinary")
else:
    print("   ❌ NO apunta a Cloudinary")

# 4. Verificar módulos
print(f"\n4. Módulos instalados:")
try:
    import cloudinary
    print(f"   ✅ cloudinary")
except:
    print(f"   ❌ cloudinary NO INSTALADO")

try:
    import cloudinary_storage
    print(f"   ✅ cloudinary_storage")
except:
    print(f"   ❌ cloudinary_storage NO INSTALADO")

# RESUMEN
print("\n" + "="*60)
print("RESUMEN:")
print("="*60)

if missing:
    print("\n❌ FALTAN ESTAS VARIABLES EN RENDER:")
    for var in missing:
        print(f"   - {var}")
    print("\n👉 SOLUCIÓN:")
    print("   1. Ve a Render Dashboard > tu servicio")
    print("   2. Click en 'Environment'")
    print("   3. Agrega las 4 variables de Cloudinary")
    print("   4. Click en 'Save Changes'")
    print("   5. Espera 3-5 minutos al redeploy")
elif settings.DEBUG:
    print("\n❌ DEBUG=True en producción")
    print("👉 SOLUCIÓN: Agrega DEBUG=False en Render Environment")
elif 'cloudinary' not in storage.lower():
    print("\n❌ DEFAULT_FILE_STORAGE no apunta a Cloudinary")
    print("👉 Verifica que el código de settings.py esté correcto")
else:
    print("\n✅ TODO ESTÁ CONFIGURADO CORRECTAMENTE")
    print("   Si aún no funciona, haz un 'Manual Deploy' en Render")

print("="*60 + "\n")

# ===== HASTA AQUÍ =====
