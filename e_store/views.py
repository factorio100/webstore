from django.shortcuts import render, redirect, get_object_or_404
from .models import Item, CartItem, Cart, Inventory, Order, OrderItem, BlackListedPhone, Display, Shipping, Size, ItemType
from .forms import AddToCartForm, OrderForm, CartItemForm
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
	displays = Display.objects.all()
	displays_urls = []
	for display in displays:
		url = reverse('e_store:items', args=[display.type.slug])
		displays_urls.append((display, url))
	
	context = {
		'displays_urls': displays_urls,
		'title': 'home',
		# Fix 'English' in the dropdown menu being translated
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	
	return render(request, 'e_store/home.html', context)

def items(request, item_type_slug):
	item_type = get_object_or_404(ItemType, slug=item_type_slug)
	items = Item.objects.filter(type=item_type)

	# Sort items for GET request
	session_sort = request.session.get('session_sort')
	if session_sort:
		items = items.order_by(session_sort)

	# Sort items for POST request
	if request.method == 'POST':
		sort = request.POST.get('sort')
		items = items.order_by(sort) 
		request.session['session_sort'] = sort
		session_sort = request.session.get('session_sort')
		print(f"sort: {sort}")

	print(f"session: {session_sort}")
	
	context = {
		'items': items,
		'title': item_type,
		'fields': [('name', 'name'), ('price', 'price (lowest)'), ('-price', 'price (highest)')],
		'session_sort': session_sort,
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	
	return render(request, 'e_store/items.html', context)


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
		# Use filter() to avoid handling missing objects
		item_type = ItemType.objects.filter(type=item.type).first()
		size = Size.objects.filter(name=selected_size).first()
		inventory = Inventory.objects.filter(size=size, type=item_type).first()
		cart_item = CartItem.objects.filter(item=item, inventory=inventory, cart=cart).first() 

		# Handle + - buttons
		quantity_raw = request.POST.get('quantity')
		try:
			quantity = int(quantity_raw)
		except (ValueError, TypeError):
			quantity = None
		
		if request.POST.get('adjust_quantity') == 'increase':
			quantity = min(quantity + 1, available_inventory(inventory))

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
					size = Size.objects.get(name=selected_size)
				except Size.DoesNotExist:
					messages.error(request, _("The selected size is unavailable for now, please select another size."))
				
				try:
					inventory = Inventory.objects.get(type=item_type, size=size)
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
		form = AddToCartForm(item=item, selected_size=selected_size, cart=cart)
		size_choices = form.fields['size'].choices

	inventories = Inventory.objects.filter(type=item.type)

	context = {
		'item': item,
		'form': form,
		'sizes_quantities': form.sizes_quantities,
		'in_stock': inventories.filter(quantity__gt=0).exists(),
		'cart_item': cart_item,
		'increase_button_disabled': increase_button_disabled,
		'decrease_button_disabled': decrease_button_disabled,
		'selected_size': selected_size,
		'items_url': reverse('e_store:items', args=[item.type.slug]),
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
		# Quantity change
		adjust_quantity = request.POST.get('adjust_quantity')  # Change from - + buttons
		manual_quantity_update = request.POST.get('quantity')  # Onchange form submission
		
		delete_cart_item = request.POST.get('delete_cart_item')
		
		try:
			cart_item = CartItem.objects.get(id=cart_item_id)
			max_available = available_inventory(cart_item.inventory)
			
			if adjust_quantity: 
				# + - buttons
				quantity = cart_item.quantity
				if adjust_quantity == 'increase':
					new_quantity = min(quantity + 1, max_available)	

				elif adjust_quantity == 'decrease':
					new_quantity = max(quantity - 1, 1)

			elif manual_quantity_update:
				new_quantity = manual_quantity_update

			form = CartItemForm({'quantity': new_quantity}, instance=cart_item)
			if form.is_valid():
				form.save()
				new_quantity = form.cleaned_data['quantity']
				if new_quantity == max_available:
					form.add_error('quantity', "Max quantity.")
					error_form = form

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
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}

	return render(request, 'e_store/cart.html', context) 

def create_order(request):
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
			form = OrderForm(cart, initial=initial_data, data=request.POST)		
		else:
			form = OrderForm(cart, data=request.POST)		
	
		if form.is_valid():  # This also call model.full_clean()
			order = form.save(commit=False)
			order.cart = cart
			order.status = "pending"
			order.total_price = cart.total_price()
			order.save()
				
			return redirect("e_store:order", order.id)
	
	else:
		if initial_data:		
			form = OrderForm(cart, initial=initial_data)		
		else:
			form = OrderForm(cart)

	context = {
		'form': form,
		'title': 'Shipping infos',
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, 'e_store/create_order.html', context)

def edit_order_shipping(request, order_id):
	order = check_order_owner(request, order_id)
	check_pending_order(order)
	cart_id = request.session.get('session_cart_id')
	try:
		cart = Cart.objects.get(id=cart_id)
	except Cart.DoesNotExist:
		messages.error("There has been a problem.")
		return redirect('e_store:cart')

	if request.method == 'POST':
		form = OrderForm(cart, instance=order, data=request.POST)
		if form.is_valid():
			form.save()
			return redirect("e_store:order", order.id)
	else:
		form = OrderForm(cart, instance=order)

	context = {
		'form': form,
		'title': 'Edit shipping',
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language()
	}

	return render(request, "e_store/edit_order_shipping.html", context)


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
		'LANGUAGES': settings.LANGUAGES,
		'LANGUAGE_CODE': get_language(),
	}
	return render(request, "e_store/order_history.html", context)

