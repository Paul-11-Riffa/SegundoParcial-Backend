"""
Parser de comandos de voz para búsqueda de productos
Convierte lenguaje natural en parámetros de filtrado
"""
import re
import logging
from typing import Dict, List, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class ProductVoiceParser:
    """
    Parser inteligente para comandos de búsqueda de productos por voz
    Convierte comandos en lenguaje natural a parámetros de filtrado
    """
    
    # Palabras clave para detectar búsqueda
    SEARCH_KEYWORDS = [
        'buscar', 'busca', 'encuentra', 'encontrar', 'mostrar', 
        'muestra', 'ver', 'dame', 'quiero', 'necesito', 'hay',
        'cuales', 'cuáles', 'que', 'qué', 'listar', 'lista'
    ]
    
    # Palabras clave para precio bajo
    CHEAP_KEYWORDS = [
        'barato', 'baratos', 'baratas', 'económico', 'económicos', 'económicas',
        'bajo', 'bajos', 'baja', 'bajas', 'accesible', 'accesibles',
        'asequible', 'asequibles', 'módico'
    ]
    
    # Palabras clave para precio alto
    EXPENSIVE_KEYWORDS = [
        'caro', 'caros', 'cara', 'caras', 'costoso', 'costosos', 'costosas',
        'premium', 'alto', 'altos', 'alta', 'altas', 'exclusivo'
    ]
    
    # Palabras clave para stock
    STOCK_KEYWORDS = [
        'disponible', 'disponibles', 'en stock', 'stock', 'hay', 
        'tienen', 'que hay', 'que tienen', 'con stock', 'existencia'
    ]
    
    # Palabras clave para ordenamiento por novedad
    NEWEST_KEYWORDS = [
        'nuevo', 'nuevos', 'nueva', 'nuevas', 'reciente', 'recientes', 
        'último', 'últimos', 'última', 'últimas', 'recién llegado'
    ]
    
    # Palabras para ordenamiento
    ORDERING_KEYWORDS = {
        'mayor a menor precio': '-price',
        'de mayor a menor': '-price',
        'más caro primero': '-price',
        'menor a mayor precio': 'price',
        'de menor a mayor': 'price',
        'más barato primero': 'price',
        'ordenar por precio': 'price',
        'por precio': 'price',
    }
    
    # Categorías conocidas (sincronizar con la base de datos)
    CATEGORIES = {
        'refrigeracion': [
            'refrigerador', 'refrigeradores', 'congelador', 'congeladores', 
            'heladera', 'heladeras', 'freezer', 'nevera', 'neveras', 'frigorífico'
        ],
        'lavado-secado': [
            'lavadora', 'lavadoras', 'lavavajilla', 'lavavajillas', 
            'secadora', 'secadoras', 'lavarropas', 'lavasecarropas'
        ],
        'cocina': [
            'cocina', 'cocinas', 'microondas', 'horno', 'hornos',
            'anafe', 'anafes', 'estufa', 'estufas'
        ],
        'climatizacion': [
            'aire', 'aires', 'acondicionado', 'ventilador', 'ventiladores',
            'climatizador', 'climatizadores', 'split', 'calefactor'
        ],
        'pequenos-electrodomesticos': [
            'cafetera', 'cafeteras', 'licuadora', 'licuadoras',
            'batidora', 'batidoras', 'tostadora', 'tostadoras',
            'plancha', 'planchas', 'minipimer', 'procesadora'
        ]
    }
    
    def parse(self, text: str) -> Dict:
        """
        Parsea un comando de voz y retorna parámetros de filtrado
        
        Args:
            text: Comando en lenguaje natural
            
        Returns:
            {
                'success': bool,
                'search_term': str,
                'filters': dict,
                'confidence': float,
                'interpretation': str,
                'original_text': str
            }
        """
        logger.info(f"🎤 Parseando comando: '{text}'")
        
        original_text = text
        text_lower = text.lower().strip()
        
        if not text_lower:
            return {
                'success': False,
                'search_term': None,
                'filters': {},
                'confidence': 0.0,
                'interpretation': 'Comando vacío',
                'original_text': original_text,
                'error': 'El comando está vacío'
            }
        
        filters = {}
        search_terms = []
        confidence = 0.0
        interpretation_parts = []
        
        # 1. Detectar categoría
        category = self._detect_category(text_lower)
        if category:
            filters['category_slug'] = category
            confidence += 0.25
            interpretation_parts.append(f"Categoría: {category}")
            logger.info(f"   ✓ Categoría detectada: {category}")
        
        # 2. Detectar filtros de precio (incluye palabras clave y rangos)
        price_filter = self._detect_price_filter(text_lower)
        if price_filter:
            filters.update(price_filter)
            confidence += 0.25
            if 'price_min' in price_filter:
                interpretation_parts.append(f"Precio mín: ${price_filter['price_min']}")
            if 'price_max' in price_filter:
                interpretation_parts.append(f"Precio máx: ${price_filter['price_max']}")
            if 'ordering' in price_filter:
                order_desc = "descendente" if price_filter['ordering'].startswith('-') else "ascendente"
                interpretation_parts.append(f"Orden: precio {order_desc}")
            logger.info(f"   ✓ Filtro de precio: {price_filter}")
        
        # 3. Detectar filtro de stock
        if self._detect_stock_filter(text_lower):
            filters['in_stock'] = True
            confidence += 0.15
            interpretation_parts.append("Solo disponibles")
            logger.info(f"   ✓ Filtro de stock activado")
        
        # 4. Detectar ordenamiento especial
        ordering = self._detect_ordering(text_lower)
        if ordering and 'ordering' not in filters:
            filters['ordering'] = ordering
            confidence += 0.15
            order_name = self._get_ordering_name(ordering)
            interpretation_parts.append(f"Ordenar: {order_name}")
            logger.info(f"   ✓ Ordenamiento: {ordering}")
        
        # 5. Extraer palabras de búsqueda (productos específicos)
        search_term = self._extract_search_term(text_lower)
        if search_term:
            search_terms.append(search_term)
            confidence += 0.35
            interpretation_parts.append(f"Buscando: {search_term}")
            logger.info(f"   ✓ Término de búsqueda: {search_term}")
        
        # Combinar términos de búsqueda
        final_search = ' '.join(search_terms) if search_terms else None
        
        # Si no se detectó nada específico, usar todo el texto como búsqueda
        if not final_search and not filters:
            final_search = self._clean_search_keywords(text_lower)
            if final_search:
                confidence = 0.4
                interpretation_parts.append(f"Búsqueda general: {final_search}")
                logger.info(f"   ℹ Búsqueda general: {final_search}")
        
        # Asegurar mínimo de confianza si hay algo válido
        if (final_search or filters) and confidence < 0.3:
            confidence = 0.35
        
        # Si aún no hay confianza, el comando no es válido
        if confidence == 0.0:
            return {
                'success': False,
                'search_term': None,
                'filters': {},
                'confidence': 0.0,
                'interpretation': 'No se pudo interpretar el comando',
                'original_text': original_text,
                'error': 'No se detectaron criterios de búsqueda válidos'
            }
        
        interpretation = ' | '.join(interpretation_parts) if interpretation_parts else 'Búsqueda de productos'
        
        logger.info(f"   ✅ Parsing completado - Confianza: {confidence:.2%}")
        
        return {
            'success': True,
            'search_term': final_search,
            'filters': filters,
            'confidence': min(confidence, 1.0),
            'interpretation': interpretation,
            'original_text': original_text
        }
    
    def _detect_category(self, text: str) -> Optional[str]:
        """Detecta la categoría mencionada en el texto"""
        for category_slug, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                if re.search(rf'\b{re.escape(keyword)}\b', text):
                    return category_slug
        return None
    
    def _extract_search_term(self, text: str) -> Optional[str]:
        """Extrae el término principal de búsqueda"""
        # Crear copia del texto
        clean_text = text
        
        # Remover palabras clave de búsqueda
        for keyword in self.SEARCH_KEYWORDS:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Remover palabras de precio
        for keyword in self.CHEAP_KEYWORDS + self.EXPENSIVE_KEYWORDS:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Remover palabras de stock
        for keyword in self.STOCK_KEYWORDS:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Remover palabras de ordenamiento
        for phrase in self.ORDERING_KEYWORDS.keys():
            clean_text = clean_text.replace(phrase, '')
        
        # Remover palabras de novedad
        for keyword in self.NEWEST_KEYWORDS:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # ✨ NUEVO: Remover palabras de categorías detectadas
        # Si la categoría ya fue detectada, no usar esas palabras en la búsqueda
        for category_slug, keywords in self.CATEGORIES.items():
            for keyword in keywords:
                clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Remover patrones de precio
        clean_text = re.sub(r'entre\s+\d+\s+y\s+\d+', '', clean_text)
        clean_text = re.sub(r'(?:bajo|menor|menos de|hasta|sobre|mayor|más de|desde)\s+\d+', '', clean_text)
        clean_text = re.sub(r'\d+\s*(?:dolares|dólares|pesos|usd)', '', clean_text)
        
        # Remover palabras comunes y genéricas
        stop_words = [
            'de', 'la', 'el', 'los', 'las', 'un', 'una', 'unos', 'unas', 
            'con', 'sin', 'para', 'por', 'en', 'a',
            'producto', 'productos',  # ✨ NUEVO: palabras genéricas
            'articulo', 'artículos', 'artículo',
            'cosa', 'cosas', 'item', 'items'
        ]
        words = clean_text.split()
        words = [w for w in words if w not in stop_words]
        
        # Limpiar espacios extras
        result = ' '.join(words).strip()
        
        return result if result else None
    
    def _detect_price_filter(self, text: str) -> Dict:
        """Detecta filtros de precio y rangos"""
        filters = {}
        
        # Patrón: "entre X y Y" (con o sin palabras como dólares/pesos)
        range_patterns = [
            r'entre\s+(\d+(?:\.\d+)?)\s+y\s+(\d+(?:\.\d+)?)',
            r'de\s+(\d+(?:\.\d+)?)\s+a\s+(\d+(?:\.\d+)?)',
        ]
        
        for pattern in range_patterns:
            range_match = re.search(pattern, text)
            if range_match:
                filters['price_min'] = Decimal(range_match.group(1))
                filters['price_max'] = Decimal(range_match.group(2))
                return filters
        
        # Patrón: "bajo/menor/menos de X" o "hasta X"
        max_patterns = [
            r'(?:bajo|menor|menos de|hasta|máximo)\s+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:o menos|como máximo)'
        ]
        
        for pattern in max_patterns:
            max_match = re.search(pattern, text)
            if max_match:
                filters['price_max'] = Decimal(max_match.group(1))
                break
        
        # Patrón: "sobre/mayor/más de X" o "desde X"
        min_patterns = [
            r'(?:sobre|mayor|más de|desde|mínimo)\s+(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*(?:o más|como mínimo)'
        ]
        
        for pattern in min_patterns:
            min_match = re.search(pattern, text)
            if min_match:
                filters['price_min'] = Decimal(min_match.group(1))
                break
        
        # Palabras clave: "barato/económico" → ordenar ascendente
        if any(keyword in text for keyword in self.CHEAP_KEYWORDS):
            if 'ordering' not in filters:
                filters['ordering'] = 'price'
        
        # Palabras clave: "caro/premium" → ordenar descendente
        elif any(keyword in text for keyword in self.EXPENSIVE_KEYWORDS):
            if 'ordering' not in filters:
                filters['ordering'] = '-price'
        
        return filters
    
    def _detect_stock_filter(self, text: str) -> bool:
        """Detecta si se solicitan solo productos disponibles"""
        return any(keyword in text for keyword in self.STOCK_KEYWORDS)
    
    def _detect_ordering(self, text: str) -> Optional[str]:
        """Detecta el tipo de ordenamiento solicitado"""
        # Buscar frases específicas de ordenamiento
        for phrase, ordering in self.ORDERING_KEYWORDS.items():
            if phrase in text:
                return ordering
        
        # Palabras clave para productos nuevos/recientes
        if any(keyword in text for keyword in self.NEWEST_KEYWORDS):
            return '-created_at'
        
        return None
    
    def _clean_search_keywords(self, text: str) -> str:
        """Limpia palabras clave de búsqueda del texto para búsqueda general"""
        clean_text = text
        
        for keyword in self.SEARCH_KEYWORDS:
            clean_text = re.sub(rf'\b{re.escape(keyword)}\b', '', clean_text, flags=re.IGNORECASE)
        
        # Limpiar espacios extras
        return ' '.join(clean_text.split()).strip()
    
    def _get_ordering_name(self, ordering: str) -> str:
        """Obtiene nombre legible del ordenamiento"""
        ordering_names = {
            'price': 'Precio (menor a mayor)',
            '-price': 'Precio (mayor a menor)',
            '-created_at': 'Más recientes primero',
            'created_at': 'Más antiguos primero',
            'name': 'Nombre (A-Z)',
            '-name': 'Nombre (Z-A)',
        }
        return ordering_names.get(ordering, ordering)
