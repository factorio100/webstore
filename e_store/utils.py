from django.db.models import Sum, F

def available_inventory(inventory):
	from .models import OrderItem  # Avoid ImportError: circular import models.py utils.py

	confirmed_quantity = OrderItem.objects.filter(
		order__status="confirmed", inventory=inventory
		).aggregate(total=Sum(F('quantity'))
		)['total'] or 0
	return inventory.quantity - confirmed_quantity
	