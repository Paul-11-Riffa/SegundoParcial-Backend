"""
Test del endpoint de reportes de auditoría con requests
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=== Test de Endpoint de Reportes de Auditoría ===\n")

# Primero login para obtener token
print("1. Obteniendo token de autenticación...")
login_data = {
    "username": "admin",
    "password": "admin123"
}

try:
    response = requests.post(f"{BASE_URL}/api/auth/login/", json=login_data)
    if response.status_code == 200:
        token = response.json().get('access')
        print(f"✓ Token obtenido")
    else:
        print(f"✗ Error en login: {response.status_code}")
        print(response.text)
        exit(1)
except Exception as e:
    print(f"✗ Error de conexión: {e}")
    print("Asegúrate de que el servidor Django esté corriendo")
    exit(1)

# Headers con autenticación
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Test 1: Reporte JSON sin filtros
print("\n2. Test: Reporte JSON sin filtros")
data = {
    "filters": {},
    "format": "json"
}

response = requests.post(
    f"{BASE_URL}/api/sales/audit/generate-report/",
    json=data,
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✓ Éxito")
    print(f"  Total registros: {result['data']['totals']['total_registros']}")
    print(f"  Total éxitos: {result['data']['totals']['total_exitos']}")
    print(f"  Total errores: {result['data']['totals']['total_errores']}")
else:
    print(f"✗ Error: {response.text}")

# Test 2: Reporte con filtros
print("\n3. Test: Reporte con filtros de fecha")
data = {
    "filters": {
        "start_date": "2025-10-01",
        "end_date": "2025-10-21"
    },
    "format": "json"
}

response = requests.post(
    f"{BASE_URL}/api/sales/audit/generate-report/",
    json=data,
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✓ Éxito")
    print(f"  Total registros: {result['data']['totals']['total_registros']}")
else:
    print(f"✗ Error: {response.text}")

# Test 3: Reporte con filtro de usuario
print("\n4. Test: Reporte filtrado por usuario")
data = {
    "filters": {
        "user": "admin"
    },
    "format": "json"
}

response = requests.post(
    f"{BASE_URL}/api/sales/audit/generate-report/",
    json=data,
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✓ Éxito")
    print(f"  Total registros: {result['data']['totals']['total_registros']}")
else:
    print(f"✗ Error: {response.text}")

# Test 4: Reporte de errores
print("\n5. Test: Reporte solo errores")
data = {
    "filters": {
        "success": False
    },
    "format": "json"
}

response = requests.post(
    f"{BASE_URL}/api/sales/audit/generate-report/",
    json=data,
    headers=headers
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✓ Éxito")
    print(f"  Total registros: {result['data']['totals']['total_registros']}")
else:
    print(f"✗ Error: {response.text}")

print("\n✓ TODAS LAS PRUEBAS COMPLETADAS")
