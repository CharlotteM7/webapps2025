from django.db import models
from django.conf import settings
# Create your models here.
class Transaction(models.Model):
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
    transaction_type = models.CharField(max_length=8, choices=TRANSACTION_TYPE_CHOICES, default='PAYMENT')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Rejected', 'Rejected')],
        default='Pending'
    )

    def __str__(self):
        return f"{self.transaction_type}: {self.sender} -> {self.recipient}, {self.amount}"