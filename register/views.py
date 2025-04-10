"""
Views for user registration and authentication.

This module provides:
- A custom login form (LoginForm)
- A custom user creation form (CustomUserCreationForm) extending Django's UserCreationForm
- A utility function get_conversion_rate() that calls a RESTful service to fetch a conversion rate
- View functions for user registration, login, and logout
"""
import requests
from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from .models import CustomUser

# Inline login form
class LoginForm(forms.Form):
    """
       Simple login form with username and password fields.
       """
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")

# Custom user creation form for registration
class CustomUserCreationForm(UserCreationForm):
    """
        Extends Django's UserCreationForm to include an email field.
        Also sets the CustomUser model and the fields to be used.
        """
    email = forms.EmailField(required=True, label="Email Address")
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

        # /conversion/<currency1>/<currency2>/<amount>/
        # Here we pass 750 as the amount to get the rate.
        url = f'http://127.0.0.1:8000/conversion/GBP/{target_currency.upper()}/750/'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get('rate', 1.0)
        else:
            print("Conversion service returned error code:", response.status_code)
            return 1.0
    except Exception as e:
        print("Error calling conversion service:", e)
        return 1.0


def register(request):
    """
       Handles user registration. On POST, validates the registration form, retrieves the
       conversion rate for the selected currency, calculates the initial balance, and creates
       the new user. On success, logs the user in and redirects to the home page.

       Args:
           request: The HTTP request object.

       Returns:
           HttpResponse: Renders the registration page or redirects on successful registration.
       """
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
            messages.error(request, "Please correct the errors to continue.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'register/register.html', {'form': form})


def user_login(request):
    """
       Authenticates and logs in a user. On POST, checks the provided credentials and logs in
       the user if valid; otherwise, displays an error message.

       Args:
           request: The HTTP request object.

       Returns:
           HttpResponse: Renders the login page or redirects to home on successful login.
       """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            uname = form.cleaned_data['username']
            pwd = form.cleaned_data['password']
            user = authenticate(username=uname, password=pwd)
            if user is not None:
                # Store the previous last_login (if any) in the session.
                # Note: user.last_login is None for a first-time login.
                if user.last_login:
                    request.session['previous_last_login'] = user.last_login.isoformat()
                else:
                    request.session['previous_last_login'] = ''
                login(request, user)
                messages.success(request, f"Welcome back, {uname}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'register/login.html', {'form': form})



def user_logout(request):
    """
    Logs out the current user and redirects to the login page.

    Args:
        request: The HTTP request object.

    Returns:
        HttpResponse: Redirects to the login page after logout.
    """
    logout(request)
    messages.success(request, "You've been logged out.")
    return redirect('login')