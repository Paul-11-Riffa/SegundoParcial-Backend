"""
ReportDispatcher: Conecta el parser de comandos con los generadores reales de reportes.

Este módulo actúa como un "router" inteligente que:
1. Recibe el tipo de reporte identificado por el parser
2. Convierte los parámetros al formato esperado por cada generador
3. Llama al generador apropiado
4. Retorna los datos reales del reporte
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone
from django.contrib.auth.models import User

from sales.report_generator import ReportGenerator
from sales.advanced_reports import AdvancedReportGenerator
from sales.ml_predictor_simple import SimpleSalesPredictor
from sales.ml_product_predictor import product_predictor
from sales.ml_recommender import recommender

logger = logging.getLogger(__name__)


class ReportDispatcher:
    """
    Despachador de reportes que conecta comandos parseados con generadores reales.
    
    Soporta 14 tipos de reportes:
    - 5 reportes básicos de ventas
    - 5 reportes avanzados (RFM, ABC, dashboard, etc.)
    - 4 reportes ML (predicciones, recomendaciones)
    """
    
    def __init__(self, user: Optional[User] = None):
        """
        Inicializa el dispatcher.
        
        Args:
            user: Usuario que solicita el reporte (necesario para recomendaciones)
        """
        self.user = user
        self.ml_predictor = None
        
    def dispatch(self, report_type: str, params: Dict) -> Dict[str, Any]:
        """
        Despacha el reporte al generador correcto.
        
        Args:
            report_type: Tipo de reporte del parser (ej: 'ventas_basico', 'analisis_rfm')
            params: Parámetros extraídos del comando (fechas, formato, etc.)
            
        Returns:
            dict: Datos del reporte generado
            
        Raises:
            ValueError: Si el tipo de reporte no es soportado
        """
        logger.info(f"🟡 [DISPATCH-1/6] ==================== ReportDispatcher.dispatch INICIADO ====================")
        logger.info(f"🟡 [DISPATCH-1/6] Report type: {report_type}")
        logger.info(f"🟡 [DISPATCH-1/6] Params keys: {list(params.keys())}")
        
        try:
            # Convertir parámetros al formato del generador
            logger.info(f"🟡 [DISPATCH-2/6] Convirtiendo parámetros...")
            gen_params = self._convert_params(params)
            logger.info(f"🟡 [DISPATCH-2/6] ✅ Parámetros convertidos")
            logger.info(f"🟡 [DISPATCH-2/6]    Gen params keys: {list(gen_params.keys())}")
            
            # === REPORTES BÁSICOS DE VENTAS ===
            if report_type in [
                'ventas_basico', 
                'ventas_por_producto', 
                'ventas_por_cliente', 
                'ventas_por_categoria', 
                'ventas_por_fecha'
            ]:
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando reporte básico de ventas: {report_type}")
                result = self._generate_sales_report(report_type, gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Reporte básico generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            # === REPORTES AVANZADOS ===
            elif report_type == 'analisis_rfm':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando análisis RFM")
                result = self._generate_rfm_analysis(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Análisis RFM generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'analisis_abc':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando análisis ABC")
                result = self._generate_abc_analysis(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Análisis ABC generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'comparativo_temporal':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando comparativo temporal")
                result = self._generate_comparative_report(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Comparativo generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'dashboard_ejecutivo':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando dashboard ejecutivo")
                result = self._generate_executive_dashboard(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Dashboard generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'analisis_inventario':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando análisis de inventario")
                result = self._generate_inventory_analysis(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Inventario generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            # === REPORTES ML ===
            elif report_type == 'prediccion_ventas':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando predicción de ventas (ML)")
                result = self._generate_sales_prediction(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Predicción generada")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'prediccion_producto':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando predicción de producto (ML)")
                result = self._generate_product_prediction(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Predicción producto generada")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'recomendaciones':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando recomendaciones (ML)")
                result = self._generate_recommendations(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Recomendaciones generadas")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            elif report_type == 'dashboard_ml':
                logger.info(f"🟡 [DISPATCH-3/6] ⏳ Generando dashboard ML")
                result = self._generate_ml_dashboard(gen_params)
                logger.info(f"🟡 [DISPATCH-3/6] ✅ Dashboard ML generado")
                logger.info(f"🟡 [DISPATCH-6/6] ==================== ReportDispatcher.dispatch COMPLETADO ====================")
                return result
            
            else:
                logger.error(f"🟡 [DISPATCH-ERROR] ❌ Tipo de reporte NO SOPORTADO: '{report_type}'")
                raise ValueError(f"Tipo de reporte no soportado: '{report_type}'")
                
        except Exception as e:
            logger.error(f"🟡 [DISPATCH-ERROR] ❌ EXCEPCIÓN en ReportDispatcher.dispatch: {type(e).__name__}: {e}")
            logger.error(f"🟡 [DISPATCH-ERROR] Report type: {report_type}")
            logger.error(f"🟡 [DISPATCH-ERROR] Stacktrace:", exc_info=True)
            raise
    
    # ========== REPORTES BÁSICOS DE VENTAS ==========
    
    def _generate_sales_report(self, report_type: str, params: Dict) -> Dict:
        """
        Genera reportes básicos de ventas usando ReportGenerator.
        """
        logger.info(f"🔶 [SALES-1/4] _generate_sales_report iniciado para: {report_type}")
        
        # Mapear tipo del parser → configuración del generador
        type_mapping = {
            'ventas_basico': {
                'report_type': 'sales',
                'group_by': None
            },
            'ventas_por_producto': {
                'report_type': 'sales',
                'group_by': 'product'
            },
            'ventas_por_cliente': {
                'report_type': 'sales',
                'group_by': 'client'
            },
            'ventas_por_categoria': {
                'report_type': 'sales',
                'group_by': 'category'
            },
            'ventas_por_fecha': {
                'report_type': 'sales',
                'group_by': 'date'
            }
        }
        
        # Agregar configuración específica
        config = type_mapping.get(report_type, {})
        params.update(config)
        
        logger.info(f"🔶 [SALES-2/4] Configuración aplicada. Report type en params: {params.get('report_type')}")
        
        # Generar reporte
        logger.info(f"🔶 [SALES-3/4] ⏳ Inicializando ReportGenerator")
        try:
            generator = ReportGenerator(params)
            logger.info(f"🔶 [SALES-3/4] ✅ ReportGenerator inicializado")
            
            logger.info(f"🔶 [SALES-4/4] ⏳ Llamando a generator.generate() - PUNTO CRÍTICO")
            result = generator.generate()
            logger.info(f"🔶 [SALES-4/4] ✅ generator.generate() COMPLETADO")
            
            return result
        except Exception as e:
            logger.error(f"🔶 [SALES-ERROR] ❌ Error en ReportGenerator: {type(e).__name__}: {e}")
            logger.error(f"🔶 [SALES-ERROR] Stacktrace:", exc_info=True)
            raise
    
    # ========== REPORTES AVANZADOS ==========
    
    def _generate_rfm_analysis(self, params: Dict) -> Dict:
        """
        Genera análisis RFM (Recency, Frequency, Monetary) de clientes.
        Segmenta en: VIP, Regular, En Riesgo, Nuevo, Inactivo.
        """
        generator = AdvancedReportGenerator(params)
        return generator.customer_rfm_analysis()
    
    def _generate_abc_analysis(self, params: Dict) -> Dict:
        """
        Genera análisis ABC (Principio de Pareto 80/20).
        Clasifica productos en A (80%), B (15%), C (5%).
        """
        generator = AdvancedReportGenerator(params)
        return generator.product_abc_analysis()
    
    def _generate_comparative_report(self, params: Dict) -> Dict:
        """
        Genera reporte comparativo entre dos períodos.
        Calcula variaciones porcentuales y tendencias.
        """
        generator = AdvancedReportGenerator(params)
        
        # Determinar período de comparación
        comparison_period = params.get('comparison_period', 'previous_month')
        
        return generator.comparative_report(comparison_period=comparison_period)
    
    def _generate_executive_dashboard(self, params: Dict) -> Dict:
        """
        Genera dashboard ejecutivo con KPIs principales.
        Incluye: ventas, clientes, productos, alertas.
        """
        generator = AdvancedReportGenerator(params)
        return generator.executive_dashboard()
    
    def _generate_inventory_analysis(self, params: Dict) -> Dict:
        """
        Genera análisis de inventario.
        Incluye: rotación, stock bajo, productos sin movimiento.
        """
        generator = AdvancedReportGenerator(params)
        return generator.inventory_analysis()
    
    # ========== REPORTES ML ==========
    
    def _generate_sales_prediction(self, params: Dict) -> Dict:
        """
        Genera predicciones de ventas futuras usando ML.
        """
        days = params.get('days', 30)
        include_trends = params.get('include_trends', True)
        include_confidence = params.get('include_confidence', True)
        
        # Inicializar predictor si no existe
        if self.ml_predictor is None:
            self.ml_predictor = SimpleSalesPredictor()
        
        # Entrenar si no está entrenado
        if self.ml_predictor.model is None:
            logger.info("Entrenando modelo de predicción de ventas...")
            self.ml_predictor.train()
        
        # Generar predicciones (el método se llama 'predict', no 'predict_future')
        predictions = self.ml_predictor.predict(days=days)
        
        # Agregar métricas del modelo
        if include_confidence:
            predictions['model_metrics'] = self.ml_predictor.metrics
        
        return predictions
    
    def _generate_product_prediction(self, params: Dict) -> Dict:
        """
        Genera predicciones de ventas por producto.
        """
        product_id = params.get('product_id')
        days = params.get('days', 30)
        include_confidence = params.get('include_confidence', True)
        
        if product_id:
            # Predicción de un producto específico
            return product_predictor.predict_product(
                product_id=product_id,
                days=days,
                include_confidence=include_confidence
            )
        else:
            # Predicción de todos los productos
            limit = params.get('limit', 10)
            return product_predictor.predict_all_products(
                days=days,
                limit=limit
            )
    
    def _generate_recommendations(self, params: Dict) -> Dict:
        """
        Genera recomendaciones personalizadas de productos.
        """
        if not self.user:
            raise ValueError("Se requiere un usuario para generar recomendaciones")
        
        n_recommendations = params.get('limit', 10)
        exclude_purchased = params.get('exclude_purchased', True)
        
        recommendations = recommender.get_recommendations_for_user(
            user_id=self.user.id,
            n_recommendations=n_recommendations,
            exclude_purchased=exclude_purchased
        )
        
        return {
            'title': 'Recomendaciones Personalizadas',
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
            },
            'recommendations': recommendations,
            'total_recommendations': len(recommendations)
        }
    
    def _generate_ml_dashboard(self, params: Dict) -> Dict:
        """
        Genera dashboard completo con predicciones ML.
        Combina: predicciones de ventas, productos top, tendencias.
        """
        days = params.get('days', 30)
        
        # 1. Predicciones de ventas
        sales_predictions = self._generate_sales_prediction({
            'days': days,
            'include_trends': True,
            'include_confidence': True
        })
        
        # 2. Top productos predichos
        product_predictions = self._generate_product_prediction({
            'days': days,
            'limit': 10
        })
        
        # 3. Recomendaciones (si hay usuario)
        recommendations = None
        if self.user:
            try:
                recommendations = self._generate_recommendations({
                    'limit': 5,
                    'exclude_purchased': True
                })
            except Exception as e:
                logger.warning(f"No se pudieron generar recomendaciones: {e}")
        
        return {
            'title': 'Dashboard de Predicciones ML',
            'subtitle': f'Predicciones para los próximos {days} días',
            'sales_predictions': sales_predictions,
            'product_predictions': product_predictions,
            'recommendations': recommendations,
            'generated_at': timezone.now().isoformat()
        }
    
    # ========== UTILIDADES ==========
    
    def _convert_params(self, parser_params: Dict) -> Dict:
        """
        Convierte parámetros del parser al formato esperado por los generadores.
        
        El parser usa nombres como 'start_date', 'end_date', 'top_n', etc.
        Los generadores pueden usar nombres diferentes o formatos diferentes.
        """
        gen_params = {}
        
        # Copiar fechas directamente (ya vienen como datetime)
        if 'start_date' in parser_params:
            gen_params['start_date'] = parser_params['start_date']
        
        if 'end_date' in parser_params:
            gen_params['end_date'] = parser_params['end_date']
        
        # Límites y top N
        if 'top_n' in parser_params:
            gen_params['limit'] = parser_params['top_n']
        elif 'limit' in parser_params:
            gen_params['limit'] = parser_params['limit']
        
        # Ordenamiento
        if 'sort_by' in parser_params:
            gen_params['sort_by'] = parser_params['sort_by']
        
        # Formato (PDF, Excel, JSON)
        if 'format' in parser_params:
            gen_params['format'] = parser_params['format']
        
        # Días para predicciones
        if 'days' in parser_params:
            gen_params['days'] = parser_params['days']
        
        # ID de producto
        if 'product_id' in parser_params:
            gen_params['product_id'] = parser_params['product_id']
        
        # Período de comparación
        if 'comparison_period' in parser_params:
            gen_params['comparison_period'] = parser_params['comparison_period']
        
        # Flags booleanos
        gen_params['include_trends'] = parser_params.get('include_trends', True)
        gen_params['include_confidence'] = parser_params.get('include_confidence', True)
        gen_params['exclude_purchased'] = parser_params.get('exclude_purchased', True)
        
        return gen_params


# Función helper para uso directo
def dispatch_report(report_type: str, params: Dict, user: Optional[User] = None) -> Dict[str, Any]:
    """
    Función helper para despachar un reporte.
    
    Args:
        report_type: Tipo de reporte
        params: Parámetros del reporte
        user: Usuario que solicita (opcional)
        
    Returns:
        dict: Datos del reporte generado
    """
    dispatcher = ReportDispatcher(user=user)
    return dispatcher.dispatch(report_type, params)
