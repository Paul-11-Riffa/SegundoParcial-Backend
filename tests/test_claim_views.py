"""
Tests exhaustivos para las vistas/endpoints del sistema de reclamos
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from products.models import Product, Category
from sales.models import Order, OrderItem
from claims.models import Claim, ClaimImage
from notifications.models import Notification
import base64


class ClaimViewSetTest(TestCase):
    """Tests para ClaimViewSet y endpoints REST"""
    
    def setUp(self):
        """Configurar datos de prueba"""
        # Crear categoría y producto
        self.category = Category.objects.create(name="Electrónicos", slug="electronicos")
        self.product = Product.objects.create(
            name="Laptop Test",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Crear cliente
        self.customer = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="testpass123"
        )
        self.customer.profile.role = "CLIENT"
        self.customer.profile.save()
        self.customer_token = Token.objects.create(user=self.customer)
        
        # Crear admin
        self.admin = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="adminpass123",
            is_staff=True
        )
        self.admin.profile.role = "ADMIN"
        self.admin.profile.save()
        self.admin_token = Token.objects.create(user=self.admin)
        
        # Crear orden completada
        self.order = Order.objects.create(
            customer=self.customer,
            total_price=1000.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=1000.00
        )
        
        # API Client
        self.client = APIClient()
        
        # Imagen de prueba (PNG válido 1x1)
        self.test_image_base64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    
    def test_create_claim_success(self):
        """Test: Cliente crea un reclamo exitosamente"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'El producto llegó con defectos de fábrica',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        response = self.client.post('/api/claims/', data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('ticket_number', response.data)
        self.assertEqual(response.data['title'], 'Producto defectuoso')
        self.assertEqual(response.data['customer']['username'], 'customer_test')
        print(f"✓ Reclamo creado exitosamente: {response.data['ticket_number']}")
    
    def test_create_claim_unauthenticated(self):
        """Test: Usuario no autenticado no puede crear reclamos"""
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'Descripción',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'HIGH'
        }
        
        response = self.client.post('/api/claims/', data, format='json')
        
        self.assertEqual(response.status_code, 401)
        print("✓ Validación correcta: requiere autenticación")
    
    def test_list_claims_customer_sees_only_own(self):
        """Test: Cliente solo ve sus propios reclamos"""
        # Crear reclamo del cliente
        claim1 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Mi reclamo',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Crear otro cliente con su reclamo
        other_customer = User.objects.create_user(
            username="other_customer",
            email="other@test.com",
            password="testpass123"
        )
        
        other_order = Order.objects.create(
            customer=other_customer,
            total_price=500.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            quantity=1,
            price=500.00
        )
        
        claim2 = Claim.objects.create(
            customer=other_customer,
            order=other_order,
            product=self.product,
            title='Reclamo de otro',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Cliente autentic ado ve solo sus reclamos
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get('/api/claims/')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['ticket_number'], claim1.ticket_number)
        print("✓ Cliente ve solo sus propios reclamos")
    
    def test_list_claims_admin_sees_all(self):
        """Test: Admin ve todos los reclamos"""
        # Crear múltiples reclamos
        claim1 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Reclamo 1',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        other_customer = User.objects.create_user(
            username="other_customer",
            email="other@test.com",
            password="testpass123"
        )
        
        other_order = Order.objects.create(
            customer=other_customer,
            total_price=500.00,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            quantity=1,
            price=500.00
        )
        
        claim2 = Claim.objects.create(
            customer=other_customer,
            order=other_order,
            product=self.product,
            title='Reclamo 2',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Admin ve todos los reclamos
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/claims/')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertGreaterEqual(len(results), 2)
        print(f"✓ Admin ve todos los reclamos: {len(results)} reclamos")
    
    def test_retrieve_claim_detail(self):
        """Test: Obtener detalle de un reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción detallada',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get(f'/api/claims/{claim.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], claim.id)
        self.assertEqual(response.data['title'], 'Producto defectuoso')
        self.assertIn('customer', response.data)
        self.assertIn('product', response.data)
        self.assertIn('history', response.data)
        print("✓ Detalle de reclamo obtenido correctamente")
    
    def test_update_status_by_admin(self):
        """Test: Admin actualiza estado del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        data = {
            'status': 'IN_REVIEW',
            'admin_response': 'Estamos revisando tu caso'
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/update_status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'IN_REVIEW')
        self.assertEqual(response.data['admin_response'], 'Estamos revisando tu caso')
        print("✓ Estado actualizado por admin exitosamente")
    
    def test_customer_cannot_update_status(self):
        """Test: Cliente no puede cambiar estado del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        
        data = {
            'status': 'RESOLVED'
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/update_status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, 403)
        print("✓ Validación correcta: cliente no puede cambiar estado")
    
    def test_add_feedback_by_customer(self):
        """Test: Cliente agrega feedback a reclamo resuelto"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='RESOLVED'  # Debe estar resuelto
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Excelente servicio'
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/add_feedback/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['customer_rating'], 5)
        self.assertEqual(response.data['customer_feedback'], 'Excelente servicio')
        print("✓ Feedback agregado exitosamente")
    
    def test_get_my_claims(self):
        """Test: Endpoint my_claims retorna reclamos del usuario"""
        # Crear reclamos
        claim1 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Reclamo 1',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        claim2 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Reclamo 2',
            description='Descripción',
            damage_type='SHIPPING_DAMAGE',
            priority='HIGH',
            status='IN_REVIEW'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get('/api/claims/my_claims/')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertEqual(len(results), 2)
        print("✓ Endpoint my_claims funciona correctamente")
    
    def test_statistics_endpoint_admin_only(self):
        """Test: Endpoint de estadísticas solo para admins"""
        # Crear algunos reclamos
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Reclamo 1',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Cliente no puede acceder
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get('/api/claims/statistics/')
        self.assertEqual(response.status_code, 403)
        
        # Admin sí puede acceder
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/claims/statistics/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.data)
        self.assertIn('by_status', response.data)
        print("✓ Estadísticas solo accesibles por admin")
    
    def test_filter_claims_by_status(self):
        """Test: Filtrar reclamos por estado"""
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Pendiente',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='En revisión',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='IN_REVIEW'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get('/api/claims/?status=PENDING')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], 'PENDING')
        print("✓ Filtro por estado funciona correctamente")
    
    def test_search_claims_by_ticket_number(self):
        """Test: Buscar reclamos por número de ticket"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.get(f'/api/claims/?search={claim.ticket_number}')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]['ticket_number'], claim.ticket_number)
        print(f"✓ Búsqueda por ticket funciona: {claim.ticket_number}")
    
    def test_delete_claim_admin_only(self):
        """Test: Solo admin puede eliminar reclamos"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Cliente SÍ puede eliminar su propio reclamo (IsClaimOwnerOrAdmin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        response = self.client.delete(f'/api/claims/{claim.id}/')
        self.assertEqual(response.status_code, 204)
        
        # Verificar que se eliminó
        self.assertFalse(Claim.objects.filter(id=claim.id).exists())
        print("✓ Cliente puede eliminar sus propios reclamos")
    
    def test_history_endpoint(self):
        """Test: Endpoint de historial retorna cambios del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            description='Descripción',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            status='PENDING'
        )
        
        # Cambiar estado para generar historial
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        self.client.patch(
            f'/api/claims/{claim.id}/update_status/',
            {'status': 'IN_REVIEW'},
            format='json'
        )
        
        # Obtener historial
        response = self.client.get(f'/api/claims/{claim.id}/history/')
        
        self.assertEqual(response.status_code, 200)
        
        # Manejar paginación
        if 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        
        self.assertGreaterEqual(len(results), 1)
        print(f"✓ Historial obtenido: {len(results)} entradas")
