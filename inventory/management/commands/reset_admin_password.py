"""
Django management command to reset admin password to a known value.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Reset admin password to admin123!'

    def handle(self, *args, **options):
        try:
            # Find admin user
            admin_user = User.objects.filter(username='admin').first()
            
            if not admin_user:
                self.stdout.write(
                    self.style.ERROR('❌ No admin user found')
                )
                return
            
            # Reset password
            admin_user.set_password('admin123!')
            admin_user.save()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Admin password reset successfully!')
            )
            self.stdout.write(f'   Username: admin')
            self.stdout.write(f'   Password: admin123!')
            self.stdout.write(f'   Email: {admin_user.email}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to reset password: {e}')
            )
