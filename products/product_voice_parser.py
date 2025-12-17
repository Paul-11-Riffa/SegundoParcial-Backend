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
    
    # Palabras clave para detectar búsqueda (AMPLIADO)
    SEARCH_KEYWORDS = [
        # Verbos de búsqueda
        'buscar', 'busca', 'encuentra', 'encontrar', 'mostrar', 
        'muestra', 'ver', 'dame', 'quiero', 'necesito', 'hay',
        'cuales', 'cuáles', 'que', 'qué', 'listar', 'lista',
        # Nuevas variaciones conversacionales
        'tendrán', 'tienen', 'tienes', 'vendran', 'vendrán',
        'muestrame', 'muéstrame', 'enseñar', 'enseña', 'presentar',
        'conseguir', 'obtener', 'adquirir', 'comprar',
        'recomendar', 'recomienda', 'recomiéndame', 'sugerir', 'sugiere',
        'filtrar', 'filtra', 'seleccionar', 'selecciona',
        # Preguntas
        'cuanto', 'cuánto', 'cuantos', 'cuántos', 'donde', 'dónde',
        'puedo', 'podría', 'puedes', 'existe', 'existen',
        # Expresiones informales
        'ando buscando', 'estoy buscando', 'me interesa', 'me gustaría',
        'quisiera', 'querría', 'me hace falta', 'necesitaría'
    ]
    
    # Palabras clave para precio bajo (AMPLIADO)
    CHEAP_KEYWORDS = [
        # Palabras directas
        'barato', 'baratos', 'baratas', 'económico', 'económicos', 'económicas',
        'bajo', 'bajos', 'baja', 'bajas', 'accesible', 'accesibles',
        'asequible', 'asequibles', 'módico',
        # Nuevas expresiones
        'precio bajo', 'precio barato', 'precio económico',
        'buen precio', 'mejor precio', 'precio justo',
        'rebajado', 'rebajados', 'rebajada', 'rebajadas',
        'oferta', 'ofertas', 'promoción', 'promociones',
        'descuento', 'descuentos', 'descuentado',
        'ganga', 'gangas', 'chollo', 'chollos',
        'ahorro', 'ahorrar', 'conveniente', 'conviene',
        # Comparativos
        'menos costoso', 'no tan caro', 'más económico',
        'precio menor', 'costo menor', 'valor menor',
        # Presupuesto limitado
        'ajustado', 'limitado', 'presupuesto', 'alcance',
        'no muy caro', 'sin gastar mucho', 'gastar poco'
    ]
    
    # Palabras clave para precio alto (AMPLIADO)
    EXPENSIVE_KEYWORDS = [
        # Palabras directas
        'caro', 'caros', 'cara', 'caras', 'costoso', 'costosos', 'costosas',
        'premium', 'alto', 'altos', 'alta', 'altas', 'exclusivo',
        # Nuevas expresiones de calidad
        'alta calidad', 'alta gama', 'gama alta', 'top',
        'lujo', 'lujoso', 'lujosos', 'lujosa', 'lujosas',
        'exclusivo', 'exclusivos', 'exclusiva', 'exclusivas',
        'profesional', 'profesionales', 'pro',
        'primera línea', 'primera marca',
        # Marcas y calidad
        'mejor calidad', 'máxima calidad', 'buena calidad',
        'marca reconocida', 'marcas reconocidas',
        'importado', 'importados', 'importada',
        # Expresiones de precio
        'más caro', 'más costoso', 'precio alto',
        'precio elevado', 'valor alto',
        # Inversión
        'inversión', 'invertir', 'mejor producto',
        'sin importar el precio', 'precio no importa'
    ]
    
    # Palabras clave para stock (AMPLIADO)
    STOCK_KEYWORDS = [
        # Palabras directas
        'disponible', 'disponibles', 'en stock', 'stock', 'hay', 
        'tienen', 'que hay', 'que tienen', 'con stock', 'existencia',
        # Nuevas expresiones de disponibilidad
        'en existencia', 'con existencia', 'inventario',
        'que tengan', 'que haya', 'que esté', 'que estén',
        'puede comprar', 'puedo comprar', 'puedo llevar',
        'listo para llevar', 'listo para comprar',
        'inmediato', 'inmediata', 'ya disponible',
        # Entrega
        'entrega inmediata', 'disponible ya', 'pronto', 'ahora',
        'para hoy', 'para mañana', 'para llevar',
        # Preguntas sobre stock
        'tienen en stock', 'hay en stock', 'está disponible',
        'están disponibles', 'se puede conseguir', 'se consigue'
    ]
    
    # Palabras clave para novedad (AMPLIADO)
    NEWEST_KEYWORDS = [
        # Palabras directas
        'nuevo', 'nuevos', 'nueva', 'nuevas', 'reciente', 'recientes', 
        'último', 'últimos', 'última', 'últimas', 'recién llegado',
        # Nuevas expresiones de novedad
        'recién', 'acabar de llegar', 'acaban de llegar',
        'novedad', 'novedades', 'lanzamiento', 'lanzamientos',
        'estreno', 'estrenos', 'recién sacado', 'recién salido',
        # Actualidad y tendencia
        'actual', 'actuales', 'moderno', 'modernos', 'moderna',
        'modelo nuevo', 'modelos nuevos', 'nueva temporada',
        'de moda', 'tendencia', 'trending', 'popular',
        # Comparativos temporales
        'más nuevo', 'más reciente', 'este mes', 'este año',
        'del año', 'de este año', 'modelo 2024', 'modelo 2025',
        # Innovación
        'innovador', 'innovadores', 'última tecnología',
        'última generación', 'tecnología nueva'
    ]
    
    # Palabras para ordenamiento (AMPLIADO)
    ORDERING_KEYWORDS = {
        # Ordenamiento por precio - descendente (mayor a menor)
        'mayor a menor precio': '-price',
        'de mayor a menor': '-price',
        'más caro primero': '-price',
        'precio mayor primero': '-price',
        'precio descendente': '-price',
        'ordenar por precio descendente': '-price',
        'del más caro': '-price',
        'empezando por el más caro': '-price',
        
        # Ordenamiento por precio - ascendente (menor a mayor)
        'menor a mayor precio': 'price',
        'de menor a mayor': 'price',
        'más barato primero': 'price',
        'precio menor primero': 'price',
        'precio ascendente': 'price',
        'ordenar por precio': 'price',
        'por precio': 'price',
        'del más barato': 'price',
        'empezando por el más barato': 'price',
        'económicos primero': 'price',
        
        # Nuevas expresiones de ordenamiento
        'mejor precio primero': 'price',
        'precio bajo primero': 'price',
        'precios bajos': 'price',
        'precios altos': '-price',
        
        # Popularidad
        'más vendido': '-popularity',
        'más vendidos': '-popularity',
        'más popular': '-popularity',
        'más populares': '-popularity',
        'favoritos': '-popularity',
        'top ventas': '-popularity',
        'best seller': '-popularity',
        
        # Relevancia
        'más relevante': '-relevance',
        'relevantes': '-relevance',
        'mejor calificado': '-rating',
        'mejor calificados': '-rating',
        'mejor puntuación': '-rating',
    }
    
    # Categorías conocidas (AMPLIADO con más sinónimos)
    CATEGORIES = {
        'refrigeracion': [
            # Básicos
            'refrigerador', 'refrigeradores', 'congelador', 'congeladores', 
            'heladera', 'heladeras', 'freezer', 'nevera', 'neveras', 'frigorífico',
            # Nuevos sinónimos
            'refri', 'refris', 'refrigeradora', 'refrigeradoras',
            'conservadora', 'conservadoras', 'enfriador', 'enfriadores',
            'combo nevera', 'nevera congelador', 'frío',
            # Especificaciones comunes
            'una puerta', 'dos puertas', 'side by side', 'french door',
            'inverter', 'no frost', 'frost free',
            # Marcas comunes (opcional)
            'lg refrigerador', 'samsung refrigerador', 'whirlpool refrigerador'
        ],
        'lavado-secado': [
            # Básicos
            'lavadora', 'lavadoras', 'lavavajilla', 'lavavajillas', 
            'secadora', 'secadoras', 'lavarropas', 'lavasecarropas',
            # Nuevos sinónimos
            'lavado', 'secado', 'lava', 'seca', 'lavaseca',
            'lavadora secadora', 'centro de lavado', 'torre de lavado',
            'lavaplatos', 'lava platos', 'lava vajillas',
            # Tipos específicos
            'carga frontal', 'carga superior', 'top load', 'front load',
            'automática', 'semiautomática', 'manual',
            # Capacidades
            'kg', 'kilos', 'libras', 'capacidad'
        ],
        'cocina': [
            # Básicos
            'cocina', 'cocinas', 'microondas', 'horno', 'hornos',
            'anafe', 'anafes', 'estufa', 'estufas',
            # Nuevos sinónimos
            'micro', 'microonda', 'horno microondas',
            'horno eléctrico', 'horno a gas', 'horno de gas',
            'parrilla', 'parrillas', 'grill', 'asador',
            'vitroceramica', 'vitrocerámica', 'inducción',
            'quemador', 'quemadores', 'hornalla', 'hornallas',
            # Tipos
            'empotrable', 'empotrables', 'sobreponer',
            'industrial', 'domestica', 'doméstica',
            # Funcionalidades
            'convección', 'eléctrico', 'gas', 'dual'
        ],
        'climatizacion': [
            # Básicos
            'aire', 'aires', 'acondicionado', 'ventilador', 'ventiladores',
            'climatizador', 'climatizadores', 'split', 'calefactor',
            # Nuevos sinónimos
            'aire acondicionado', 'ac', 'a/c', 'aa',
            'enfriador', 'enfriadores', 'refrigeración de aire',
            'fan', 'abanico', 'turbo ventilador',
            'climatización', 'clima', 'confort térmico',
            # Tipos específicos
            'split pared', 'split piso', 'split techo',
            'portátil', 'portatil', 'ventana', 'central',
            'inverter', 'on-off', 'frío calor', 'solo frío',
            # Capacidades
            'btu', 'frigorías', 'frigorias', 'watts',
            'para habitación', 'para sala', 'para oficina',
            # Calefacción
            'calefacción', 'calefaccion', 'calor', 'calentar',
            'estufa', 'radiador', 'radiadores', 'caloventor'
        ],
        'pequenos-electrodomesticos': [
            # Básicos
            'cafetera', 'cafeteras', 'licuadora', 'licuadoras',
            'batidora', 'batidoras', 'tostadora', 'tostadoras',
            'plancha', 'planchas', 'minipimer', 'procesadora',
            # Nuevos sinónimos de cocina
            'exprimidor', 'exprimidores', 'juguera', 'extractor',
            'procesador de alimentos', 'picadora', 'picadoras',
            'molinillo', 'molinillos', 'mixer', 'batidor',
            # Café
            'cafetera eléctrica', 'cafetera express', 'cafetera italiana',
            'prensa francesa', 'espresso', 'nespresso', 'dolce gusto',
            # Preparación
            'sandwichera', 'sandwicheras', 'gofrera', 'waflera',
            'freidora', 'freidoras', 'air fryer', 'freidora de aire',
            'olla', 'ollas', 'arrocera', 'arroceras',
            'olla eléctrica', 'olla a presión', 'slow cooker',
            # Limpieza personal
            'plancha vapor', 'plancha seca', 'centro de planchado',
            'aspiradora', 'aspiradoras', 'robot aspirador',
            'aspiradora mano', 'aspiradora portátil',
            # Otros pequeños
            'hervidor', 'hervidores', 'pava eléctrica', 'tetera',
            'balanza', 'balanzas', 'báscula', 'peso cocina',
            'ventilador mesa', 'ventilador torre', 'ventilador pie'
        ],
        # NUEVAS CATEGORÍAS
        'audio-video': [
            'televisor', 'televisores', 'tv', 'smart tv', 'pantalla',
            'parlante', 'parlantes', 'bocina', 'bocinas', 'altavoz',
            'barra de sonido', 'soundbar', 'home theater',
            'auricular', 'auriculares', 'audífono', 'audífonos',
            'bluetooth speaker', 'parlante bluetooth'
        ],
        'computacion': [
            'computadora', 'computadoras', 'pc', 'laptop', 'notebook',
            'tablet', 'tableta', 'ipad', 'monitor', 'monitores',
            'teclado', 'teclados', 'mouse', 'ratón', 'impresora',
            'router', 'modem', 'wifi', 'disco duro', 'ssd',
            'memoria ram', 'pendrive', 'usb'
        ]
    }
    
    # ===== NUEVOS: Patrones de características específicas =====
    BRAND_PATTERNS = [
        'marca', 'marcas', 'fabricante', 'fabricantes',
        'lg', 'samsung', 'whirlpool', 'ge', 'mabe', 'frigidaire',
        'sony', 'panasonic', 'philips', 'bosch', 'electrolux',
        'midea', 'hisense', 'haier', 'carrier', 'trane'
    ]
    
    COLOR_PATTERNS = [
        'blanco', 'negro', 'gris', 'plata', 'plateado', 'silver',
        'acero', 'acero inoxidable', 'inox', 'metalico', 'metálico',
        'rojo', 'azul', 'verde', 'amarillo', 'rosa', 'dorado'
    ]
    
    SIZE_PATTERNS = [
        # Capacidades
        'litros', 'lts', 'l', 'galones', 'pies cúbicos', 'pies',
        'kg', 'kilos', 'libras', 'lb',
        # Dimensiones
        'pulgadas', 'pulgada', 'pulg', '"', 'pies', 'metros', 'cm',
        'grande', 'mediano', 'pequeño', 'chico', 'compacto',
        'familiar', 'personal', 'individual',
        # Capacidad específica
        'para familia', 'para dos personas', 'para soltero',
        'para oficina', 'para hogar', 'para negocio'
    ]
    
    ENERGY_PATTERNS = [
        'eficiente', 'eficiencia energética', 'ahorro energía',
        'clase a', 'clase a+', 'clase a++', 'clase a+++',
        'inverter', 'eco', 'ecológico', 'verde', 'green',
        'bajo consumo', 'ahorra luz', 'ahorra energía'
    ]
    
    FEATURE_PATTERNS = {
        'no_frost': ['no frost', 'frost free', 'sin hielo', 'sin escarcha', 'auto defrost'],
        'inverter': ['inverter', 'inverter tecnología', 'motor inverter'],
        'smart': ['smart', 'inteligente', 'wifi', 'conectado', 'app', 'internet'],
        'digital': ['digital', 'display digital', 'pantalla digital', 'táctil', 'touch'],
        'quiet': ['silencioso', 'silenciosa', 'bajo ruido', 'sin ruido', 'quiet'],
        'multi': ['multifunción', 'multifuncional', 'combo', '2 en 1', '3 en 1']
    }
    
    # Preguntas frecuentes y patterns conversacionales
    QUESTION_PATTERNS = [
        r'cuál es el (?:más|menos) (barato|caro|económico|costoso)',
        r'cuánto cuesta (?:un|una|el|la) (.+)',
        r'tienen (?:algún|alguna|un|una) (.+)',
        r'hay (?:algún|alguna|un|una) (.+) (?:disponible|en stock)',
        r'me (?:recomiendas|recomiendan|sugieres|sugieren) (?:un|una) (.+)',
        r'qué (?:.*) (?:me recomiendas|es mejor|conviene)',
        r'para (?:qué|que) sirve (?:un|una|el|la) (.+)',
        r'diferencia entre (.+) y (.+)',
        r'mejor (.+) (?:para|de) (.+)'
    ]
    
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
            confidence += 0.20
            interpretation_parts.append(f"Categoría: {category}")
            logger.info(f"   ✓ Categoría detectada: {category}")
        
        # 2. Detectar filtros de precio (incluye palabras clave y rangos)
        price_filter = self._detect_price_filter(text_lower)
        if price_filter:
            filters.update(price_filter)
            confidence += 0.20
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
            confidence += 0.10
            interpretation_parts.append("Solo disponibles")
            logger.info(f"   ✓ Filtro de stock activado")
        
        # 4. Detectar ordenamiento especial
        ordering = self._detect_ordering(text_lower)
        if ordering and 'ordering' not in filters:
            filters['ordering'] = ordering
            confidence += 0.10
            order_name = self._get_ordering_name(ordering)
            interpretation_parts.append(f"Ordenar: {order_name}")
            logger.info(f"   ✓ Ordenamiento: {ordering}")
        
        # 5. ===== NUEVO: Detectar marcas =====
        brand = self._detect_brand(text_lower)
        if brand:
            search_terms.append(brand)
            confidence += 0.10
            interpretation_parts.append(f"Marca: {brand}")
            logger.info(f"   ✓ Marca detectada: {brand}")
        
        # 6. ===== NUEVO: Detectar colores =====
        color = self._detect_color(text_lower)
        if color:
            search_terms.append(color)
            confidence += 0.08
            interpretation_parts.append(f"Color: {color}")
            logger.info(f"   ✓ Color detectado: {color}")
        
        # 7. ===== NUEVO: Detectar características especiales =====
        features = self._detect_features(text_lower)
        if features:
            search_terms.extend(features)
            confidence += 0.05 * len(features)
            interpretation_parts.append(f"Características: {', '.join(features)}")
            logger.info(f"   ✓ Características: {features}")
        
        # 8. ===== NUEVO: Detectar tamaño/capacidad =====
        size = self._detect_size(text_lower)
        if size:
            search_terms.append(size)
            confidence += 0.08
            interpretation_parts.append(f"Tamaño/Capacidad: {size}")
            logger.info(f"   ✓ Tamaño detectado: {size}")
        
        # 9. Extraer palabras de búsqueda (productos específicos)
        search_term = self._extract_search_term(text_lower)
        if search_term:
            search_terms.append(search_term)
            confidence += 0.25
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
            # Generar sugerencias para ayudar al usuario
            suggestions = self.generate_suggestions(text_lower, filters)
            
            return {
                'success': False,
                'search_term': None,
                'filters': {},
                'confidence': 0.0,
                'interpretation': 'No se pudo interpretar el comando',
                'original_text': original_text,
                'error': 'No se detectaron criterios de búsqueda válidos',
                'suggestions': suggestions
            }
        
        interpretation = ' | '.join(interpretation_parts) if interpretation_parts else 'Búsqueda de productos'
        
        # Generar sugerencias para refinar búsqueda (solo si confianza < 70%)
        suggestions = []
        if confidence < 0.7:
            suggestions = self.generate_suggestions(text_lower, filters)
        
        logger.info(f"   ✅ Parsing completado - Confianza: {confidence:.2%}")
        
        return {
            'success': True,
            'search_term': final_search,
            'filters': filters,
            'confidence': min(confidence, 1.0),
            'interpretation': interpretation,
            'original_text': original_text,
            'suggestions': suggestions,
            # Información adicional para el frontend
            'detected': {
                'category': category,
                'has_price_filter': bool(price_filter),
                'has_stock_filter': filters.get('in_stock', False),
                'has_ordering': filters.get('ordering'),
                'search_terms_count': len(search_terms)
            }
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
            '-popularity': 'Más vendidos primero',
            '-rating': 'Mejor calificados',
        }
        return ordering_names.get(ordering, ordering)
    
    # ===== NUEVOS MÉTODOS DE DETECCIÓN =====
    
    def _detect_brand(self, text: str) -> Optional[str]:
        """
        Detecta marcas mencionadas en el texto
        Retorna la marca encontrada o None
        """
        for brand in self.BRAND_PATTERNS:
            if brand.lower() in text and brand.lower() not in ['marca', 'marcas', 'fabricante', 'fabricantes']:
                logger.info(f"      → Marca encontrada: {brand}")
                return brand.upper()
        return None
    
    def _detect_color(self, text: str) -> Optional[str]:
        """
        Detecta colores mencionados en el texto
        Retorna el color encontrado o None
        """
        for color in self.COLOR_PATTERNS:
            if re.search(rf'\b{re.escape(color)}\b', text):
                logger.info(f"      → Color encontrado: {color}")
                return color
        return None
    
    def _detect_size(self, text: str) -> Optional[str]:
        """
        Detecta tamaños, capacidades o dimensiones específicas
        Retorna el tamaño encontrado o None
        """
        # Buscar patrones numéricos + unidad
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*(litros?|lts?|l\b)',
            r'(\d+(?:\.\d+)?)\s*(kg|kilos?|libras?|lb)',
            r'(\d+(?:\.\d+)?)\s*(pulgadas?|pulg|")',
            r'(\d+(?:\.\d+)?)\s*(pies|metros?|cm)',
            r'(\d+(?:\.\d+)?)\s*(btu|frigorías?)',
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text)
            if match:
                size_str = f"{match.group(1)} {match.group(2)}"
                logger.info(f"      → Tamaño/Capacidad encontrado: {size_str}")
                return size_str
        
        # Buscar palabras descriptivas de tamaño
        descriptive_sizes = ['grande', 'mediano', 'pequeño', 'chico', 'compacto', 'familiar']
        for size_word in descriptive_sizes:
            if re.search(rf'\b{size_word}\b', text):
                logger.info(f"      → Tamaño descriptivo encontrado: {size_word}")
                return size_word
        
        return None
    
    def _detect_features(self, text: str) -> List[str]:
        """
        Detecta características especiales mencionadas
        Retorna lista de características encontradas
        """
        found_features = []
        
        for feature_key, keywords in self.FEATURE_PATTERNS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    # Normalizar nombre de feature para mostrar
                    feature_name = {
                        'no_frost': 'No Frost',
                        'inverter': 'Inverter',
                        'smart': 'Smart/WiFi',
                        'digital': 'Display Digital',
                        'quiet': 'Silencioso',
                        'multi': 'Multifunción'
                    }.get(feature_key, feature_key)
                    
                    if feature_name not in found_features:
                        found_features.append(feature_name)
                        logger.info(f"      → Característica encontrada: {feature_name}")
                    break
        
        # Detectar eficiencia energética
        if any(keyword in text for keyword in self.ENERGY_PATTERNS):
            if 'Eficiencia Energética' not in found_features:
                found_features.append('Eficiencia Energética')
                logger.info(f"      → Característica encontrada: Eficiencia Energética")
        
        return found_features
    
    def _detect_question_intent(self, text: str) -> Optional[Dict[str, str]]:
        """
        Detecta si el comando es una pregunta y extrae la intención
        Retorna dict con tipo de pregunta e información extraída
        """
        for pattern in self.QUESTION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return {
                    'is_question': True,
                    'pattern': pattern,
                    'matches': match.groups()
                }
        return None
    
    def generate_suggestions(self, text: str, filters: Dict) -> List[str]:
        """
        Genera sugerencias basadas en el comando ingresado
        Ayuda al usuario a refinar su búsqueda
        """
        suggestions = []
        
        # Si no hay categoría, sugerir categorías relevantes
        if 'category_slug' not in filters:
            suggestions.append("💡 Intenta especificar una categoría como 'refrigeradores', 'lavadoras' o 'aires acondicionados'")
        
        # Si no hay filtro de precio, sugerirlo
        if 'price_min' not in filters and 'price_max' not in filters:
            suggestions.append("💡 Puedes agregar un rango de precio, por ejemplo: 'entre 500 y 1000'")
        
        # Si no especificó disponibilidad
        if 'in_stock' not in filters:
            suggestions.append("💡 Agrega 'disponible' o 'en stock' para ver solo productos que puedes comprar ya")
        
        # Sugerencias de características
        if not any(keyword in text.lower() for keywords in self.FEATURE_PATTERNS.values() for keyword in keywords):
            suggestions.append("💡 Puedes buscar por características como 'inverter', 'no frost', 'smart' o 'silencioso'")
        
        # Sugerencias de marca
        if not any(brand.lower() in text.lower() for brand in self.BRAND_PATTERNS):
            suggestions.append("💡 Especifica una marca preferida como 'LG', 'Samsung', 'Whirlpool', etc.")
        
        return suggestions[:3]  # Limitar a 3 sugerencias máximo

