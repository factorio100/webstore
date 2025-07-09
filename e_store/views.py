from django.shortcuts import render, redirect, get_object_or_404
from .models import Item, CartItem, Cart, Inventory, Order, OrderItem, BlackListedPhone, Display, Shipping
from .forms import AddToCartForm, OrderInformationsForm, CartItemForm
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponseForbidden, Http404
from django.utils.translation import gettext as _, get_language
from django.conf import settings
from django.urls import reverse
from django.db.models import Q, F, Sum
from .utils import available_inventory

def get_user_ip(request):
    # Check for IP address in the 'X-Forwarded-For' header (used when behind a proxy)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP if there are multiples
        ip = x_forwarded_for.split(',')[0]
    else:
        # Or get the direct IP address
        ip = request.META.get('REMOTE_ADDR')
    return ip

def cart_get_create(request):
	cart_id = request.session.get('session_cart_id')
	cart, created = Cart.objects.get_or_create(id=cart_id)
	
	if created: # store new cart id in session
		request.session['session_cart_id'] = cart.id 
	
	elif cart_id and created: # delete session storing card id if cart instance no longer exists 
		del request.session['session_cart_id']
		request.session['session_cart_id'] = cart.id				

	return cart

def check_order_owner(request, order_id):
	""" Allow access only to the owner of the order"""
	try:
		cart_id = request.session.get('session_cart_id')
		cart = Cart.objects.get(id=cart_id)
	except Cart.DoesNotExist:
		messages.error(request, _("There has been a problem"))
		return redirect("e_store:cart")
 	
	order = get_object_or_404(Order, id=order_id, cart=cart)

	return order

def check_pending_order(order):
	if order.status != "pending":
		raise Http404

def home(request):
	#display_t_shirt = Display.objects.filter(type="t_shirt").first()
	#display_pant = Display.objects.filter(type="pant").first()
	displays = Display.objects.all()
	displays_urls = []
	for display in displays:
		url = reverse(f"e_store:{display.type}s")
		displays_urls.append((display, url))

	context = {
		'displays_urls': displays_urls,
		#'display_t_shirt': display_t_shirt, 
		#'display_pant': display_pant,
		'title': 'home',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, 'e_store/home.html', context)

def t_shirts(request):
	t_shirts = Item.objects.filter(type='t_shirt')
	context = {
		't_shirts': t_shirts,
		'title': 'T shirts',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, 'e_store/t_shirts.html', context)

def pants(request):
	pants = Item.objects.filter(type='pant')
	context = {
		'pants': pants,
		'title': 'Pants',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, 'e_store/pants.html', context)

def item(request, item_id):
	item = get_object_or_404(Item, id=item_id)
	cart = cart_get_create(request)

	selected_size = None
	cart_item = None
	increase_button_disabled = None
	decrease_button_disabled = None

	if request.method == 'POST':
		# Display quantity in cart message when pressing size button  
		selected_size = request.POST.get('size')
		inventory = Inventory.objects.filter(size=selected_size, type=item.type).first()
		cart_item = CartItem.objects.filter(item=item, inventory=inventory, cart=cart).first() 

		# Handle + - buttons
		quantity_raw = request.POST.get('quantity')
		try:
			quantity = int(quantity_raw)
		except (ValueError, TypeError):
			quantity = None
		
		if request.POST.get('adjust_quantity') == 'increase':
			#if inventory:
				# + button wont increase quantity when cart item quantity reaches available inventory 
			#	if cart_item and quantity + cart_item.quantity == available_inventory(inventory):
			#		pass

			#	else:
					# Set quantity max_value to available inventory
					quantity = min(quantity + 1, available_inventory(inventory))

			# Set quantity max_value to 1 if no size is selected
			#else:
			#	quantity = 1

		elif request.POST.get('adjust_quantity') == 'decrease':
			quantity = max(quantity - 1, 1) 

		# Set quantity max_value to 1 when selected size change  
		session_selected_size = request.session.get('selected_size')    
		if selected_size != session_selected_size:  # Compare current selected size with the previous session
			quantity = 1
		request.session['selected_size'] = request.POST.get('size')  # Selected size session update

		form = AddToCartForm(
			data={**request.POST.dict(), 'quantity': quantity},  
			item=item,
			selected_size=selected_size,
			cart=cart
		)		

		# Disable + - buttons
		if 'add_to_cart' not in request.POST: 
			if form.is_valid():
				quantity = form.cleaned_data['quantity']
				
				if ( 
					cart_item and ( 
						quantity + cart_item.quantity == available_inventory(inventory) 
					) or (
						quantity == available_inventory(inventory)
					)
				
				):
					increase_button_disabled = True  
					form.add_error('quantity', "Max quantity.")

				if quantity == 1:
					decrease_button_disabled = True

			else:
				# When cartitem quantity is increased from cart page, 
				# display addtocart form error and disable + button  
				increase_button_disabled = True  

		if 'add_to_cart' in request.POST: 
			if form.is_valid():
				size = form.cleaned_data['size']
				quantity = form.cleaned_data['quantity']
				try:
					inventory = Inventory.objects.get(type=item.type, size=size)
					cart_item, created = CartItem.objects.get_or_create(
						item=item,
						item_name=item.name,
						inventory=inventory,
						cart=cart,
					)
					if created:
						cart_item.quantity = quantity
					else: 
						cart_item.quantity += quantity

					cart_item.save()

					messages.success(request, _("Item added to cart."))
					return redirect('e_store:item', item.id)

				except Inventory.DoesNotExist:
					messages.error(request, _("This item is out of stock."))
			else:
				print(f"invalid form, {quantity}")
	else:	
		form = AddToCartForm(item=item, selected_size=selected_size, cart=cart)

	inventories = Inventory.objects.filter(type=item.type)

	context = {
		'item': item,
		'form': form,
		'sizes_with_status': form.sizes_with_status,
		'in_stock': inventories.filter(quantity__gt=0).exists(),
		'cart_item': cart_item,
		'increase_button_disabled': increase_button_disabled,
		'decrease_button_disabled': decrease_button_disabled,
		'selected_size': selected_size,
		'items_url': reverse(f"e_store:{item.type}s"),
		'title': 'Item',
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}

	return render(request, 'e_store/item.html', context)

def cart(request):     
	# cart is created for the first time when: visiting item page or cart page
	cart = cart_get_create(request)

	# Check if customer has a pending order and display a message instead of add to cart button
	cart_id = request.session.get('session_cart_id')
	cart = Cart.objects.filter(id=cart_id).first()  
	pending_order = Order.objects.filter(cart=cart, status="pending").first()

	cart_items = cart.cartitem_set.all()

	forms = []

	error_form = None

	if request.method == 'POST':  
		cart_item_id = request.POST.get('cart_item_id')
		adjust_quantity = request.POST.get('adjust_quantity')
		delete_cart_item = request.POST.get('delete_cart_item')
		
		try:
			cart_item = CartItem.objects.get(id=cart_item_id)
			if adjust_quantity: 
				# + - buttons
				quantity = cart_item.quantity
				max_available = available_inventory(cart_item.inventory)

				if adjust_quantity == 'increase':
					new_quantity = min(quantity + 1, max_available)	
					form = CartItemForm({'quantity': new_quantity}, instance=cart_item)
					if form.is_valid():
						form.save()

						if new_quantity == max_available:
							form.add_error('quantity', "Max quantity.")
							error_form = form

				elif adjust_quantity == 'decrease':
					new_quantity = max(quantity - 1, 1)
					form = CartItemForm({'quantity': new_quantity}, instance=cart_item)
					if form.is_valid():
						form.save()

			elif delete_cart_item:
				# Remove button
				cart_item.delete()
				# Check for pending order and cancel it if the cart is empty
				if not cart_items and pending_order:
					pending_order.status = "canceled"
					pending_order.save()
					messages.success(request, _("Order canceled successfully."))
				return redirect("e_store:cart")

		except CartItem.DoesNotExist:
			messages.error(request, "Could not find the item.")
		
	# Add the updated form instance: cart_item.id to the forms list in order to display field errors      
	for cart_item in cart_items:
		if error_form and error_form.instance.id == cart_item.id:
			forms.append((error_form, cart_item, available_inventory(cart_item.inventory)))
		else:
			forms.append((CartItemForm(instance=cart_item), cart_item, available_inventory(cart_item.inventory)))  
	
	context = { 
		'forms': forms,
		'cart': cart,  # for total price and "cart is empty" message
		'pending_order': pending_order,
		'unavailable_inventory_item': cart_items.filter(
			Q(quantity__gt=F('inventory__quantity')) | Q(inventory__isnull=True) | Q(item__isnull=True)
		),
		'title': 'Cart',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}

	return render(request, 'e_store/cart.html', context) 

def order_informations(request):
	cart = cart_get_create(request)
	
	# Block access to the page if cart is empty, or if there is a pending order 
	if cart.is_empty() or Order.objects.filter(cart=cart, status="pending").exists():
		raise Http404

	# Limit orders by IP
	"""
	user_ip = get_user_ip(request)
	time_limit = timezone.now() - timedelta(hours=24)
	order_count = Order.objects.filter(ip_address=user_ip, created_at__gte=time_limit).count()

	if order_count >= 2:
		return HttpResponseForbidden(_("Too many orders. Try again later."))
	"""
	
	try:
		# Prefill the form
		latest_order = Order.objects.filter(cart=cart).latest('created_at')
		initial_data = {
				'last_name': latest_order.last_name,
				'first_name': latest_order.first_name,
				'email': latest_order.email,
				'phone_number': latest_order.phone_number,
				'address': latest_order.address,
				'city': latest_order.city,
				'postal_code': latest_order.postal_code 
			}
				
	except Order.DoesNotExist:
		initial_data = None		
	
	if request.method == 'POST':
		if initial_data:
			form = OrderInformationsForm(cart, initial=initial_data, data=request.POST)		
		else:
			form = OrderInformationsForm(cart, data=request.POST)		
	
		if form.is_valid():  # This also call model.full_clean()
			order = form.save(commit=False)
			order.cart = cart
			order.status = "pending"
			order.total_price = cart.total_price()
			order.save()
				
			return redirect("e_store:order", order.id)
	
	else:
		if initial_data:		
			form = OrderInformationsForm(cart, initial=initial_data)		
		else:
			form = OrderInformationsForm(cart)

	context = {
		'form': form,
		'title': 'Shipping infos',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, 'e_store/order_informations.html', context)

def edit_order_informations(request, order_id):
	order = check_order_owner(request, order_id)
	check_pending_order(order)
	if request.method == 'POST':
		form = OrderInformationsForm(cart, instance=order, data=request.POST)
		if form.is_valid():
			form.save()
			return redirect("e_store:order", order.id)
	else:
		form = OrderInformationsForm(cart, instance=order)

	context = {
		'form': form,
		'title': 'Edit shipping',
	}

	return render(request, "e_store/edit_order_informations.html")


def order(request, order_id):
	order = check_order_owner(request, order_id)
	
	# Customer can cancel pending and confirmed orders
	if request.method == 'POST':
		confirm_order = request.POST.get("confirm_order")

		# Confirm order button
		if confirm_order:
			# Check if stock in item are available 
			cart_items = order.cart.cartitem_set.all()
			for cart_item in cart_items:
				if cart_item.quantity > available_inventory(cart_item.inventory) or cart_item.inventory is None: 
					messages.error(request, _("One or more items in your cart are out of stock. Please review your cart."))
					return redirect(request, "e_store:cart")

				elif cart_item.item is None:
					messages.error(request, _("One or more items are no longer available, Please review your cart."))
					return redirect(request, "e_store:cart")

			# Create order items
			if order.status == "pending" and not order.orderitem_set.exists():
				OrderItem.objects.create(
					item=cart_item.item,
					item_name=cart_item.item.name,
					inventory=cart_item.inventory,
					quantity=cart_item.quantity,
					total_price=cart_item.total_price(),
					order=order
				)

			# Change order status from pending to confirmed
			order.status = "confirmed"
			order.save()

			# Create shipping instance when order is confirmed
			Shipping.objects.create(order=order)

			# Clear cart after order is confirmed
			cart_items.delete()

			request.session['success'] = True
			
			return redirect('e_store:order_success', order_id=order.id)

		# Cancel order button
		else:
			try:
				order = Order.objects.get(id=order_id)
				if order.status not in ['pending', 'confirmed']:
					messages.error(request, _("You cannot cancel this order."))

				else:
					if order.status == 'pending':
						# Delete cart items if order is "pending"
						cart_items = order.cart.cartitem_set.all().delete()
					
					order.status = 'canceled'
					order.save()

					# Delete shipping instance when order is canceled
					Shipping.objects.filter(order=order).delete()

					messages.success(request, _("Order canceled successfully."))
					
				return redirect('e_store:order', order_id=order.id)
			
			except Order.DoesNotExist:
				pass  

	context = {
		'order': order,
		'title': 'Order',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, "e_store/order.html", context)

def order_success(request, order_id):
	if not request.session.get('success'):
		raise Http404

	order = check_order_owner(request, order_id)
	order = Order.objects.get(id=order_id)
	del request.session['success']
	
	context = {
		'order': order,
		'title': 'Order success message',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, "e_store/order_success.html", context)

def order_history(request):
	cart = cart_get_create(request)
	orders = Order.objects.filter(cart=cart)	
	context = {
		'orders': orders,
		'title': 'Order history',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, "e_store/order_history.html", context)

