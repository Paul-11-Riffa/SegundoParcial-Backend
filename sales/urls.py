from django.urls import path
from .views import CartView, CartItemView, StripeCheckoutView, StripeWebhookView, ManualOrderCompletionView, \
    SalesHistoryView

urlpatterns = [
    # URL para ver el carrito y añadir artículos
    path('cart/', CartView.as_view(), name='cart'),
    # URL para actualizar o eliminar un artículo específico por su ID
    path('cart/items/<int:item_id>/', CartItemView.as_view(), name='cart-item'),
    path('checkout/', StripeCheckoutView.as_view(), name='checkout'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('sales-history/', SalesHistoryView.as_view(), name='sales-history'),
    path('debug/complete-order/', ManualOrderCompletionView.as_view(), name='debug-complete-order'),

]
