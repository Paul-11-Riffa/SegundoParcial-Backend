"""
Script de prueba para el sistema de recomendaciones.
Verifica todas las funcionalidades del sistema.
"""
import os
import django
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from sales.ml_recommender import recommender
from django.contrib.auth import get_user_model
from products.models import Product, Category
from sales.models import Order, OrderItem
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


def print_section(title):
    """Imprime un separador visual."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def test_system_status():
    """Verifica el estado del sistema."""
    print_section("📊 ESTADO DEL SISTEMA")
    
    # Contar recursos
    users_count = User.objects.count()
    products_count = Product.objects.count()
    categories_count = Category.objects.count()
    orders_count = Order.objects.filter(status='COMPLETED').count()
    
    print(f"✓ Usuarios registrados: {users_count}")
    print(f"✓ Productos activos: {products_count}")
    print(f"✓ Categorías: {categories_count}")
    print(f"✓ Órdenes completadas: {orders_count}")
    
    if users_count == 0:
        print("\n⚠️  No hay usuarios. Crea usuarios primero.")
        return False
    
    if products_count == 0:
        print("\n⚠️  No hay productos. Crea productos primero.")
        return False
    
    if orders_count == 0:
        print("\n⚠️  No hay órdenes completadas. El sistema necesita datos de compras.")
        print("   Sugerencia: Realiza algunas compras de prueba o genera datos demo.")
        return False
    
    print("\n✅ Sistema listo para pruebas de recomendaciones")
    return True


def test_user_recommendations():
    """Prueba recomendaciones personalizadas."""
    print_section("🎯 TEST 1: Recomendaciones Personalizadas")
    
    # Buscar un usuario con compras
    users_with_orders = User.objects.filter(
        orders__status='COMPLETED'
    ).distinct()[:3]
    
    if not users_with_orders:
        print("⚠️  No hay usuarios con compras completadas")
        return False
    
    for user in users_with_orders:
        print(f"\n👤 Usuario: {user.username} (ID: {user.id})")
        
        # Contar compras
        orders_count = Order.objects.filter(
            customer=user,
            status='COMPLETED'
        ).count()
        print(f"   Órdenes completadas: {orders_count}")
        
        try:
            # Obtener recomendaciones
            recommendations = recommender.get_recommendations_for_user(
                user_id=user.id,
                n_recommendations=5,
                exclude_purchased=True
            )
            
            print(f"\n   📦 Recomendaciones generadas: {recommendations['total_recommendations']}")
            print(f"   🔧 Estrategias usadas: {', '.join(recommendations['strategies_used'])}")
            
            # Mostrar top 3
            for i, rec in enumerate(recommendations['recommendations'][:3], 1):
                print(f"\n   {i}. {rec['name']}")
                print(f"      💰 Precio: ${rec['price']}")
                print(f"      📊 Score: {rec['recommendation_score']}")
                print(f"      💡 Razón: {rec['reason']}")
            
            print("\n   ✅ Test exitoso")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False
    
    return True


def test_similar_products():
    """Prueba productos similares."""
    print_section("🔗 TEST 2: Productos Similares")
    
    # Obtener productos con ventas
    products_with_sales = Product.objects.filter(
        order_items__order__status='COMPLETED'
    ).distinct()[:3]
    
    if not products_with_sales:
        print("⚠️  No hay productos con ventas")
        return False
    
    for product in products_with_sales:
        print(f"\n📦 Producto: {product.name} (ID: {product.id})")
        print(f"   Categoría: {product.category.name if product.category else 'Sin categoría'}")
        print(f"   Precio: ${product.price}")
        
        try:
            similar = recommender.get_similar_products(
                product_id=product.id,
                n=5
            )
            
            print(f"\n   🔗 Productos similares encontrados: {len(similar)}")
            
            for i, sim in enumerate(similar[:3], 1):
                print(f"\n   {i}. {sim['name']}")
                print(f"      💰 ${sim['price']}")
                print(f"      💡 {sim['reason']}")
            
            print("\n   ✅ Test exitoso")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False
    
    return True


def test_trending_products():
    """Prueba productos en tendencia."""
    print_section("📈 TEST 3: Productos en Tendencia")
    
    try:
        trending_data = recommender._get_trending_products(10)
        
        if not trending_data:
            print("⚠️  No hay productos en tendencia")
            return False
        
        print(f"✓ Productos trending encontrados: {len(trending_data)}")
        
        # Obtener detalles
        product_ids = [pid for pid, _ in trending_data]
        products = Product.objects.filter(id__in=product_ids).select_related('category')
        
        print("\n🔥 Top 5 Productos en Tendencia (últimos 30 días):\n")
        
        for i, product in enumerate(products[:5], 1):
            score = next((s for pid, s in trending_data if pid == product.id), 0)
            print(f"{i}. {product.name}")
            print(f"   💰 ${product.price}")
            print(f"   📊 Score: {score:.3f}")
            print(f"   📦 Stock: {product.stock}")
            print()
        
        print("✅ Test exitoso")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_category_trending():
    """Prueba trending por categoría."""
    print_section("📂 TEST 4: Trending por Categoría")
    
    categories = Category.objects.all()[:2]
    
    if not categories:
        print("⚠️  No hay categorías")
        return False
    
    for category in categories:
        print(f"\n📂 Categoría: {category.name}")
        
        try:
            trending = recommender.get_trending_in_category(
                category_id=category.id,
                n=5
            )
            
            print(f"   ✓ Productos trending: {len(trending)}")
            
            for i, prod in enumerate(trending[:3], 1):
                print(f"\n   {i}. {prod['name']}")
                print(f"      💰 ${prod['price']}")
                print(f"      📊 Ventas recientes: {prod['recent_sales']}")
            
            print("\n   ✅ Test exitoso")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return False
    
    return True


def run_performance_test():
    """Prueba de rendimiento."""
    print_section("⚡ TEST 5: Rendimiento")
    
    import time
    
    user = User.objects.filter(orders__status='COMPLETED').first()
    
    if not user:
        print("⚠️  No hay usuarios con compras")
        return False
    
    print(f"Usuario de prueba: {user.username}")
    
    # Test 1: Recomendaciones personalizadas
    start = time.time()
    try:
        recommendations = recommender.get_recommendations_for_user(
            user_id=user.id,
            n_recommendations=20
        )
        elapsed = time.time() - start
        print(f"\n✓ Recomendaciones (20 items): {elapsed:.3f}s")
    except Exception as e:
        print(f"❌ Error en recomendaciones: {str(e)}")
    
    # Test 2: Productos similares
    product = Product.objects.first()
    if product:
        start = time.time()
        try:
            similar = recommender.get_similar_products(product.id, n=10)
            elapsed = time.time() - start
            print(f"✓ Productos similares (10 items): {elapsed:.3f}s")
        except Exception as e:
            print(f"❌ Error en similares: {str(e)}")
    
    # Test 3: Trending
    start = time.time()
    try:
        trending = recommender._get_trending_products(20)
        elapsed = time.time() - start
        print(f"✓ Productos trending (20 items): {elapsed:.3f}s")
    except Exception as e:
        print(f"❌ Error en trending: {str(e)}")
    
    print("\n✅ Tests de rendimiento completados")
    return True


def main():
    """Ejecuta todos los tests."""
    print("\n" + "🎯"*35)
    print("   SISTEMA DE RECOMENDACIONES - SUITE DE PRUEBAS")
    print("🎯"*35)
    
    # Verificar estado del sistema
    if not test_system_status():
        print("\n❌ Sistema no listo para pruebas")
        print("\n💡 Sugerencias:")
        print("   1. Asegúrate de tener usuarios registrados")
        print("   2. Crea productos y categorías")
        print("   3. Genera órdenes de prueba o usa datos demo")
        return
    
    # Ejecutar tests
    results = []
    results.append(("Recomendaciones Personalizadas", test_user_recommendations()))
    results.append(("Productos Similares", test_similar_products()))
    results.append(("Productos Trending", test_trending_products()))
    results.append(("Trending por Categoría", test_category_trending()))
    results.append(("Rendimiento", run_performance_test()))
    
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
