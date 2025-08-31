"""Django management command to reset admin password using configured value."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.config import settings


class Command(BaseCommand):
    help = 'Reset admin password to environment variable or fallback'

    def handle(self, *args, **options):
        try:
            # Get password from configuration or use fallback
            new_password = settings.django_superuser_password or "admin123!"

            # Find admin user
            admin_user = User.objects.filter(username='admin').first()

            if not admin_user:
                self.stdout.write(
                    self.style.ERROR('❌ No admin user found')
                )
                return

            # Reset password
            admin_user.set_password(new_password)
            admin_user.save()

            self.stdout.write(
                self.style.SUCCESS('✅ Admin password reset successfully!')
            )
            self.stdout.write('   Username: admin')
            self.stdout.write(
                f'   Password: {"*" * len(new_password)} '
                f'({len(new_password)} chars)'
            )
            self.stdout.write(f'   Email: {admin_user.email}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to reset password: {e}')
            )
