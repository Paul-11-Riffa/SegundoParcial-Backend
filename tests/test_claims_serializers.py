"""
Tests para los serializers del sistema de reclamaciones
Fase 2: Tests de Serializers
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory
from decimal import Decimal

from claims.serializers import (
    ClaimImageSerializer,
    ClaimHistorySerializer,
    ClaimListSerializer,
    ClaimDetailSerializer,
    ClaimCreateSerializer,
    ClaimUpdateSerializer,
    ClaimCustomerFeedbackSerializer
)
from claims.models import Claim, ClaimImage, ClaimHistory
from sales.models import Order, OrderItem
from products.models import Product, Category


class ClaimImageSerializerTest(TestCase):
    """Tests para ClaimImageSerializer"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Test Product',
            price=Decimal('100.00'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
    
    def test_serialize_claim_image(self):
        """Test: Serializar imagen de reclamo"""
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'fake image content',
            content_type='image/jpeg'
        )
        
        claim_image = ClaimImage.objects.create(
            claim=self.claim,
            image=image,
            description='Test image'
        )
        
        request = self.factory.get('/')
        serializer = ClaimImageSerializer(claim_image, context={'request': request})
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('image_url', data)
        self.assertIn('description', data)
        self.assertEqual(data['description'], 'Test image')
        print(f"✓ Imagen serializada correctamente: {data}")
    
    def test_validate_image_size(self):
        """Test: Validar tamaño máximo de imagen (5MB)"""
        # Crear imagen de 6MB (muy grande)
        large_image = SimpleUploadedFile(
            name='large_image.jpg',
            content=b'x' * (6 * 1024 * 1024),  # 6MB
            content_type='image/jpeg'
        )
        
        serializer = ClaimImageSerializer(data={
            'claim': self.claim.id,
            'image': large_image
        })
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('image', serializer.errors)
        print("✓ Validación de tamaño de imagen funciona correctamente")


class ClaimListSerializerTest(TestCase):
    """Tests para ClaimListSerializer"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Laptop dañada',
            description='La pantalla está rota',
            damage_type=Claim.DamageType.SHIPPING_DAMAGE
        )
    
    def test_serialize_claim_list(self):
        """Test: Serializar lista de reclamos"""
        serializer = ClaimListSerializer(self.claim)
        data = serializer.data
        
        self.assertIn('ticket_number', data)
        self.assertIn('product_name', data)
        self.assertEqual(data['product_name'], 'Laptop')
        self.assertIn('status_display', data)
        self.assertIn('priority_display', data)
        self.assertIn('images_count', data)
        self.assertEqual(data['images_count'], 0)
        print(f"✓ Lista de reclamos serializada: {data['ticket_number']}")
    
    def test_images_count(self):
        """Test: Contador de imágenes"""
        # Agregar 3 imágenes
        for i in range(3):
            image = SimpleUploadedFile(
                name=f'test_{i}.jpg',
                content=b'fake',
                content_type='image/jpeg'
            )
            ClaimImage.objects.create(claim=self.claim, image=image)
        
        serializer = ClaimListSerializer(self.claim)
        data = serializer.data
        
        self.assertEqual(data['images_count'], 3)
        print(f"✓ Contador de imágenes correcto: {data['images_count']}")


class ClaimDetailSerializerTest(TestCase):
    """Tests para ClaimDetailSerializer"""
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.admin = User.objects.create_user(
            username='testadmin',
            password='adminpass123',
            is_staff=True
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED,
            total_price=Decimal('999.99')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test',
            assigned_to=self.admin
        )
    
    def test_serialize_claim_detail(self):
        """Test: Serializar detalle completo de reclamo"""
        serializer = ClaimDetailSerializer(self.claim)
        data = serializer.data
        
        self.assertIn('ticket_number', data)
        self.assertIn('customer', data)
        self.assertIn('product', data)
        self.assertIn('assigned_to', data)
        self.assertIn('images', data)
        self.assertIn('history', data)
        self.assertIn('order_id', data)
        self.assertIn('order_total', data)
        self.assertEqual(data['order_id'], self.order.id)
        self.assertEqual(float(data['order_total']), 999.99)
        print(f"✓ Detalle de reclamo serializado completamente")


class ClaimCreateSerializerTest(TestCase):
    """Tests para ClaimCreateSerializer"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
    
    def test_create_claim_without_images(self):
        """Test: Crear reclamo sin imágenes"""
        request = self.factory.post('/')
        request.user = self.customer
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto defectuoso',
            'description': 'El producto llegó con defectos',
            'damage_type': Claim.DamageType.FACTORY_DEFECT
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        claim = serializer.save()
        
        self.assertIsNotNone(claim.ticket_number)
        self.assertEqual(claim.customer, self.customer)
        self.assertEqual(claim.product, self.product)
        self.assertEqual(claim.images.count(), 0)
        print(f"✓ Reclamo creado sin imágenes: {claim.ticket_number}")
    
    def test_create_claim_with_images(self):
        """Test: Crear reclamo con múltiples imágenes"""
        request = self.factory.post('/')
        request.user = self.customer
        
        # Crear imágenes PNG válidas de 1x1 pixel
        # Datos de una imagen PNG de 1x1 pixel en formato base64
        import base64
        png_data = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        
        images = [
            SimpleUploadedFile(
                name=f'test_{i}.png',
                content=png_data,
                content_type='image/png'
            ) for i in range(3)
        ]
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Producto dañado',
            'description': 'Daños visibles',
            'damage_type': Claim.DamageType.SHIPPING_DAMAGE,
            'images': images
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        claim = serializer.save()
        
        self.assertEqual(claim.images.count(), 3)
        print(f"✓ Reclamo creado con {claim.images.count()} imágenes")
    
    def test_validation_order_not_belongs_to_user(self):
        """Test: Validación - orden no pertenece al usuario"""
        other_customer = User.objects.create_user(
            username='othercustomer',
            password='pass123'
        )
        
        request = self.factory.post('/')
        request.user = other_customer
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': 'Test',
            'description': 'Test'
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        print("✓ Validación: orden debe pertenecer al usuario")
    
    def test_validation_order_not_completed(self):
        """Test: Validación - orden debe estar completada"""
        pending_order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.PENDING
        )
        
        OrderItem.objects.create(
            order=pending_order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        request = self.factory.post('/')
        request.user = self.customer
        
        data = {
            'order_id': pending_order.id,
            'product_id': self.product.id,
            'title': 'Test',
            'description': 'Test'
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('order_id', serializer.errors)
        print("✓ Validación: solo órdenes completadas")
    
    def test_validation_product_not_in_order(self):
        """Test: Validación - producto debe estar en la orden"""
        other_product = Product.objects.create(
            category=self.category,
            name='Other Product',
            price=Decimal('50.00'),
            stock=5
        )
        
        request = self.factory.post('/')
        request.user = self.customer
        
        data = {
            'order_id': self.order.id,
            'product_id': other_product.id,
            'title': 'Test',
            'description': 'Test'
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('product_id', serializer.errors)
        print("✓ Validación: producto debe estar en la orden")
    
    def test_validation_empty_title(self):
        """Test: Validación - título no puede estar vacío"""
        request = self.factory.post('/')
        request.user = self.customer
        
        data = {
            'order_id': self.order.id,
            'product_id': self.product.id,
            'title': '   ',  # Solo espacios
            'description': 'Test'
        }
        
        serializer = ClaimCreateSerializer(data=data, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('title', serializer.errors)
        print("✓ Validación: título no puede estar vacío")


class ClaimUpdateSerializerTest(TestCase):
    """Tests para ClaimUpdateSerializer"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.admin = User.objects.create_user(
            username='testadmin',
            password='adminpass123',
            is_staff=True
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test'
        )
    
    def test_update_claim_status(self):
        """Test: Actualizar estado del reclamo"""
        request = self.factory.patch('/')
        request.user = self.admin
        
        data = {
            'status': Claim.ClaimStatus.IN_REVIEW,
            'admin_response': 'Estamos revisando tu caso'
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.status, Claim.ClaimStatus.IN_REVIEW)
        self.assertEqual(updated_claim.admin_response, 'Estamos revisando tu caso')
        
        # Verificar que se creó entrada en historial
        self.assertGreater(updated_claim.history.count(), 1)
        print(f"✓ Reclamo actualizado y registrado en historial")
    
    def test_assign_claim_to_admin(self):
        """Test: Asignar reclamo a administrador"""
        request = self.factory.patch('/')
        request.user = self.admin
        
        data = {
            'assigned_to_id': self.admin.id
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.assigned_to, self.admin)
        print("✓ Reclamo asignado a administrador correctamente")
    
    def test_validation_assigned_to_non_staff(self):
        """Test: Validación - solo se puede asignar a staff"""
        request = self.factory.patch('/')
        request.user = self.admin
        
        data = {
            'assigned_to_id': self.customer.id  # No es staff
        }
        
        serializer = ClaimUpdateSerializer(
            self.claim,
            data=data,
            partial=True,
            context={'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('assigned_to_id', serializer.errors)
        print("✓ Validación: solo se puede asignar a administradores")


class ClaimCustomerFeedbackSerializerTest(TestCase):
    """Tests para ClaimCustomerFeedbackSerializer"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.customer = User.objects.create_user(
            username='testcustomer',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Electronics',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Laptop',
            price=Decimal('999.99'),
            stock=10
        )
        
        self.order = Order.objects.create(
            customer=self.customer,
            status=Order.OrderStatus.COMPLETED
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Test Claim',
            description='Test',
            status=Claim.ClaimStatus.RESOLVED
        )
    
    def test_add_customer_feedback(self):
        """Test: Agregar feedback del cliente"""
        request = self.factory.patch('/')
        request.user = self.customer
        
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Excelente servicio, muy satisfecho'
        }
        
        serializer = ClaimCustomerFeedbackSerializer(
            self.claim,
            data=data,
            context={'request': request}
        )
        
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_claim = serializer.save()
        
        self.assertEqual(updated_claim.customer_rating, 5)
        self.assertEqual(updated_claim.customer_feedback, 'Excelente servicio, muy satisfecho')
        print("✓ Feedback del cliente agregado correctamente")
    
    def test_validation_rating_range(self):
        """Test: Validación - calificación entre 1 y 5"""
        request = self.factory.patch('/')
        request.user = self.customer
        
        # Calificación inválida: 6
        data = {'customer_rating': 6}
        serializer = ClaimCustomerFeedbackSerializer(
            self.claim,
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('customer_rating', serializer.errors)
        
        # Calificación inválida: 0
        data = {'customer_rating': 0}
        serializer = ClaimCustomerFeedbackSerializer(
            self.claim,
            data=data,
            context={'request': request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('customer_rating', serializer.errors)
        
        print("✓ Validación de rango de calificación correcta")
    
    def test_validation_claim_must_be_resolved(self):
        """Test: Validación - solo se puede calificar reclamos resueltos"""
        pending_claim = Claim.objects.create(
            customer=self.customer,
            order=self.order,
            product=self.product,
            title='Pending Claim',
            description='Test',
            status=Claim.ClaimStatus.PENDING
        )
        
        request = self.factory.patch('/')
        request.user = self.customer
        
        data = {
            'customer_rating': 5,
            'customer_feedback': 'Test'
        }
        
        serializer = ClaimCustomerFeedbackSerializer(
            pending_claim,
            data=data,
            context={'request': request}
        )
        
        self.assertFalse(serializer.is_valid())
        print("✓ Validación: solo reclamos resueltos pueden ser calificados")


# Ejecutar tests si se ejecuta directamente
if __name__ == '__main__':
    import django
    django.setup()
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["claims.tests_serializers"])
