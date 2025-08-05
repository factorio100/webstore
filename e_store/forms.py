from django import forms
from .models import Inventory, CartItem, Order, BlackListedPhone, OrderItem, Size
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F, Sum
from .utils import available_inventory, ItemType

class AddToCartForm(forms.Form):
	size = forms.ChoiceField(
		widget=forms.RadioSelect, 
		error_messages={'required': _("Please select a size.")}
	)
	quantity = forms.IntegerField(
		initial=1,
		min_value=1,   
		widget=forms.NumberInput(attrs={"class": "form-control text-center quantity-input"}),
		error_messages={
			'required': _("Please enter a quantity."),  # When field is empty: quantity None
			'invalid': _("Please enter a valid whole number."),
			'min_value': _("You must add at least one item.")
		},
	)

	def __init__(self, item, selected_size, cart, *args,  **kwargs):
		super().__init__(*args, **kwargs)
		self.item = item
		self.selected_size = selected_size
		self.cart = cart
		self.item_type = ItemType.objects.get(type=item.type)
		self.size = Size.objects.filter(name=selected_size).first()

		inventories = Inventory.objects.filter(type=self.item_type)
		
		sizes_quantities = {inv.size: inv.quantity for inv in inventories}

		self._sizes_quantities = [(size, size, quantity) for size, quantity in sizes_quantities.items()]  # items() turn dictionary {size: quant} into tuple (size, quant)  	

		# Only available sizes are inclued in size field choices, 
		# the frontend uses sizes_with_status() include all the sizes: unavailable sizes are crossed/greyed 
		choices = [(size, size) for size, size, quantity in self._sizes_quantities if quantity > 0]

		self.fields['size'].choices = choices
        
		# Set max_value to available inventory 
		inventory = Inventory.objects.filter(type=self.item_type, size=self.size).first()
		if inventory:
			cart_item = CartItem.objects.filter(item=item, inventory=inventory, cart=cart).first()
			if cart_item:  
				max_quantity = available_inventory(inventory) - cart_item.quantity
				
			else:
				max_quantity = available_inventory(inventory)

		else: 
			max_quantity = 1
		
		# Prevent manually entering: quantity > inventory, or quantity < 0,
		# this doesn't set constraints on - + buttons
		self.fields['quantity'].widget.attrs.update({
			'class': 'form-control text-center',
			'max': max_quantity,
			'oninput': 'if (this.value < 0) this.value = 0; this.value = Math.min(this.value, this.max)',
		})

	@property
	def sizes_quantities(self):
		"""Passed to the template via view context."""
		return self._sizes_quantities

	def clean(self):
		cleaned_data = super().clean()
		size = self.cleaned_data.get('size')
		quantity = self.cleaned_data.get('quantity')

		inventory = Inventory.objects.filter(type=self.item_type, size=self.size).first()
		if not inventory:  # Prevent AttributeError: 'NoneType' object has no attribute 'quantity', + button runs: quantity > inventory.quantity 
			return cleaned_data

		cart_item = CartItem.objects.filter(item=self.item, inventory=inventory, cart=self.cart).first()

		# Prevent exceeding available inventory if cart item exists
		if quantity and cart_item:  # Prevent AttributeError
			if quantity + cart_item.quantity > available_inventory(inventory):
				# Add error message to quantity field
				self.add_error('quantity', _("Available stock already in the cart."))	
			
			elif quantity < 1:
				self.add_error('quantity', _('Quantity must at least be 1.'))
		
		else:
			if quantity > available_inventory(inventory):
				self.add_error('quantity', _("Stock unavailable, select a lower amount."))
				
			elif quantity < 1:
				self.add_error('quantity', _('Quantity must at least be 1.'))
		
		return cleaned_data


class CartItemForm(forms.ModelForm):
	quantity = forms.IntegerField(
		min_value=0,
		initial=1,
		widget=forms.NumberInput(attrs={"class": "form-control text-center quantity-input"}),
		error_messages={
			'required': _("Please enter a quantity."),
			'invalid': _("Please enter a valid whole number."),
			'min_value': _("You must add at least one item.")
		},
	)

	class Meta:
		model = CartItem
		fields = ['quantity']
	
	def __init__(self, *args,  **kwargs):
		super().__init__(*args, **kwargs)

		try:
			# Set max_value to available inventory 
			max_quantity = available_inventory(self.instance.inventory)  # self.instance to access cartitem model
		except AttributeError:
			max_quantity = 1
			
		# Prevent manually entering: quantity > inventory, or quantity < 1,
		# this doesn't set constraints on - + buttons
		self.fields['quantity'].widget.attrs.update({
			'class': 'form-control text-center',
			'max': max_quantity,
			'oninput': 'if (this.value < 0) this.value = 0; this.value = Math.min(this.value, this.max)',
			'onchange': 'this.form.submit()'
		})

	def clean_quantity(self):
		quantity = self.cleaned_data.get('quantity')

		if not self.instance.inventory:
			raise forms.ValidationError(_("Inventory not found for this item."))   	                                                                                                  

		if quantity > available_inventory(self.instance.inventory):
			raise forms.ValidationError(_("Stock unavailable, select a lower amount."))
			
		elif quantity < 1:
			self.add_error('quantity', _('Quantity must at least be 1.'))

		return quantity

 

class OrderForm(forms.ModelForm):	
	class Meta:
		model = Order
		fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'city', 'postal_code']

	def __init__(self, cart, *args, **kwargs):
		# Pass cart as parameter instead of using self.instance.cart,
		# because it wont work when creating a new order instance
		self.cart = cart  
		super().__init__(*args, **kwargs)
		# Applying bootstrap
		for field_name, field in self.fields.items():
			field.widget.attrs['class'] = 'form-control'

	def clean_phone_number(self):
		phone_number = self.cleaned_data.get('phone_number')
		
		if BlackListedPhone.objects.filter(phone_number=phone_number).exists():
			raise ValidationError(_("This phone number has been blacklisted due to repeated order cancellations"))

		return phone_number

	def clean(self):
		cleaned_data = super().clean()
				
		# Prevent creating new order if a pending order exists
		if not self.instance.id:
			if Order.objects.filter(cart=self.cart, status="pending").exists():
				raise ValidationError(
					_(f"You have a pending order, confirm or cancel it before creating a new order."
				))
			
		# Check if inventory and item are available when creating or editing order
		cart_items = self.cart.cartitem_set.all()
		for cart_item in cart_items:
			if cart_item.quantity > available_inventory(cart_item.inventory) or cart_item.inventory is None: 
				raise ValidationError(_("One or more items in your cart are out of stock. Please review your cart."))

			elif cart_item.item is None:
				raise ValidationError(_("One or more items are no longer available, Please review your cart."))

		return cleaned_data

