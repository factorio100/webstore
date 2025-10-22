from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import CheckConstraint, Q, Sum, F, UniqueConstraint
from django.utils.formats import number_format
from .email_utils import notify_order_status_email, send_order_confirmation_email
from phonenumber_field.modelfields import PhoneNumberField
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField
from django.conf import settings
from .utils import available_inventory, ItemType


# Allow letters (including accents), spaces, hyphens, apostrophes
name_validator = RegexValidator(
    regex=r"^[A-Za-zÀ-ÖØ-öø-ÿ '-]+$",
    message="Enter a valid name. Only letters, spaces, hyphens, and apostrophes are allowed."
)


class Size(models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name


class Inventory(models.Model):
	type = models.ForeignKey(ItemType, on_delete=models.CASCADE)
	size = models.ForeignKey(Size, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=0)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['type', 'size'], name='unique_type_size'),  # Prevent duplicate records
		]  
		verbose_name_plural = 'inventories'

	def __str__(self):
		return f"{self.type} - {self.size}: {self.quantity} in stock"
	
	def save(self, *args, **kwargs):
		"""Updating cart items max quantities when the inventory decreases."""  
		inventory = Inventory.objects.filter(id=self.id).first()
		if inventory:
			# Check if stock decreases
			if self.quantity < inventory.quantity:  # New quantity < old quantity
				cart_items = CartItem.objects.filter(inventory=inventory, quantity=inventory.quantity) 
				# Prevent setting cart items quantities to 0 
				if self.quantity > 0:					
					cart_items.update(quantity=self.quantity)

				# Keep cart item quantity to 1 when inventory is 0, 
				# in the templates the cart item will be disabled until the inventory is available again 
				elif self.quantity == 0:
					cart_items.update(quantity=1)

		super().save(*args, **kwargs)


class Cart(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def total_price(self):
		return self.cartitem_set.aggregate(
			total_price=Sum(F('quantity') * F('item__price'))
		)['total_price'] or 0 

	def is_empty(self):
	    return self.total_price() == 0
	

class Order(models.Model):
	STATUS_CHOICES = [
    	("pending", _("Pending")),  
    	("confirmed", _("Confirmed")),  
    	("printing", _("Printing")),  
    	("shipped", _("Shipped")),  
    	("delivered", _("Delivered")),  
    	("cancelled", _("Cancelled")),  
    	("delivery refused", _("Delivery")),
	]
	STATUS_FLOW = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["printing", "cancelled"],
        "printing": ["shipped"],
        "shipped": ["delivered", "delivery refused"],
        "delivered": ["delivered"],
        "cancelled": ["cancelled"],
        "delivery refused": ["delivery refused"],
    }
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE)  
	created_at = models.DateTimeField(auto_now_add=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES) 
	# Shipping infos
	last_name = models.CharField(_("Last_name"), max_length=50, validators=[name_validator])
	first_name = models.CharField(_("First name"), max_length=50, validators=[name_validator])
	email = models.EmailField(_("Email"), max_length=50)
	phone_number = PhoneNumberField(_("Phone number"), region="DZ")  # Validates Algerian numbers
	address = models.CharField(_("Address"), max_length=200, validators=[MinLengthValidator(5)])
	CITIES_CHOICES = [
	    ("Adrar", "Adrar"),
	    ("Chlef", "Chlef"),
	    ("Laghouat", "Laghouat"),
	    ("Oum El Bouaghi", "Oum El Bouaghi"),
	    ("Batna", "Batna"),
	    ("Béjaïa", "Béjaïa"),
	    ("Biskra", "Biskra"),
	    ("Béchar", "Béchar"),
	    ("Blida", "Blida"),
	    ("Bouira", "Bouira"),
	    ("Tamanrasset", "Tamanrasset"),
	    ("Tébessa", "Tébessa"),
	    ("Tlemcen", "Tlemcen"),
	    ("Tiaret", "Tiaret"),
	    ("Tizi Ouzou", "Tizi Ouzou"),
	    ("Algers", "Algers"),
	    ("Djelfa", "Djelfa"),
	    ("Jijel", "Jijel"),
	    ("Sétif", "Sétif"),
	    ("Saïda", "Saïda"),
	    ("Skikda", "Skikda"),
	    ("Sidi Bel Abbès", "Sidi Bel Abbès"),
	    ("Annaba", "Annaba"),
	    ("Guelma", "Guelma"),
	    ("Constantine", "Constantine"),
	    ("Médéa", "Médéa"),
	    ("Mostaganem", "Mostaganem"),
	    ("M'Sila", "M'Sila"),
	    ("Mascara", "Mascara"),
	    ("Ouargla", "Ouargla"),
	    ("Oran", "Oran"),
	    ("El Bayadh", "El Bayadh"),
	    ("Illizi", "Illizi"),
	    ("Bordj Bou Arréridj", "Bordj Bou Arréridj"),
	    ("Boumerdès", "Boumerdès"),
	    ("El Tarf", "El Tarf"),
	    ("Tindouf", "Tindouf"),
	    ("Tissemsilt", "Tissemsilt"),
	    ("El Oued", "El Oued"),
	    ("Khenchela", "Khenchela"),
	    ("Souk Ahras", "Souk Ahras"),
	    ("Tipaza", "Tipaza"),
	    ("Mila", "Mila"),
	    ("Aïn Defla", "Aïn Defla"),
	    ("Naâma", "Naâma"),
	    ("Aïn Témouchent", "Aïn Témouchent"),
	    ("Ghardaïa", "Ghardaïa"),
	    ("Relizane", "Relizane"),
	    ("Timimoun", "Timimoun"),
	    ("Bordj Badji Mokhtar", "Bordj Badji Mokhtar"),
	    ("Ouled Djellal", "Ouled Djellal"),
	    ("Béni Abbès", "Béni Abbès"),
	    ("In Salah", "In Salah"),
	    ("In Guezzam", "In Guezzam"),
	    ("Touggourt", "Touggourt"),
	    ("Djanet", "Djanet"),
	    ("El M'Ghair", "El M'Ghair"),
	    ("El Menia", "El Menia"),
	]
	city = models.CharField(_("City"), max_length=50, choices=CITIES_CHOICES)
	# For spam
	ip_address = models.GenericIPAddressField(null=True, blank=True)  

	def total_price(self):
		return self.orderitem_set.aggregate(
				total_price=Sum(F('total_price'))
			)['total_price'] or 0 

	def decrease_inventory(self, order_item):
		try:
			inventory = Inventory.objects.get(type=order_item.inventory.type, size=order_item.inventory.size)
			print(_(f"Before: {inventory.type} - {inventory.size} has {inventory.quantity}"))

			if inventory.quantity >= order_item.quantity:
				inventory.quantity -= order_item.quantity
				inventory.save()
				print(_(f"After: {inventory.type} - {inventory.size} now has {inventory.quantity}"))

			else:
				raise ValueError(_(f"Not enough stock for {order_item.type} - {order_item.size}"))

		except Inventory.DoesNotExist:
			raise ValueError(f"No inventory found for {order_item.type} - {order_item.size}")

	def clean(self):
		# Check if phone number is blacklisted
		if BlackListedPhone.objects.filter(phone_number=self.phone_number).exists():
			raise ValidationError(_("This phone number has been blacklisted due to repeated order cancellations"))

		# Check if inventory and item are available before confirming order
		if self.status == "confirmed":
			cart_items = self.cart.cartitem_set.all()
			for cart_item in cart_items:
				if cart_item.quantity > available_inventory(cart_item.inventory) or cart_item.inventory is None: 
					raise ValidationError(_(f"{cart_item.item.name} size {cart_item.inventory.size} is out of stock."))

				elif cart_item.item is None:
					raise ValidationError(_(f"{cart_item.item_name} is no longer available."))

		# Check if inventory and item are available before printing order
		elif self.status == "printing":	
			if self.orderitem_set.filter(Q(quantity__gt=F('inventory__quantity')) | Q(inventory__isnull=True)):
				raise ValidationError(_(f"{order_item.item.name} size {order_item.inventory.size} is out of stock."))
				
			elif self.orderitem_set.filter(item__isnull=True):
				raise ValidationError(_(f"{order_item.item_name} is no longer available."))

	def check_pending_order(self):
		"""
		Use validations that involve cart outside clean(),
		or else self.cart will be called before cart field is set.
		"""
		if not self.id:
			if Order.objects.filter(cart=self.cart, status="pending").exists():
				raise ValidationError(
					_(f"You have a pending order, confirm or cancel it before creating a new order.")
				)

			# Check if inventory and item are available for new instance
			cart_items = self.cart.cartitem_set.all()
			for cart_item in cart_items:
				if cart_item.quantity > available_inventory(cart_item.inventory) or cart_item.inventory is None: 
					raise ValidationError(_(f"{cart_item.item.name} size {cart_item.inventory.size} is out of stock."))

				elif cart_item.item is None:
					raise ValidationError(_(f"{cart_item.item_name} is no longer available."))

	def save(self, *args, **kwargs):		
		if self.id:  # Ensure the order already exists (not a new instance)
			old_status = Order.objects.get(id=self.id).status  
			# Enforce changing status in the correct order,
            # Using dictionary to enforce correct status order,  
			# Old status value is used (key) to retreive the next allowed status (value): "old status": ["next status"]
			# Prevents applying status flow when editing pending order through views: 
			# call save() if old_status == self.status   
			if old_status != self.status:  # Detect order status change  
				allowed_next_statuses = self.STATUS_FLOW.get(old_status, []) 
				if self.status not in allowed_next_statuses:
					raise ValidationError(
						_(f"Invalid status transition from '{old_status}' to '{self.status}'. Allowed: {allowed_next_statuses}")
					)

			# Decrease inventory when changing order status to "printing":
			if self.status == "printing":	
				for order_item in self.orderitem_set.all():
					self.decrease_inventory(order_item) 

			# Notify customer about order status by email
			#if old_status != self.status:  # Check if order status has changed 
			#	if self.status == "confirmed":
			#		send_order_confirmation_email(order=self)
			#	elif self.status in ["shipped", "delivered", "canceled"]:
			#		notify_order_status_email(order=self)
			#	else:
			#		pass

		self.check_pending_order()
		
		self.full_clean()

		super().save(*args, **kwargs)  # Call the original save method



if settings.DEBUG:
    from .models_local import Item, Display
else:
   from .models_cloudinary import Item, Display

class OrderItem(models.Model):
	"""
	Store cart items permanently after converting them into order items
	"""
	item = models.ForeignKey(Item, null=True, on_delete=models.SET_NULL)
	item_name = models.CharField(max_length=200)
	
	inventory = models.ForeignKey(Inventory, null=True, on_delete=models.SET_NULL)
	quantity = models.PositiveIntegerField()
	total_price = models.DecimalField(max_digits=10, decimal_places=2)  
	order = models.ForeignKey("Order", on_delete=models.CASCADE)

	#def __str__(self):
	#	return f"{self.quantity}x {self.inventory.type} ({self.inventory.size}) in Order {self.order.id}"  


	def inventory_is_available(self):
		""" 
		Display "out of stock" message, 
		order item will be available again when inventory is restocked, 
		"""
		return self.inventory and self.quantity <= self.inventory.quantity

	def save(self, *args, **kwargs):
		self.full_clean()

		super().save(*args, **kwargs)


class CartItem(models.Model):
	item = models.ForeignKey(Item, null=True, on_delete=models.SET_NULL)
	item_name = models.CharField(max_length=200)
	inventory = models.ForeignKey(Inventory, null=True, on_delete=models.SET_NULL)
	quantity = models.PositiveIntegerField(
		default=1, 
		validators=[
			MinValueValidator(1),
		]
	)
	cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
	
	class Meta:
		constraints = [
			CheckConstraint(
				check=Q(quantity__gte=1),
				name="quantity_min"
			),
			models.UniqueConstraint(fields=['cart', 'inventory', 'item'], name='unique_cart_inventory_item'),
		]
	
	def total_price(self):
		if self.item:
			return self.quantity * self.item.price
		return None

	def inventory_is_available(self):
		""" 
		Display "out of stock" message, 
		cart item will be available again when inventory is restocked. 
		"""
		#return self.inventory and self.quantity <= available_inventory(self.inventory)
		return True
	def clean(self):
		if not self.item:
			raise ValidationError("Cart item must be associated with a valid item.")

		if not self.inventory:
			raise ValidationError(_("Inventory not found for this item."))   	                                                                                                  

		if self.quantity > available_inventory(self.inventory):
			raise ValidationError(_("Stock unavailable, select a lower amount."))
			
		if self.quantity < 1:
			raise ValidationError( _('Quantity must at least be 1.'))

	def save(self, *args, **kwargs):
		self.full_clean()

		super().save(*args, **kwargs)


class Shipping(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    tracking_number = models.CharField(max_length=50, blank=True, null=True)
    estimated_delivery = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Shipping for Order {self.order.id}"


class BlackListedPhone(models.Model):
	phone_number = models.CharField(max_length=20, unique=True)
	reason = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.phone_number