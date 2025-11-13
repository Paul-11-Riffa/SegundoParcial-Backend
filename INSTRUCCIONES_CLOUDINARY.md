# ✅ INSTRUCCIONES: Configuración de Cloudinary

## 📋 Paso 1: Actualizar requirements.txt

Abre `requirements.txt` y agrega estas 2 líneas al final:

```
cloudinary==1.41.0
django-cloudinary-storage==0.3.0
```

---

## 📋 Paso 2: Actualizar backend/settings.py

### 2.1: Agregar Cloudinary a INSTALLED_APPS

Busca la sección `INSTALLED_APPS` y agrégale `cloudinary_storage` y `cloudinary`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',  # ← AGREGAR ESTA LÍNEA
    'cloudinary',          # ← AGREGAR ESTA LÍNEA
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'api',
    'products',
    'sales',
    'notifications',
    'voice_commands',
    'claims',
]
```

### 2.2: Agregar configuración de Cloudinary al FINAL del archivo

Abre `backend/settings.py` y **al final del archivo** (después de GOOGLE_CLOUD_CREDENTIALS_PATH) agrega:

```python

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
```

---

## 📋 Paso 3: Crear cuenta en Cloudinary

1. Ve a: https://cloudinary.com/users/register/free
2. Regístrate (gratis, sin tarjeta de crédito)
3. En el Dashboard, copia estos 3 valores:
   - **Cloud Name** (ej: `dxxxxxxxx`)
   - **API Key** (ej: `123456789012345`)
   - **API Secret** (ej: `abcdefghijklmnopqrstuvwxyz`)

---

## 📋 Paso 4: Configurar variables en Render

Ve a **Render Dashboard** → **segundoparcial-backend** → **Environment**

Agrega estas 4 variables:

```
CLOUDINARY_CLOUD_NAME=<tu_cloud_name>
CLOUDINARY_API_KEY=<tu_api_key>
CLOUDINARY_API_SECRET=<tu_api_secret>
CLOUDINARY_URL=cloudinary://<tu_api_key>:<tu_api_secret>@<tu_cloud_name>
```

**Ejemplo** (reemplaza con tus datos reales):
```
CLOUDINARY_CLOUD_NAME=dxxxxxxxx
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz
CLOUDINARY_URL=cloudinary://123456789012345:abcdefghijklmnopqrstuvwxyz@dxxxxxxxx
```

---

## 📋 Paso 5: Actualizar .env local (opcional, para desarrollo)

Abre tu archivo `.env` y agrega:

```bash
# Cloudinary (opcional en desarrollo)
CLOUDINARY_CLOUD_NAME=tu_cloud_name
CLOUDINARY_API_KEY=tu_api_key
CLOUDINARY_API_SECRET=tu_api_secret
CLOUDINARY_URL=cloudinary://tu_api_key:tu_api_secret@tu_cloud_name
```

---

## 📋 Paso 6: Commit y Deploy

```powershell
git add .
git commit -m "Add Cloudinary for media storage in production"
git push origin main
```

Render automáticamente redesplegará (3-5 minutos).

---

## ✅ Verificar que Funciona

### 1. Ver logs en Render
- Deberías ver: `[INFO] Starting gunicorn` sin errores

### 2. Subir una imagen de producto
- Sube una imagen desde el admin o frontend
- La imagen se guardará en Cloudinary

### 3. Verificar la URL
El JSON del producto ahora devolverá:

**Antes** (No funciona):
```json
{
  "image": "https://segundoparcial-backend.onrender.com/media/products/imagen.jpg"
}
```

**Ahora** (Funciona):
```json
{
  "image": "https://res.cloudinary.com/tu_cloud_name/image/upload/v1234567890/products/imagen.jpg"
}
```

---

## 🎯 Resumen

### ✅ Frontend:
- **NO requiere cambios**
- Solo espera las URLs en el JSON

### ✅ Backend:
- ✅ Agregar cloudinary a `requirements.txt`
- ✅ Agregar cloudinary a `INSTALLED_APPS` en `settings.py`
- ✅ Agregar configuración de Cloudinary al final de `settings.py`
- ✅ Configurar variables en Render
- ✅ Deploy

**Tiempo total: 10-15 minutos** 🚀

---

## 🆘 Si necesitas ayuda

Avísame cuando:
1. Hayas creado tu cuenta en Cloudinary
2. Tengas tus credenciales (Cloud Name, API Key, API Secret)
3. Y te ayudo con los siguientes pasos

¿Ya creaste tu cuenta en Cloudinary? 😊
