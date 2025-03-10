from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model

class RegisterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'register'

    def ready(self):
        User = get_user_model()

        def create_initial_admin(sender, **kwargs):
            if not User.objects.filter(username='admin1').exists():
                User.objects.create_superuser(username='admin1', email='', password='admin1')

        post_migrate.connect(create_initial_admin, sender=self)