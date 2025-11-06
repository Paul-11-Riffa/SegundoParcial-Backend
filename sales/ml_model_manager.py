"""
Sistema de gestión de modelos ML: serialización, versionado y carga.
"""
import os
import joblib
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from sales.ml_predictor_simple import SimpleSalesPredictor


# Lock global para evitar carga concurrente de modelos
_model_load_lock = threading.Lock()

# Clave para Django cache
PREDICTOR_CACHE_KEY = 'ml_sales_predictor_instance'
PREDICTOR_CACHE_TIMEOUT = 300  # 5 minutos


class ModelManager:
    """
    Gestiona la serialización y carga de modelos ML entrenados.
    """
    
    def __init__(self):
        # Directorio para guardar modelos
        self.models_dir = Path(settings.BASE_DIR) / 'ml_models'
        self.models_dir.mkdir(exist_ok=True)
        
        # Archivo de metadata
        self.metadata_file = self.models_dir / 'models_metadata.json'
        
    def _get_model_filename(self, version: Optional[str] = None) -> str:
        """
        Genera nombre de archivo para el modelo.
        
        Args:
            version: Versión del modelo (timestamp si es None)
            
        Returns:
            Nombre de archivo
        """
        if version is None:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'sales_model_{version}.pkl'
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Carga metadata de modelos guardados."""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {'models': [], 'current_model': None}
    
    def _save_metadata(self, metadata: Dict[str, Any]):
        """Guarda metadata de modelos."""
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def save_model(
        self, 
        predictor: SimpleSalesPredictor, 
        version: Optional[str] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Guarda un modelo entrenado en disco.
        
        Args:
            predictor: Instancia de SimpleSalesPredictor entrenado
            version: Versión del modelo (opcional)
            notes: Notas sobre este modelo (opcional)
            
        Returns:
            Dict con información del modelo guardado
        """
        if predictor.model is None:
            raise ValueError("El predictor no tiene un modelo entrenado")
        
        # Generar nombre de archivo
        filename = self._get_model_filename(version)
        filepath = self.models_dir / filename
        
        print(f"💾 Guardando modelo en: {filepath}")
        
        # Guardar modelo y datos de entrenamiento
        model_data = {
            'model': predictor.model,
            'poly_features': predictor.poly_features,
            'training_data': predictor.training_data,
            'last_trained': predictor.last_trained,
            'metrics': predictor.metrics,
            'min_date': predictor.min_date
        }
        
        joblib.dump(model_data, filepath)
        
        # Actualizar metadata
        metadata = self._load_metadata()
        
        model_info = {
            'version': version or filename.replace('sales_model_', '').replace('.pkl', ''),
            'filename': filename,
            'saved_at': datetime.now().isoformat(),
            'metrics': predictor.metrics,
            'notes': notes,
            'file_size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2)
        }
        
        metadata['models'].append(model_info)
        metadata['current_model'] = model_info['version']
        
        self._save_metadata(metadata)
        
        print(f"✓ Modelo guardado exitosamente")
        print(f"  Versión: {model_info['version']}")
        print(f"  Tamaño: {model_info['file_size_mb']} MB")
        
        return model_info
    
    def load_model(self, version: Optional[str] = None, use_cache: bool = True) -> SimpleSalesPredictor:
        """
        Carga un modelo guardado desde disco (con thread safety y Django cache).
        
        Args:
            version: Versión del modelo a cargar (usa el actual si es None)
            use_cache: Si True, intenta usar caché de Django primero
            
        Returns:
            Instancia de SimpleSalesPredictor con el modelo cargado
        """
        # Intentar obtener del caché de Django primero
        if use_cache:
            cached_predictor = cache.get(PREDICTOR_CACHE_KEY)
            if cached_predictor is not None:
                print(f"✓ Usando modelo desde Django cache")
                return cached_predictor
        
        # Usar lock para evitar cargas concurrentes
        with _model_load_lock:
            # Verificar caché nuevamente dentro del lock (double-check locking)
            if use_cache:
                cached_predictor = cache.get(PREDICTOR_CACHE_KEY)
                if cached_predictor is not None:
                    print(f"✓ Usando modelo desde Django cache (double-check)")
                    return cached_predictor
            
            print(f"📂 Cargando modelo desde disco...")
            
            metadata = self._load_metadata()
            
            if not metadata['models']:
                raise ValueError("No hay modelos guardados")
            
            # Determinar qué modelo cargar
            if version is None:
                version = metadata['current_model']
                if version is None:
                    raise ValueError("No hay modelo actual definido")
            
            # Buscar información del modelo
            model_info = None
            for m in metadata['models']:
                if m['version'] == version:
                    model_info = m
                    break
            
            if model_info is None:
                raise ValueError(f"No se encontró el modelo con versión: {version}")
            
            # Cargar modelo
            filepath = self.models_dir / model_info['filename']
            
            if not filepath.exists():
                raise FileNotFoundError(f"Archivo de modelo no encontrado: {filepath}")
            
            print(f"  � Archivo: {model_info['filename']}")
            
            try:
                model_data = joblib.load(filepath)
            except Exception as e:
                print(f"⚠️  Error al cargar modelo: {e}")
                print(f"   Limpiando caché y reintentando...")
                cache.delete(PREDICTOR_CACHE_KEY)
                raise ValueError(f"Modelo corrupto o incompatible: {e}")
            
            # Crear predictor y restaurar estado
            predictor = SimpleSalesPredictor()
            predictor.model = model_data['model']
            predictor.poly_features = model_data.get('poly_features')
            predictor.training_data = model_data['training_data']
            predictor.last_trained = model_data['last_trained']
            predictor.metrics = model_data['metrics']
            predictor.min_date = model_data.get('min_date')
            
            # Cachear en Django cache (compartido entre todos los workers)
            try:
                cache.set(PREDICTOR_CACHE_KEY, predictor, PREDICTOR_CACHE_TIMEOUT)
                print(f"✓ Modelo cargado y guardado en Django cache ({PREDICTOR_CACHE_TIMEOUT}s)")
            except Exception as e:
                print(f"⚠️  No se pudo cachear el modelo: {e}")
            
            print(f"  ✓ Entrenado: {model_data['last_trained']}")
            print(f"  ✓ Muestras: {model_data['metrics'].get('training_samples', 'N/A')}")
            
            return predictor
        
        return predictor
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        Lista todos los modelos guardados.
        
        Returns:
            Lista de información de modelos
        """
        metadata = self._load_metadata()
        return metadata['models']
    
    def get_current_model_info(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información del modelo actual.
        
        Returns:
            Dict con información del modelo actual o None
        """
        metadata = self._load_metadata()
        current_version = metadata['current_model']
        
        if current_version is None:
            return None
        
        for model_info in metadata['models']:
            if model_info['version'] == current_version:
                return model_info
        
        return None
    
    def set_current_model(self, version: str) -> Dict[str, Any]:
        """
        Establece qué modelo usar como actual.
        
        Args:
            version: Versión del modelo a establecer como actual
            
        Returns:
            Dict con información del modelo establecido
        """
        metadata = self._load_metadata()
        
        # Verificar que el modelo existe
        model_info = None
        for m in metadata['models']:
            if m['version'] == version:
                model_info = m
                break
        
        if model_info is None:
            raise ValueError(f"No se encontró el modelo con versión: {version}")
        
        metadata['current_model'] = version
        self._save_metadata(metadata)
        
        print(f"✓ Modelo actual establecido: {version}")
        
        return model_info
    
    def delete_model(self, version: str) -> bool:
        """
        Elimina un modelo guardado.
        
        Args:
            version: Versión del modelo a eliminar
            
        Returns:
            True si se eliminó exitosamente
        """
        metadata = self._load_metadata()
        
        # No permitir eliminar el modelo actual
        if version == metadata['current_model']:
            raise ValueError("No se puede eliminar el modelo actual. Establece otro como actual primero.")
        
        # Buscar y eliminar
        model_info = None
        for i, m in enumerate(metadata['models']):
            if m['version'] == version:
                model_info = m
                metadata['models'].pop(i)
                break
        
        if model_info is None:
            raise ValueError(f"No se encontró el modelo con versión: {version}")
        
        # Eliminar archivo
        filepath = self.models_dir / model_info['filename']
        if filepath.exists():
            os.remove(filepath)
        
        self._save_metadata(metadata)
        
        print(f"✓ Modelo eliminado: {version}")
        
        return True
    
    def get_or_create_current_model(self) -> SimpleSalesPredictor:
        """
        Obtiene el modelo actual. Si no existe o falla, lanza error descriptivo.
        NO entrena automáticamente para evitar timeouts.
        
        Returns:
            Instancia de SimpleSalesPredictor
            
        Raises:
            ValueError: Si no hay modelo o no se puede cargar
        """
        try:
            return self.load_model(use_cache=True)
        except ValueError as e:
            error_msg = (
                f"No se pudo cargar el modelo: {str(e)}\n"
                "Por favor, entrena un modelo manualmente usando:\n"
                "POST /api/orders/ml/train/"
            )
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except FileNotFoundError as e:
            error_msg = (
                f"Archivo de modelo no encontrado: {str(e)}\n"
                "El modelo puede haber sido eliminado. Entrena uno nuevo usando:\n"
                "POST /api/orders/ml/train/"
            )
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
        except Exception as e:
            error_msg = f"Error inesperado al cargar modelo: {str(e)}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
    
    def clear_predictor_cache(self):
        """
        Limpia el caché del predictor.
        Útil cuando se entrena un nuevo modelo.
        """
        cache.delete(PREDICTOR_CACHE_KEY)
        print("✓ Caché del predictor limpiado")
    
    @property
    def current_model_version(self) -> Optional[str]:
        """
        Obtiene la versión del modelo actual.
        
        Returns:
            Versión del modelo o None si no hay modelo
        """
        metadata = self._load_metadata()
        return metadata.get('current_model')
    
    def get_models_info(self) -> Dict[str, Any]:
        """
        Obtiene información de todos los modelos guardados.
        
        Returns:
            Dict con lista de modelos y modelo actual
        """
        metadata = self._load_metadata()
        return {
            'models': metadata.get('models', []),
            'current_model': next(
                (m for m in metadata.get('models', []) if m['version'] == metadata.get('current_model')),
                None
            )
        }


# Instancia global del manager
model_manager = ModelManager()


def get_predictor() -> SimpleSalesPredictor:
    """
    Función helper para obtener el predictor actual.
    
    Returns:
        Instancia de SimpleSalesPredictor con modelo cargado
        
    Ejemplo:
        >>> from sales.ml_model_manager import get_predictor
        >>> predictor = get_predictor()
        >>> predictions = predictor.predict(days=30)
    """
    return model_manager.get_or_create_current_model()
