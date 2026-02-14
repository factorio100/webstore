from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from decouple import config
import cloudinary.uploader

from e_store.models import ItemType, Size, Inventory, Display, Item

User = get_user_model()


class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **kwargs):

        # =========================
        # SUPERUSER
        # =========================
        username = config('USERNAME')
        email = config('EMAIL')
        password = config('PASSWORD')

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            }
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
        else:
            self.stdout.write(self.style.WARNING(f"Superuser '{username}' already exists."))


        # =========================
        # DEMO ADMIN
        # =========================
        demo_user, created = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "email": "demo_admin@example.com",
                "is_staff": True,
                "is_superuser": False,
            }
        )

        if created:
            demo_user.set_password("demo1234")
            demo_user.save()
            self.stdout.write(self.style.SUCCESS("Demo admin created."))
        else:
            self.stdout.write(self.style.WARNING("Demo admin already exists."))


        # =========================
        # ITEM TYPES
        # =========================
        clothes_types = ['t_shirt', 'pant', 'shirt', 'hoodie', 'sweater']

        for t in clothes_types:
            ItemType.objects.get_or_create(type=t)

        shoe_type, _ = ItemType.objects.get_or_create(type="shoe")

        item_types = ItemType.objects.all()


        # =========================
        # SIZES
        # =========================
        sizes_clothes = ['S', 'M', 'L', 'XL', 'XXL']
        for s in sizes_clothes:
            Size.objects.get_or_create(name=s)

        sizes_shoes = ['39', '40', '41', '42']
        for s in sizes_shoes:
            Size.objects.get_or_create(name=s)


        # =========================
        # INVENTORY (CLOTHES)
        # =========================
        qty_clothes = [
            [50, 0, 100, 40, 0],
            [50, 40, 100, 0, 80],
            [50, 10, 100, 0, 0],
            [50, 50, 0, 0, 0],
            [0, 0, 100, 40, 0]
        ]

        clothes_type_instances = ItemType.objects.filter(type__in=clothes_types)
        clothes_size_instances = Size.objects.filter(name__in=sizes_clothes)

        quantities = [n for sublist in qty_clothes for n in sublist]

        type_size_pairs = [
            (t, s)
            for t in clothes_type_instances
            for s in clothes_size_instances
        ]

        for (t, s), qty in zip(type_size_pairs, quantities):
            Inventory.objects.update_or_create(
                type=t,
                size=s,
                defaults={"quantity": qty}
            )


        # =========================
        # INVENTORY (SHOES)
        # =========================
        qty_shoes = [10, 50, 0, 50]

        shoe_sizes_instances = Size.objects.filter(name__in=sizes_shoes)

        for size, qty in zip(shoe_sizes_instances, qty_shoes):
            Inventory.objects.update_or_create(
                type=shoe_type,
                size=size,
                defaults={"quantity": qty}
            )


        # =========================
        # DISPLAYS
        # =========================
        display_images = [
            "C:/Users/EM/Desktop/programing/designs/t_shirts/display_t_shirt.jpg",
            "C:/Users/EM/Desktop/programing/designs/pants/display_pant.jpg",
            "C:/Users/EM/Desktop/programing/designs/shirts/display_shirt.jpg",
            "C:/Users/EM/Desktop/programing/designs/hoodies/display_hoodie.jpg",
            "C:/Users/EM/Desktop/programing/designs/sweaters/display_sweater.jpg",
            "C:/Users/EM/Desktop/programing/designs/shoes/display_shoes.jpg"
        ]

        for item_type, image_path in zip(item_types, display_images):
            upload_result = cloudinary.uploader.upload(image_path, folder="displays/")
            Display.objects.update_or_create(
                type=item_type,
                defaults={"image": upload_result["public_id"]}
            )


        # =========================
        # ITEMS
        # =========================
        item_images = [
            ("C:/Users/EM/Desktop/programing/designs/t_shirts/t_shirt_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/t_shirts/t_shirt_2.jpg"),

            ("C:/Users/EM/Desktop/programing/designs/pants/pant_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/pants/pant_2.jpg"),

            ("C:/Users/EM/Desktop/programing/designs/shirts/shirt_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/shirts/shirt_2.jpg"),

            ("C:/Users/EM/Desktop/programing/designs/hoodies/hoodie_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/hoodies/hoodie_2.jpg"),

            ("C:/Users/EM/Desktop/programing/designs/sweaters/sweater_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/sweaters/sweater_2.jpg"),

            ("C:/Users/EM/Desktop/programing/designs/shoes/shoes_1.jpg",
             "C:/Users/EM/Desktop/programing/designs/shoes/shoes_2.jpg")
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

        for item_type, (name1, name2), (price1, price2), (img1, img2) in zip(
                item_types, names, prices, item_images):

            upload1 = cloudinary.uploader.upload(img1, folder="items/")
            upload2 = cloudinary.uploader.upload(img2, folder="items/")

            Item.objects.update_or_create(
                name=name1,
                type=item_type,
                defaults={
                    "image": upload1["public_id"],
                    "price": price1
                }
            )

            Item.objects.update_or_create(
                name=name2,
                type=item_type,
                defaults={
                    "image": upload2["public_id"],
                    "price": price2
                }
            )

        self.stdout.write(self.style.SUCCESS("Seeding completed successfully."))
