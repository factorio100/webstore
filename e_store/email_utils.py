from django.core.mail import EmailMessage
from django.urls import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

def notify_order_status_email(order):
    # Get the current domain
    current_site = Site.objects.get_current()
    domain = current_site.domain 

    # Build URLs
    if settings.DEBUG == True:
        http_scheme = 'http'
    else:
        http_scheme = 'https'

    order_url = f"{http_scheme}://{domain}" + reverse("e_store:order", args=[order.id])
    store_url = f"{http_scheme}://{domain}"
    order_link = f'<a href="{order_url}">order</a>' # Create an HTML link for "order"    

    # Prepare address details
    address = order.address
    city = order.city
    address_city_postal_code = f"{address} {city}"

    # Build the message based on order status, using the HTML link
    if order.status == 'shipped':
        message = _(f"Your {order_link} from <a href='{store_url}'>{store_url}</a> has been shipped to {address_city_postal_code}.")
    elif order.status == 'delivered':
        message = _(f"Your {order_link} from <a href='{store_url}'>{store_url}</a> has been delivered to {address_city_postal_code}.")
    elif order.status == 'canceled':
        message = _(f"Your {order_link} from <a href='{store_url}'>{store_url}</a> has been canceled.")
    else:
        return

    email = order.email

    # Create an EmailMessage and set the content_subtype to "html"
    email_message = EmailMessage(
        subject='Order Status Update',
        body=message,
        to=[email]
    )
    email_message.content_subtype = "html"  # This ensures the email is rendered as HTML

    return email_message.send()

def send_order_confirmation_email(order): 
    # Render email template
    html_message = render_to_string("email_messages/order_confirmation_message.html", {"order": order})
    message = strip_tags(html_message)  # Remove HTML for plain text version

    email_message = EmailMessage(
        subject=f"Order Confirmation - #{order.id}", 
        body=message, 
        to=[order.email]
    )
    email_message.send()


