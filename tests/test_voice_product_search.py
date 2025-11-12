"""
Tests completos para el sistema de búsqueda de productos por comando de voz
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from products.models import Product, Category
from products.product_voice_parser import ProductVoiceParser
from products.product_search_engine import ProductSearchEngine
from decimal import Decimal


class ProductVoiceParserTestCase(TestCase):
    """Tests para el parser de comandos de voz"""
    
    def setUp(self):
        """Configuración inicial"""
        self.parser = ProductVoiceParser()
    
    def test_simple_search(self):
        """Test: Búsqueda simple por nombre de producto"""
        result = self.parser.parse("buscar laptops")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['search_term'], 'laptops')
        self.assertGreater(result['confidence'], 0.3)
        self.assertIn('Buscando: laptops', result['interpretation'])
    
    def test_search_with_cheap_filter(self):
        """Test: Búsqueda con filtro de productos baratos"""
        result = self.parser.parse("laptops baratas")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['search_term'], 'laptops')
        self.assertIn('ordering', result['filters'])
        self.assertEqual(result['filters']['ordering'], 'price')  # Ascendente
    
    def test_search_with_expensive_filter(self):
        """Test: Búsqueda con filtro de productos caros"""
        result = self.parser.parse("refrigeradores caros")
        
        self.assertTrue(result['success'])
        # "refrigeradores" se detecta como categoría
        self.assertEqual(result['filters'].get('category_slug'), 'refrigeracion')
        self.assertEqual(result['filters']['ordering'], '-price')  # Descendente
    
    def test_search_with_stock_filter(self):
        """Test: Búsqueda solo productos disponibles"""
        result = self.parser.parse("laptops disponibles")
        
        self.assertTrue(result['success'])
        self.assertTrue(result['filters'].get('in_stock'))
    
    def test_price_range_between(self):
        """Test: Rango de precio con 'entre X y Y'"""
        result = self.parser.parse("productos entre 100 y 500")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['price_min'], Decimal('100'))
        self.assertEqual(result['filters']['price_max'], Decimal('500'))
    
    def test_price_max_filter(self):
        """Test: Precio máximo con 'bajo/hasta X'"""
        result = self.parser.parse("productos bajo 300")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['price_max'], Decimal('300'))
    
    def test_price_min_filter(self):
        """Test: Precio mínimo con 'sobre/más de X'"""
        result = self.parser.parse("productos sobre 200")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['price_min'], Decimal('200'))
    
    def test_category_detection(self):
        """Test: Detección de categoría"""
        result = self.parser.parse("productos de cocina")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['category_slug'], 'cocina')
    
    def test_category_refrigeracion(self):
        """Test: Detección de categoría refrigeración"""
        result = self.parser.parse("buscar refrigeradores")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['category_slug'], 'refrigeracion')
    
    def test_newest_ordering(self):
        """Test: Ordenamiento por productos más recientes"""
        result = self.parser.parse("productos nuevos")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['filters']['ordering'], '-created_at')
    
    def test_combined_filters(self):
        """Test: Combinación de múltiples filtros"""
        result = self.parser.parse("laptops baratas en stock")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['search_term'], 'laptops')
        self.assertEqual(result['filters']['ordering'], 'price')
        self.assertTrue(result['filters']['in_stock'])
        self.assertGreater(result['confidence'], 0.5)
    
    def test_complex_command(self):
        """Test: Comando complejo con múltiples criterios"""
        result = self.parser.parse("buscar refrigeradores entre 500 y 1000 disponibles")
        
        self.assertTrue(result['success'])
        # Ahora "refrigeradores" se detecta como categoría, no como búsqueda
        self.assertEqual(result['filters'].get('category_slug'), 'refrigeracion')
        self.assertEqual(result['filters']['price_min'], Decimal('500'))
        self.assertEqual(result['filters']['price_max'], Decimal('1000'))
        self.assertTrue(result['filters']['in_stock'])
    
    def test_empty_command(self):
        """Test: Comando vacío"""
        result = self.parser.parse("")
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
    
    def test_low_confidence_command(self):
        """Test: Comando con baja confianza"""
        result = self.parser.parse("xyz abc")
        
        # Debería tener baja confianza pero no fallar
        self.assertLessEqual(result['confidence'], 0.5)
    
    def test_various_search_keywords(self):
        """Test: Diferentes palabras clave de búsqueda"""
        commands = [
            "mostrar laptops",
            "encuentra smartphones",  # Cambiado de refrigeradores a smartphones
            "dame tablets",  # Cambiado de "productos de cocina" que ahora es categoría
            "quiero ver televisores"  # Cambiado de licuadoras
        ]
        
        for cmd in commands:
            result = self.parser.parse(cmd)
            self.assertTrue(result['success'], f"Falló con: {cmd}")
            # Ahora puede tener search_term O category_slug
            has_search_or_category = result['search_term'] or result['filters'].get('category_slug')
            self.assertTrue(has_search_or_category, f"No detectó búsqueda ni categoría en: {cmd}")


class ProductSearchEngineTestCase(TestCase):
    """Tests para el motor de búsqueda de productos"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = APIClient()
        self.engine = ProductSearchEngine()
        
        # Crear categorías
        self.cat_electronics = Category.objects.create(
            name='Electrodomésticos',
            slug='electrodomesticos'
        )
        self.cat_kitchen = Category.objects.create(
            name='Cocina',
            slug='cocina'
        )
        
        # Crear productos
        self.laptop1 = Product.objects.create(
            category=self.cat_electronics,
            name='Laptop HP Pavilion',
            price=Decimal('599.99'),
            stock=10,
            description='Laptop para uso diario'
        )
        self.laptop2 = Product.objects.create(
            category=self.cat_electronics,
            name='Laptop Dell Inspiron',
            price=Decimal('799.99'),
            stock=5,
            description='Laptop profesional'
        )
        self.laptop3 = Product.objects.create(
            category=self.cat_electronics,
            name='Laptop Lenovo ThinkPad',
            price=Decimal('1299.99'),
            stock=0,  # Sin stock
            description='Laptop empresarial'
        )
        self.microwave = Product.objects.create(
            category=self.cat_kitchen,
            name='Microondas Panasonic',
            price=Decimal('199.99'),
            stock=15,
            description='Microondas 32L'
        )
    
    def test_search_by_term(self):
        """Test: Búsqueda por término simple"""
        result = self.engine.search(search_term='laptop')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 3)  # 3 laptops
    
    def test_search_with_price_min(self):
        """Test: Búsqueda con precio mínimo"""
        result = self.engine.search(
            search_term='laptop',
            filters={'price_min': Decimal('700')}
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 2)  # Solo las 2 más caras
    
    def test_search_with_price_max(self):
        """Test: Búsqueda con precio máximo"""
        result = self.engine.search(
            search_term='laptop',
            filters={'price_max': Decimal('800')}
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 2)  # Las 2 más baratas
    
    def test_search_with_price_range(self):
        """Test: Búsqueda con rango de precio"""
        result = self.engine.search(
            search_term='laptop',
            filters={
                'price_min': Decimal('600'),
                'price_max': Decimal('900')
            }
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 1)  # Solo la Dell
    
    def test_search_with_stock_filter(self):
        """Test: Búsqueda solo productos en stock"""
        result = self.engine.search(
            search_term='laptop',
            filters={'in_stock': True}
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 2)  # Solo las 2 con stock
    
    def test_search_by_category(self):
        """Test: Búsqueda por categoría"""
        result = self.engine.search(
            filters={'category_slug': 'cocina'}
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 1)  # Solo el microondas
    
    def test_search_ordering_price_asc(self):
        """Test: Ordenamiento por precio ascendente"""
        result = self.engine.search(
            search_term='laptop',
            filters={'ordering': 'price'}
        )
        
        self.assertTrue(result['success'])
        # Verificar que el primero es el más barato
        self.assertEqual(result['products'][0]['name'], 'Laptop HP Pavilion')
    
    def test_search_ordering_price_desc(self):
        """Test: Ordenamiento por precio descendente"""
        result = self.engine.search(
            search_term='laptop',
            filters={'ordering': '-price'}
        )
        
        self.assertTrue(result['success'])
        # Verificar que el primero es el más caro
        self.assertEqual(result['products'][0]['name'], 'Laptop Lenovo ThinkPad')
    
    def test_combined_filters(self):
        """Test: Combinación de múltiples filtros"""
        result = self.engine.search(
            search_term='laptop',
            filters={
                'price_max': Decimal('900'),
                'in_stock': True,
                'ordering': 'price'
            }
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 2)
        # Verificar orden
        self.assertEqual(result['products'][0]['name'], 'Laptop HP Pavilion')
        self.assertEqual(result['products'][1]['name'], 'Laptop Dell Inspiron')
    
    def test_no_results(self):
        """Test: Búsqueda sin resultados"""
        result = self.engine.search(search_term='celular')
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_results'], 0)
    
    def test_get_suggestions(self):
        """Test: Obtener sugerencias"""
        suggestions = self.engine.get_suggestions('lap')
        
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(all('Laptop' in s for s in suggestions))


class ProductVoiceSearchAPITestCase(TestCase):
    """Tests para el endpoint API de búsqueda por voz"""
    
    def setUp(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear usuario
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Crear categoría y productos
        self.category = Category.objects.create(
            name='Electrodomésticos',
            slug='electrodomesticos'
        )
        
        Product.objects.create(
            category=self.category,
            name='Laptop HP',
            price=Decimal('599.99'),
            stock=10
        )
        Product.objects.create(
            category=self.category,
            name='Laptop Dell',
            price=Decimal('899.99'),
            stock=5
        )
        
        # Login
        login_response = self.client.post('/api/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.token = login_response.data.get('token')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token}')
    
    def test_search_by_voice_simple(self):
        """Test: Búsqueda simple por voz"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'buscar laptops'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total_results'], 2)
        self.assertGreater(response.data['confidence'], 0.3)
    
    def test_search_by_voice_with_filters(self):
        """Test: Búsqueda con filtros de precio"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'laptops baratas'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('ordering', response.data['filters_applied'])
        self.assertEqual(response.data['filters_applied']['ordering'], 'price')
    
    def test_search_by_voice_no_text(self):
        """Test: Búsqueda sin enviar texto"""
        response = self.client.post('/api/shop/products/search_by_voice/', {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_search_by_voice_empty_text(self):
        """Test: Búsqueda con texto vacío"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': '   '
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_search_by_voice_no_results(self):
        """Test: Búsqueda sin resultados"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'buscar celulares'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['total_results'], 0)
        self.assertIn('message', response.data)
    
    def test_search_by_voice_complex_command(self):
        """Test: Comando complejo"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'laptops baratas en stock'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('in_stock', response.data['filters_applied'])
        self.assertIn('ordering', response.data['filters_applied'])
    
    def test_search_by_voice_unauthenticated(self):
        """Test: Búsqueda sin autenticación"""
        self.client.credentials()  # Remover credenciales
        
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'buscar laptops'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_response_structure(self):
        """Test: Verificar estructura de respuesta correcta"""
        response = self.client.post('/api/shop/products/search_by_voice/', {
            'text': 'buscar laptops'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar campos requeridos
        required_fields = [
            'success', 'query', 'interpretation', 'products', 
            'total_results', 'confidence', 'filters_applied'
        ]
        
        for field in required_fields:
            self.assertIn(field, response.data)
        
        # Verificar tipos
        self.assertIsInstance(response.data['success'], bool)
        self.assertIsInstance(response.data['products'], list)
        self.assertIsInstance(response.data['total_results'], int)
        self.assertIsInstance(response.data['confidence'], float)
        self.assertIsInstance(response.data['filters_applied'], dict)
