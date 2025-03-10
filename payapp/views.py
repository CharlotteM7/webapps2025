from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django import forms
from django.contrib.auth import get_user_model
from .models import Transaction
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol

# Inline definition of PaymentForm
class PaymentForm(forms.Form):
    recipient = forms.CharField(max_length=150, label="Recipient Username")
    amount = forms.DecimalField(decimal_places=2, max_digits=10, label="Amount")

@require_GET
def conversion(request, currency1, currency2, amount):
    """
    A RESTful service to convert an amount from one currency to another.
    URL pattern: /conversion/<currency1>/<currency2>/<amount>/
    """
    try:
        amount = float(amount)
    except ValueError:
        return JsonResponse({'error': 'Invalid amount value'}, status=400)

    # Define hard-coded conversion rates
    rates = {
        ('GBP', 'USD'): 1.20,
        ('GBP', 'EUR'): 1.13,
        ('USD', 'GBP'): 0.83,
        ('USD', 'EUR'): 0.94,
        ('EUR', 'GBP'): 0.88,
        ('EUR', 'USD'): 1.06,
    }

    # Allow same currency conversion (rate = 1)
    if currency1.upper() == currency2.upper():
        return JsonResponse({
            'from_currency': currency1.upper(),
            'to_currency': currency2.upper(),
            'original_amount': amount,
            'rate': 1.0,
            'converted_amount': amount
        })

    rate = rates.get((currency1.upper(), currency2.upper()))
    if rate is None:
        return JsonResponse({'error': 'Unsupported currency conversion'}, status=400)

    converted_amount = amount * rate
    return JsonResponse({
        'from_currency': currency1.upper(),
        'to_currency': currency2.upper(),
        'original_amount': amount,
        'rate': rate,
        'converted_amount': round(converted_amount, 2)
    })

def home(request):
    return render(request, 'payapp/home.html')


def is_staff_check(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_staff_check)
@transaction.atomic
def admin_users(request):
    # even though it's read-only, let's wrap for consistency
    User = get_user_model()
    all_users = User.objects.all()
    return render(request, 'admin_users.html', {'users': all_users})
@user_passes_test(is_staff_check)
def admin_users(request):
    """View all user accounts."""
    User = get_user_model()
    all_users = User.objects.all()
    return render(request, 'admin_users.html', {'users': all_users})

@user_passes_test(is_staff_check)
def admin_transactions(request):
    """View all payment transactions."""
    all_txs = Transaction.objects.all()
    return render(request, 'admin_transactions.html', {'transactions': all_txs})

@user_passes_test(is_staff_check)
@transaction.atomic
def admin_register_admin(request):
    """Register new administrators (staff or superuser)."""
    if request.method == 'POST':
        # Example inline approach
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if username and password:
            User = get_user_model()
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            else:
                # Create a staff user or superuser
                new_admin = User.objects.create_user(username=username, email=email, password=password)
                new_admin.is_staff = True  # or new_admin.is_superuser = True
                new_admin.save()
                messages.success(request, "New administrator created!")
                return redirect('admin_users')
        else:
            messages.error(request, "Invalid form input.")
    return render(request, 'admin_register_admin.html')


@transaction.atomic
@login_required
def make_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Extract cleaned data from the form
            recipient_name = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']  # This remains a Decimal, not float

            sender = request.user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            recipient = User.objects.filter(username=recipient_name).first()

            if not recipient:
                messages.error(request, "Recipient not found.")
                return redirect('make_payment')

            # Now this comparison is Decimal - Decimal
            if sender.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('make_payment')

            # Create a transaction
            transaction = Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='PAYMENT',
                amount=amount,
                status='Completed'
            )

            # Update balances (Decimal - Decimal)
            sender.balance -= amount
            recipient.balance += amount
            sender.save()
            recipient.save()

            messages.success(request, f"Payment of {amount} to {recipient.username} completed.")
            return redirect('transaction_history')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentForm()
    return render(request, 'payapp/make_payment.html', {'form': form})


@login_required
def request_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Get the recipient and amount from cleaned_data
            recipient_name = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']

            sender = request.user
            User = get_user_model()
            recipient = User.objects.filter(username=recipient_name).first()

            if not recipient:
                messages.error(request, "User not found.")
                return redirect('request_payment')

            # Create a "Pending" transaction of type REQUEST
            Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='REQUEST',
                amount=amount,
                status='Pending'
            )

            messages.success(request, f"Payment request of {amount} sent to {recipient.username}.")
            return redirect('transaction_history')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentForm()
    return render(request, 'payapp/request_payment.html', {'form': form})


@login_required
def handle_request(request, transaction_id):
    transaction = Transaction.objects.filter(id=transaction_id, transaction_type='REQUEST').first()
    if not transaction:
        messages.error(request, "Transaction not found or not a request.")
        return redirect('transaction_history')

    # Only allow the recipient to respond to the request
    if request.user != transaction.recipient:
        messages.error(request, "You are not the recipient of this request.")
        return redirect('transaction_history')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            # Check if recipient has enough balance
            if transaction.recipient.balance >= transaction.amount:
                transaction.recipient.balance -= transaction.amount
                transaction.sender.balance += transaction.amount
                transaction.recipient.save()
                transaction.sender.save()
                transaction.status = 'Completed'
                messages.success(request, "Payment request accepted and paid.")
            else:
                transaction.status = 'Rejected'
                messages.error(request, "Not enough balance to accept this request.")
        else:
            transaction.status = 'Rejected'
            messages.warning(request, "Payment request rejected.")
        transaction.save()
        return redirect('transaction_history')

    return render(request, 'payapp/handle_request.html', {'transaction': transaction})

@login_required
def transaction_history(request):
    user = request.user
    sent = user.sent_transactions.all()
    received = user.received_transactions.all()
    return render(request, 'payapp/transaction_history.html', {
        'sent': sent,
        'received': received,
    })


def get_remote_timestamp():
    transport = TSocket.TSocket('localhost', 10000)
    transport = TTransport.TBufferedTransport(transport)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    try:
        from payapp.gen_py.timestamp_service import TimestampService
    except ImportError as e:
        print("Error importing Thrift generated code:", e)
        return None
    client = TimestampService.Client(protocol)
    transport.open()
    ts = client.getTimestamp()
    transport.close()
    return ts