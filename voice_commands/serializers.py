from rest_framework import serializers
from .models import VoiceCommand, VoiceCommandHistory


class VoiceCommandHistorySerializer(serializers.ModelSerializer):
    """Serializer para el historial de comandos"""
    
    class Meta:
        model = VoiceCommandHistory
        fields = ['id', 'stage', 'message', 'data', 'timestamp']
        read_only_fields = fields


class VoiceCommandSerializer(serializers.ModelSerializer):
    """Serializer para comandos de voz"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    history = VoiceCommandHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = VoiceCommand
        fields = [
            'id', 'user', 'user_username', 'audio_file', 'transcribed_text',
            'status', 'command_type', 'interpreted_params', 'result_data',
            'error_message', 'duration_seconds', 'processing_time_ms', 
            'confidence', 'created_at', 'updated_at', 'history'
        ]
        read_only_fields = [
            'id', 'user', 'transcribed_text', 'status', 'command_type',
            'interpreted_params', 'result_data', 'error_message',
            'duration_seconds', 'processing_time_ms', 'confidence',
            'created_at', 'updated_at'
        ]


class VoiceCommandUploadSerializer(serializers.Serializer):
    """Serializer para subir archivos de audio"""
    
    audio = serializers.FileField(
        required=True,
        help_text='Archivo de audio (MP3, OGG, WAV, WEBM, etc.)'
    )
    
    language = serializers.ChoiceField(
        choices=[('es-MX', 'Español (México)'), ('es-ES', 'Español (España)')],
        default='es-MX',
        help_text='Idioma del audio'
    )


class VoiceCommandTextSerializer(serializers.Serializer):
    """Serializer para procesar texto directamente (sin audio)"""
    
    text = serializers.CharField(
        required=True,
        max_length=1000,
        help_text='Texto del comando a procesar'
    )
