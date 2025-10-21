"""
Script de prueba para los endpoints de predicciones ML del dashboard.
Prueba los 3 endpoints principales para asegurar que funcionan correctamente.
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from rest_framework.test import force_authenticate

from sales.views_sales_predictions_dashboard import (
    sales_predictions_dashboard,
    top_products_predictions_dashboard,
    combined_predictions_dashboard
)
from sales.ml_predictor_simple import SimpleSalesPredictor
from sales.ml_model_manager import model_manager
from sales.models import Order


def print_separator(title):
    """Imprime un separador visual."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_sales_predictions_dashboard():
    """Prueba el endpoint de predicciones de ventas."""
    print_separator("TEST 1: Dashboard de Predicciones de Ventas")

    try:
        # Crear request simulado
        factory = RequestFactory()
        request = factory.get('/api/orders/dashboard/predictions/sales/')

        # Autenticar como admin
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            print("❌ ERROR: No hay usuario admin. Crea uno primero.")
            return False

        # Agregar usuario al request (necesario para ratelimit)
        request.user = admin_user
        force_authenticate(request, user=admin_user)

        # Llamar a la vista
        response = sales_predictions_dashboard(request)

        if response.status_code == 200:
            data = response.data
            print("✅ Endpoint responde correctamente")
            print(f"\n📊 Períodos disponibles:")

            for period_key in ['predictions_7d', 'predictions_14d', 'predictions_30d', 'predictions_90d']:
                if period_key in data.get('data', {}):
                    period_data = data['data'][period_key]
                    print(f"\n  • {period_data['period_label']} ({period_data['period_days']} días):")
                    print(f"    - Total predicho: ${period_data['summary']['total_sales']:,.2f}")
                    print(f"    - Promedio diario: ${period_data['summary']['average_daily']:,.2f}")
                    print(f"    - Crecimiento: {period_data['summary']['growth_rate']:+.2f}%")
                    print(f"    - Datos diarios: {len(period_data['daily_predictions'])} registros")

            # Verificar resumen
            if 'summary' in data.get('data', {}):
                summary = data['data']['summary']
                print(f"\n📈 Resumen General:")
                print(f"  - Forecast próxima semana: ${summary['next_week_forecast']:,.2f}")
                print(f"  - Forecast próximo mes: ${summary['next_month_forecast']:,.2f}")
                print(f"  - Forecast próximo trimestre: ${summary['next_quarter_forecast']:,.2f}")
                print(f"  - Tendencia general: {summary['overall_trend']}")
                print(f"  - Precisión del modelo (R²): {summary['model_accuracy']:.2%}")

            print(f"\n💾 Caché: {'Activo' if data.get('cached') else 'No usado'}")
            return True

        elif response.status_code == 424:
            print("⚠️ ADVERTENCIA: Modelo no entrenado")
            print(f"   Mensaje: {response.data.get('message')}")
            print(f"   Acción requerida: {response.data.get('action_required')}")
            return False
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"   {response.data}")
            return False

    except Exception as e:
        print(f"❌ EXCEPCIÓN: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_top_products_predictions_dashboard():
    """Prueba el endpoint de productos más vendidos."""
    print_separator("TEST 2: Dashboard de Productos Más Vendidos")

    try:
        factory = RequestFactory()
        request = factory.get('/api/orders/dashboard/predictions/top-products/?limit=5')

        admin_user = User.objects.filter(is_superuser=True).first()
        request.user = admin_user
        force_authenticate(request, user=admin_user)

        response = top_products_predictions_dashboard(request)

        if response.status_code == 200:
            data = response.data
            print("✅ Endpoint responde correctamente")

            for period_key in ['top_products_7d', 'top_products_14d', 'top_products_30d', 'top_products_90d']:
                if period_key in data.get('data', {}):
                    period_data = data['data'][period_key]
                    print(f"\n📦 {period_data['period_label']} - Top {period_data['total_products']} Productos:")

                    for product in period_data['products'][:3]:  # Mostrar solo top 3
                        print(f"\n  {product['rank']}. {product['product_name']}")
                        print(f"     - Ventas predichas: {product['predicted_sales']:.1f} unidades")
                        print(f"     - Ingresos: ${product['predicted_revenue']:,.2f}")
                        print(f"     - Crecimiento: {product['trend_icon']} {product['growth_rate']:+.1f}%")
                        print(f"     - Stock: {product['stock_icon']} {product['current_stock']} ({product['stock_status']})")

                    summary = period_data['period_summary']
                    print(f"\n  📊 Resumen del período:")
                    print(f"     - Total unidades: {summary['total_predicted_sales']:.1f}")
                    print(f"     - Total ingresos: ${summary['total_predicted_revenue']:,.2f}")
                    print(f"     - Productos con stock bajo: {summary['products_with_low_stock']}")

            # Análisis de consistencia
            if 'consistency_analysis' in data.get('data', {}):
                analysis = data['data']['consistency_analysis']
                print(f"\n🎯 Productos Más Consistentes:")
                for product in analysis['most_consistent'][:3]:
                    print(f"  • {product['product_name']}")
                    print(f"    - Aparece en {product['appearances_count']}/4 períodos")
                    print(f"    - Ranking promedio: #{product['average_rank']:.1f}")

            print(f"\n💾 Caché: {'Activo' if data.get('cached') else 'No usado'}")
            return True

        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"   {response.data}")
            return False

    except Exception as e:
        print(f"❌ EXCEPCIÓN: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_combined_predictions_dashboard():
    """Prueba el endpoint combinado."""
    print_separator("TEST 3: Dashboard Combinado (Todo en Uno)")

    try:
        factory = RequestFactory()
        request = factory.get('/api/orders/dashboard/predictions/combined/?products_limit=3')

        admin_user = User.objects.filter(is_superuser=True).first()
        request.user = admin_user
        force_authenticate(request, user=admin_user)

        response = combined_predictions_dashboard(request)

        if response.status_code == 200:
            data = response.data
            print("✅ Endpoint responde correctamente")

            # Ventas
            if 'sales_predictions' in data.get('data', {}):
                sales = data['data']['sales_predictions']
                print(f"\n💰 Predicciones de Ventas:")
                for period_key in ['7d', '14d', '30d', '90d']:
                    if period_key in sales:
                        period = sales[period_key]
                        print(f"  • {period['period_label']}: ${period['total_sales']:,.2f}")
                        print(f"    - Promedio diario: ${period['average_daily']:,.2f}")
                        print(f"    - Crecimiento: {period['growth_rate']:+.1f}%")

            # Productos
            if 'top_products' in data.get('data', {}):
                products = data['data']['top_products']
                print(f"\n🏆 Top Productos por Período:")
                for period_key in ['7d', '30d', '90d']:
                    if period_key in products and products[period_key]['products']:
                        period = products[period_key]
                        top_product = period['products'][0]
                        print(f"  • {period['period_label']}: {top_product['name']}")
                        print(f"    - {top_product['predicted_sales']:.1f} unidades ({top_product['growth_rate']:+.1f}%)")

            # Overview
            if 'overview' in data.get('data', {}):
                overview = data['data']['overview']
                print(f"\n📊 Resumen Ejecutivo:")
                print(f"  - Próxima semana: ${overview['next_week']['total_sales']:,.2f}")
                print(f"    Top: {overview['next_week']['top_product']['name'] if overview['next_week']['top_product'] else 'N/A'}")
                print(f"  - Próximo mes: ${overview['next_month']['total_sales']:,.2f}")
                print(f"  - Próximo trimestre: ${overview['next_quarter']['total_sales']:,.2f}")
                print(f"  - Tendencia: {overview['overall_growth_trend']:+.1f}%")

            print(f"\n💾 Caché: {'Activo' if data.get('cached') else 'No usado'}")
            return True

        elif response.status_code == 424:
            print("⚠️ ADVERTENCIA: Modelo no entrenado")
            print(f"   {response.data.get('action_required')}")
            return False
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ EXCEPCIÓN: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites():
    """Verifica que los prerrequisitos estén cumplidos."""
    print_separator("VERIFICANDO PRERREQUISITOS")

    # 1. Usuario admin
    admin_count = User.objects.filter(is_superuser=True).count()
    print(f"✓ Usuarios admin: {admin_count}")

    # 2. Órdenes completadas
    completed_orders = Order.objects.filter(status='COMPLETED').count()
    print(f"✓ Órdenes completadas: {completed_orders}")

    # 3. Modelo entrenado
    current_model = model_manager.get_current_model_info()
    if current_model:
        print(f"✓ Modelo ML entrenado:")
        print(f"  - Versión: {current_model['version']}")
        print(f"  - R² Score: {current_model['metrics'].get('r2_score', 0):.4f}")
        print(f"  - Entrenado: {current_model['saved_at']}")
    else:
        print(f"⚠️ No hay modelo entrenado")
        print(f"   Ejecuta: POST /api/orders/ml/train/")

    return admin_count > 0 and current_model is not None


def main():
    """Función principal de pruebas."""
    print("\n" + "=" * 80)
    print("  PRUEBAS DE ENDPOINTS DE PREDICCIONES ML")
    print("=" * 80)

    # Verificar prerrequisitos
    if not check_prerequisites():
        print("\n❌ FALLO: No se cumplen los prerrequisitos")
        print("\n💡 SOLUCIONES:")
        print("   1. Crea un usuario admin si no existe")
        print("   2. Genera datos de prueba: POST /api/orders/ml/generate-demo-data/")
        print("   3. Entrena el modelo: POST /api/orders/ml/train/")
        return

    # Ejecutar pruebas
    results = {
        'sales_dashboard': test_sales_predictions_dashboard(),
        'products_dashboard': test_top_products_predictions_dashboard(),
        'combined_dashboard': test_combined_predictions_dashboard()
    }

    # Resumen final
    print_separator("RESUMEN DE PRUEBAS")

    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)

    print(f"Total de pruebas: {total_tests}")
    print(f"Exitosas: {passed_tests}")
    print(f"Fallidas: {total_tests - passed_tests}")

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed_tests == total_tests:
        print("\n[SUCCESS] TODAS LAS PRUEBAS PASARON!")
        print("\nPROXIMOS PASOS:")
        print("   1. Revisa la documentacion en GUIA_PREDICCIONES_ML_FRONTEND.md")
        print("   2. Comparte los endpoints con el equipo de frontend")
        print("   3. Implementa las graficas siguiendo los ejemplos de la guia")
    else:
        print("\n[WARNING] ALGUNAS PRUEBAS FALLARON")
        print("   Revisa los errores anteriores y corrige los problemas")

    print("\n" + "=" * 80 + "\n")


if __name__ == '__main__':
    main()
