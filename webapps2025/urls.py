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

from django.contrib import admin
from django.urls import path

from payapp.views import (
    home, make_payment, request_payment, requests_list, conversion, handle_request,
    transaction_history, admin_users, admin_transactions, make_admin, remote_timestamp_view
)
from register.views import register, user_login, user_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('webapps2025/', home, name='home'),

    # User routes
    path('webapps2025/pay/make/', make_payment, name='make_payment'),
    path('webapps2025/pay/request/', request_payment, name='request_payment'),
    path('webapps2025/pay/history/', transaction_history, name='transaction_history'),
    path('webapps2025/requests/', requests_list, name='requests_list'),
    path('webapps2025/pay/handle/<int:transaction_id>/', handle_request, name='handle_request'),

    # Registration & login
    path('webapps2025/register/signup/', register, name='register'),
    path('webapps2025/register/login/', user_login, name='login'),
    path('webapps2025/register/logout/', user_logout, name='logout'),

    # Admin routes
    path('webapps2025/admin/users/', admin_users, name='admin_users'),
    path('webapps2025/admin/transactions/', admin_transactions, name='admin_transactions'),
    path('webapps2025/admin/make_admin/<int:user_id>/', make_admin, name='make_admin'),

    # Currency conversion RESTful service
    path('conversion/<str:currency1>/<str:currency2>/<str:amount>/', conversion, name='conversion'),

    # RTC
    path('remote-timestamp/', remote_timestamp_view, name='remote_timestamp'),
]
