from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class CustomUser(AbstractUser):
    CURRENCY_CHOICES = [
        ('GBP', 'Pounds'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GBP')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('750.00'))

    def __str__(self):
        return f"{self.username} ({self.currency})"
