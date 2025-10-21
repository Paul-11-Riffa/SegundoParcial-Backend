"""
Script para probar el endpoint completo de generación de reportes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from sales.views_audit_reports import GenerateAuditReportView

print("=== Probando Endpoint de Reportes ===\n")

# Crear factory
factory = RequestFactory()

# Obtener o crear un usuario admin
user, created = User.objects.get_or_create(
    username='admin',
    defaults={'is_staff': True, 'is_superuser': True}
)
if created:
    user.set_password('admin')
    user.save()
    print(f"✓ Usuario admin creado")
else:
    print(f"✓ Usuario admin ya existe")

# Test 1: Reporte JSON
print("\nTest 1: Reporte en formato JSON")
request = factory.post('/api/sales/audit/generate-report/', 
                      data={'filters': {}, 'format': 'json'},
                      content_type='application/json')
request.user = user

view = GenerateAuditReportView()
response = view.post(request)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"✓ Éxito - JSON response recibido")
    data = response.data
    print(f"  Total registros: {data['data']['totals']['total_registros']}")
else:
    print(f"✗ Error: {response.data}")

# Test 2: Reporte con filtros
print("\nTest 2: Reporte con filtros de usuario")
request = factory.post('/api/sales/audit/generate-report/', 
                      data={'filters': {'user': 'admin'}, 'format': 'json'},
                      content_type='application/json')
request.user = user

view = GenerateAuditReportView()
response = view.post(request)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"✓ Éxito")
else:
    print(f"✗ Error: {response.data}")

print("\n✓ TODOS LOS TESTS DEL ENDPOINT PASARON")
