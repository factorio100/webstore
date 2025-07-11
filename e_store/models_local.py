from django.db import models
from .models import Inventory

class Item(models.Model): 
	name = models.CharField(max_length=200)
	image = models.ImageField(upload_to='pictures/')
	price = models.DecimalField(max_digits=10, decimal_places=2)
	type = models.CharField(max_length=20, choices=[('t_shirt', 'T_shirt'), ('pant', 'Pant')])

	def __str__(self):
		return self.name


class Display(models.Model):
	image = models.ImageField(upload_to='display_category/')
	type = models.CharField(max_length=50, choices=[('t_shirt', 'T_shirt'), ('pant', 'Pant')], unique=True)

	def __str__(self):
		return self.type


