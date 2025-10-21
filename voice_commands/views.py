import time
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.uploadedfile import UploadedFile

from .models import VoiceCommand, VoiceCommandHistory
from .serializers import (
    VoiceCommandSerializer,
    VoiceCommandUploadSerializer,
    VoiceCommandTextSerializer
)
from .speech_service import speech_service
from .voice_processor import VoiceCommandProcessor

logger = logging.getLogger(__name__)


class VoiceCommandViewSet(viewsets.ModelViewSet):
    """
    ViewSet para comandos de voz
    
    Endpoints:
    - GET /voice-commands/ - Listar comandos del usuario
    - GET /voice-commands/{id}/ - Detalle de un comando
    - POST /voice-commands/process-audio/ - Procesar un archivo de audio
    - POST /voice-commands/process-text/ - Procesar texto directamente
    - GET /voice-commands/history/ - Historial de todos los comandos
    - GET /voice-commands/status/ - Estado del servicio
    """
    
    serializer_class = VoiceCommandSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Solo comandos del usuario actual"""
        return VoiceCommand.objects.filter(user=self.request.user).prefetch_related('history')
    
    @action(detail=False, methods=['POST'], url_path='process-audio')
    def process_audio(self, request):
        """
        Procesa un archivo de audio y genera el reporte correspondiente
        
        **Request:**
        - audio: Archivo de audio (multipart/form-data)
        - language: 'es-MX' o 'es-ES' (opcional, default: 'es-MX')
        
        **Response:**
        ```json
        {
            "success": true,
            "data": {
                "id": 1,
                "transcribed_text": "generar reporte de ventas del último mes",
                "status": "EXECUTED",
                "command_type": "reporte",
                "result_data": {...},
                "confidence": 0.95,
                "processing_time_ms": 2500
            }
        }
        ```
        """
        
        start_time = time.time()
        
        # Validar el input
        serializer = VoiceCommandUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Datos inválidos',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        audio_file: UploadedFile = serializer.validated_data['audio']
        language = serializer.validated_data.get('language', 'es-MX')
        
        # Crear el comando en BD
        voice_command = VoiceCommand.objects.create(
            user=request.user,
            audio_file=audio_file,
            status='PROCESSING'
        )
        
        # Historial: Audio recibido
        VoiceCommandHistory.objects.create(
            voice_command=voice_command,
            stage='UPLOAD',
            message='Archivo de audio recibido',
            data={'filename': audio_file.name, 'size': audio_file.size}
        )
        
        try:
            # Verificar que el servicio esté inicializado
            if not speech_service.is_initialized():
                raise RuntimeError(
                    "Google Cloud Speech-to-Text no está configurado. "
                    "Verifica las credenciales en el archivo .env"
                )
            
            # Leer el contenido del audio
            audio_data = audio_file.read()
            
            # Detectar el formato del audio
            audio_format = self.detect_audio_format(audio_file.name)
            
            # Historial: Iniciando transcripción
            VoiceCommandHistory.objects.create(
                voice_command=voice_command,
                stage='TRANSCRIPTION_START',
                message=f'Iniciando transcripción (formato: {audio_format}, idioma: {language})',
                data={'format': audio_format, 'language': language}
            )
            
            # Transcribir el audio
            transcribed_text, confidence, metadata = speech_service.transcribe_audio(
                audio_data=audio_data,
                language_code=language,
                audio_format=audio_format
            )
            
            if not transcribed_text:
                voice_command.status = 'FAILED'
                voice_command.error_message = 'No se pudo transcribir el audio. Intenta hablar más claro o con menos ruido de fondo.'
                voice_command.save()
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='TRANSCRIPTION_FAILED',
                    message='No se obtuvo texto del audio',
                    data={}
                )
                
                return Response({
                    'success': False,
                    'error': voice_command.error_message
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar el comando con la transcripción
            voice_command.transcribed_text = transcribed_text
            voice_command.confidence = confidence
            voice_command.duration_seconds = metadata.get('duration_seconds')
            voice_command.status = 'TRANSCRIBED'
            voice_command.save()
            
            # Historial: Transcripción exitosa
            VoiceCommandHistory.objects.create(
                voice_command=voice_command,
                stage='TRANSCRIPTION_SUCCESS',
                message=f'Texto transcrito: "{transcribed_text}"',
                data={'confidence': confidence, 'duration': metadata.get('duration_seconds')}
            )
            
            # Procesar el comando
            processor = VoiceCommandProcessor(user=request.user)
            command_result = processor.process_command(transcribed_text)
            
            # Actualizar el comando con el resultado
            voice_command.command_type = command_result.get('command_type')
            voice_command.interpreted_params = command_result.get('params', {})
            
            if command_result.get('success'):
                voice_command.status = 'EXECUTED'
                voice_command.result_data = command_result.get('result', {})
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='EXECUTION_SUCCESS',
                    message=f'Comando ejecutado exitosamente',
                    data={'command_type': command_result.get('command_type')}
                )
            else:
                voice_command.status = 'FAILED'
                voice_command.error_message = command_result.get('error', 'Error desconocido')
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='EXECUTION_FAILED',
                    message=f'Error: {voice_command.error_message}',
                    data={}
                )
            
            # Calcular tiempo de procesamiento
            end_time = time.time()
            voice_command.processing_time_ms = int((end_time - start_time) * 1000)
            voice_command.save()
            
            # Serializar y devolver
            serializer = VoiceCommandSerializer(voice_command)
            
            return Response({
                'success': command_result.get('success', False),
                'data': serializer.data,
                'message': 'Comando procesado exitosamente' if command_result.get('success') else voice_command.error_message
            }, status=status.HTTP_200_OK if command_result.get('success') else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"❌ Error al procesar audio: {e}")
            
            voice_command.status = 'FAILED'
            voice_command.error_message = str(e)
            voice_command.save()
            
            VoiceCommandHistory.objects.create(
                voice_command=voice_command,
                stage='ERROR',
                message=f'Error inesperado: {str(e)}',
                data={}
            )
            
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['POST'], url_path='process-text')
    def process_text(self, request):
        """
        Procesa un comando de texto directamente (sin audio)
        
        Útil para testing o interfaces de texto
        
        **Request:**
        ```json
        {
            "text": "generar reporte de ventas del último mes"
        }
        ```
        """
        
        start_time = time.time()
        
        # Validar el input
        serializer = VoiceCommandTextSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Datos inválidos',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        text = serializer.validated_data['text']
        
        # Crear el comando en BD
        voice_command = VoiceCommand.objects.create(
            user=request.user,
            transcribed_text=text,
            status='TRANSCRIBED',
            confidence=1.0  # Confianza máxima para texto directo
        )
        
        VoiceCommandHistory.objects.create(
            voice_command=voice_command,
            stage='TEXT_INPUT',
            message=f'Texto recibido: "{text}"',
            data={'source': 'text_api'}
        )
        
        try:
            # Procesar el comando
            processor = VoiceCommandProcessor(user=request.user)
            command_result = processor.process_command(text)
            
            # Actualizar el comando
            voice_command.command_type = command_result.get('command_type')
            voice_command.interpreted_params = command_result.get('params', {})
            
            if command_result.get('success'):
                voice_command.status = 'EXECUTED'
                voice_command.result_data = command_result.get('result', {})
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='EXECUTION_SUCCESS',
                    message='Comando ejecutado exitosamente',
                    data={'command_type': command_result.get('command_type')}
                )
            else:
                voice_command.status = 'FAILED'
                voice_command.error_message = command_result.get('error', 'Error desconocido')
                
                VoiceCommandHistory.objects.create(
                    voice_command=voice_command,
                    stage='EXECUTION_FAILED',
                    message=f'Error: {voice_command.error_message}',
                    data={}
                )
            
            # Tiempo de procesamiento
            end_time = time.time()
            voice_command.processing_time_ms = int((end_time - start_time) * 1000)
            voice_command.save()
            
            # Serializar y devolver
            serializer = VoiceCommandSerializer(voice_command)
            
            return Response({
                'success': command_result.get('success', False),
                'data': serializer.data,
                'message': 'Comando procesado exitosamente' if command_result.get('success') else voice_command.error_message
            }, status=status.HTTP_200_OK if command_result.get('success') else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"❌ Error al procesar texto: {e}")
            
            voice_command.status = 'FAILED'
            voice_command.error_message = str(e)
            voice_command.save()
            
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['GET'], url_path='history')
    def history(self, request):
        """
        Obtiene el historial de todos los comandos del usuario
        """
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @action(detail=False, methods=['GET'], url_path='status')
    def service_status(self, request):
        """
        Verifica el estado del servicio de Google Cloud Speech-to-Text
        """
        
        is_initialized = speech_service.is_initialized()
        
        return Response({
            'success': True,
            'data': {
                'speech_service_active': is_initialized,
                'message': 'Servicio activo y listo para usar' if is_initialized else 'Servicio no configurado. Verifica las credenciales de Google Cloud.',
                'supported_languages': ['es-MX', 'es-ES'],
                'supported_formats': ['MP3', 'OGG', 'WAV', 'WEBM', 'M4A']
            }
        })
    
    def detect_audio_format(self, filename: str) -> str:
        """
        Detecta el formato de audio basándose en la extensión del archivo
        """
        
        extension = filename.lower().split('.')[-1]
        
        format_map = {
            'mp3': 'mp3',
            'wav': 'wav',
            'ogg': 'ogg',
            'webm': 'webm',
            'm4a': 'm4a',
            'oga': 'ogg',
        }
        
        return format_map.get(extension, 'mp3')  # Default a mp3

