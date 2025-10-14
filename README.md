# Backend Django - Segundo Parcial

Backend configurado con Django 5.2.7 y Django REST Framework.

## Tecnologías Instaladas

- Django 5.2.7
- Django REST Framework 3.16.1
- Django CORS Headers 4.9.0
- Python Decouple 3.8

## Estructura del Proyecto

```
SegundoParcial-Backend/
├── backend/           # Configuración principal del proyecto
│   ├── settings.py    # Configuración de Django
│   ├── urls.py        # URLs principales
│   └── wsgi.py
├── api/               # Aplicación API
│   ├── models.py      # Define tus modelos aquí
│   ├── views.py       # Define tus vistas aquí
│   ├── urls.py        # URLs de la API
│   └── serializers.py # Crea este archivo para los serializers
├── venv/              # Entorno virtual
├── manage.py          # Script de gestión de Django
├── requirements.txt   # Dependencias del proyecto
├── .env.example       # Ejemplo de variables de entorno
└── .gitignore         # Archivos ignorados por Git
```

## Instalación y Configuración

### 1. Clonar el repositorio (si aplica)
```bash
git clone <tu-repositorio>
cd SegundoParcial-Backend
```

### 2. Crear y activar el entorno virtual

**Windows:**
```bash
python -m venv venv
source venv/Scripts/activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (opcional)
```bash
cp .env.example .env
# Edita el archivo .env con tus configuraciones
```

### 5. Ejecutar migraciones
```bash
python manage.py migrate
```

### 6. Crear superusuario (opcional)
```bash
python manage.py createsuperuser
```

### 7. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

El servidor estará disponible en: http://127.0.0.1:8000/

## Endpoints Disponibles

- **Admin Panel:** http://127.0.0.1:8000/admin/
- **API:** http://127.0.0.1:8000/api/

## Configuración de CORS

El proyecto está configurado para aceptar peticiones desde:
- http://localhost:3000
- http://127.0.0.1:3000

Puedes modificar esto en el archivo `.env` o directamente en `backend/settings.py`.

## Próximos Pasos

1. Crear modelos en `api/models.py`
2. Crear serializers en `api/serializers.py`
3. Crear vistas en `api/views.py`
4. Configurar URLs en `api/urls.py`
5. Ejecutar migraciones cuando crees nuevos modelos:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## Comandos Útiles

```bash
# Crear una nueva aplicación
python manage.py startapp nombre_app

# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Ejecutar tests
python manage.py test

# Recolectar archivos estáticos
python manage.py collectstatic
```

## Notas

- La base de datos por defecto es SQLite3 (db.sqlite3)
- El proyecto usa Django REST Framework para crear APIs
- CORS está habilitado para desarrollo
- Las configuraciones sensibles deben ir en el archivo .env