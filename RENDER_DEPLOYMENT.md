# Despliegue en Render.com

Este proyecto Django está configurado para desplegarse en Render.com.

## Pasos para Desplegar

### 1. Preparar el Repositorio
```bash
git add .
git commit -m "chore: Configuración para producción en Render"
git push origin main
```

### 2. Crear Servicio Web en Render

1. Ve a [Render.com](https://render.com) e inicia sesión
2. Click en "New +" → "Web Service"
3. Conecta tu repositorio de GitHub: `Paul-11-Riffa/SegundoParcial-Backend`
4. Configura el servicio:
   - **Name**: segundoparcial-backend
   - **Region**: Oregon (US West)
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn backend.wsgi:application`

### 3. Configurar Variables de Entorno

En Render Dashboard → tu servicio → Environment, agrega:

```bash
# Django
SECRET_KEY=<genera-una-nueva-con-python>
DEBUG=False
ALLOWED_HOSTS=tu-app.onrender.com

# CORS
CORS_ALLOWED_ORIGINS=https://tu-frontend.com

# Database (Neon PostgreSQL)
DB_NAME=tu_base_datos
DB_USER=tu_usuario
DB_PASSWORD=tu_contraseña
DB_HOST=ep-solitary-grass-ae1qvak0-pooler.c-2.us-east-2.aws.neon.tech
DB_PORT=5432

# Email
EMAIL_HOST_USER=paulriff.prb@gmail.com
EMAIL_HOST_PASSWORD=tu_app_password

# Stripe
STRIPE_PUBLIC_KEY=pk_live_xxxxxxxx
STRIPE_SECRET_KEY=sk_live_xxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxx

# Firebase (opcional - sube el archivo JSON)
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Google Cloud (opcional - sube el archivo JSON)
GOOGLE_CLOUD_CREDENTIALS_PATH=./google-cloud-credentials.json
```

### 4. Subir Archivos de Credenciales (Opcional)

Si usas Firebase o Google Cloud:

1. En Render Dashboard → tu servicio → Environment → Files
2. Sube `firebase-credentials.json`
3. Sube `google-cloud-credentials.json`

### 5. Desplegar

Render automáticamente desplegará tu aplicación cuando hagas push a `main`.

## Comando Correcto de Gunicorn

**IMPORTANTE**: El comando correcto para Django es:

```bash
gunicorn backend.wsgi:application
```

**NO uses**: `gunicorn app:app` (eso es para Flask)

## Estructura del Proyecto

```
backend/
  wsgi.py          ← Punto de entrada WSGI
  settings.py      ← Configuración Django
manage.py          ← Django management
build.sh           ← Script de construcción
requirements.txt   ← Dependencias Python
```

## Verificar el Despliegue

Después del despliegue, prueba:

```bash
curl https://tu-app.onrender.com/api/
```

## Troubleshooting

### Error: "No module named 'app'"
✅ **Solución**: Usa `gunicorn backend.wsgi:application` (no `app:app`)

### Error: "collectstatic failed"
✅ **Solución**: Verifica que `STATIC_ROOT` esté configurado en `settings.py`

### Error: "Database connection failed"
✅ **Solución**: Verifica las variables de entorno de la base de datos

### Error: "DisallowedHost"
✅ **Solución**: Agrega tu dominio de Render a `ALLOWED_HOSTS`

## Logs

Ver logs en tiempo real:
```bash
# En Render Dashboard → tu servicio → Logs
```

## Migraciones

Las migraciones se ejecutan automáticamente en `build.sh`:

```bash
python manage.py migrate --no-input
python manage.py collectstatic --no-input --clear
```

## Archivos Clave

- `build.sh` - Script de construcción (migraciones, static files)
- `render.yaml` - Configuración de infraestructura (opcional)
- `requirements.txt` - Dependencias Python
- `backend/wsgi.py` - Punto de entrada WSGI para Gunicorn
- `backend/settings.py` - Configuración Django (WhiteNoise, STATIC_ROOT)

## Generar SECRET_KEY

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Notas de Producción

✅ `DEBUG=False` en producción
✅ `gunicorn` instalado (`requirements.txt`)
✅ `whitenoise` para archivos estáticos
✅ `psycopg2-binary` para PostgreSQL
✅ Base de datos Neon (PostgreSQL)
✅ Archivos estáticos en `/staticfiles`
✅ HTTPS automático con Render

## Soporte

- Documentación Render: https://render.com/docs
- Troubleshooting: https://render.com/docs/troubleshooting-deploys
