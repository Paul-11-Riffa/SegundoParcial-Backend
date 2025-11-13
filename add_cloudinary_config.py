"""
Script para agregar la configuración de Cloudinary a settings.py automáticamente
"""

settings_path = "backend/settings.py"

cloudinary_config = """

# ======================================
# CLOUDINARY CONFIGURATION (Media Storage)
# ======================================
import cloudinary
import cloudinary.uploader
import cloudinary.api

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME', default=''),
    'API_KEY': config('CLOUDINARY_API_KEY', default=''),
    'API_SECRET': config('CLOUDINARY_API_SECRET', default=''),
}

# Usar Cloudinary solo en producción
if not DEBUG:
    # Producción: Usar Cloudinary para media files
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
    CLOUDINARY_URL = config('CLOUDINARY_URL', default='')
else:
    # Desarrollo: Usar almacenamiento local
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
"""

# Leer el archivo actual
with open(settings_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar si ya tiene la configuración
if 'CLOUDINARY' in content:
    print("✅ Cloudinary ya está configurado en settings.py")
else:
    # Agregar al final
    with open(settings_path, 'a', encoding='utf-8') as f:
        f.write(cloudinary_config)
    print("✅ Configuración de Cloudinary agregada a settings.py")
