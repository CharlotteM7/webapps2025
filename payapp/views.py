from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PaymentForm
from .models import Transaction
from django.conf import settings
# Create your views here.
@login_required
def make_payment(request):
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            recipient_name = form.cleaned_data['recipient']
            amount = form.cleaned_data['amount']
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            messages.error(request, "Invalid amount.")
            return redirect('make_payment')

        # Get sender (current user) & recipient
        sender = request.user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = User.objects.filter(username=recipient_name).first()

        if not recipient:
            messages.error(request, "Recipient not found.")
            return redirect('make_payment')

        if sender.balance < amount:
            messages.error(request, "Insufficient funds.")
            return redirect('make_payment')

        # Create transaction
        transaction = Transaction.objects.create(
            sender=sender,
            recipient=recipient,
            transaction_type='PAYMENT',
            amount=amount,
            status='Completed'
        )

        # Update balances
        sender.balance -= amount
        recipient.balance += amount
        sender.save()
        recipient.save()

        messages.success(request, f"Payment of {amount} to {recipient.username} completed.")
        return redirect('transaction_history')
    else:
        form = PaymentForm()
    return render(request, 'payapp/make_payment.html', {'form': form})


@login_required
def request_payment(request):
    if request.method == 'POST':
        recipient_username = request.POST.get('recipient')
        amount = request.POST.get('amount')
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            messages.error(request, "Invalid amount.")
            return redirect('request_payment')

        sender = request.user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = User.objects.filter(username=recipient_username).first()

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

    return render(request, 'payapp/request_payment.html')


@login_required
def handle_request(request, transaction_id):
    transaction = Transaction.objects.filter(id=transaction_id, transaction_type='REQUEST').first()
    if not transaction:
        messages.error(request, "Transaction not found or not a request.")
        return redirect('transaction_history')

    # Only the "recipient" can respond to a request
    if request.user != transaction.recipient:
        messages.error(request, "You are not the recipient of this request.")
        return redirect('transaction_history')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            # Check if recipient has enough balance
            if transaction.recipient.balance >= transaction.amount:
                # Perform the actual payment
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
    # Show all transactions involving current user
    user = request.user
    sent = user.sent_transactions.all()
    received = user.received_transactions.all()
    return render(request, 'payapp/transaction_history.html', {
        'sent': sent,
        'received': received,
    })
