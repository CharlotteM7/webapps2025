# register/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
import requests

# Inline login form
class LoginForm(forms.Form):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

# (Example) Register form for reference
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'currency', 'password1', 'password2']

def get_conversion_rate(target_currency):
    """
    Calls the RESTful conversion service to get the conversion rate from GBP to the target currency.
    If the target currency is GBP, returns 1.0.
    """
    if target_currency.upper() == 'GBP':
        return 1.0
    try:
        # Assuming your conversion service is running at localhost:8000
        # and its endpoint is defined as:
        # /conversion/<currency1>/<currency2>/<amount>/
        # Here we pass 750 as the amount to get the rate.
        url = f'http://127.0.0.1:8000/conversion/GBP/{target_currency.upper()}/750/'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Expecting the JSON to include a 'rate' field
            return data.get('rate', 1.0)
        else:
            print("Conversion service returned error code:", response.status_code)
            return 1.0
    except Exception as e:
        print("Error calling conversion service:", e)
        return 1.0

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # Get the chosen currency from the form
            chosen_currency = form.cleaned_data['currency']
            # Call the REST service to get the conversion rate from GBP to chosen currency.
            conversion_rate = get_conversion_rate(chosen_currency)
            baseline = 750.0  # The baseline amount in GBP.
            initial_balance = baseline * conversion_rate

            # Save the user with commit=False so we can set balance before saving.
            user = form.save(commit=False)
            user.balance = initial_balance
            user.save()

            messages.success(request, "Registration successful!")
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'register/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            uname = form.cleaned_data['username']
            pwd = form.cleaned_data['password']
            user = authenticate(username=uname, password=pwd)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {uname}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'register/login.html', {'form': form})


def user_logout(request):
    """Logs out the current user and redirects."""
    logout(request)

    messages.success(request, "You've been logged out.")
    return redirect('login')  # or redirect('home')

