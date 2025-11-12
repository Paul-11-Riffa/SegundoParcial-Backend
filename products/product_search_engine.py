"""
Motor de búsqueda de productos basado en comandos de voz parseados
Ejecuta búsquedas en la base de datos según los parámetros interpretados
"""
import logging
from typing import Dict, Optional
from django.db.models import Q
from .models import Product
from .serializers import ProductSerializer

logger = logging.getLogger(__name__)


class ProductSearchEngine:
    """
    Ejecuta búsquedas de productos basadas en parámetros parseados del comando de voz
    """
    
    def search(
        self, 
        search_term: Optional[str] = None, 
        filters: Optional[Dict] = None, 
        user=None
    ) -> Dict:
        """
        Ejecuta búsqueda de productos con los parámetros especificados
        
        Args:
            search_term: Término de búsqueda principal (nombre/descripción)
            filters: Dict con filtros adicionales:
                - category_slug: str
                - price_min: Decimal
                - price_max: Decimal
                - in_stock: bool
                - ordering: str
            user: Usuario que ejecuta la búsqueda (para permisos)
            
        Returns:
            {
                'success': bool,
                'products': list,
                'total_results': int,
                'filters_applied': dict,
                'query_info': dict
            }
        """
        logger.info("🔍 Ejecutando búsqueda de productos")
        logger.info(f"   Término: {search_term}")
        logger.info(f"   Filtros: {filters}")
        
        # Iniciar con productos activos (optimizado con select_related)
        queryset = Product.objects.select_related('category').filter(is_active=True)
        
        filters = filters or {}
        filters_applied = {}
        
        # 1. Aplicar búsqueda por término (nombre o descripción)
        if search_term:
            # Normalizar búsqueda: intentar singular y plural
            # En español, muchos plurales terminan en 's', 'es'
            search_terms = [search_term]
            
            # Agregar variante singular si termina en 's' (laptops -> laptop)
            if search_term.endswith('s') and len(search_term) > 2:
                singular = search_term[:-1]
                search_terms.append(singular)
            
            # Agregar variante plural si no termina en 's' (laptop -> laptops)
            if not search_term.endswith('s'):
                plural = search_term + 's'
                search_terms.append(plural)
            
            # Buscar con todas las variantes (OR)
            q_filter = Q()
            for term in search_terms:
                q_filter |= Q(name__icontains=term) | Q(description__icontains=term)
            
            queryset = queryset.filter(q_filter)
            filters_applied['search'] = search_term
            logger.info(f"   ✓ Búsqueda por término: {search_term}")
            logger.info(f"   📊 Productos después de filtrar por término: {queryset.count()}")
        
        # 2. Filtrar por categoría
        if 'category_slug' in filters:
            queryset = queryset.filter(category__slug=filters['category_slug'])
            filters_applied['category'] = filters['category_slug']
            logger.info(f"   ✓ Filtro de categoría: {filters['category_slug']}")
        
        # 3. Filtrar por precio mínimo
        if 'price_min' in filters:
            queryset = queryset.filter(price__gte=filters['price_min'])
            filters_applied['price_min'] = str(filters['price_min'])
            logger.info(f"   ✓ Precio mínimo: ${filters['price_min']}")
        
        # 4. Filtrar por precio máximo
        if 'price_max' in filters:
            queryset = queryset.filter(price__lte=filters['price_max'])
            filters_applied['price_max'] = str(filters['price_max'])
            logger.info(f"   ✓ Precio máximo: ${filters['price_max']}")
        
        # 5. Filtrar solo productos con stock
        if filters.get('in_stock'):
            queryset = queryset.filter(stock__gt=0)
            filters_applied['in_stock'] = True
            logger.info(f"   ✓ Solo productos en stock")
        
        # 6. Aplicar ordenamiento
        if 'ordering' in filters:
            queryset = queryset.order_by(filters['ordering'])
            filters_applied['ordering'] = filters['ordering']
            logger.info(f"   ✓ Ordenamiento: {filters['ordering']}")
        else:
            # Orden por defecto: más recientes primero
            queryset = queryset.order_by('-created_at')
            filters_applied['ordering'] = '-created_at'
        
        # 7. Ejecutar query y serializar
        total_results = queryset.count()
        logger.info(f"   📊 Resultados encontrados: {total_results}")
        
        # Serializar productos
        products = ProductSerializer(queryset, many=True).data
        
        return {
            'success': True,
            'products': products,
            'total_results': total_results,
            'filters_applied': filters_applied,
            'query_info': {
                'search_term': search_term,
                'total_filters': len(filters_applied),
                'has_results': total_results > 0
            }
        }
    
    def get_suggestions(self, search_term: str, limit: int = 5) -> list:
        """
        Obtiene sugerencias de productos basadas en un término de búsqueda
        Útil para autocompletado o sugerencias cuando no hay resultados
        
        Args:
            search_term: Término de búsqueda
            limit: Número máximo de sugerencias
            
        Returns:
            Lista de nombres de productos sugeridos
        """
        if not search_term:
            return []
        
        products = Product.objects.filter(
            Q(name__icontains=search_term) | 
            Q(description__icontains=search_term),
            is_active=True
        ).values_list('name', flat=True)[:limit]
        
        return list(products)
