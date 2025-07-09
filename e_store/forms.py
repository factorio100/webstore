from django import forms
from .models import Inventory, CartItem, Order, BlackListedPhone, OrderItem
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, F, Sum
from .utils import available_inventory

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

		inventories = Inventory.objects.filter(type=item.type)
		size_quantities = {inv.size: inv.quantity for inv in inventories}
		self._sizes_with_status = [(size, size, qty > 0) for size, qty in size_quantities.items()]  # items turn dictionary {size: quant} into tuple (size, quant)

		# Only include available sizes in form choices for the backend, 
		# the template will use sizes_with_status() to shows all the sizes: unavailable sizes are crossed/greyed 
		choices = [(size, label) for size, label, available in self._sizes_with_status if available]
		self.fields['size'].choices = choices

		inventory = Inventory.objects.filter(type=item.type, size=selected_size).first()
		# Set max_value to available inventory 
		if inventory:
			cart_item = CartItem.objects.filter(item=item, inventory=inventory, cart=cart).first()
			if cart_item:  
				max_quantity = available_inventory(inventory) - cart_item.quantity
				
			else:
				max_quantity = available_inventory(inventory)

		else: 
			max_quantity = 1
		# Prevent manually entering values: quantity > inventory and quantiy < 0,
		# this doesn't set constraints on - + buttons
		self.fields['quantity'].widget.attrs.update({
			'class': 'form-control text-center',
			'max': max_quantity,
			'oninput': 'if (this.value < 0) this.value = 0; this.value = Math.min(this.value, this.max)',
		})

	@property
	def sizes_with_status(self):
		return self._sizes_with_status

	def clean(self):
		cleaned_data = super().clean()
		size = self.cleaned_data.get('size')
		quantity = self.cleaned_data.get('quantity')

		inventory = Inventory.objects.filter(type=self.item.type, size=size).first()
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
			
		# Prevent manually entering values: quantity > inventory or quantiy < 1,
		# this doesn't set constraints on - + buttons
		self.fields['quantity'].widget.attrs.update({
			'class': 'form-control text-center',
			'max': max_quantity,
			'oninput': 'if (this.value < 1) this.value = 0; this.value = Math.min(this.value, this.max)',
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

 

class OrderInformationsForm(forms.ModelForm):	
	class Meta:
		model = Order
		fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'city', 'postal_code']

	def __init__(self, cart, *args, **kwargs):
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

