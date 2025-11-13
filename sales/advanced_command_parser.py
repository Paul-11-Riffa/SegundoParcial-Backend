# sales/advanced_command_parser.py
"""
🎯 Parser Avanzado de Comandos para Reportes Ultra-Específicos
Detecta: clientes, productos, categorías, precios, cantidades, fechas, métodos de pago y más.

Ejemplos soportados:
- "Generame un reporte de las compras que realizo el cliente Paul10 en el mes de noviembre"
- "Muéstrame los productos más caros que compró Juan García"
- "Clientes que compraron refrigeradores LG entre agosto y octubre"
- "Ventas de lavadoras de más de $800 a clientes VIP"
- "Historial completo de compras de maria.lopez en PDF"
"""

import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from products.models import Product, Category


class AdvancedCommandParser:
    """
    Parser ultra-avanzado que detecta entidades específicas en comandos de texto.
    """
    
    # Patrones para detectar tipos de reporte
    REPORT_PATTERNS = {
        'compras_cliente': [
            r'compras? (?:del?|que (?:realizo|hizo)) (?:el )?cliente',
            r'historial (?:de compras )?del? cliente',
            r'ventas? al? cliente',
            r'pedidos? del? cliente',
            r'ordenes? del? cliente'
        ],
        'productos_comprados_por_cliente': [
            r'productos? que compro',
            r'que compro (?:el )?cliente',
            r'articulos? comprados? por'
        ],
        'clientes_que_compraron_producto': [
            r'clientes? que compraron?',
            r'quienes? compraron?',
            r'quien compro'
        ],
        'productos_mas_vendidos': [
            r'productos? mas vendidos?',
            r'top (?:de )?productos?',
            r'best sellers?'
        ],
        'ventas_por_categoria_especifica': [
            r'ventas? (?:de|en) (?:la )?categoria',
            r'productos? (?:de|en) categoria'
        ],
        'ventas_rango_precio': [
            r'entre \$?\d+\.?\d* y \$?\d+\.?\d*',
            r'mas (?:de|caros? que) \$?\d+',
            r'menos (?:de|baratos? que) \$?\d+'
        ],
        'comparativa_clientes': [
            r'comparar clientes?',
            r'comparativa (?:de|entre) clientes?'
        ],
        'timeline_compras': [
            r'timeline (?:de compras)?',
            r'linea (?:de )?tiempo (?:de compras)?',
            r'cronologia (?:de compras)?'
        ],
        'analisis_comportamiento_cliente': [
            r'analisis (?:de )?(?:comportamiento )?(?:del? )?cliente',
            r'perfil (?:de compra )?(?:del? )?cliente'
        ]
    }
    
    # Palabras clave para detectar clientes específicos
    CLIENT_KEYWORDS = [
        'cliente', 'comprador', 'usuario', 'user', 'customer',
        'persona', 'quien', 'quienes'
    ]
    
    # Palabras clave para detectar productos específicos
    PRODUCT_KEYWORDS = [
        'producto', 'articulo', 'item', 'mercancia',
        'refrigerador', 'lavadora', 'microondas', 'aire', 'estufa'
    ]
    
    # Categorías comunes (sincronizado con product_voice_parser)
    CATEGORY_KEYWORDS = {
        'refrigeracion': ['refrigerador', 'refri', 'nevera', 'frigorífico', 'frigo', 'refrigeradores'],
        'lavado': ['lavadora', 'secadora', 'lavasecadora', 'lavadoras', 'secadoras'],
        'cocina': ['estufa', 'horno', 'parrilla', 'cocineta', 'anafe', 'estufas', 'hornos'],
        'climatizacion': ['aire', 'climatizador', 'ventilador', 'calefactor', 'aires', 'aa', 'a/c'],
        'pequenos': ['microondas', 'licuadora', 'batidora', 'cafetera', 'tostadora', 'sandwichera'],
        'audio-video': ['tv', 'television', 'parlante', 'bocina', 'auricular', 'soundbar'],
        'computacion': ['laptop', 'tablet', 'monitor', 'teclado', 'mouse', 'impresora']
    }
    
    # Marcas detectables
    BRAND_KEYWORDS = [
        'lg', 'samsung', 'whirlpool', 'ge', 'mabe', 'frigidaire',
        'sony', 'panasonic', 'electrolux', 'bosch', 'siemens'
    ]
    
    # Meses en español
    MONTHS = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    # Métodos de pago
    PAYMENT_METHODS = {
        'stripe': ['stripe', 'tarjeta', 'credito', 'debito', 'card'],
        'efectivo': ['efectivo', 'cash', 'contado'],
        'transferencia': ['transferencia', 'deposito', 'transfer']
    }
    
    def __init__(self, command):
        """
        Inicializa el parser con un comando.
        
        Args:
            command (str): Comando en lenguaje natural
        """
        self.command = command.lower().strip()
        self.original_command = command
        self.result = {
            'report_type': None,
            'filters': {},
            'format': 'json',
            'confidence': 0.0,
            'detected_entities': {
                'clients': [],
                'products': [],
                'categories': [],
                'brands': [],
                'price_range': None,
                'date_range': None,
                'payment_method': None,
                'quantity_range': None
            },
            'interpretation': '',
            'suggestions': []
        }
    
    def parse(self):
        """
        Analiza el comando completo y extrae todas las entidades.
        
        Returns:
            dict: Resultado del análisis con todos los detalles
        """
        # 1. Detectar tipo de reporte
        self._detect_report_type()
        
        # 2. Detectar clientes específicos (nombres, usernames)
        self._detect_clients()
        
        # 3. Detectar productos específicos
        self._detect_products()
        
        # 4. Detectar categorías
        self._detect_categories()
        
        # 5. Detectar marcas
        self._detect_brands()
        
        # 6. Detectar rangos de precio
        self._detect_price_range()
        
        # 7. Detectar rangos de fecha
        self._detect_date_range()
        
        # 8. Detectar método de pago
        self._detect_payment_method()
        
        # 9. Detectar cantidades
        self._detect_quantities()
        
        # 10. Detectar formato de salida
        self._detect_format()
        
        # 11. Construir interpretación legible
        self._build_interpretation()
        
        # 12. Calcular confianza
        self._calculate_confidence()
        
        # 13. Generar sugerencias si es necesario
        self._generate_suggestions()
        
        return self.result
    
    def _detect_report_type(self):
        """
        Detecta el tipo de reporte solicitado.
        """
        best_match = None
        best_score = 0
        
        for report_type, patterns in self.REPORT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, self.command):
                    score = len(pattern)
                    if score > best_score:
                        best_score = score
                        best_match = report_type
        
        if best_match:
            self.result['report_type'] = best_match
        else:
            # Por defecto: compras_cliente si se menciona "cliente"
            if any(kw in self.command for kw in self.CLIENT_KEYWORDS):
                self.result['report_type'] = 'compras_cliente'
            else:
                self.result['report_type'] = 'ventas_general'
    
    def _detect_clients(self):
        """
        Detecta clientes específicos por nombre o username.
        Ejemplos: "Paul10", "Juan García", "maria.lopez"
        """
        detected_clients = []
        
        # Patrón 1: Detectar usernames (alfanuméricos, puntos, guiones)
        username_patterns = [
            r'cliente\s+([a-zA-Z0-9._-]+)',
            r'usuario\s+([a-zA-Z0-9._-]+)',
            r'comprador\s+([a-zA-Z0-9._-]+)',
            r'de\s+([a-zA-Z0-9._-]+)',
            r'por\s+([a-zA-Z0-9._-]+)'
        ]
        
        for pattern in username_patterns:
            matches = re.finditer(pattern, self.command)
            for match in matches:
                potential_username = match.group(1)
                
                # Verificar si existe en la base de datos
                try:
                    user = User.objects.get(username__iexact=potential_username)
                    if user not in [c['user'] for c in detected_clients]:
                        detected_clients.append({
                            'user': user,
                            'username': user.username,
                            'full_name': f"{user.first_name} {user.last_name}".strip(),
                            'detected_as': 'username',
                            'confidence': 1.0
                        })
                except User.DoesNotExist:
                    # Si no existe, guardarlo como potencial
                    detected_clients.append({
                        'user': None,
                        'username': potential_username,
                        'full_name': potential_username,
                        'detected_as': 'potential_username',
                        'confidence': 0.6
                    })
        
        # Patrón 2: Detectar nombres completos (dos palabras capitalizadas)
        name_pattern = r'\b([A-Z][a-zá-úñ]+)\s+([A-Z][a-zá-úñ]+)\b'
        name_matches = re.finditer(name_pattern, self.original_command)
        
        for match in name_matches:
            first_name = match.group(1)
            last_name = match.group(2)
            full_name = f"{first_name} {last_name}"
            
            # Buscar en base de datos
            users = User.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name
            )
            
            if users.exists():
                for user in users:
                    if user not in [c['user'] for c in detected_clients if c['user']]:
                        detected_clients.append({
                            'user': user,
                            'username': user.username,
                            'full_name': full_name,
                            'detected_as': 'full_name',
                            'confidence': 0.95
                        })
            else:
                # Intentar solo por first_name
                users = User.objects.filter(first_name__iexact=first_name)
                if users.count() == 1:
                    user = users.first()
                    detected_clients.append({
                        'user': user,
                        'username': user.username,
                        'full_name': f"{user.first_name} {user.last_name}".strip(),
                        'detected_as': 'first_name_only',
                        'confidence': 0.7
                    })
        
        self.result['detected_entities']['clients'] = detected_clients
        
        # Agregar filtro si se detectó exactamente 1 cliente con alta confianza
        if len(detected_clients) == 1 and detected_clients[0]['confidence'] >= 0.7:
            if detected_clients[0]['user']:
                self.result['filters']['customer_id'] = detected_clients[0]['user'].id
                self.result['filters']['customer_username'] = detected_clients[0]['username']
    
    def _detect_products(self):
        """
        Detecta productos específicos mencionados.
        """
        detected_products = []
        
        # Buscar productos en la base de datos que coincidan con palabras del comando
        words = self.command.split()
        
        for i in range(len(words)):
            # Intentar con 1, 2, 3 y 4 palabras consecutivas
            for length in range(4, 0, -1):
                if i + length <= len(words):
                    phrase = ' '.join(words[i:i+length])
                    
                    # Buscar productos que contengan esta frase
                    products = Product.objects.filter(name__icontains=phrase)
                    
                    for product in products:
                        if product not in [p['product'] for p in detected_products]:
                            detected_products.append({
                                'product': product,
                                'name': product.name,
                                'detected_phrase': phrase,
                                'confidence': 0.8
                            })
        
        self.result['detected_entities']['products'] = detected_products
        
        # Agregar filtro si se detectó exactamente 1 producto
        if len(detected_products) == 1:
            self.result['filters']['product_id'] = detected_products[0]['product'].id
    
    def _detect_categories(self):
        """
        Detecta categorías mencionadas.
        """
        detected_categories = []
        
        for category_slug, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in self.command:
                    # Buscar la categoría en la base de datos
                    try:
                        category = Category.objects.get(slug=category_slug)
                        if category not in [c['category'] for c in detected_categories]:
                            detected_categories.append({
                                'category': category,
                                'slug': category_slug,
                                'name': category.name,
                                'detected_keyword': keyword,
                                'confidence': 0.9
                            })
                    except Category.DoesNotExist:
                        detected_categories.append({
                            'category': None,
                            'slug': category_slug,
                            'name': category_slug.title(),
                            'detected_keyword': keyword,
                            'confidence': 0.6
                        })
        
        self.result['detected_entities']['categories'] = detected_categories
        
        # Agregar filtro si se detectó exactamente 1 categoría
        if len(detected_categories) == 1:
            self.result['filters']['category_slug'] = detected_categories[0]['slug']
    
    def _detect_brands(self):
        """
        Detecta marcas mencionadas.
        """
        detected_brands = []
        
        for brand in self.BRAND_KEYWORDS:
            if brand in self.command:
                detected_brands.append({
                    'brand': brand.upper(),
                    'confidence': 0.85
                })
        
        self.result['detected_entities']['brands'] = detected_brands
        
        # Agregar filtro si se detectó exactamente 1 marca
        if len(detected_brands) == 1:
            self.result['filters']['brand'] = detected_brands[0]['brand']
    
    def _detect_price_range(self):
        """
        Detecta rangos de precio mencionados.
        Ejemplos: "entre 500 y 1000", "más de 800", "menos de 500"
        """
        # Patrón: "entre X y Y"
        between_pattern = r'entre\s+\$?(\d+\.?\d*)\s+y\s+\$?(\d+\.?\d*)'
        match = re.search(between_pattern, self.command)
        if match:
            min_price = float(match.group(1))
            max_price = float(match.group(2))
            self.result['detected_entities']['price_range'] = {
                'min': min_price,
                'max': max_price,
                'type': 'between'
            }
            self.result['filters']['price_min'] = min_price
            self.result['filters']['price_max'] = max_price
            return
        
        # Patrón: "más de X" o "mayor a X"
        more_than_pattern = r'(?:mas|mayor|mayores|superior)\s+(?:de|a|que)\s+\$?(\d+\.?\d*)'
        match = re.search(more_than_pattern, self.command)
        if match:
            min_price = float(match.group(1))
            self.result['detected_entities']['price_range'] = {
                'min': min_price,
                'max': None,
                'type': 'more_than'
            }
            self.result['filters']['price_min'] = min_price
            return
        
        # Patrón: "menos de X" o "menor a X"
        less_than_pattern = r'(?:menos|menor|menores|inferior)\s+(?:de|a|que)\s+\$?(\d+\.?\d*)'
        match = re.search(less_than_pattern, self.command)
        if match:
            max_price = float(match.group(1))
            self.result['detected_entities']['price_range'] = {
                'min': None,
                'max': max_price,
                'type': 'less_than'
            }
            self.result['filters']['price_max'] = max_price
            return
    
    def _detect_date_range(self):
        """
        Detecta rangos de fecha mencionados.
        Ejemplos: "en noviembre", "del 1 al 15 de octubre", "últimos 30 días"
        """
        # Patrón 1: "mes de [nombre_mes]" o "en [nombre_mes]"
        for month_name, month_num in self.MONTHS.items():
            pattern = f'(?:mes de|en|durante) {month_name}'
            if re.search(pattern, self.command):
                year = timezone.now().year
                start_date = timezone.make_aware(datetime(year, month_num, 1, 0, 0, 0))
                
                if month_num == 12:
                    end_date = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59))
                else:
                    end_date = timezone.make_aware(datetime(year, month_num + 1, 1, 0, 0, 0)) - timedelta(seconds=1)
                
                self.result['detected_entities']['date_range'] = {
                    'start': start_date,
                    'end': end_date,
                    'type': 'month',
                    'description': f"Mes de {month_name.title()} {year}"
                }
                self.result['filters']['start_date'] = start_date
                self.result['filters']['end_date'] = end_date
                return
        
        # Patrón 2: "últimos X días"
        days_pattern = r'(?:ultimos?|pasados?)\s+(\d+)\s+dias?'
        match = re.search(days_pattern, self.command)
        if match:
            days = int(match.group(1))
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            self.result['detected_entities']['date_range'] = {
                'start': start_date,
                'end': end_date,
                'type': 'last_days',
                'description': f"Últimos {days} días"
            }
            self.result['filters']['start_date'] = start_date
            self.result['filters']['end_date'] = end_date
            return
        
        # Patrón 3: Rangos explícitos "del DD/MM/YYYY al DD/MM/YYYY"
        date_range_pattern = r'del?\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+al?\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        match = re.search(date_range_pattern, self.command)
        if match:
            start_str = match.group(1).replace('-', '/')
            end_str = match.group(2).replace('-', '/')
            
            start_dt = self._parse_date(start_str)
            end_dt = self._parse_date(end_str)
            
            if start_dt and end_dt:
                self.result['detected_entities']['date_range'] = {
                    'start': timezone.make_aware(start_dt),
                    'end': timezone.make_aware(end_dt.replace(hour=23, minute=59, second=59)),
                    'type': 'explicit_range',
                    'description': f"{start_str} al {end_str}"
                }
                self.result['filters']['start_date'] = timezone.make_aware(start_dt)
                self.result['filters']['end_date'] = timezone.make_aware(end_dt.replace(hour=23, minute=59, second=59))
                return
        
        # Patrón 4: "entre [mes1] y [mes2]"
        between_months_pattern = r'entre\s+(\w+)\s+y\s+(\w+)'
        match = re.search(between_months_pattern, self.command)
        if match:
            month1_name = match.group(1).lower()
            month2_name = match.group(2).lower()
            
            if month1_name in self.MONTHS and month2_name in self.MONTHS:
                month1_num = self.MONTHS[month1_name]
                month2_num = self.MONTHS[month2_name]
                year = timezone.now().year
                
                start_date = timezone.make_aware(datetime(year, month1_num, 1, 0, 0, 0))
                
                if month2_num == 12:
                    end_date = timezone.make_aware(datetime(year, 12, 31, 23, 59, 59))
                else:
                    end_date = timezone.make_aware(datetime(year, month2_num + 1, 1, 0, 0, 0)) - timedelta(seconds=1)
                
                self.result['detected_entities']['date_range'] = {
                    'start': start_date,
                    'end': end_date,
                    'type': 'between_months',
                    'description': f"Entre {month1_name.title()} y {month2_name.title()} {year}"
                }
                self.result['filters']['start_date'] = start_date
                self.result['filters']['end_date'] = end_date
                return
    
    def _parse_date(self, date_str):
        """
        Parsea una fecha en formato DD/MM/YYYY.
        """
        try:
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                try:
                    return datetime.strptime(date_str, fmt).replace(hour=0, minute=0, second=0)
                except ValueError:
                    continue
            return None
        except:
            return None
    
    def _detect_payment_method(self):
        """
        Detecta método de pago mencionado.
        """
        for method, keywords in self.PAYMENT_METHODS.items():
            for keyword in keywords:
                if keyword in self.command:
                    self.result['detected_entities']['payment_method'] = {
                        'method': method,
                        'keyword': keyword,
                        'confidence': 0.8
                    }
                    self.result['filters']['payment_method'] = method
                    return
    
    def _detect_quantities(self):
        """
        Detecta cantidades mencionadas.
        Ejemplos: "más de 5 unidades", "entre 2 y 10 productos"
        """
        # Patrón: "más de X unidades"
        more_than_pattern = r'mas de (\d+)\s+(?:unidades?|productos?|items?)'
        match = re.search(more_than_pattern, self.command)
        if match:
            min_qty = int(match.group(1))
            self.result['detected_entities']['quantity_range'] = {
                'min': min_qty,
                'max': None,
                'type': 'more_than'
            }
            self.result['filters']['quantity_min'] = min_qty
            return
        
        # Patrón: "entre X y Y unidades"
        between_pattern = r'entre (\d+) y (\d+)\s+(?:unidades?|productos?|items?)'
        match = re.search(between_pattern, self.command)
        if match:
            min_qty = int(match.group(1))
            max_qty = int(match.group(2))
            self.result['detected_entities']['quantity_range'] = {
                'min': min_qty,
                'max': max_qty,
                'type': 'between'
            }
            self.result['filters']['quantity_min'] = min_qty
            self.result['filters']['quantity_max'] = max_qty
            return
    
    def _detect_format(self):
        """
        Detecta formato de salida solicitado.
        """
        if 'pdf' in self.command:
            self.result['format'] = 'pdf'
        elif 'excel' in self.command or 'xlsx' in self.command or 'xls' in self.command:
            self.result['format'] = 'excel'
        else:
            self.result['format'] = 'json'
    
    def _build_interpretation(self):
        """
        Construye una interpretación legible del comando.
        """
        parts = []
        
        # Tipo de reporte
        if self.result['report_type']:
            report_name = self.result['report_type'].replace('_', ' ').title()
            parts.append(f"📊 Tipo: {report_name}")
        
        # Clientes
        if self.result['detected_entities']['clients']:
            clients = self.result['detected_entities']['clients']
            client_names = [c['username'] for c in clients]
            parts.append(f"👤 Cliente(s): {', '.join(client_names)}")
        
        # Productos
        if self.result['detected_entities']['products']:
            products = self.result['detected_entities']['products']
            product_names = [p['name'] for p in products]
            parts.append(f"📦 Producto(s): {', '.join(product_names)}")
        
        # Categorías
        if self.result['detected_entities']['categories']:
            categories = self.result['detected_entities']['categories']
            category_names = [c['name'] for c in categories]
            parts.append(f"🏷️ Categoría(s): {', '.join(category_names)}")
        
        # Marcas
        if self.result['detected_entities']['brands']:
            brands = self.result['detected_entities']['brands']
            brand_names = [b['brand'] for b in brands]
            parts.append(f"🔖 Marca(s): {', '.join(brand_names)}")
        
        # Precios
        if self.result['detected_entities']['price_range']:
            pr = self.result['detected_entities']['price_range']
            if pr['type'] == 'between':
                parts.append(f"💰 Precio: ${pr['min']} - ${pr['max']}")
            elif pr['type'] == 'more_than':
                parts.append(f"💰 Precio: Más de ${pr['min']}")
            elif pr['type'] == 'less_than':
                parts.append(f"💰 Precio: Menos de ${pr['max']}")
        
        # Fechas
        if self.result['detected_entities']['date_range']:
            dr = self.result['detected_entities']['date_range']
            parts.append(f"📅 Período: {dr['description']}")
        
        # Formato
        parts.append(f"📄 Formato: {self.result['format'].upper()}")
        
        self.result['interpretation'] = '\n'.join(parts)
    
    def _calculate_confidence(self):
        """
        Calcula nivel de confianza del análisis.
        """
        score = 0.0
        
        # Tipo de reporte identificado (+20%)
        if self.result['report_type']:
            score += 0.20
        
        # Clientes detectados (+25%)
        if self.result['detected_entities']['clients']:
            avg_confidence = sum(c['confidence'] for c in self.result['detected_entities']['clients']) / len(self.result['detected_entities']['clients'])
            score += 0.25 * avg_confidence
        
        # Productos detectados (+15%)
        if self.result['detected_entities']['products']:
            score += 0.15
        
        # Categorías detectadas (+10%)
        if self.result['detected_entities']['categories']:
            score += 0.10
        
        # Rango de fechas (+15%)
        if self.result['detected_entities']['date_range']:
            score += 0.15
        
        # Rango de precio (+10%)
        if self.result['detected_entities']['price_range']:
            score += 0.10
        
        # Marcas (+5%)
        if self.result['detected_entities']['brands']:
            score += 0.05
        
        self.result['confidence'] = min(score, 1.0)
    
    def _generate_suggestions(self):
        """
        Genera sugerencias si la confianza es baja.
        """
        suggestions = []
        
        if self.result['confidence'] < 0.5:
            if not self.result['detected_entities']['clients']:
                suggestions.append("💡 Intenta especificar un cliente (ej: 'cliente Paul10' o 'Juan García')")
            
            if not self.result['detected_entities']['date_range']:
                suggestions.append("💡 Agrega un período de tiempo (ej: 'en noviembre' o 'últimos 30 días')")
            
            if not self.result['detected_entities']['categories'] and not self.result['detected_entities']['products']:
                suggestions.append("💡 Especifica un producto o categoría (ej: 'refrigeradores' o 'Refrigerador LG 500L')")
        
        self.result['suggestions'] = suggestions


def parse_advanced_command(command):
    """
    Función helper para parsear un comando avanzado.
    
    Args:
        command (str): Comando en lenguaje natural
    
    Returns:
        dict: Resultado del análisis con entidades detectadas
    """
    parser = AdvancedCommandParser(command)
    return parser.parse()
