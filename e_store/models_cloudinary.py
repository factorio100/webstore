from django.db import models
from .models import Inventory
from cloudinary.models import CloudinaryField

class Item(models.Model): 
	name = models.CharField(max_length=200)
	image = CloudinaryField('image') 
	price = models.DecimalField(max_digits=10, decimal_places=2)
	type = models.CharField(max_length=50, choices=[('t_shirt', 'T_shirt'), ('pant', 'Pant')])

	def __str__(self):
		return self.name


class Display(models.Model):
	image = CloudinaryField('image') 
	type = models.CharField(max_length=50, choices=[('t_shirt', 'T_shirt'), ('pant', 'pant')], unique=True)

	def __str__(self):
		return self.type


