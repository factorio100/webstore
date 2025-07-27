from django.db.models import Sum, F
from django.db import models
from django.utils.text import slugify


def available_inventory(inventory):
	from .models import OrderItem  # Avoid ImportError: circular import models.py utils.py

	confirmed_quantity = OrderItem.objects.filter(
		order__status="confirmed", inventory=inventory
		).aggregate(total=Sum(F('quantity'))
		)['total'] or 0
	return inventory.quantity - confirmed_quantity


# Import to models from here to avoid ImportError: circular import
class ItemType(models.Model):
	type = models.CharField(max_length=50)
	slug = models.SlugField(unique=True, blank=True)

	def __str__(self):
		return self.type

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.type)

		super().save(*args, **kwargs)

	

