import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Creates a superuser automatically from environment variables if not already exists"

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.getenv("ADMIN_EMAIL", "admin@superkidz.com").strip()
        password = os.getenv("ADMIN_PASSWORD")
        first_name = os.getenv("ADMIN_FIRST_NAME", "Super").strip()
        last_name = os.getenv("ADMIN_LAST_NAME", "Admin").strip()

        if not password:
            self.stdout.write("No ADMIN_PASSWORD provided, skipping superuser creation.")
            return

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' created successfully!"))
        else:
            self.stdout.write(f"Superuser '{email}' already exists.")
