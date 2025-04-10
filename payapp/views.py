"""
Views for the Online Payment Service.

This module defines view functions for:
- Currency conversion via a RESTful service.
- Displaying the home page with pending payment requests.
- Handling user transactions: making payments, requesting payments, and viewing transaction history.
- Admin functionalities: viewing all users, transactions, and promoting users to admin.
- Integrating a remote Thrift timestamp service for transaction timestamping.
"""
import requests
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
from decimal import Decimal, ROUND_HALF_UP
from django.utils.dateparse import parse_datetime


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

def get_transaction_rate(from_currency, to_currency):
    """
    Fetches the conversion rate from from_currency to to_currency.
    For transactions, we pass an amount of 1 so that the returned rate is directly usable.
    Returns a Decimal conversion multiplier.
    """
    if from_currency.upper() == to_currency.upper():
        return Decimal('1.0')
    try:
        url = f"http://127.0.0.1:8000/conversion/{from_currency.upper()}/{to_currency.upper()}/1/"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            rate = data.get('rate', 1.0)
            return Decimal(str(rate))
        else:
            print("Transaction conversion service returned error:", response.status_code)
            return Decimal('1.0')
    except Exception as e:
        print("Error calling transaction conversion service:", e)
        return Decimal('1.0')

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

        # Check for new payments since the user's previous last_login
        previous_last_login_iso = request.session.get('previous_last_login', '')
        if previous_last_login_iso:
            previous_last_login = parse_datetime(previous_last_login_iso)
            if previous_last_login:
                new_payments = Transaction.objects.filter(
                    recipient=user,
                    transaction_type='PAYMENT',
                    timestamp__gt=previous_last_login
                )
                if new_payments.exists():
                    messages.info(request,
                        f"You have {new_payments.count()} new payment(s) received since your last login."
                    )
            # Now clear the stored last login so the notification doesn't appear again
            del request.session['previous_last_login']

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

                # Prevent users from sending payment to themselves.
            if sender == recipient:
                messages.error(request, "You cannot send payment to yourself.")
                return redirect('make_payment')

            if sender.balance < amount:
                messages.error(request, "Insufficient funds.")
                return redirect('make_payment')

            # For transaction conversion, use sender.currency as the source and recipient.currency as the target.
            if sender.currency != recipient.currency:
                conversion_rate = get_transaction_rate(sender.currency, recipient.currency)
                amount_in_recipient_currency = amount * conversion_rate
                amount_in_recipient_currency = amount_in_recipient_currency.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
            else:
                amount_in_recipient_currency = amount

            # Get remote timestamp
            remote_ts = get_remote_timestamp()

            # Create the transaction (store original amount and converted amount)
            transaction = Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='PAYMENT',
                amount=amount,  # amount in sender's currency
                converted_amount=amount_in_recipient_currency,  # record the converted amount
                status='Completed',
                remote_timestamp=remote_ts,
            )

            # Update sender's balance (deduct original amount)
            sender.balance -= amount
            sender.balance = sender.balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Update recipient's balance (add converted amount)
            recipient.balance += amount_in_recipient_currency

            sender.save()
            recipient.save()

            messages.success(request, f"Payment of {amount} {sender.currency} to {recipient.username} completed.")
            return redirect('transaction_history')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentForm()
    return render(request, 'payapp/make_payment.html', {'form': form})

@transaction.atomic
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

            # Prevent requesting payment from yourself
            if sender == recipient:
                messages.error(request, "You cannot request payment from yourself.")
                return redirect('request_payment')

            # For transaction conversion, use sender.currency as source and recipient.currency as target.
            if sender.currency != recipient.currency:
                conversion_rate = get_transaction_rate(sender.currency, recipient.currency)
                amount_in_recipient_currency = amount * conversion_rate
                amount_in_recipient_currency = amount_in_recipient_currency.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                amount_in_recipient_currency = amount

            # Get the remote timestamp
            remote_ts = get_remote_timestamp()

            # Create a "Pending" transaction with conversion info stored
            Transaction.objects.create(
                sender=sender,
                recipient=recipient,
                transaction_type='REQUEST',
                amount=amount,
                converted_amount=amount_in_recipient_currency,
                status='Pending',
                remote_timestamp=remote_ts,
            )
            messages.success(
                request,
                f"Payment request of {amount} {sender.currency} (equivalent to {amount_in_recipient_currency} {recipient.currency}) sent to {recipient.username}."
            )
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

    # For received transactions, if converted_amount exists, use it.
    for tx in received:
        if tx.converted_amount:
            tx.effective_amount = tx.converted_amount
        else:
            tx.effective_amount = tx.amount

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
    return redirect('admin_users')

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
    ts = client.getTimestamp()
    transport.close()
    return ts

@login_required
def remote_timestamp_view(request):
    ts = get_remote_timestamp()
    if ts is None:
        return HttpResponse("Error retrieving remote timestamp.")
    return HttpResponse(f"Remote timestamp: {ts}")