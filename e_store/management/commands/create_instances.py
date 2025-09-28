from django.core.management.base import BaseCommand
from django.contrib.auth.models import User 
from e_store.models import Size, Inventory
from e_store.models_cloudinary import Display, Item
from e_store.utils import ItemType
from decouple import config
from django.core.files import File
import os
import cloudinary.uploader

class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        username = config('USERNAME')
        email = config('EMAIL')
        password = config('PASSWORD')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))

        # Demo admin
        demo_username = "demo_admin"
        demo_email = "demo_admin@example.com"
        demo_password = "demo1234"

        if not User.objects.filter(username=demo_username).exists():
            User.objects.create_user(
            username=demo_username,
            email=demo_email,
            password=demo_password,
            is_staff=True,   
            is_superuser=False 
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{demo_username}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{demo_username}' already exists."))

        # Create inventory for clothes
        clothes_types = ['t_shirt', 'pant', 'shirt', 'hoodie', 'sweater']
        for type in clothes_types:
            ItemType.objects.create(type=type)

        clothes_types_instances = ItemType.objects.all()

        sizes_for_clothes = ['S', 'M', 'L', 'XL', 'XXL']
        for size in sizes_for_clothes:
            Size.objects.create(name=size)
        
        clothes_sizes_instances = Size.objects.all()

        qty_clothes = [
            [50, 0, 100, 40, 0], [50, 40, 100, 0, 80], [50, 10, 100, 0, 0],
            [50, 50, 0, 0, 0], [0, 0, 100, 40, 0]
        ]
        
        quantities = []
        for l in qty_clothes:
            for n in l:
                quantities.append(n)

        type_size = []
        for type in clothes_types_instances:
            for size in clothes_sizes_instances:
                    type_size.append((type, size))

        type_size_qty = []
        for pair, qty in zip(type_size, quantities):
            type_size_qty.append((pair, qty))

        type_size_qty_formated = []
        for a in type_size_qty:
            ((x, y), z) = a
            type_size_qty_formated.append((x, y, z))
        
        for type,size, qty in type_size_qty_formated:
            Inventory.objects.create(type=type, size=size, quantity=qty)

        # Create inventory for shoes
        shoe = ItemType.objects.create(type="shoe")
        sizes_shoes = ['39', '40', '41', '42']
        for size in sizes_shoes:
            Size.objects.create(name=size)
        
        sizes_shoes_instances = []
        for size in sizes_shoes:
            instance = Size.objects.filter(name=size).first()
            sizes_shoes_instances.append(instance)

        qty_shoe = [10, 50, 0, 50]

        size_qty_shoe = []
        for size, qty in zip(sizes_shoes_instances, qty_shoe):
            size_qty_shoe.append((size, qty))

        for size, qty in size_qty_shoe:
            Inventory.objects.create(type=shoe, size=size, quantity=qty)
        
        # Create displays
        item_type_instances = ItemType.objects.all()
        
        display_path_images = [
            "C:/Users/EM/Desktop/designs/t_shirts/display_t_shirt.jpg",
            "C:/Users/EM/Desktop/designs/pants/display_pant.jpg",
            "C:/Users/EM/Desktop/designs/shirts/display_shirt.jpg",
            "C:/Users/EM/Desktop/designs/hoodies/display_hoodie.jpg",
            "C:/Users/EM/Desktop/designs/sweaters/display_sweater.jpg",
            "C:/Users/EM/Desktop/designs/shoes/display_shoes.jpg"
        ]

        for type, image_path in zip(item_type_instances, display_path_images):
            upload_result = cloudinary.uploader.upload(image_path, folder="displays/")
            Display.objects.create(
                image=upload_result['public_id'],  
                type=type
            )

        
        # Create items
        item_path_images = [
            ("C:/Users/EM/Desktop/designs/t_shirts/t_shirt_1.jpg", "C:/Users/EM/Desktop/designs/t_shirts/t_shirt_2.jpg"),
            ("C:/Users/EM/Desktop/designs/pants/pant_1.jpg", "C:/Users/EM/Desktop/designs/pants/pant_2.jpg"),
            ("C:/Users/EM/Desktop/designs/shirts/shirt_1.jpg", "C:/Users/EM/Desktop/designs/shirts/shirt_2.jpg"),
            ("C:/Users/EM/Desktop/designs/hoodies/hoodie_1.jpg", "C:/Users/EM/Desktop/designs/hoodies/hoodie_2.jpg"),
            ("C:/Users/EM/Desktop/designs/sweaters/sweater_1.jpg", "C:/Users/EM/Desktop/designs/sweaters/sweater_2.jpg"),
            ("C:/Users/EM/Desktop/designs/shoes/shoes_1.jpg", "C:/Users/EM/Desktop/designs/shoes/shoes_2.jpg")
        ]

        names = [
            ("t_shirt_1", "t_shirt_2"),
            ("pant_1", "pant_2"),
            ("shirt_1", "shirt_2"),
            ("hoodie_1", "hoodie_2"),
            ("sweater_1", "sweater_2"),
            ("shoes_1", "shoes_2")
        ]

        prices = [
            ("40", "100"), 
            ("250", "80"),
            ("10", "35"),
            ("60", "80"),
            ("50", "50"),
            ("47", "5000")
        ]

        for type, (name_1, name_2), (price_1, price_2), (image_1, image_2) in zip(item_type_instances, names, prices, item_path_images): 
            upload_result_1 = cloudinary.uploader.upload(image_1, folder="displays/")
            upload_result_2 = cloudinary.uploader.upload(image_2, folder="displays/")
            Item.objects.create(
                name=name_1,
                image=upload_result_1["public_id"],
                type=type,
                price=price_1
            )
            Item.objects.create(
                name=name_2,
                image=upload_result_2["public_id"],
                type=type,
                price=price_2
            )

        

        



