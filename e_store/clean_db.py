from django.utils.timezone import now
from datetime import timedelta

def clean_old_guest_data():
    expiration_date = now() - timedelta(days=30)

    # Delete carts with no linked orders
    old_carts = Cart.objects.filter(created_at__lt=expiration_date, order__isnull=True)
    old_carts.delete()

    # Delete guest users who have no valid orders
    GuestUser.objects.filter(cart__isnull=True).delete()
