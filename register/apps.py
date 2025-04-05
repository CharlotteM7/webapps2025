"""
App configuration for the 'register' app.

This module ensures that an initial superuser (admin1/admin1) is created
after migrations run if it does not already exist.
"""

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate

class RegisterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'register'

    def ready(self):
        User = get_user_model()

        def create_initial_admin(sender, **kwargs):
            """
            Signal handler to create an initial admin user after migrations.

            Args:
                sender: The model class that sent the signal.
                **kwargs: Additional keyword arguments.
            """
            if not User.objects.filter(username='admin1').exists():
                User.objects.create_superuser(username='admin1', email='', password='admin1')

        # Connect the create_initial_admin signal to post_migrate.
        post_migrate.connect(create_initial_admin, sender=self)
