"""
Django management command to create a default superuser for production.
This will create a superuser with known credentials if none exists.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a default superuser for production if none exists"

    def handle(self, *args, **options):
        # Check if any superuser exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("✅ Superuser already exists"))
            return

        # Create default superuser with known credentials
        username = "admin"
        email = "admin@inventory.app"
        password = "admin123!"  # Simple password for testing

        try:
            User.objects.create_superuser(
                username=username, email=email, password=password
            )

            self.stdout.write(self.style.SUCCESS("✅ Default superuser created:"))
            self.stdout.write(f"   Username: {username}")
            self.stdout.write(f"   Password: {password}")
            self.stdout.write(f"   Email: {email}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to create superuser: {e}"))
