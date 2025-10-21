"""
Procesador de comandos de voz - Interpreta texto y ejecuta acciones
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from django.utils import timezone

# Importar el parser y generador de reportes existentes
from sales.prompt_parser import parse_prompt
from sales.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


class VoiceCommandProcessor:
    """
    Procesa comandos de voz transcritos y ejecuta la acción correspondiente
    """
    
    def __init__(self, user):
        """
        Inicializa el procesador con el usuario que ejecuta el comando
        
        Args:
            user: Usuario de Django que ejecuta el comando
        """
        self.user = user
        self.report_generator = ReportGenerator()
    
    def process_command(self, text: str) -> Dict[str, Any]:
        """
        Procesa un comando de voz y devuelve el resultado
        
        Args:
            text: Texto transcrito del comando de voz
        
        Returns:
            Dict con el resultado del comando:
            {
                'success': bool,
                'command_type': str,
                'params': dict,
                'result': dict o None,
                'error': str o None
            }
        """
        
        try:
            # Normalizar el texto
            text = self.normalize_text(text)
            
            logger.info(f"🎤 Procesando comando de voz: '{text}'")
            
            # Identificar el tipo de comando
            command_type = self.identify_command_type(text)
            
            if command_type == 'reporte':
                return self.process_report_command(text)
            elif command_type == 'consulta':
                return self.process_query_command(text)
            elif command_type == 'ayuda':
                return self.process_help_command(text)
            else:
                return {
                    'success': False,
                    'command_type': 'desconocido',
                    'params': {},
                    'result': None,
                    'error': 'No se pudo identificar el tipo de comando. Intenta con: "generar reporte de...", "consultar...", "ayuda"'
                }
                
        except Exception as e:
            logger.error(f"❌ Error al procesar comando: {e}")
            return {
                'success': False,
                'command_type': 'error',
                'params': {},
                'result': None,
                'error': str(e)
            }
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza el texto: minúsculas, elimina espacios extras
        """
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)  # Múltiples espacios a uno
        return text
    
    def identify_command_type(self, text: str) -> str:
        """
        Identifica el tipo de comando basándose en palabras clave
        
        Returns:
            'reporte', 'consulta', 'ayuda', 'desconocido'
        """
        
        # Palabras clave para reportes
        reporte_keywords = ['reporte', 'informe', 'genera', 'generar', 'muestra', 'mostrar']
        
        # Palabras clave para consultas
        consulta_keywords = ['consultar', 'buscar', 'ver', 'listar', 'cuántos', 'cuantos']
        
        # Palabras clave para ayuda
        ayuda_keywords = ['ayuda', 'help', 'cómo', 'como', 'qué puedo', 'que puedo']
        
        text_lower = text.lower()
        
        # Verificar palabras clave
        if any(keyword in text_lower for keyword in reporte_keywords):
            return 'reporte'
        elif any(keyword in text_lower for keyword in consulta_keywords):
            return 'consulta'
        elif any(keyword in text_lower for keyword in ayuda_keywords):
            return 'ayuda'
        else:
            return 'desconocido'
    
    def process_report_command(self, text: str) -> Dict[str, Any]:
        """
        Procesa un comando de generación de reporte
        
        Ejemplos:
        - "generar reporte de ventas del último mes"
        - "mostrar productos más vendidos esta semana"
        - "informe de clientes que más compraron en diciembre"
        """
        
        try:
            # Usar el parser existente de sales.prompt_parser
            parsed = parse_prompt(text)
            
            logger.info(f"📊 Comando parseado: {parsed}")
            
            if not parsed.get('success'):
                return {
                    'success': False,
                    'command_type': 'reporte',
                    'params': {},
                    'result': None,
                    'error': parsed.get('error', 'No se pudo interpretar el comando')
                }
            
            # Extraer parámetros
            params = parsed['filters']
            report_type = self.infer_report_type(text, params)
            
            # Generar el reporte usando ReportGenerator
            if report_type == 'ventas':
                result = self.report_generator.generate_sales_report(
                    start_date=params.get('start_date'),
                    end_date=params.get('end_date'),
                    customer_id=params.get('customer_id'),
                    product_id=params.get('product_id'),
                )
            elif report_type == 'productos':
                result = self.report_generator.generate_product_report(
                    start_date=params.get('start_date'),
                    end_date=params.get('end_date'),
                    category=params.get('category'),
                    top_n=params.get('limit', 10),
                )
            elif report_type == 'clientes':
                result = self.report_generator.generate_customer_report(
                    start_date=params.get('start_date'),
                    end_date=params.get('end_date'),
                    top_n=params.get('limit', 10),
                )
            else:
                # Por defecto, reporte de ventas
                result = self.report_generator.generate_sales_report(
                    start_date=params.get('start_date'),
                    end_date=params.get('end_date'),
                )
            
            return {
                'success': True,
                'command_type': 'reporte',
                'params': {
                    'report_type': report_type,
                    'filters': params,
                    'original_text': text,
                },
                'result': result,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"❌ Error al generar reporte: {e}")
            return {
                'success': False,
                'command_type': 'reporte',
                'params': {},
                'result': None,
                'error': f"Error al generar el reporte: {str(e)}"
            }
    
    def infer_report_type(self, text: str, params: Dict) -> str:
        """
        Infiere el tipo de reporte basándose en el texto
        
        Returns:
            'ventas', 'productos', 'clientes'
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['producto', 'productos', 'artículo', 'artículos', 'vendidos']):
            return 'productos'
        elif any(word in text_lower for word in ['cliente', 'clientes', 'comprador', 'compradores']):
            return 'clientes'
        else:
            return 'ventas'
    
    def process_query_command(self, text: str) -> Dict[str, Any]:
        """
        Procesa un comando de consulta simple
        
        Ejemplos:
        - "cuántos productos tenemos"
        - "consultar ventas de hoy"
        """
        
        # Por ahora, redirigir a reporte
        return self.process_report_command(text)
    
    def process_help_command(self, text: str) -> Dict[str, Any]:
        """
        Procesa un comando de ayuda
        """
        
        help_text = """
        **Comandos de voz disponibles:**
        
        📊 **Reportes de Ventas:**
        - "Generar reporte de ventas del último mes"
        - "Mostrar ventas de esta semana"
        - "Informe de ventas de diciembre"
        
        📦 **Reportes de Productos:**
        - "Productos más vendidos del mes"
        - "Mostrar artículos vendidos esta semana"
        - "Top 10 productos del año"
        
        👥 **Reportes de Clientes:**
        - "Clientes que más compraron"
        - "Mejores compradores del mes"
        - "Top clientes de esta semana"
        
        📅 **Referencias de tiempo válidas:**
        - "hoy", "ayer", "esta semana", "este mes", "este año"
        - "última semana", "último mes", "último año"
        - "en diciembre", "en 2024"
        - "desde el 1 de enero hasta hoy"
        
        💡 **Consejos:**
        - Habla claramente y en español
        - Usa frases completas
        - Especifica el período de tiempo que te interesa
        """
        
        return {
            'success': True,
            'command_type': 'ayuda',
            'params': {},
            'result': {'help_text': help_text},
            'error': None
        }
    
    def extract_date_from_text(self, text: str) -> Optional[datetime]:
        """
        Extrae una fecha específica del texto
        
        Ejemplos: "1 de enero", "15 de diciembre de 2024"
        """
        
        # Mapa de meses en español
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        # Patrón: "15 de diciembre de 2024" o "1 de enero"
        pattern = r'(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?'
        match = re.search(pattern, text.lower())
        
        if match:
            day = int(match.group(1))
            month_name = match.group(2)
            year = int(match.group(3)) if match.group(3) else timezone.now().year
            
            if month_name in meses:
                month = meses[month_name]
                try:
                    return datetime(year, month, day)
                except ValueError:
                    pass
        
        return None
