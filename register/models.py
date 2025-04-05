"""
This module defines the custom user model used in the application. The CustomUser model
extends Django's AbstractUser to include additional fields for currency and balance.
Each new user is given a default balance of 750.00 in their selected currency.
"""

from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    """
       Custom user model that extends Django's AbstractUser.

       Additional Fields:
           currency (CharField): The currency in which the user's account is maintained.
               Choices are 'GBP', 'USD', and 'EUR'. Defaults to 'GBP'.
           balance (DecimalField): The monetary balance of the user's account.
               Defaults to 750.00.
       """
    CURRENCY_CHOICES = [
        ('GBP', 'Pounds'),
        ('USD', 'US Dollars'),
        ('EUR', 'Euros'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='GBP')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('750.00'))

    def __str__(self):
        """
               Return a human-readable representation of the user.

               Returns:
                   str: A string containing the username and the currency.
               """
        return f"{self.username} ({self.currency})"
