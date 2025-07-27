from django.db import models
from .models import Inventory
from .utils import ItemType
from django.utils.text import slugify

class Display(models.Model):
	image = models.ImageField(upload_to='display/', max_length=200)
	type = models.OneToOneField(ItemType, on_delete=models.CASCADE)

	def __str__(self):
		return self.type.type


class Item(models.Model): 
	name = models.CharField(max_length=200)
	image = models.ImageField(upload_to='item/', max_length=200)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	type = models.ForeignKey(ItemType, on_delete=models.CASCADE)

	def __str__(self):
		return self.name


