"""
Views for the Online Payment Service.

This module defines view functions for:
- Currency conversion via a RESTful service.
- Displaying the home page with pending payment requests.
- Handling user transactions: making payments, requesting payments, and viewing transaction history.
- Admin functionalities: viewing all users, transactions, and promoting users to admin.
- Integrating a remote Thrift timestamp service for transaction timestamping.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from thrift.protocol import TBinaryProtocol
from thrift.transport import TSocket, TTransport
from .models import Transaction

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

# --------------------------
# User Views
# --------------------------
def home(request):
    user = request.user
    pending_requests_count = 0


    if user.is_authenticated:
        # Count pending payment requests for the current user
        pending_requests_count = Transaction.objects.filter(
            recipient=user,
            transaction_type='REQUEST',
            status='Pending'
        ).count()

    return render(request, 'payapp/home.html', {
        'pending_requests_count': pending_requests_count,

    })

def is_staff_check(user):
    return user.is_staff or user.is_superuser

@transaction.atomic
@login_required
def requests_list(request):
    user = request.user
    pending_requests = Transaction.objects.filter(
        recipient=user,
        transaction_type='REQUEST',
        status='Pending'
    )
    return render(request, 'payapp/requests_list.html', {'pending_requests': pending_requests})

@transaction.atomic
@login_required
def make_payment(request):
    """
        Allows a logged-in user to make a direct payment to another registered user.

        Validates the payment form, checks that the recipient exists and that the sender has sufficient funds.
        Retrieves a remote timestamp via the Thrift service and creates a Payment transaction.
        Updates the sender's and recipient's balances atomically.

        Returns:
            HttpResponse redirecting to the transaction history with a success or error message.
        """
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            recipient_name = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']

            sender = request.user
            User = get_user_model()
            recipient = User.objects.filter(username=recipient_name).first()

            if not recipient:
                messages.error(request, "Recipient not found.")
                return redirect('make_payment')

            if sender.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('make_payment')

            # Now that all checks have passed, get the remote timestamp.
            remote_ts = get_remote_timestamp()

            transaction = Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='PAYMENT',
                amount=amount,
                status='Completed',
                remote_timestamp=remote_ts,
            )

            # Update balances
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
            recipient_name = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']

            sender = request.user
            User = get_user_model()
            recipient = User.objects.filter(username=recipient_name).first()

            if not recipient:
                messages.error(request, "User not found.")
                return redirect('request_payment')

            # Get the remote timestamp once all checks are passed.
            remote_ts = get_remote_timestamp()

            # Create a "Pending" transaction of type REQUEST
            Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='REQUEST',
                amount=amount,
                status='Pending',
                remote_timestamp=remote_ts,
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

# --------------------------
# Admin Views
# --------------------------

@user_passes_test(is_staff_check)
@transaction.atomic
def admin_users(request):
    # even though it's read-only, let's wrap for consistency
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
def make_admin(request, user_id):
    """Elevate a regular user to admin (staff) status."""
    User = get_user_model()
    user_to_promote = get_object_or_404(User, id=user_id)
    if user_to_promote.is_staff:
        messages.warning(request, f"{user_to_promote.username} is already an admin.")
    else:
        user_to_promote.is_staff = True
        user_to_promote.save()
        messages.success(request, f"{user_to_promote.username} has been made an admin!")
    return redirect('admin_users')  # or wherever you want to go after making admin

# --------------------------
# RTC
# --------------------------
def get_remote_timestamp():
    transport = TSocket.TSocket('localhost', 10000)
    transport = TTransport.TBufferedTransport(transport)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)
    try:
        from payapp.gen.TimestampService import Client
    except ImportError as e:
        print("Error importing Thrift generated code:", e)
        return None
    client = Client(protocol)
    transport.open()
    ts = client.getTimestamp()  # e.g. '2025-03-14T15:00:00.123456'
    transport.close()
    return ts

@login_required
def remote_timestamp_view(request):
    ts = get_remote_timestamp()
    if ts is None:
        return HttpResponse("Error retrieving remote timestamp.")
    return HttpResponse(f"Remote timestamp: {ts}")