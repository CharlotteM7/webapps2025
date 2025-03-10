from django import forms

class PaymentForm(forms.Form):
    recipient = forms.CharField(max_length=150)
    amount = forms.DecimalField(decimal_places=2, max_digits=10)
