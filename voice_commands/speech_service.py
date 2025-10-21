"""
Servicio de Speech-to-Text usando Google Cloud
"""
import os
import io
import logging
import wave
import struct
from typing import Dict, Tuple, Optional
from google.cloud import speech
from django.conf import settings

logger = logging.getLogger(__name__)


class SpeechService:
    """
    Servicio para convertir audio a texto usando Google Cloud Speech-to-Text
    """
    
    _instance = None
    _client = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa el cliente de Google Cloud Speech"""
        if not self._client:
            try:
                # Configurar las credenciales desde el archivo .env
                credentials_path = getattr(settings, 'GOOGLE_CLOUD_CREDENTIALS_PATH', None)
                
                if credentials_path and os.path.exists(credentials_path):
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                    self._client = speech.SpeechClient()
                    logger.info("✅ Google Cloud Speech-to-Text inicializado correctamente")
                else:
                    logger.warning("⚠️ No se encontró el archivo de credenciales de Google Cloud")
                    self._client = None
                    
            except Exception as e:
                logger.error(f"❌ Error al inicializar Google Cloud Speech: {e}")
                self._client = None
    
    def is_initialized(self) -> bool:
        """Verifica si el servicio está inicializado"""
        return self._client is not None
    
    def get_audio_duration(self, audio_data: bytes) -> float:
        """
        Estima la duración del audio en segundos basándose en el tamaño
        
        Args:
            audio_data: Bytes del archivo de audio
        
        Returns:
            float: Duración estimada en segundos
        """
        try:
            # Estimación simple: ~16KB por segundo para audio de calidad media
            duration = len(audio_data) / 16000.0
            return duration
        except Exception as e:
            logger.error(f"❌ Error al estimar duración del audio: {e}")
            return 0.0
    
    def transcribe_audio(
        self, 
        audio_data: bytes, 
        language_code: str = 'es-MX',
        audio_format: str = 'mp3'
    ) -> Tuple[Optional[str], Optional[float], Optional[Dict]]:
        """
        Transcribe audio a texto usando Google Cloud Speech-to-Text
        
        Args:
            audio_data: Bytes del archivo de audio
            language_code: Código de idioma (es-MX para español México, es-ES para español España)
            audio_format: Formato del audio original (mp3, ogg, webm, wav, etc.)
        
        Returns:
            Tuple: (texto_transcrito, confianza, metadata)
        """
        
        if not self.is_initialized():
            raise RuntimeError("Google Cloud Speech-to-Text no está inicializado. Verifica las credenciales.")
        
        try:
            # Estimar duración del audio
            duration = self.get_audio_duration(audio_data)
            logger.info(f"⏱️ Duración estimada del audio: {duration:.2f} segundos")
            
            # Configurar el audio para Google Cloud Speech
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Detectar el encoding basándose en el formato
            encoding = self.get_audio_encoding(audio_format)
            
            config = speech.RecognitionConfig(
                encoding=encoding,
                language_code=language_code,
                enable_automatic_punctuation=True,  # Puntuación automática
                audio_channel_count=1,  # Mono
            )
            
            # Realizar la transcripción
            logger.info(f"🎤 Transcribiendo audio (formato: {audio_format}, encoding: {encoding})...")
            response = self._client.recognize(config=config, audio=audio)
            
            # Extraer el texto transcrito
            if not response.results:
                logger.warning("⚠️ No se obtuvo ninguna transcripción del audio")
                return None, None, None
            
            # Combinar todos los resultados
            transcript = ''
            total_confidence = 0.0
            num_results = 0
            
            for result in response.results:
                if result.alternatives:
                    alternative = result.alternatives[0]
                    transcript += alternative.transcript + ' '
                    total_confidence += alternative.confidence
                    num_results += 1
            
            transcript = transcript.strip()
            avg_confidence = total_confidence / num_results if num_results > 0 else 0.0
            
            logger.info(f"✅ Transcripción exitosa: '{transcript[:100]}...' (confianza: {avg_confidence:.2%})")
            
            metadata = {
                'duration_seconds': duration,
                'language_code': language_code,
                'num_results': num_results,
            }
            
            return transcript, avg_confidence, metadata
            
        except Exception as e:
            logger.error(f"❌ Error al transcribir audio: {e}")
            raise RuntimeError(f"Error en la transcripción: {str(e)}")
    
    def get_audio_encoding(self, audio_format: str) -> speech.RecognitionConfig.AudioEncoding:
        """
        Mapea el formato de audio al encoding de Google Cloud Speech
        
        Args:
            audio_format: Formato del audio (mp3, wav, ogg, webm, etc.)
        
        Returns:
            AudioEncoding: Encoding correspondiente
        """
        
        format_lower = audio_format.lower()
        
        encoding_map = {
            'wav': speech.RecognitionConfig.AudioEncoding.LINEAR16,
            'mp3': speech.RecognitionConfig.AudioEncoding.MP3,
            'ogg': speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            'webm': speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            'm4a': speech.RecognitionConfig.AudioEncoding.LINEAR16,
            'flac': speech.RecognitionConfig.AudioEncoding.FLAC,
        }
        
        return encoding_map.get(format_lower, speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)
    
    def transcribe_long_audio(
        self, 
        audio_uri: str, 
        language_code: str = 'es-MX'
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Transcribe audio largo (> 1 minuto) desde Google Cloud Storage
        
        Args:
            audio_uri: URI del audio en GCS (gs://bucket/file.wav)
            language_code: Código de idioma
        
        Returns:
            Tuple: (texto_transcrito, confianza)
        """
        
        if not self.is_initialized():
            raise RuntimeError("Google Cloud Speech-to-Text no está inicializado")
        
        try:
            audio = speech.RecognitionAudio(uri=audio_uri)
            
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                language_code=language_code,
                enable_automatic_punctuation=True,
            )
            
            # Operación asíncrona para audios largos
            operation = self._client.long_running_recognize(config=config, audio=audio)
            
            logger.info("⏳ Esperando transcripción de audio largo...")
            response = operation.result(timeout=300)  # 5 minutos máximo
            
            transcript = ''
            total_confidence = 0.0
            num_results = 0
            
            for result in response.results:
                if result.alternatives:
                    alternative = result.alternatives[0]
                    transcript += alternative.transcript + ' '
                    total_confidence += alternative.confidence
                    num_results += 1
            
            transcript = transcript.strip()
            avg_confidence = total_confidence / num_results if num_results > 0 else 0.0
            
            logger.info(f"✅ Transcripción larga exitosa: '{transcript[:100]}...'")
            
            return transcript, avg_confidence
            
        except Exception as e:
            logger.error(f"❌ Error al transcribir audio largo: {e}")
            raise RuntimeError(f"Error en la transcripción: {str(e)}")


# Instancia singleton
speech_service = SpeechService()
