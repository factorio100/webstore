from django.conf import settings
from django.utils.translation import get_language
from .views import cart_get_create
from django.db.models import Sum, F

def global_context(request):
	"""Send context to all views."""
	cart = cart_get_create(request)

	return {
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
		'cart_item_count': cart.cartitem_set.aggregate(
			cart_item_count=Sum(F('quantity'))
		)['cart_item_count'] or 0,
	}	