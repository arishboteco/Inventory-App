"""Management command to ensure a superuser exists for production deployment."""

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.config import settings as app_settings


class Command(BaseCommand):
    help = 'Ensure a superuser exists for production deployment'

    def handle(self, *args, **options):
        # Only run this in production
        if not settings.DEBUG:
            # Check if any superuser exists
            if User.objects.filter(is_superuser=True).exists():
                self.stdout.write(
                    self.style.SUCCESS('✅ Superuser already exists')
                )
                return

            # Create superuser with environment variables
            username = app_settings.django_superuser_username
            email = app_settings.django_superuser_email
            password = app_settings.django_superuser_password

            if not password:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  No DJANGO_SUPERUSER_PASSWORD set, '
                        'skipping superuser creation'
                    )
                )
                return

            # Create the superuser
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )

            self.stdout.write(
                self.style.SUCCESS(f'✅ Superuser "{username}" created successfully')
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  This command only runs in production (DEBUG=False)'
                )
            )
