"""
Management command to ensure a superuser exists for production deployment.
"""
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


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
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@inventory.app')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

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
