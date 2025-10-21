#!/usr/bin/env python
"""
Script para probar la generación de reportes con datos reales.
Genera reportes en los 3 formatos disponibles.
"""

import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from sales.audit_report_generator import AuditReportGenerator, AuditSessionReportGenerator
from sales.views_audit_reports import GenerateAuditReportView, GenerateSessionReportView
from django.contrib.auth.models import User
from rest_framework.test import APIClient


def test_json_report():
    """Prueba generación de reporte JSON."""
    print("\n" + "="*70)
    print("TEST 1: Generando reporte JSON con datos reales")
    print("="*70)

    filters = {
        'limit': 10
    }

    generator = AuditReportGenerator(filters)
    report = generator.generate()

    print(f"\n[OK] Título: {report['title']}")
    print(f"[OK] Subtítulo: {report['subtitle']}")
    print(f"\n[STATS] Estadísticas:")
    print(f"   - Total de registros: {report['totals']['total_registros']}")
    print(f"   - Éxitos: {report['totals']['total_exitos']}")
    print(f"   - Errores: {report['totals']['total_errores']}")
    print(f"   - Tasa de error: {report['totals']['tasa_error']}")

    print(f"\n[INFO] Resumen:")
    print(f"   - Usuarios únicos: {report['summary']['usuarios_unicos']}")
    print(f"   - IPs únicas: {report['summary']['ips_unicas']}")
    print(f"   - Tiempo promedio: {report['summary']['tiempo_promedio_ms']} ms")

    print(f"\n[LIST] Primeros 3 registros:")
    for i, row in enumerate(report['rows'][:3], 1):
        print(f"   {i}. {row[0]} | {row[1]} | {row[2][:50]}...")

    return True


def test_pdf_report():
    """Prueba generación de reporte PDF."""
    print("\n" + "="*70)
    print("TEST 2: Generando reporte PDF con datos reales")
    print("="*70)

    client = APIClient()
    admin = User.objects.filter(is_superuser=True).first()

    if not admin:
        print("[ERROR] No se encontró usuario administrador")
        return False

    # Autenticar
    client.force_authenticate(user=admin)

    # Hacer request
    response = client.post('/api/sales/audit/generate-report/', {
        'filters': {
            'limit': 20
        },
        'format': 'pdf'
    }, format='json')

    if response.status_code == 200:
        print(f"[OK] PDF generado correctamente")
        print(f"   - Content-Type: {response['Content-Type']}")
        print(f"   - Tamaño: {len(response.content)} bytes")
        print(f"   - Nombre archivo: {response['Content-Disposition']}")

        # Guardar PDF para verificación manual
        with open('test_reporte_real.pdf', 'wb') as f:
            f.write(response.content)
        print(f"   - Archivo guardado: test_reporte_real.pdf")

        return True
    else:
        print(f"[ERROR] Error al generar PDF: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"   - Detalles: {response.data}")
        return False


def test_excel_report():
    """Prueba generación de reporte Excel."""
    print("\n" + "="*70)
    print("TEST 3: Generando reporte Excel con datos reales")
    print("="*70)

    client = APIClient()
    admin = User.objects.filter(is_superuser=True).first()

    if not admin:
        print("[ERROR] No se encontró usuario administrador")
        return False

    # Autenticar
    client.force_authenticate(user=admin)

    # Hacer request
    response = client.post('/api/sales/audit/generate-report/', {
        'filters': {
            'action_type': 'READ',
            'limit': 30
        },
        'format': 'excel'
    }, format='json')

    if response.status_code == 200:
        print(f"[OK] Excel generado correctamente")
        print(f"   - Content-Type: {response['Content-Type']}")
        print(f"   - Tamaño: {len(response.content)} bytes")
        print(f"   - Nombre archivo: {response['Content-Disposition']}")

        # Guardar Excel para verificación manual
        with open('test_reporte_real.xlsx', 'wb') as f:
            f.write(response.content)
        print(f"   - Archivo guardado: test_reporte_real.xlsx")

        return True
    else:
        print(f"[ERROR] Error al generar Excel: {response.status_code}")
        if hasattr(response, 'data'):
            print(f"   - Detalles: {response.data}")
        return False


def test_filtered_report():
    """Prueba reporte con filtros específicos."""
    print("\n" + "="*70)
    print("TEST 4: Reporte con filtros específicos")
    print("="*70)

    from datetime import datetime, timedelta

    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    filters = {
        'start_date': week_ago,
        'end_date': today,
        'limit': 50
    }

    generator = AuditReportGenerator(filters)
    report = generator.generate()

    print(f"\n[OK] Reporte de la última semana generado")
    print(f"   - Período: {week_ago} a {today}")
    print(f"   - Total de registros: {report['totals']['total_registros']}")
    print(f"   - Errores: {report['totals']['total_errores']}")

    if report['summary']['por_accion']:
        print(f"\n[STATS] Distribución por tipo de acción:")
        for action, count in report['summary']['por_accion'].items():
            print(f"   - {action}: {count}")

    return True


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*70)
    print("PRUEBA DE GENERACIÓN DE REPORTES CON DATOS REALES")
    print("="*70)

    results = []

    try:
        results.append(("Reporte JSON", test_json_report()))
        results.append(("Reporte PDF", test_pdf_report()))
        results.append(("Reporte Excel", test_excel_report()))
        results.append(("Reporte Filtrado", test_filtered_report()))
    except Exception as e:
        print(f"\n[ERROR] Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        return

    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN DE RESULTADOS")
    print("="*70)

    for test_name, result in results:
        status = "[OK] PASÓ" if result else "[ERROR] FALLÓ"
        print(f"{status} - {test_name}")

    total_passed = sum(1 for _, result in results if result)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests pasaron")

    if total_passed == total_tests:
        print("\n[SUCCESS] ¡Todos los tests pasaron exitosamente!")
        print("\nArchivos generados:")
        print("  - test_reporte_real.pdf")
        print("  - test_reporte_real.xlsx")
    else:
        print("\n[WARNING] Algunos tests fallaron. Revisar los errores arriba.")
        sys.exit(1)


if __name__ == '__main__':
    main()
