"""
ViewSet para procesar comandos de texto inteligentes
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import VoiceCommand, VoiceCommandHistory
from .serializers import (
    VoiceCommandSerializer,
    VoiceCommandTextSerializer
)
from .voice_processor import VoiceCommandProcessor

logger = logging.getLogger(__name__)


class VoiceCommandViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para comandos de texto inteligentes.
    
    Endpoints:
    - GET    /api/voice-commands/              → Listar historial de comandos
    - GET    /api/voice-commands/{id}/         → Detalle de un comando
    - POST   /api/voice-commands/process/      → Procesar nuevo comando
    """
    
    serializer_class = VoiceCommandSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Retorna solo los comandos del usuario actual
        """
        return VoiceCommand.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['post'], url_path='process')
    def process(self, request):
        """
        POST /api/voice-commands/process/
        
        Procesa un comando de texto en lenguaje natural y genera el reporte correspondiente.
        
        Body:
        {
            "text": "reporte de ventas del último mes"
        }
        
        Returns:
        {
            "command_id": 123,
            "status": "EXECUTED",
            "command_text": "...",
            "confidence_score": 0.85,
            "result_data": { ... }
        }
        """
        
        logger.info(f"🔵 [VIEW-1/5] ==================== process() INICIADO ====================")
        logger.info(f"🔵 [VIEW-1/5] Usuario: {request.user.username}")
        
        # Validar input
        serializer = VoiceCommandTextSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"🔵 [VIEW-1/5] ⚠️ Validación fallida: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        text = serializer.validated_data['text']
        logger.info(f"🔵 [VIEW-2/5] Texto validado: '{text}' (length={len(text)})")
        
        # Crear registro del comando
        start_time = timezone.now()
        
        voice_command = VoiceCommand.objects.create(
            user=request.user,
            command_text=text,
            status='PROCESSING'
        )
        
        logger.info(f"🔵 [VIEW-2/5] ✅ VoiceCommand creado (ID={voice_command.id})")
        
        # Registrar inicio en el historial
        VoiceCommandHistory.objects.create(
            voice_command=voice_command,
            stage='PARSING',
            message='Iniciando procesamiento del comando',
            data={'text': text}
        )
        
        try:
            # Procesar comando
            logger.info(f"🔵 [VIEW-3/5] ⏳ Inicializando VoiceCommandProcessor")
            processor = VoiceCommandProcessor(user=request.user)
            logger.info(f"🔵 [VIEW-3/5] ✅ Processor inicializado")
            
            logger.info(f"🔵 [VIEW-3/5] ⏳ Llamando a processor.process_command() - PUNTO CRÍTICO")
            result = processor.process_command(text)
            logger.info(f"🔵 [VIEW-3/5] ✅ processor.process_command() COMPLETADO")
            logger.info(f"🔵 [VIEW-3/5]    Success: {result.get('success')}")
            logger.info(f"🔵 [VIEW-3/5]    Command type: {result.get('command_type')}")
            
            # Calcular tiempo de procesamiento
            end_time = timezone.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(f"🔵 [VIEW-4/5] Tiempo de procesamiento: {processing_time_ms}ms")
            
            # Actualizar registro
            if result['success']:
                voice_command.status = 'EXECUTED'
                voice_command.command_type = result['command_type']
                voice_command.interpreted_params = result.get('params', {})
                voice_command.result_data = result.get('result', {})
                voice_command.confidence_score = result.get('confidence', 0.0)
                voice_command.processing_time_ms = processing_time_ms
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='COMPLETED',
                    message='Comando procesado exitosamente',
                    data={'processing_time_ms': processing_time_ms}
                )
                
                logger.info(f"🔵 [VIEW-4/5] ✅ Comando ejecutado exitosamente")
                
            else:
                voice_command.status = 'FAILED'
                voice_command.error_message = result.get('error', 'Error desconocido')
                voice_command.confidence_score = result.get('confidence', 0.0)
                voice_command.processing_time_ms = processing_time_ms
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='FAILED',
                    message=result.get('error', 'Error desconocido'),
                    data={'processing_time_ms': processing_time_ms}
                )
                
                logger.warning(f"🔵 [VIEW-4/5] ⚠️ Comando falló: {result.get('error')}")
            
            voice_command.save()
            
            logger.info(f"🔵 [VIEW-5/5] ✅ VoiceCommand guardado (status={voice_command.status})")
            logger.info(f"🔵 [VIEW-5/5] ==================== process() COMPLETADO ====================")
            
            # Serializar respuesta
            serializer = VoiceCommandSerializer(voice_command)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"🔵 [VIEW-ERROR] ❌ EXCEPCIÓN en process(): {type(e).__name__}: {e}")
            logger.error(f"🔵 [VIEW-ERROR] Stacktrace:", exc_info=True)
            
            # Actualizar estado como fallido
            voice_command.status = 'FAILED'
            voice_command.error_message = f"Error inesperado: {str(e)}"
            voice_command.processing_time_ms = int((timezone.now() - start_time).total_seconds() * 1000)
            voice_command.save()
            
            VoiceCommandHistory.objects.create(
                voice_command=voice_command,
                stage='ERROR',
                message=f"Excepción: {type(e).__name__}: {str(e)}",
                data={'error_type': type(e).__name__}
            )
            
            return Response({
                'error': 'Error interno del servidor',
                'detail': str(e) if logger.level == logging.DEBUG else 'Error al procesar el comando'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='capabilities')
    def capabilities(self, request):
        """
        GET /api/voice-commands/capabilities/
        
        Retorna información sobre los tipos de comandos disponibles.
        """
        from sales.unified_command_parser import get_available_reports
        
        try:
            catalog = get_available_reports()
            
            return Response({
                'success': True,
                'total_reports': catalog['total_reports'],
                'categories': catalog['categories'],
                'message': 'Usa el endpoint /process/ para generar reportes con lenguaje natural'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error al obtener capabilities: {e}")
            return Response({
                'error': 'Error al obtener información de reportes disponibles'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
