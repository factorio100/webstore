from django.contrib import admin
from .models import Item, Inventory, CartItem, Cart, Order, Shipping, OrderItem, BlackListedPhone, Display
from django.utils.html import format_html
from django.db.models import Q, F

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'image_tag')  # Add 'image_tag' to display the image
    readonly_fields = ('image_tag',)  # Makes image preview readonly in the detail view

    def image_tag(self, obj):
        return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        
    image_tag.short_description = 'Image Preview' # name of the field


@admin.register(Display)
class DisplayAdmin(admin.ModelAdmin):
    list_display = ('type', 'image_tag')

    def image_tag(self, obj):
        return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        
    image_tag.short_description = 'Image Preview'

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Prevent admin from selecting a type if it already exists."""
        field = super().formfield_for_choice_field(db_field, request, **kwargs)

        if db_field.name == "type": 
            displays = self.model.objects.all()
            display_types = [display.type for display in displays]
            field.choices = [(value, label) for value, label in field.choices if value not in display_types]
            
        return field


@admin.register(BlackListedPhone)
class BlacklistedPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'created_at', 'reason')  # Show these fields in the list view
    search_fields = ('phone_number', 'reason')  # Enables search for phone numbers & reasons
    list_filter = ('created_at',)  # Filter by date added


class CartItemInline(admin.TabularInline):  
    """
    To display cart items in cart admin
    """
    model = CartItem
    extra = 0  # Prevents extra empty forms
    fields = ("item", "inventory", "quantity", "total_price")  # Show relevant fields
    readonly_fields = ("item", "inventory", "quantity", "total_price",)  
    can_delete = False  # Remove the delete check box 

    def has_add_permission(self, request, obj):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "total_price", "created_at", "updated_at", "total_price")  
    readonly_fields = ("id", "total_price", "created_at", "updated_at", "total_price")
    inlines = [CartItemInline]  # Attach CartItemInline

    def has_add_permission(self, request):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "item", "inventory", "quantity", "cart", "total_price")  
    readonly_fields = ("id", "item", "inventory", "quantity", "cart", "total_price")

    def has_add_permission(self, request):
        return False


class ShippingInline(admin.TabularInline):
    model = Shipping
    extra = 0
    fields = ("order", "tracking_number", "estimated_delivery")
    readonly_fields = ("order",)
    can_delete = False
    
    def has_add_permission(self, request, obj):
        return False


class OrderItemInline(admin.TabularInline):  
    """To display order items in admin order page"""
    model = OrderItem
    extra = 0  # Prevents extra empty forms
    fields = ("item", "inventory", "quantity", "total_price", "order")  # Show relevant fields
    readonly_fields = ("item", "inventory", "quantity", "total_price", "order")  
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "cart", "created_at", "display_total_price", "status", 
        "last_name", "first_name", "email", "phone_number", "address", "city", "postal_code", "ip_address"
    )
    
    fieldsets = (
        ("Order Information", {
            "fields": ("cart", "display_total_price", "status"),
        }),
        ("Customer Information", {
            "fields": ("last_name", "first_name", "email", "phone_number", "address", "city", "postal_code"),
        }),
        ("Other Details", {
            "fields": ("ip_address",),
        }),
    ) 

    inlines = [OrderItemInline, ShippingInline]  # Attach Inlines

    def has_add_permission(self, request):
        return False

    def display_total_price(self, obj):
        if obj.status == "pending":
            return obj.cart.total_price()

        return obj.total_price()

    display_total_price.short_description = "Total Price"
    
    def get_readonly_fields(self, request, obj=None):
        """Make order status readonly if order is pending to prevent status change in admin form."""
        if obj and obj.status == "pending":  
            return ("id", "cart", "display_total_price", "created_at", "status")

        return ("id", "cart", "display_total_price", "created_at")  

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        """Prevent admin from selecting certain status after the status has changed."""
        field = super().formfield_for_choice_field(db_field, request, **kwargs)

        if db_field.name == "status": 
            order_id = request.resolver_match.kwargs.get("object_id")
            try:
                order = self.model.objects.get(id=order_id)
                allowed_choices = Order.STATUS_FLOW.get(order.status, [])
                field.choices = [(value, label) for value, label in field.choices if value in allowed_choices]
                
            except self.model.DoesNotExist:
                pass  

        return field

    def clean(self):
        # Check if inventory and item are available before printing order
        if self.status == "printing": 
            if self.orderitem_set.filter(Q(quantity__gt=F('inventory__quantity')) | Q(inventory__isnull=True)):
                raise ValidationError(_(f"{order_item.item.name} size {order_item.inventory.size} is out of stock."))
                
            elif self.orderitem_set.filter(item__isnull=True):
                raise ValidationError(_(f"{order_item.item_name} is no longer available."))        


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("item", "inventory", "quantity", "total_price", "order")
    
    readonly_fields = ("item", "inventory", "quantity", "total_price", "order")
    
    fieldsets = (
        (None, {
            "fields": ("item", "inventory", "quantity", "total_price", "order")
        }),
    )

    def image_tag(self, obj):
        return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        
    image_tag.short_description = 'Image Preview' # name of the field

    def has_add_permission(self, request):
        return False


@admin.register(Shipping)
class ShippingAdmin(admin.ModelAdmin):
    list_display = ("order", "tracking_number", "estimated_delivery",)

    readonly_fields = ("order",)

    fieldsets = (
        (None, {
            "fields": ("order", "tracking_number", "estimated_delivery")
        }),
    )

    def has_add_permission(self, request):
        return False


admin.site.register(Inventory)



