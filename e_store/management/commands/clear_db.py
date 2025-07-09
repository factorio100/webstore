from django.core.management.base import BaseCommand
from e_store.models import Cart, CartItem
from datetime import timedelta

class Command(BaseCommand):

	def handle(self, *args, **kwargs):
		"""Delete carts after 30 days (session duration)."""
		Cart.objects.filter(created_at__gte=timedelta(days=30)).delete()
		
		
		

