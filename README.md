# Online Payment Service Project 

## Table of Contents

- [About the Project](#about-the-project)
- [Built with](#built-with)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Credits](#credits)
- [License](#license)

![image](https://github.com/user-attachments/assets/942da36b-3e26-4f74-bdd7-c7e9e8b56abd)


## About the Project
The **Online Payment Service** is a Django-based web application that simulates a simplified multi-user payment system (similar to PayPal). Through a web interface, registered users can:
- Send money to other users.
- Request money.
- View their transaction history and account balance.

Administrators have additional privileges to view all user transactions, manage user accounts, and promote users to admin status.

The system also integrates:
- A RESTful currency conversion service (to convert a baseline amount in GBP to USD/EUR).
- A remote timestamp service using Apache Thrift, which stamps transactions reliably.

## Built with
- **Backend:** Django, Python
- **Frontend:** HTML, Bootstrap 
- **API & RPC:** Django REST Framework for the currency conversion API; Apache Thrift for the remote timestamp service.
- **Database:** PostgreSQL
- **Other Dependencies:** Requests library (for HTTP calls), django-crispy-forms for enhanced form rendering.

## Features
- **User Registration and Authentication:**  
  - Custom registration with email and currency choice.  
  - Automatically computes an initial balance (750 GBP or its converted equivalent) using a RESTful conversion service.  
  - Auto-creation of an initial admin account (`admin1/admin1`) after migrations.  

- **Payments and Payment Requests:**  
  - Direct payment functionality with balance updates and cross-currency conversion.  
  - Payment request functionality that tracks pending requests, with options to accept or reject requests.

- **RESTful Currency Conversion:**  
  - A dedicated REST service converts specified amounts between supported currencies.  
  - This service is integrated into the registration and transaction processes.

- **Transaction History:**  
  - Detailed history of sent and received transactions with proper timestamping.  
  - Conversion details are displayed for cross-currency transactions.

- **Admin Functionality:**  
  - Admin users can view all user accounts and all payment transactions.  
  - They can also promote regular users to admin status.

- **Security and Transaction Management:**  
  - Authentication, authorisation, and secure session management are implemented using Django’s built-in features.  
  - All changes occur within atomic database transactions to guarantee ACID properties.  

- **Remote Timestamp Service:**  
  - Integration with a Thrift-based remote timestamp service ensures reliable timing for transactions.  
  - The service runs in a separate daemon thread and is automatically started with the application.

- **Responsive User Interface:**  
  - Designed using Bootstrap 5 for a modern, responsive, and user-friendly experience.  


## Installation and Setup

### Prerequisites
- **Python 3.8 or higher**
- **Virtualenv** (recommended)
- **Git**

### Clone the Repository
```bash
git clone https://github.com/yourusername/online-payment-service.git
cd online-payment-service
 ```
### Create and Activate a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # For Windows: venv\Scripts\activate
```
### Install Dependencies
```bash
pip install -r requirements.txt
```
### Apply Database Migrations
```bash
python manage.py migrate
```
### Run the Development Server
```bash
python manage.py runserver 
 ```

## Usage

### For Regular Users
- **Registration:**  
  Go to `/webapps2025/register/signup/` to create an account.  
  The system converts a baseline of **750 GBP** to your chosen currency.
  
- **Login/Logout:**  
  Login at `/webapps2025/register/login/` and logout at `/webapps2025/register/logout/`.

- **Payments:**  
  Make payments at `/webapps2025/pay/make/`.  
  The system handles currency conversion and updates balances in both accounts.

- **Payment Requests:**  
  Request payments at `/webapps2025/pay/request/` and view pending requests at `/webapps2025/requests/`.

- **Transaction History:**  
  Review your transactions at `/webapps2025/pay/history/`.

### For Admin Users
- **Manage Users:**  
  View all users at `/webapps2025/admin/users/`.

- **Manage Transactions:**  
  View all transactions at `/webapps2025/admin/transactions/`.

- **Promote Users:**  
  Promote a user to admin with `/webapps2025/admin/make_admin/<user_id>/`.

### Additional Services
- **Currency Conversion API:**  
  `/conversion/<currency1>/<currency2>/<amount>/` provides RESTful conversion.

- **Remote Timestamp Service:**  
  Access a timestamp from the Thrift-based service at `/remote-timestamp/`.

## Credits
- [Django Documentation](https://docs.djangoproject.com/)
- [Bootstrap](https://getbootstrap.com/)

## License

This project is licensed under the MIT License - see the [Licence](LICENSE) file for details.
