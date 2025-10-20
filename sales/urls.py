from django.urls import path
from .views import (
    CartView, CartItemView, StripeCheckoutView, StripeWebhookView, CompleteOrderView, 
    ManualOrderCompletionView, SalesHistoryView, GenerateOrderReceiptPDF, MyOrderListView,
    GenerateDynamicReportView
)
from .views_advanced_reports import (
    CustomerAnalysisReportView, ProductABCAnalysisView, ComparativeReportView,
    ExecutiveDashboardView, InventoryAnalysisView
)

urlpatterns = [
    # URL para ver el carrito y añadir artículos
    path('cart/', CartView.as_view(), name='cart'),
    # URL para actualizar o eliminar un artículo específico por su ID
    path('cart/items/<int:item_id>/', CartItemView.as_view(), name='cart-item'),
    path('checkout/', StripeCheckoutView.as_view(), name='checkout'),
    path('complete-order/', CompleteOrderView.as_view(), name='complete-order'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('sales-history/', SalesHistoryView.as_view(), name='sales-history'),
    path('sales-history/<int:order_id>/receipt/', GenerateOrderReceiptPDF.as_view(), name='order-receipt'),
    path('my-orders/', MyOrderListView.as_view(), name='my-orders'),
    path('debug/complete-order/', ManualOrderCompletionView.as_view(), name='debug-complete-order'),
    
    # === REPORTES DINÁMICOS ===
    path('reports/generate/', GenerateDynamicReportView.as_view(), name='generate-report'),
    
    # === REPORTES AVANZADOS ===
    path('reports/customer-analysis/', CustomerAnalysisReportView.as_view(), name='customer-analysis'),
    path('reports/product-abc/', ProductABCAnalysisView.as_view(), name='product-abc'),
    path('reports/comparative/', ComparativeReportView.as_view(), name='comparative-report'),
    path('reports/dashboard/', ExecutiveDashboardView.as_view(), name='executive-dashboard'),
    path('reports/inventory-analysis/', InventoryAnalysisView.as_view(), name='inventory-analysis'),
]
