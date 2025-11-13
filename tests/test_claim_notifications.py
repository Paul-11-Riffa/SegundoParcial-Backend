"""
Test para verificar el sistema de notificaciones del módulo de reclamos.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from api.models import Profile
from products.models import Product, Category
from sales.models import Order, OrderItem
from claims.models import Claim
from notifications.models import Notification
import base64


class ClaimNotificationTest(TestCase):
    """Tests para verificar las notificaciones de reclamos."""
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Crear categoría
        self.category = Category.objects.create(
            name="Electrónicos",
            slug="electronicos"
        )
        
        # Crear producto
        self.product = Product.objects.create(
            name="Laptop Test",
            description="Laptop de prueba",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Crear cliente
        self.customer = User.objects.create_user(
            username="customer1",
            email="customer1@test.com",
            password="testpass123"
        )
        self.customer_profile = self.customer.profile  # El perfil se crea automáticamente
        self.customer_profile.role = "CLIENT"
        self.customer_profile.save()
        self.customer_token = Token.objects.create(user=self.customer)
        
        # Crear administrador
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin1@test.com",
            password="adminpass123",
            is_staff=True
        )
        self.admin_profile = self.admin.profile  # El perfil se crea automáticamente
        self.admin_profile.role = "ADMIN"
        self.admin_profile.save()
        self.admin_token = Token.objects.create(user=self.admin)
        
        # Crear segundo administrador
        self.admin2 = User.objects.create_user(
            username="admin2",
            email="admin2@test.com",
            password="adminpass123",
            is_staff=True
        )
        self.admin2_profile = self.admin2.profile  # El perfil se crea automáticamente
        self.admin2_profile.role = "ADMIN"
        self.admin2_profile.save()
        self.admin2_token = Token.objects.create(user=self.admin2)
        
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
        
        # Cliente API
        self.client_api = APIClient()
        
        # Imagen de prueba (PNG válido 1x1)
        self.test_image_base64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    
    def test_admin_receives_notification_on_new_claim(self):
        """Test que los administradores reciben notificación cuando se crea un nuevo reclamo."""
        # Autenticar como cliente
        self.client_api.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        
        # Contar notificaciones antes
        notifications_before_admin1 = Notification.objects.filter(user=self.admin).count()
        notifications_before_admin2 = Notification.objects.filter(user=self.admin2).count()
        
        # Crear reclamo
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'damage_type': 'FACTORY_DEFECT',
            'priority': 'MEDIUM',
            'description': 'El producto llegó con defectos de fábrica'
        }
        
        response = self.client_api.post('/api/claims/', data, format='json')
        if response.status_code != 201:
            print(f"\n❌ Error {response.status_code}: {response.data}")
        self.assertEqual(response.status_code, 201)
        
        # Verificar que se crearon notificaciones para ambos administradores
        notifications_after_admin1 = Notification.objects.filter(user=self.admin).count()
        notifications_after_admin2 = Notification.objects.filter(user=self.admin2).count()
        
        self.assertEqual(notifications_after_admin1, notifications_before_admin1 + 1)
        self.assertEqual(notifications_after_admin2, notifications_before_admin2 + 1)
        
        # Verificar contenido de la notificación
        notification_admin1 = Notification.objects.filter(user=self.admin).latest('created_at')
        self.assertEqual(notification_admin1.notification_type, 'CLAIM_CREATED')
        self.assertIn('nuevo reclamo', notification_admin1.title.lower())
        self.assertIn('customer1', notification_admin1.body)
    
    def test_customer_receives_notification_on_status_change(self):
        """Test que el cliente recibe notificación cuando cambia el estado de su reclamo."""
        # Crear reclamo manualmente
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            description='Producto defectuoso',
            status='PENDING'
        )
        
        # Contar notificaciones del cliente antes
        notifications_before = Notification.objects.filter(user=self.customer).count()
        
        # Autenticar como admin
        self.client_api.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Cambiar estado a IN_REVIEW
        response = self.client_api.patch(
            f'/api/claims/{claim.id}/update_status/',
            {'status': 'IN_REVIEW', 'admin_notes': 'Estamos revisando tu reclamo'},
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el cliente recibió notificación
        notifications_after = Notification.objects.filter(user=self.customer).count()
        self.assertEqual(notifications_after, notifications_before + 1)
        
        # Verificar contenido de la notificación
        notification = Notification.objects.filter(user=self.customer).latest('created_at')
        self.assertEqual(notification.notification_type, 'CLAIM_UPDATED')
        self.assertIn('actualización', notification.title.lower())
    
    def test_assigned_admin_receives_notification(self):
        """Test que el administrador asignado recibe notificación."""
        # Crear reclamo manualmente
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            description='Producto defectuoso',
            status='PENDING'
        )
        
        # Contar notificaciones de asignación del admin2 antes
        notifications_before = Notification.objects.filter(
            user=self.admin2,
            notification_type='CLAIM_ASSIGNED'
        ).count()
        
        # Autenticar como admin
        self.client_api.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Asignar reclamo a admin2
        response = self.client_api.patch(
            f'/api/claims/{claim.id}/update_status/',
            {'assigned_to_id': self.admin2.id, 'admin_response': 'Te asigno este reclamo'},
            format='json'
        )
        if response.status_code != 200:
            print(f"\n❌ Error al asignar: {response.status_code} - {response.data}")
        self.assertEqual(response.status_code, 200)
        
        # Verificar que admin2 recibió notificación de asignación
        notifications_after = Notification.objects.filter(
            user=self.admin2,
            notification_type='CLAIM_ASSIGNED'
        ).count()
        self.assertEqual(notifications_after, notifications_before + 1)
        
        # Verificar contenido de la notificación
        notification = Notification.objects.filter(user=self.admin2).latest('created_at')
        self.assertEqual(notification.notification_type, 'CLAIM_ASSIGNED')
        self.assertIn('asignado', notification.title.lower())
    
    def test_customer_receives_notification_on_resolution(self):
        """Test que el cliente recibe notificación cuando se resuelve su reclamo."""
        # Crear reclamo manualmente
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            description='Producto defectuoso',
            status='IN_REVIEW',
            assigned_to=self.admin
        )
        
        # Contar notificaciones del cliente antes
        notifications_before = Notification.objects.filter(user=self.customer).count()
        
        # Autenticar como admin
        self.client_api.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        
        # Resolver reclamo
        response = self.client_api.patch(
            f'/api/claims/{claim.id}/update_status/',
            {
                'status': 'RESOLVED',
                'resolution': 'Producto reemplazado',
                'admin_notes': 'Hemos enviado un producto nuevo'
            },
            format='json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verificar que el cliente recibió notificación
        notifications_after = Notification.objects.filter(user=self.customer).count()
        self.assertEqual(notifications_after, notifications_before + 1)
        
        # Verificar contenido de la notificación (debería ser CLAIM_RESOLVED)
        notification = Notification.objects.filter(user=self.customer).latest('created_at')
        self.assertEqual(notification.notification_type, 'CLAIM_RESOLVED')
        self.assertIn('reclamo', notification.title.lower())
    
    def test_no_duplicate_notifications(self):
        """Test que no se envían notificaciones duplicadas al mismo usuario."""
        # Crear reclamo
        claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Producto defectuoso',
            damage_type='FACTORY_DEFECT',
            priority='MEDIUM',
            description='Producto defectuoso',
            status='PENDING'
        )
        
        # Contar notificaciones
        initial_count = Notification.objects.filter(user=self.customer).count()
        
        # Actualizar descripción sin cambiar estado (no debería enviar notificación)
        claim.description = 'Producto defectuoso - actualizado'
        claim.save()
        
        # Verificar que no se crearon notificaciones nuevas
        final_count = Notification.objects.filter(user=self.customer).count()
        self.assertEqual(final_count, initial_count)
    
    def test_notification_contains_claim_details(self):
        """Test que las notificaciones contienen detalles relevantes del reclamo."""
        # Autenticar como cliente
        self.client_api.credentials(HTTP_AUTHORIZATION=f'Token {self.customer_token.key}')
        
        # Crear reclamo
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto llegó roto',
            'damage_type': 'SHIPPING_DAMAGE',
            'priority': 'HIGH',
            'description': 'Producto llegó completamente roto'
        }
        
        response = self.client_api.post('/api/claims/', data, format='json')
        self.assertEqual(response.status_code, 201)
        
        # Obtener notificación del admin
        notification = Notification.objects.filter(user=self.admin).latest('created_at')
        
        # Verificar que contiene información relevante
        self.assertIn('customer1', notification.body)  # Nombre del cliente
        claim_ticket = response.data['ticket_number']
        # El ticket debería estar en el título o body
        self.assertTrue(
            claim_ticket in notification.title or 
            claim_ticket in notification.body or
            (notification.data and claim_ticket in str(notification.data))
        )
