"""
Tests para las vistas y endpoints del sistema de reclamaciones
Fase 3: Tests de Vistas/Endpoints
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
import base64

from claims.models import Claim, ClaimImage
from sales.models import Order, OrderItem
from products.models import Product, Category
from api.models import Profile


def get_response_data(response):
    """Helper para obtener datos de respuesta (paginada o no)"""
    if isinstance(response.data, dict) and 'results' in response.data:
        return response.data['results']
    return response.data


class ClaimViewSetTest(TestCase):
    """Tests para el ClaimViewSet"""
    
    def setUp(self):
        """Configuración inicial para los tests"""
        # Limpiar datos existentes
        Claim.objects.all().delete()
        ClaimImage.objects.all().delete()
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()
        
        self.client = APIClient()
        
        # Crear usuarios
        self.customer = User.objects.create_user(
            username='customer1',
            password='testpass123',
            email='customer@test.com'
        )
        # Asegurar que tenga perfil de cliente
        if hasattr(self.customer, 'profile'):
            self.customer.profile.role = Profile.Role.CLIENT
            self.customer.profile.save()
        
        self.admin = User.objects.create_user(
            username='admin1',
            password='adminpass123',
            email='admin@test.com',
            is_staff=True
        )
        # Asegurar que tenga perfil de admin
        if hasattr(self.admin, 'profile'):
            self.admin.profile.role = Profile.Role.ADMIN
            self.admin.profile.save()
        
        # Crear categoría y producto
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            description='Test Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        # Crear orden completada
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED,
            total_price=Decimal('999.99')
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
    
    def test_create_claim_authenticated_customer(self):
        """Test: Cliente autenticado puede crear reclamo"""
        self.client.force_authenticate(user=self.customer)
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Laptop defectuosa',
            'description': 'La pantalla no enciende',
            'damage_type': Claim.DamageType.FACTORY_DEFECT
        }
        
        response = self.client.post('/api/claims/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('ticket_number', response.data)
        self.assertEqual(response.data['title'], 'Laptop defectuosa')
        print(f"✓ Reclamo creado: {response.data['ticket_number']}")
    
    def test_create_claim_unauthenticated(self):
        """Test: Usuario no autenticado no puede crear reclamo"""
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Test',
            'description': 'Test'
        }
        
        response = self.client.post('/api/claims/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print("✓ Usuario no autenticado rechazado correctamente")
    
    def test_list_claims_customer_sees_only_own(self):
        """Test: Cliente solo ve sus propios reclamos"""
        # Crear reclamo del customer
        claim1 = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Mi reclamo',
            description='Test'
        )
        
        # Crear otro usuario y su reclamo
        other_customer = User.objects.create_user(
            username='othercustomer',
            password='pass123'
        )
        other_order = Order.objects.create(
            customer=other_customer,
            status=Order.OrderStatus.COMPLETED
        )
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        claim2 = Claim.objects.create(
            customer=other_customer,
            order=other_order,
            product=self.product,
            title='Reclamo de otro',
            description='Test'
        )
        
        # Autenticar como customer
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/claims/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = get_response_data(response)
        
        # Solo debe ver su propio reclamo
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Mi reclamo')
        print("✓ Cliente solo ve sus propios reclamos")
    
    def test_list_claims_admin_sees_all(self):
        """Test: Admin ve todos los reclamos"""
        # Crear varios reclamos
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Reclamo 1',
            description='Test'
        )
        
        other_customer = User.objects.create_user(
            username='othercustomer',
            password='pass123'
        )
        other_order = Order.objects.create(
            customer=other_customer,
            status=Order.OrderStatus.COMPLETED
        )
        OrderItem.objects.create(
            order=other_order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        Claim.objects.create(
            customer=other_customer,
            order=other_order,
            product=self.product,
            title='Reclamo 2',
            description='Test'
        )
        
        # Autenticar como admin
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/claims/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = get_response_data(response)
        
        # Admin debe ver todos los reclamos
        self.assertEqual(len(results), 2)
        print("✓ Admin ve todos los reclamos")
    
    def test_get_claim_detail(self):
        """Test: Obtener detalle de un reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Descripción detallada'
        )
        
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f'/api/claims/{claim.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Claim')
        self.assertIn('images', response.data)
        self.assertIn('history', response.data)
        print("✓ Detalle de reclamo obtenido correctamente")
    
    def test_update_status_by_admin(self):
        """Test: Admin puede actualizar estado del reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
        
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'status': Claim.ClaimStatus.IN_REVIEW,
            'admin_response': 'Estamos revisando tu caso',
            'priority': Claim.Priority.HIGH
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/update_status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Claim.ClaimStatus.IN_REVIEW)
        self.assertEqual(response.data['priority'], Claim.Priority.HIGH)
        print("✓ Admin actualizó estado correctamente")
    
    def test_update_status_by_customer_forbidden(self):
        """Test: Cliente no puede actualizar estado"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
        
        self.client.force_authenticate(user=self.customer)
        
        data = {
            'status': Claim.ClaimStatus.APPROVED
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/update_status/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        print("✓ Cliente no puede actualizar estado (correcto)")
    
    def test_add_feedback_by_customer(self):
        """Test: Cliente puede agregar feedback a reclamo resuelto"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test',
            status=Claim.ClaimStatus.RESOLVED
        )
        
        self.client.force_authenticate(user=self.customer)
        
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Excelente servicio, muy satisfecho'
        }
        
        response = self.client.patch(
            f'/api/claims/{claim.id}/add_feedback/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['customer_rating'], 5)
        print("✓ Cliente agregó feedback correctamente")
    
    def test_add_images_to_claim(self):
        """Test: Agregar imágenes adicionales a un reclamo"""
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
        
        self.client.force_authenticate(user=self.customer)
        
        # Crear imagen PNG válida de 1x1 pixel
        png_data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        image1 = SimpleUploadedFile('test1.png', png_data, content_type='image/png')
        image2 = SimpleUploadedFile('test2.png', png_data, content_type='image/png')
        
        response = self.client.post(
            f'/api/claims/{claim.id}/add_images/',
            {'images': [image1, image2]},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('images', response.data)
        
        # Verificar que se agregaron las imágenes
        claim.refresh_from_db()
        self.assertEqual(claim.images.count(), 2)
        print(f"✓ {claim.images.count()} imágenes agregadas correctamente")
    
    def test_my_claims_endpoint(self):
        """Test: Endpoint my_claims retorna solo reclamos del usuario"""
        # Crear varios reclamos
        for i in range(3):
            Claim.objects.create(
                customer=self.customer,
                order=self.order,
                product=self.product,
                title=f'Reclamo {i+1}',
                description='Test'
            )
        
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/claims/my_claims/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = get_response_data(response)
        
        self.assertEqual(len(results), 3)
        print("✓ Endpoint my_claims funciona correctamente")
    
    def test_statistics_endpoint_admin_only(self):
        """Test: Endpoint de estadísticas solo para admin"""
        # Crear algunos reclamos
        for i in range(5):
            Claim.objects.create(
                customer=self.customer,
                order=self.order,
                product=self.product,
                title=f'Reclamo {i+1}',
                description='Test',
                status=Claim.ClaimStatus.PENDING if i < 3 else Claim.ClaimStatus.RESOLVED
            )
        
        # Cliente no debe poder acceder
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/claims/statistics/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Admin debe poder acceder
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/claims/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('summary', response.data)
        self.assertIn('by_status', response.data)
        self.assertEqual(response.data['summary']['total_claims'], 5)
        print("✓ Estadísticas solo disponibles para admin")
    
    def test_filter_claims_by_status(self):
        """Test: Filtrar reclamos por estado"""
        # Crear reclamos con diferentes estados
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Pendiente',
            description='Test',
            status=Claim.ClaimStatus.PENDING
        )
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='En revisión',
            description='Test',
            status=Claim.ClaimStatus.IN_REVIEW
        )
        
        self.client.force_authenticate(user=self.customer)
        
        # Filtrar solo pendientes
        response = self.client.get('/api/claims/?status=PENDING')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = get_response_data(response)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['status'], Claim.ClaimStatus.PENDING)
        print("✓ Filtro por estado funciona correctamente")
    
    def test_search_claims(self):
        """Test: Búsqueda de reclamos por texto"""
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Laptop con pantalla rota',
            description='La pantalla está completamente rota'
        )
        Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Teclado defectuoso',
            description='El teclado no funciona'
        )
        
        self.client.force_authenticate(user=self.customer)
        
        # Buscar por "pantalla"
        response = self.client.get('/api/claims/?search=pantalla')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = get_response_data(response)
        
        self.assertEqual(len(results), 1)
        self.assertIn('pantalla', results[0]['title'].lower())
        print("✓ Búsqueda de reclamos funciona correctamente")


class ClaimPermissionsTest(TestCase):
    """Tests para permisos del sistema de reclamos"""
    
    def setUp(self):
        # Limpiar datos existentes
        Claim.objects.all().delete()
        Order.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        User.objects.all().delete()
        
        self.client = APIClient()
        
        self.customer1 = User.objects.create_user(
            username='customer1',
            password='pass123'
        )
        
        self.customer2 = User.objects.create_user(
            username='customer2',
            password='pass123'
        )
        
        self.category = Category.objects.create(name='Test', slug='test')
        self.product = Product.objects.create(
            category=self.category,
            name='Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        self.order1 = Order.objects.create(
            customer=self.customer1,
            status=Order.OrderStatus.COMPLETED
        )
        OrderItem.objects.create(
            order=self.order1,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer1,
            order=self.order1,
            product=self.product,
            title='Test',
            description='Test'
        )
    
    def test_customer_cannot_view_other_customer_claim(self):
        """Test: Un cliente no puede ver el reclamo de otro cliente"""
        self.client.force_authenticate(user=self.customer2)
        
        response = self.client.get(f'/api/claims/{self.claim.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        print("✓ Cliente no puede ver reclamos de otros")
    
    def test_customer_cannot_update_other_customer_claim(self):
        """Test: Un cliente no puede actualizar el reclamo de otro"""
        self.client.force_authenticate(user=self.customer2)
        
        data = {'customer_rating': 5}
        response = self.client.patch(
            f'/api/claims/{self.claim.id}/add_feedback/',
            data,
            format='json'
        )
        
        # Debería dar 404 porque no puede ver el reclamo
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        print("✓ Cliente no puede actualizar reclamos de otros")


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    import django
    django.setup()
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests.test_claims_views"])
