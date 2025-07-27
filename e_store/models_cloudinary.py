from cloudinary.models import CloudinaryField
from django.db import models
from .models import Inventory
from .utils import ItemType
from django.utils.text import slugify

class Display(models.Model):
	image = CloudinaryField('image') 
	type = models.OneToOneField(ItemType, on_delete=models.CASCADE)

	def __str__(self):
		return self.type.type


class Item(models.Model): 
	name = models.CharField(max_length=200)
	image = CloudinaryField('image') 
	price = models.DecimalField(max_digits=10, decimal_places=2)
	type = models.ForeignKey(ItemType, on_delete=models.CASCADE)

	def __str__(self):
		return self.name
