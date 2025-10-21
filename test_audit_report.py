"""
Script para probar el generador de reportes de auditoría
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from sales.audit_report_generator import AuditReportGenerator

print("=== Probando Generador de Reportes de Auditoría ===\n")

try:
    # Test 1: Sin filtros
    print("Test 1: Sin filtros")
    generator = AuditReportGenerator({})
    report_data = generator.generate()
    print(f"✓ Éxito - Total registros: {report_data['totals']['total_registros']}")
    print(f"  Keys: {list(report_data.keys())}")
    print()

    # Test 2: Con filtros
    print("Test 2: Con filtros de fechas")
    filters = {
        'start_date': '2025-10-01',
        'end_date': '2025-10-21'
    }
    generator = AuditReportGenerator(filters)
    report_data = generator.generate()
    print(f"✓ Éxito - Total registros: {report_data['totals']['total_registros']}")
    print()

    # Test 3: Con usuario específico
    print("Test 3: Con usuario específico")
    filters = {'user': 'admin'}
    generator = AuditReportGenerator(filters)
    report_data = generator.generate()
    print(f"✓ Éxito - Total registros: {report_data['totals']['total_registros']}")
    print()

    print("✓ TODOS LOS TESTS PASARON")

except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
