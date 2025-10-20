# Sistema de Ventas - Backend API

Backend de un sistema de ventas en línea desarrollado con Django y Django REST Framework.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Tecnologías](#tecnologías)
- [Instalación](#instalación)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [API Endpoints](#api-endpoints)
- [Modelos](#modelos)
- [Permisos y Roles](#permisos-y-roles)
- [Filtros Avanzados](#filtros-avanzados)
- [Testing](#testing)

## ✨ Características

### Para Administradores
- ✅ **Gestión de Productos**
  - Registrar, modificar y eliminar productos
  - Especificar categoría, precio y stock
  - Subir imágenes de productos
  
- ✅ **Gestión de Categorías**
  - Crear, editar y eliminar categorías
  - Organizar productos por categorías
  
- ✅ **Gestión de Usuarios**
  - Registrar nuevos clientes
  - Modificar datos de cualquier usuario
  - Asignar roles (Admin/Cliente)
  - Consultar historial de compras de clientes
  
- ✅ **Reportes y Consultas**
  - Ver historial completo de ventas
  - Filtrar ventas por fecha, cliente, monto
  - Generar reportes en PDF y Excel
  - Reportes dinámicos con comandos de texto

### Para Clientes
- ✅ **Gestión de Cuenta**
  - Registrarse en el sistema
  - Modificar datos personales
  - Ver historial de compras propias
  
- ✅ **Proceso de Compra**
  - Ver catálogo de productos con filtros
  - Añadir productos al carrito
  - Modificar cantidades en el carrito
  - Eliminar productos del carrito
  - Completar compra con Stripe

- ✅ **Navegación y Búsqueda**
  - Filtrar por categoría, precio, stock
  - Buscar productos por nombre
  - Ver solo productos disponibles

## 🛠 Tecnologías

- **Django 5.2** - Framework web
- **Django REST Framework** - API REST
- **PostgreSQL** - Base de datos
- **Stripe** - Procesamiento de pagos
- **ReportLab** - Generación de PDFs
- **OpenPyXL** - Generación de reportes Excel
- **django-filter** - Filtrado avanzado
- **django-cors-headers** - CORS
- **Pillow** - Manejo de imágenes

## 📦 Instalación

### Prerequisitos

- Python 3.11+
- PostgreSQL
- pip

### Pasos

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/Paul-11-Riffa/SegundoParcial-Backend.git
   cd SegundoParcial-Backend
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install django djangorestframework django-filter django-cors-headers python-decouple pillow stripe reportlab openpyxl psycopg2-binary
   ```

4. **Configurar variables de entorno**
   
   Crear un archivo `.env` en la raíz del proyecto:
   ```env
   SECRET_KEY=tu-clave-secreta-aqui
   DEBUG=True
   DB_NAME=nombre_bd
   DB_USER=usuario_bd
   DB_PASSWORD=contraseña_bd
   DB_HOST=localhost
   DB_PORT=5432
   STRIPE_SECRET_KEY=tu-clave-stripe
   STRIPE_WEBHOOK_SECRET=tu-webhook-secret
   ```

5. **Ejecutar migraciones**
   ```bash
   python manage.py migrate
   ```

6. **Crear superusuario**
   ```bash
   python manage.py createsuperuser
   ```

7. **Ejecutar el servidor**
   ```bash
   python manage.py runserver
   ```

## 📁 Estructura del Proyecto

```
SegundoParcial-Backend/
├── api/                    # App de autenticación y usuarios
│   ├── models.py          # Modelo Profile con roles
│   ├── serializers.py     # Serializadores de usuario
│   ├── permissions.py     # Permisos personalizados
│   ├── views/
│   │   ├── auth.py       # Vistas de autenticación
│   │   └── user.py       # Gestión de usuarios (admin)
│   └── urls.py
│
├── products/              # App de productos y categorías
│   ├── models.py         # Models Category y Product
│   ├── serializers.py    # Serializadores
│   ├── filters.py        # Filtros avanzados de productos
│   ├── views.py          # ViewSets de productos/categorías
│   └── urls.py
│
├── sales/                # App de ventas y carrito
│   ├── models.py        # Models Order y OrderItem
│   ├── serializers.py   # Serializadores
│   ├── filters.py       # Filtros de ventas
│   ├── views.py         # Vistas de carrito y ventas
│   ├── excel_exporter.py     # Exportación a Excel
│   ├── prompt_parser.py      # Parser de comandos
│   └── report_generator.py   # Generador de reportes
│
├── tests/               # Tests del proyecto
│   ├── test_auth.py    # Tests de autenticación
│   ├── test_products.py # Tests de productos
│   └── test_sales.py    # Tests de ventas
│
└── backend/            # Configuración del proyecto
    ├── settings.py
    └── urls.py
```

## 🌐 API Endpoints

### Autenticación (`/api/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| POST | `/api/register/` | Registrar nuevo usuario | No |
| POST | `/api/login/` | Iniciar sesión | No |
| POST | `/api/logout/` | Cerrar sesión | Sí |
| GET | `/api/profile/` | Ver perfil propio | Sí |
| PUT | `/api/profile/` | Actualizar perfil propio | Sí |

### Gestión de Usuarios (`/api/`) - Solo Admin

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/users/` | Listar todos los usuarios |
| POST | `/api/users/` | Crear nuevo usuario |
| GET | `/api/users/{id}/` | Ver detalle de usuario |
| PUT/PATCH | `/api/users/{id}/` | Actualizar usuario |
| DELETE | `/api/users/{id}/` | Eliminar usuario |
| GET | `/api/clients/` | Listar solo clientes |

### Categorías (`/api/shop/categories/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/shop/categories/` | Listar categorías | No |
| POST | `/api/shop/categories/` | Crear categoría | Admin |
| GET | `/api/shop/categories/{slug}/` | Ver categoría | No |
| PUT/PATCH | `/api/shop/categories/{slug}/` | Actualizar categoría | Admin |
| DELETE | `/api/shop/categories/{slug}/` | Eliminar categoría | Admin |

### Productos (`/api/shop/products/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/shop/products/` | Listar productos | No |
| POST | `/api/shop/products/` | Crear producto | Admin |
| GET | `/api/shop/products/{id}/` | Ver producto | No |
| PUT/PATCH | `/api/shop/products/{id}/` | Actualizar producto | Admin |
| DELETE | `/api/shop/products/{id}/` | Eliminar producto | Admin |

**Filtros de productos:**
- `?name=laptop` - Buscar por nombre
- `?category_slug=electronics` - Filtrar por categoría
- `?price_min=100&price_max=500` - Rango de precio
- `?stock_min=10` - Stock mínimo
- `?in_stock=true` - Solo en stock
- `?ordering=-price` - Ordenar por precio descendente
- `?search=mouse` - Búsqueda en nombre y descripción

### Carrito de Compras (`/api/orders/cart/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/orders/cart/` | Ver carrito actual |
| POST | `/api/orders/cart/` | Añadir producto al carrito |
| PUT | `/api/orders/cart/items/{id}/` | Actualizar cantidad |
| DELETE | `/api/orders/cart/items/{id}/` | Eliminar item |

**Ejemplo añadir al carrito:**
```json
{
  "product_id": 5,
  "quantity": 2
}
```

### Órdenes y Ventas (`/api/orders/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET | `/api/orders/my-orders/` | Ver mis órdenes | Cliente |
| POST | `/api/orders/checkout/` | Procesar pago | Cliente |
| POST | `/api/orders/complete-order/` | Completar orden | Cliente |
| GET | `/api/orders/sales-history/` | Ver todas las ventas | Admin |
| GET | `/api/orders/sales-history/{id}/receipt/` | Generar recibo PDF | Admin |

**Filtros de ventas (solo admin):**
- `?start_date=2024-01-01` - Fecha inicio
- `?end_date=2024-12-31` - Fecha fin
- `?customer={id}` - Por ID de cliente
- `?customer_username=johndoe` - Por username
- `?customer_email=john@example.com` - Por email
- `?status=COMPLETED` - Por estado
- `?total_min=50&total_max=500` - Rango de monto
- `?ordering=-total_price` - Ordenar

### Reportes Dinámicos (`/api/orders/reports/`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/orders/reports/generate/` | Generar reporte dinámico |

**Ejemplo de comandos:**
```json
{
  "prompt": "ventas del 01/01/2024 al 31/12/2024 en pdf"
}
```

```json
{
  "prompt": "reporte de ventas de enero 2024 en excel"
}
```

```json
{
  "prompt": "mostrar ventas en pantalla"
}
```

## 📊 Modelos

### Profile (Usuario)
```python
- user: OneToOne -> User
- role: ADMIN | CLIENT
```

### Category
```python
- name: CharField (único)
- slug: SlugField (único)
```

### Product
```python
- category: ForeignKey -> Category
- name: CharField
- description: TextField
- price: DecimalField
- stock: PositiveIntegerField
- image: ImageField
- created_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)
```

### Order
```python
- customer: ForeignKey -> User
- status: PENDING | PROCESSING | COMPLETED | CANCELLED
- total_price: DecimalField
- created_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)
```

### OrderItem
```python
- order: ForeignKey -> Order
- product: ForeignKey -> Product
- quantity: PositiveIntegerField
- price: DecimalField (precio al momento de compra)
```

## 🔐 Permisos y Roles

### Roles Disponibles
- **ADMIN**: Acceso completo a todas las funcionalidades
- **CLIENT**: Acceso limitado a funcionalidades de cliente

### Permisos Personalizados

**IsAdminUser**: Solo permite acceso a usuarios con rol ADMIN
```python
# Usado en:
- Gestión de usuarios
- CRUD de categorías (excepto lectura)
- CRUD de productos (excepto lectura)
- Historial completo de ventas
- Generación de reportes
```

**IsAuthenticated**: Requiere que el usuario esté logueado
```python
# Usado en:
- Ver/actualizar perfil propio
- Carrito de compras
- Realizar pedidos
- Ver historial de compras propias
```

**AllowAny**: Acceso público
```python
# Usado en:
- Registro
- Login
- Listar productos
- Ver detalles de productos
- Listar categorías
```

## 🔍 Filtros Avanzados

### Filtros de Productos

La clase `ProductFilter` permite filtrado avanzado:

```python
# Por nombre (búsqueda parcial)
?name=laptop

# Por categoría
?category_slug=electronics
?category=5  # Por ID

# Por rango de precio
?price_min=100&price_max=500

# Por stock
?stock_min=10
?in_stock=true  # Solo con stock > 0

# Ordenamiento
?ordering=price           # Ascendente
?ordering=-price          # Descendente
?ordering=name
?ordering=-created_at
```

### Filtros de Ventas (Admin)

La clase `OrderFilter` permite filtrado avanzado de ventas:

```python
# Por fechas de creación
?start_date=2024-01-01
?end_date=2024-12-31

# Por fechas de completado
?completed_start=2024-01-01
?completed_end=2024-12-31

# Por cliente
?customer=5                      # ID
?customer_username=johndoe      # Username
?customer_email=john@example.com # Email

# Por estado
?status=COMPLETED

# Por monto
?total_min=50
?total_max=500

# Ordenamiento
?ordering=-total_price    # Mayor a menor
?ordering=created_at      # Más antiguas primero
?ordering=-updated_at     # Más recientes primero
```

## 🧪 Testing

El proyecto incluye tests completos para todas las funcionalidades:

### Ejecutar Tests

```bash
# Todos los tests
python manage.py test tests

# Tests específicos
python manage.py test tests.test_auth
python manage.py test tests.test_products
python manage.py test tests.test_sales

# Con verbosity
python manage.py test tests --verbosity=2
```

### Cobertura de Tests

**test_auth.py** (18 tests)
- Registro de usuarios
- Login con username/email
- Logout
- Gestión de perfil
- Gestión de usuarios (admin)
- Permisos y autorizaciones

**test_products.py** (17 tests)
- CRUD de categorías
- CRUD de productos
- Filtros y búsqueda
- Ordenamiento
- Permisos de admin vs cliente

**test_sales.py** (13 tests)
- Carrito de compras
- Añadir/modificar/eliminar items
- Validación de stock
- Historial de órdenes
- Filtros de ventas
- Gestión de stock al completar orden

## 📝 Ejemplos de Uso

### 1. Registrar un nuevo cliente

```bash
POST /api/register/
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

### 2. Login

```bash
POST /api/login/
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepass123"
}

# Respuesta:
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user_id": 1,
  "email": "john@example.com",
  "username": "johndoe"
}
```

### 3. Ver productos con filtros

```bash
GET /api/shop/products/?category_slug=electronics&price_max=1000&in_stock=true
```

### 4. Añadir producto al carrito

```bash
POST /api/orders/cart/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "product_id": 5,
  "quantity": 2
}
```

### 5. Ver historial de ventas (Admin)

```bash
GET /api/orders/sales-history/?start_date=2024-01-01&customer_username=johndoe&ordering=-total_price
Authorization: Token {admin_token}
```

### 6. Generar reporte dinámico

```bash
POST /api/orders/reports/generate/
Authorization: Token {admin_token}
Content-Type: application/json

{
  "prompt": "ventas de enero 2024 en excel"
}
```

## 🚀 Funcionalidades Avanzadas

### 1. Reportes Dinámicos

El sistema permite generar reportes mediante comandos de texto:

```python
# PDF
"ventas del 01/01/2024 al 31/12/2024 en pdf"

# Excel
"reporte de ventas de enero 2024 en excel"

# Pantalla (JSON)
"mostrar ventas en pantalla"

# Por año
"ventas del año 2024"

# Por mes
"ventas de diciembre 2024"
```

### 2. Integración con Stripe

- Checkout session para pagos seguros
- Webhooks para confirmación de pagos
- Reducción automática de stock
- Generación de recibos en PDF

### 3. Gestión Inteligente de Carrito

- Un carrito activo por usuario (estado PENDING)
- Validación automática de stock
- Cálculo automático de totales
- Actualización en tiempo real

## 📧 Contacto

- **Autor**: Paul Riffa
- **GitHub**: [Paul-11-Riffa](https://github.com/Paul-11-Riffa)
- **Repositorio**: [SegundoParcial-Backend](https://github.com/Paul-11-Riffa/SegundoParcial-Backend)

## 📄 Licencia

Este proyecto fue desarrollado como parte del Segundo Parcial de Backend.

---

**Nota**: Este README documenta la rama `Arreglando-funcionalidades` que incluye mejoras en filtros, tests completos y optimizaciones de código.
