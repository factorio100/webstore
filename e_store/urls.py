from django.urls import path
from . import views

app_name = 'e_store'

urlpatterns = [
	path('', views.home, name='home'),
	path('items/<slug:item_type_slug>/', views.items, name='items'),
	path('item/<int:item_id>/', views.item, name='item'),
	path('cart/', views.cart, name='cart'),
	path('order_informations/', views.order_informations, name='order_informations'),
	path('edit_order_informations/<int:order_id>/', views.edit_order_informations, name='edit_order_informations'),
	path('order_success/<int:order_id>/', views.order_success, name='order_success'),
	path('order_history/', views.order_history, name='order_history'),
	path('order/<int:order_id>/', views.order, name='order'),
]