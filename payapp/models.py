"""
Models for the Online Payment Service.
This module defines the Transaction model for recording payments and payment requests,
and the CustomUser model extending Django's AbstractUser to include currency and balance fields.
"""

from django.conf import settings
from django.db import models


class Transaction(models.Model):
    """
       Represents a transaction (either a payment or a request) between two users.

       Attributes:
           sender: ForeignKey to the user initiating the transaction.
           recipient: ForeignKey to the user receiving the transaction.
           transaction_type: Type of transaction (PAYMENT or REQUEST).
           amount: The monetary value involved in the transaction (in the sender's currency).
           converted_amount: The monetary value converted to the recipient's currency.
           timestamp: The date and time when the transaction was created.
           remote_timestamp: The timestamp obtained from the remote Thrift service.
           status: The current status of the transaction (Pending, Completed, or Rejected).
       """

    TRANSACTION_TYPE_CHOICES = [
        ('PAYMENT', 'Payment'),
        ('REQUEST', 'Request'),
    ]
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_transactions'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_transactions'
    )
    transaction_type = models.CharField(
        max_length=8, choices=TRANSACTION_TYPE_CHOICES, default='PAYMENT'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # New field to record the converted amount (in the recipient's currency)
    converted_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    remote_timestamp = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Rejected', 'Rejected')],
        default='Pending'
    )

    def __str__(self):
        return f"{self.transaction_type}: {self.sender} -> {self.recipient}, {self.amount}"
