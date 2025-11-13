"""
Script para limpiar bytes nulos de archivos Python
"""

import os

def clean_null_bytes(filepath):
    """Elimina bytes nulos de un archivo"""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        null_count = content.count(b'\x00')
        
        if null_count > 0:
            clean_content = content.replace(b'\x00', b'')
            with open(filepath, 'wb') as f:
                f.write(clean_content)
            print(f"✅ {filepath}: Eliminados {null_count} bytes nulos")
            return True
        else:
            print(f"✓ {filepath}: Sin bytes nulos")
            return False
    except Exception as e:
        print(f"❌ Error en {filepath}: {e}")
        return False

# Archivos a limpiar
files_to_check = [
    'backend/settings.py',
    'requirements.txt',
    'manage.py',
    'backend/wsgi.py',
    'backend/urls.py',
]

print("🔍 Limpiando archivos...\n")
cleaned = 0

for filepath in files_to_check:
    if os.path.exists(filepath):
        if clean_null_bytes(filepath):
            cleaned += 1
    else:
        print(f"⚠️  {filepath}: No existe")

print(f"\n✅ Total archivos limpiados: {cleaned}")
