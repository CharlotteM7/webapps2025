"""
URL configuration for webapps2025 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from django.contrib import admin
from register.views import register, user_login, user_logout
from payapp.views import home, make_payment, request_payment, conversion, transaction_history, admin_users, admin_transactions, admin_register_admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webapps2025/', home, name='home'),

    # User routes
    path('webapps2025/pay/make/', make_payment, name='make_payment'),
    path('webapps2025/pay/request/', request_payment, name='request_payment'),
    path('webapps2025/pay/history/', transaction_history, name='transaction_history'),

    # Registration & login
    path('webapps2025/register/signup/', register, name='register'),
    path('webapps2025/register/login/', user_login, name='login'),
    path('webapps2025/register/logout/', user_logout, name='logout'),

    # Admin routes
    path('webapps2025/admin/users/', admin_users, name='admin_users'),
    path('webapps2025/admin/transactions/', admin_transactions, name='admin_transactions'),
    path('webapps2025/admin/register_admin/', admin_register_admin, name='admin_register_admin'),

    # Currency conversion RESTful service
    path('conversion/<str:currency1>/<str:currency2>/<str:amount>/', conversion, name='conversion'),
]


