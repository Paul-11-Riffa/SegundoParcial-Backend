"""
Test de Integración - Sistema de Comandos de Voz
Verifica el flujo completo Backend con diferentes tipos de comandos
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/voice-commands/process/"
TOKEN = "4f6a191d2eb8f13a7e7420caf9922c96681a843c"  # Token de admin1

HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}

# Comandos de prueba
TEST_COMMANDS = [
    {
        "name": "Reporte de ventas básico",
        "command": "reporte de ventas del último mes",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    },
    {
        "name": "Ventas por cliente",
        "command": "ventas por cliente",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    },
    {
        "name": "Productos más vendidos",
        "command": "top 10 productos más vendidos",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    },
    {
        "name": "Dashboard ejecutivo",
        "command": "dashboard ejecutivo",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    },
    {
        "name": "Predicción de ventas",
        "command": "predicción de ventas para 7 días",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    },
    {
        "name": "Reporte con formato específico",
        "command": "Dame un reporte de ventas del último mes en pdf",
        "expected_type": "reporte",
        "expected_status": "EXECUTED"
    }
]


def print_separator(char="=", length=80):
    """Imprime un separador visual"""
    print(char * length)


def print_header(text):
    """Imprime un encabezado formateado"""
    print_separator()
    print(f"  {text}")
    print_separator()


def test_single_command(command_data):
    """
    Prueba un comando individual y valida la respuesta
    
    Args:
        command_data: Diccionario con datos del comando
        
    Returns:
        Dict con resultado de la prueba
    """
    print(f"\n🧪 Probando: {command_data['name']}")
    print(f"   Comando: '{command_data['command']}'")
    
    payload = {"text": command_data["command"]}
    
    try:
        # Hacer request
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=HEADERS,
            timeout=30
        )
        
        # Validar código de respuesta
        if response.status_code == 200:
            print(f"   ✅ Status: {response.status_code} OK")
        else:
            print(f"   ❌ Status: {response.status_code} ERROR")
            print(f"   Response: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text
            }
        
        # Parsear JSON
        data = response.json()
        
        # Verificar estructura básica
        if "success" not in data:
            print(f"   ❌ Falta campo 'success' en respuesta")
            return {"success": False, "error": "Missing 'success' field"}
        
        if not data.get("success"):
            error_msg = data.get("error") or data.get("message", "Unknown error")
            print(f"   ❌ Backend reportó error: {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Verificar data anidada
        if "data" not in data:
            print(f"   ❌ Falta campo 'data' en respuesta")
            return {"success": False, "error": "Missing 'data' field"}
        
        command_result = data["data"]
        
        # Validar campos importantes
        required_fields = [
            "id", 
            "command_text", 
            "status", 
            "command_type",
            "result_data",
            "created_at"
        ]
        
        missing_fields = [f for f in required_fields if f not in command_result]
        if missing_fields:
            print(f"   ⚠️  Campos faltantes: {missing_fields}")
        
        # Validar valores esperados
        actual_status = command_result.get("status")
        actual_type = command_result.get("command_type")
        
        if actual_status != command_data["expected_status"]:
            print(f"   ⚠️  Estado inesperado: {actual_status} (esperado: {command_data['expected_status']})")
        else:
            print(f"   ✅ Estado: {actual_status}")
        
        if actual_type != command_data["expected_type"]:
            print(f"   ⚠️  Tipo inesperado: {actual_type} (esperado: {command_data['expected_type']})")
        else:
            print(f"   ✅ Tipo: {actual_type}")
        
        # Validar tiempo de procesamiento
        processing_time = command_result.get("processing_time_ms")
        if processing_time:
            print(f"   ⏱️  Tiempo: {processing_time}ms")
            if processing_time > 5000:
                print(f"   ⚠️  Advertencia: Tiempo de procesamiento alto (>{5000}ms)")
        
        # Validar confidence
        confidence = command_result.get("confidence_score")
        if confidence is not None:
            print(f"   🎯 Confianza: {confidence * 100:.1f}%")
            if confidence < 0.5:
                print(f"   ⚠️  Advertencia: Baja confianza (<50%)")
        
        # Validar result_data
        result_data = command_result.get("result_data", {})
        if not result_data:
            print(f"   ⚠️  Advertencia: result_data está vacío")
        else:
            if "report_info" in result_data:
                report_info = result_data["report_info"]
                print(f"   📊 Reporte: {report_info.get('name', 'N/A')}")
                print(f"   📁 Formato: {report_info.get('format', 'N/A')}")
            
            if "metadata" in result_data:
                metadata = result_data["metadata"]
                total_records = metadata.get("total_records", 0)
                print(f"   📈 Registros: {total_records}")
        
        print(f"   ✅ PRUEBA EXITOSA")
        
        return {
            "success": True,
            "command_id": command_result.get("id"),
            "status": actual_status,
            "type": actual_type,
            "processing_time": processing_time,
            "confidence": confidence,
            "data": command_result
        }
        
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT: El servidor no respondió en 30 segundos")
        return {"success": False, "error": "Timeout"}
    
    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNECTION ERROR: No se pudo conectar al servidor")
        print(f"   Verifica que el backend esté corriendo en {BASE_URL}")
        return {"success": False, "error": "Connection refused"}
    
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON ERROR: Respuesta no es JSON válido")
        print(f"   Error: {str(e)}")
        print(f"   Response: {response.text[:200]}")
        return {"success": False, "error": "Invalid JSON"}
    
    except Exception as e:
        print(f"   ❌ UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        return {"success": False, "error": str(e)}


def test_authentication():
    """Prueba la autenticación"""
    print_header("TEST 1: AUTENTICACIÓN")
    
    print("\n🔐 Verificando autenticación...")
    
    # Probar sin token
    print("\n   1️⃣ Request sin token:")
    response = requests.post(
        API_ENDPOINT,
        json={"text": "test"},
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    if response.status_code == 401:
        print(f"   ✅ Correctamente rechazado (401)")
    else:
        print(f"   ⚠️  Inesperado: {response.status_code}")
    
    # Probar con token inválido
    print("\n   2️⃣ Request con token inválido:")
    response = requests.post(
        API_ENDPOINT,
        json={"text": "test"},
        headers={
            "Authorization": "Token invalid_token_12345",
            "Content-Type": "application/json"
        },
        timeout=10
    )
    
    if response.status_code == 401:
        print(f"   ✅ Correctamente rechazado (401)")
    else:
        print(f"   ⚠️  Inesperado: {response.status_code}")
    
    # Probar con token válido
    print("\n   3️⃣ Request con token válido:")
    response = requests.post(
        API_ENDPOINT,
        json={"text": "test de autenticación"},
        headers=HEADERS,
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"   ✅ Autenticado correctamente (200)")
    else:
        print(f"   ❌ Error: {response.status_code}")
    
    print("\n✅ TEST DE AUTENTICACIÓN COMPLETADO\n")


def test_all_commands():
    """Ejecuta todos los tests de comandos"""
    print_header("TEST 2: PROCESAMIENTO DE COMANDOS")
    
    results = []
    successful = 0
    failed = 0
    
    for i, command_data in enumerate(TEST_COMMANDS, 1):
        result = test_single_command(command_data)
        results.append({
            "command": command_data["name"],
            "result": result
        })
        
        if result.get("success"):
            successful += 1
        else:
            failed += 1
    
    # Resumen
    print_header("RESUMEN DE PRUEBAS")
    print(f"\n   Total de pruebas: {len(TEST_COMMANDS)}")
    print(f"   ✅ Exitosas: {successful}")
    print(f"   ❌ Fallidas: {failed}")
    print(f"   📊 Tasa de éxito: {(successful/len(TEST_COMMANDS))*100:.1f}%")
    
    if failed > 0:
        print(f"\n   ⚠️  Comandos que fallaron:")
        for r in results:
            if not r["result"].get("success"):
                print(f"      - {r['command']}: {r['result'].get('error', 'Unknown')}")
    
    print()
    
    return results


def test_invalid_inputs():
    """Prueba inputs inválidos"""
    print_header("TEST 3: MANEJO DE INPUTS INVÁLIDOS")
    
    invalid_cases = [
        {
            "name": "Texto vacío",
            "payload": {"text": ""},
            "expected_code": 400
        },
        {
            "name": "Sin campo 'text'",
            "payload": {},
            "expected_code": 400
        },
        {
            "name": "Texto muy largo (>1000 chars)",
            "payload": {"text": "x" * 1001},
            "expected_code": 400
        },
        {
            "name": "Comando incomprensible",
            "payload": {"text": "asfkjahskfjhasfkjh"},
            "expected_code": 200  # Debe procesar pero con baja confianza
        }
    ]
    
    for case in invalid_cases:
        print(f"\n🧪 Probando: {case['name']}")
        
        try:
            response = requests.post(
                API_ENDPOINT,
                json=case["payload"],
                headers=HEADERS,
                timeout=10
            )
            
            if response.status_code == case["expected_code"]:
                print(f"   ✅ Código correcto: {response.status_code}")
            else:
                print(f"   ⚠️  Código inesperado: {response.status_code} (esperado: {case['expected_code']})")
            
            # Verificar que devuelve JSON válido
            try:
                data = response.json()
                print(f"   ✅ Respuesta JSON válida")
            except:
                print(f"   ❌ Respuesta no es JSON válido")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n✅ TEST DE INPUTS INVÁLIDOS COMPLETADO\n")


def main():
    """Función principal"""
    print("\n")
    print_separator("#", 80)
    print("##")
    print("##   TEST DE INTEGRACIÓN - SISTEMA DE COMANDOS DE VOZ")
    print("##   Backend: Django REST Framework")
    print(f"##   URL: {API_ENDPOINT}")
    print(f"##   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("##")
    print_separator("#", 80)
    print("\n")
    
    try:
        # Test 1: Autenticación
        test_authentication()
        
        # Test 2: Comandos válidos
        test_all_commands()
        
        # Test 3: Inputs inválidos
        test_invalid_inputs()
        
        print_separator("#", 80)
        print("##")
        print("##   ✅ TODOS LOS TESTS COMPLETADOS")
        print("##")
        print_separator("#", 80)
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrumpidos por el usuario\n")
    except Exception as e:
        print(f"\n\n❌ ERROR CRÍTICO: {str(e)}\n")
        raise


if __name__ == "__main__":
    main()
