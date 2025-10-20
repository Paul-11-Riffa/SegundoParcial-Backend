"""
Tests para la funcionalidad de productos y categorías.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product, Category
from api.models import Profile


class CategoryTestCase(TestCase):
    """Tests para gestión de categorías"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.admin_user.profile.role = Profile.Role.ADMIN
        self.admin_user.profile.save()
        
        # Crear cliente
        self.client_user = User.objects.create_user(
            username='client',
            email='client@example.com',
            password='clientpass123'
        )
        
        # Crear categorías de prueba
        self.category1 = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        self.category2 = Category.objects.create(
            name='Books',
            slug='books'
        )
    
    def test_anyone_can_list_categories(self):
        """Test: Cualquiera puede listar categorías"""
        response = self.client.get('/api/products/categories/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_anyone_can_view_category_detail(self):
        """Test: Cualquiera puede ver detalle de categoría"""
        response = self.client.get(f'/api/products/categories/{self.category1.slug}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Electronics')
    
    def test_admin_can_create_category(self):
        """Test: Admin puede crear categorías"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'name': 'Clothing',
            'slug': 'clothing'
        }
        
        response = self.client.post('/api/products/categories/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 3)
    
    def test_admin_can_update_category(self):
        """Test: Admin puede actualizar categorías"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'name': 'Electronics & Gadgets',
            'slug': 'electronics-gadgets'
        }
        
        response = self.client.put(f'/api/products/categories/{self.category1.slug}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar cambios
        category = Category.objects.get(id=self.category1.id)
        self.assertEqual(category.name, 'Electronics & Gadgets')
    
    def test_admin_can_delete_category(self):
        """Test: Admin puede eliminar categorías"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        response = self.client.delete(f'/api/products/categories/{self.category2.slug}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 1)
    
    def test_client_cannot_create_category(self):
        """Test: Cliente no puede crear categorías"""
        # Login como cliente
        login_response = self.client.post('/api/auth/login/', {
            'username': 'client',
            'password': 'clientpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'name': 'Sports',
            'slug': 'sports'
        }
        
        response = self.client.post('/api/products/categories/', data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProductTestCase(TestCase):
    """Tests para gestión de productos"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_superuser=True
        )
        self.admin_user.profile.role = Profile.Role.ADMIN
        self.admin_user.profile.save()
        
        # Crear categoría
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        # Crear productos de prueba
        self.product1 = Product.objects.create(
            category=self.category,
            name='Laptop',
            description='High-end laptop',
            price=1200.00,
            stock=10
        )
        self.product2 = Product.objects.create(
            category=self.category,
            name='Mouse',
            description='Wireless mouse',
            price=25.00,
            stock=50
        )
        self.product3 = Product.objects.create(
            category=self.category,
            name='Keyboard',
            description='Mechanical keyboard',
            price=80.00,
            stock=0  # Sin stock
        )
    
    def test_anyone_can_list_products(self):
        """Test: Cualquiera puede listar productos"""
        response = self.client.get('/api/products/products/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_anyone_can_view_product_detail(self):
        """Test: Cualquiera puede ver detalle de producto"""
        response = self.client.get(f'/api/products/products/{self.product1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Laptop')
        self.assertEqual(float(response.data['price']), 1200.00)
    
    def test_filter_products_by_category(self):
        """Test: Filtrar productos por categoría"""
        response = self.client.get(f'/api/products/products/?category_slug={self.category.slug}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
    
    def test_filter_products_by_price_range(self):
        """Test: Filtrar productos por rango de precio"""
        response = self.client.get('/api/products/products/?price_min=20&price_max=100')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Mouse y Keyboard
    
    def test_filter_products_in_stock(self):
        """Test: Filtrar solo productos en stock"""
        response = self.client.get('/api/products/products/?in_stock=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Laptop y Mouse (Keyboard tiene stock 0)
    
    def test_search_products_by_name(self):
        """Test: Buscar productos por nombre"""
        response = self.client.get('/api/products/products/?search=laptop')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Laptop')
    
    def test_order_products_by_price(self):
        """Test: Ordenar productos por precio"""
        response = self.client.get('/api/products/products/?ordering=price')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que están ordenados de menor a mayor precio
        prices = [float(p['price']) for p in response.data]
        self.assertEqual(prices, sorted(prices))
    
    def test_admin_can_create_product(self):
        """Test: Admin puede crear productos"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'category': self.category.id,
            'name': 'Monitor',
            'description': '27-inch monitor',
            'price': 350.00,
            'stock': 15
        }
        
        response = self.client.post('/api/products/products/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 4)
    
    def test_admin_can_update_product(self):
        """Test: Admin puede actualizar productos"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'price': 1100.00,
            'stock': 15
        }
        
        response = self.client.patch(f'/api/products/products/{self.product1.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar cambios
        product = Product.objects.get(id=self.product1.id)
        self.assertEqual(float(product.price), 1100.00)
        self.assertEqual(product.stock, 15)
    
    def test_admin_can_delete_product(self):
        """Test: Admin puede eliminar productos"""
        # Login como admin
        login_response = self.client.post('/api/auth/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        response = self.client.delete(f'/api/products/products/{self.product3.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Product.objects.count(), 2)
    
    def test_client_cannot_create_product(self):
        """Test: Cliente no puede crear productos"""
        # Crear y hacer login como cliente
        client_user = User.objects.create_user(
            username='client',
            password='clientpass123'
        )
        
        login_response = self.client.post('/api/auth/login/', {
            'username': 'client',
            'password': 'clientpass123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {login_response.data["token"]}')
        
        data = {
            'category': self.category.id,
            'name': 'Headphones',
            'price': 50.00,
            'stock': 20
        }
        
        response = self.client.post('/api/products/products/', data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
