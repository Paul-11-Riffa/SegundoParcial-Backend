"""
Script de prueba para predicciones por producto con filtros.
"""
import os
import django
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from sales.ml_product_predictor import product_predictor
from products.models import Product, Category


def print_section(title):
    """Imprime un separador visual."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_product_prediction():
    """Prueba predicción de un producto específico."""
    print_section("📦 TEST 1: Predicción por Producto")
    
    # Obtener un producto con ventas
    product = Product.objects.filter(
        order_items__order__status='COMPLETED'
    ).first()
    
    if not product:
        print("⚠️  No hay productos con ventas")
        return False
    
    print(f"Producto: {product.name} (ID: {product.id})")
    print(f"Stock actual: {product.stock}")
    print(f"Precio: ${product.price}\n")
    
    # Predicción a 1 semana
    print("📊 Predicción a 1 SEMANA (7 días):")
    try:
        pred_week = product_predictor.predict_product_sales(
            product_id=product.id,
            days=7,
            include_confidence=True
        )
        
        if 'error' in pred_week:
            print(f"   ⚠️  {pred_week['error']}")
            print(f"   💡 {pred_week['message']}")
        else:
            print(f"   ✓ Unidades predichas: {pred_week['summary']['total_predicted_units']}")
            print(f"   ✓ Revenue predicho: ${pred_week['summary']['total_predicted_revenue']:.2f}")
            print(f"   ✓ Promedio diario: {pred_week['summary']['average_daily_units']:.2f} unidades")
            print(f"   ✓ Tendencia: {pred_week['trend']['trend_direction']}")
            
            if pred_week['stock_alert']['days_until_stockout']:
                print(f"\n   🚨 ALERTA: Stock se agotará en {pred_week['stock_alert']['days_until_stockout']} días")
                print(f"   📦 Reabastecer: {pred_week['stock_alert']['restock_recommended']} unidades")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Predicción a 2 semanas
    print("\n📊 Predicción a 2 SEMANAS (14 días):")
    try:
        pred_2weeks = product_predictor.predict_product_sales(
            product_id=product.id,
            days=14,
            include_confidence=False
        )
        
        if 'error' not in pred_2weeks:
            print(f"   ✓ Unidades predichas: {pred_2weeks['summary']['total_predicted_units']}")
            print(f"   ✓ Revenue predicho: ${pred_2weeks['summary']['total_predicted_revenue']:.2f}")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Predicción a 1 mes
    print("\n📊 Predicción a 1 MES (30 días):")
    try:
        pred_month = product_predictor.predict_product_sales(
            product_id=product.id,
            days=30,
            include_confidence=False
        )
        
        if 'error' not in pred_month:
            print(f"   ✓ Unidades predichas: {pred_month['summary']['total_predicted_units']}")
            print(f"   ✓ Revenue predicho: ${pred_month['summary']['total_predicted_revenue']:.2f}")
            print(f"   ✓ Crecimiento vs histórico: {pred_month['summary']['growth_vs_historical']['units_growth_percent']:.2f}%")
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print("\n✅ Test completado")
    return True


def test_category_prediction():
    """Prueba predicción por categoría."""
    print_section("📂 TEST 2: Predicción por Categoría")
    
    category = Category.objects.first()
    
    if not category:
        print("⚠️  No hay categorías")
        return False
    
    print(f"Categoría: {category.name} (ID: {category.id})\n")
    
    try:
        pred = product_predictor.predict_category_sales(
            category_id=category.id,
            days=30
        )
        
        if 'error' in pred:
            print(f"⚠️  {pred['error']}")
        else:
            print(f"✓ Productos analizados: {pred['category']['total_products']}")
            print(f"✓ Unidades totales predichas: {pred['summary']['total_predicted_units']:.2f}")
            print(f"✓ Revenue total predicho: ${pred['summary']['total_predicted_revenue']:.2f}")
            
            print(f"\n🏆 Top 3 Productos de la Categoría:")
            for i, prod in enumerate(pred['top_products'][:3], 1):
                print(f"\n{i}. {prod['product_name']}")
                print(f"   Predicción: {prod['predicted_units']:.2f} unidades")
                print(f"   Revenue: ${prod['predicted_revenue']:.2f}")
                print(f"   Stock actual: {prod['current_stock']}")
        
        print("\n✅ Test completado")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_top_products_forecast():
    """Prueba ranking de productos más vendidos futuros."""
    print_section("🏆 TEST 3: Top Productos Predichos")
    
    print("📊 Predicción: ¿Qué se venderá más en los próximos 30 días?\n")
    
    try:
        forecast = product_predictor.get_top_products_forecast(
            days=30,
            limit=10
        )
        
        print(f"✓ Productos analizados: {forecast['total_analyzed']}")
        print(f"\n🔝 Top 10 Productos que se Venderán Más:\n")
        
        for prod in forecast['top_products']:
            print(f"#{prod['rank']} - {prod['product_name']}")
            print(f"     Categoría: {prod['category']}")
            print(f"     Predicción: {prod['predicted_units']:.2f} unidades")
            print(f"     Revenue: ${prod['predicted_revenue']:.2f}")
            print(f"     Tendencia: {prod['trend']}")
            print()
        
        print("✅ Test completado")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_compare_products():
    """Prueba comparación de productos."""
    print_section("⚖️  TEST 4: Comparar Productos")
    
    products = Product.objects.filter(
        order_items__order__status='COMPLETED'
    ).distinct()[:5]
    
    if len(products) < 2:
        print("⚠️  Se necesitan al menos 2 productos con ventas")
        return False
    
    product_ids = [p.id for p in products]
    
    print(f"Comparando {len(product_ids)} productos...")
    print(f"IDs: {product_ids}\n")
    
    try:
        comparison = product_predictor.compare_products(
            product_ids=product_ids,
            days=14
        )
        
        print(f"✓ Período de comparación: {comparison['period_days']} días\n")
        print("📊 Resultados:\n")
        
        for i, prod in enumerate(comparison['comparison'], 1):
            if 'error' not in prod:
                print(f"{i}. {prod['product_name']}")
                print(f"   Predicción: {prod['predicted_units']:.2f} unidades")
                print(f"   Revenue: ${prod['predicted_revenue']:.2f}")
                print(f"   Crecimiento: {prod['growth_percent']:.2f}%")
                print()
        
        if comparison['best_performer']:
            print(f"🏆 MEJOR PREDICCIÓN: {comparison['best_performer']['product_name']}")
            print(f"   {comparison['best_performer']['predicted_units']:.2f} unidades")
        
        print("\n✅ Test completado")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_stock_alerts():
    """Prueba alertas de stock."""
    print_section("🚨 TEST 5: Alertas de Stock")
    
    try:
        # Simular llamada a través de la vista
        from sales.views_product_predictions import get_stock_alerts
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        admin = User.objects.filter(is_staff=True).first()
        
        if not admin:
            print("⚠️  No hay usuarios admin")
            return False
        
        factory = APIRequestFactory()
        request = factory.get('/api/orders/predictions/stock-alerts/?days=30')
        request.user = admin
        
        response = get_stock_alerts(request)
        data = response.data
        
        if data['success']:
            alerts = data['data']['alerts']
            print(f"✓ Alertas encontradas: {data['data']['total_alerts']}")
            print(f"✓ Críticas: {data['data']['critical_count']}")
            print(f"✓ Advertencias: {data['data']['warning_count']}\n")
            
            if alerts:
                print("🚨 Top Alertas:\n")
                for alert in alerts[:5]:
                    print(f"⚠️  {alert['product_name']}")
                    print(f"   Stock actual: {alert['current_stock']} unidades")
                    print(f"   Se agota en: {alert['days_until_stockout']} días")
                    print(f"   Reabastecer: {alert['restock_recommended']} unidades")
                    print(f"   Nivel: {alert['alert_level']}")
                    print()
            else:
                print("✅ No hay alertas críticas de stock")
        
        print("✅ Test completado")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "🎯"*35)
    print("   PREDICCIONES POR PRODUCTO - SUITE DE PRUEBAS")
    print("🎯"*35)
    
    results = []
    results.append(("Predicción por Producto (1 sem, 2 sem, 1 mes)", test_product_prediction()))
    results.append(("Predicción por Categoría", test_category_prediction()))
    results.append(("Top Productos Predichos", test_top_products_forecast()))
    results.append(("Comparar Productos", test_compare_products()))
    results.append(("Alertas de Stock", test_stock_alerts()))
    
    # Resumen
    print_section("📊 RESUMEN DE PRUEBAS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*70}")
    print(f"   Tests completados: {passed}/{total}")
    
    if passed == total:
        print("   🎉 ¡TODOS LOS TESTS PASARON!")
    else:
        print(f"   ⚠️  {total - passed} test(s) fallaron")
    
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
