import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import RequestFactory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug login functionality step by step'

    def handle(self, *args, **options):
        self.stdout.write('🔍 Starting Login Debug Session...\n')

        # Test database connection
        self.stdout.write('📊 Testing Database Connection...')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Database connection: OK (result: {result})'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Database connection failed: {e}')
            )
            return

        # Check admin user exists
        self.stdout.write('\n👤 Checking Admin User...')
        try:
            admin_user = User.objects.get(username='admin')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Admin user found: {admin_user.username}'
                )
            )
            self.stdout.write(f'   - ID: {admin_user.id}')
            self.stdout.write(f'   - Email: {admin_user.email}')
            self.stdout.write(f'   - Is Active: {admin_user.is_active}')
            self.stdout.write(f'   - Is Staff: {admin_user.is_staff}')
            self.stdout.write(f'   - Is Superuser: {admin_user.is_superuser}')
            self.stdout.write(f'   - Last Login: {admin_user.last_login}')
            self.stdout.write(f'   - Date Joined: {admin_user.date_joined}')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Admin user not found'))
            return
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error checking admin user: {e}')
            )
            return

        # Test password authentication with environment variable
        self.stdout.write('\n🔐 Testing Password Authentication...')
        import os
        env_password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123!')
        self.stdout.write(
            f'   Using password from env: {"*" * len(env_password)}'
        )

        try:
            authenticated_user = authenticate(username='admin', password=env_password)
            if authenticated_user:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Authentication successful: '
                        f'{authenticated_user.username}'
                    )
                )
            else:
                self.stdout.write(self.style.ERROR('❌ Authentication failed'))

                # Try with the hardcoded password
                self.stdout.write('\n🔄 Trying with fallback password...')
                fallback_authenticated = authenticate(
                    username='admin', password='admin123!'
                )
                if fallback_authenticated:
                    self.stdout.write(
                        self.style.SUCCESS(
                            '✅ Fallback authentication successful'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            '❌ Fallback authentication also failed'
                        )
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Authentication error: {e}'))

        # Test password hash
        self.stdout.write('\n🔒 Password Hash Analysis...')
        try:
            self.stdout.write(
                f'   Current hash: {admin_user.password[:20]}...'
            )
            algo = (
                admin_user.password.split("$")[0]
                if "$" in admin_user.password
                else "Unknown"
            )
            self.stdout.write('   Hash algorithm: ' + algo)

            # Test if password needs to be reset
            if admin_user.check_password(env_password):
                self.stdout.write(
                    self.style.SUCCESS(
                        '✅ Password hash matches environment password'
                    )
                )
            elif admin_user.check_password('admin123!'):
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  Password hash matches fallback, '
                        'but not environment'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        '❌ Password hash matches neither password'
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Password hash check error: {e}'))

        # Test Django authentication backend
        self.stdout.write('\n🔧 Authentication Backend Test...')
        try:
            from django.conf import settings
            backends = settings.AUTHENTICATION_BACKENDS
            self.stdout.write(f'   Configured backends: {backends}')

            for backend_path in backends:
                try:
                    from django.utils.module_loading import import_string
                    # Import to validate; discard object to avoid unused var
                    import_string(backend_path)
                    self.stdout.write(
                        f'   ✅ Backend loaded: {backend_path}'
                    )
                except Exception as e:
                    self.stdout.write(
                        f'   ❌ Backend error: {backend_path} - {e}'
                    )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Backend test error: {e}'))

        # Test session framework
        self.stdout.write('\n📝 Session Framework Test...')
        try:
            from django.contrib.sessions.models import Session
            session_count = Session.objects.count()
            self.stdout.write(f'   Active sessions: {session_count}')

            # Test session creation
            factory = RequestFactory()
            request = factory.get('/')
            from django.contrib.sessions.middleware import SessionMiddleware
            middleware = SessionMiddleware(lambda r: None)
            middleware.process_request(request)
            request.session.save()
            self.stdout.write('   ✅ Session creation test: OK')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Session test error: {e}'))

        # Environment variables check
        self.stdout.write('\n🌍 Environment Variables Check...')
        important_vars = [
            'DJANGO_SETTINGS_MODULE',
            'DATABASE_URL',
            'DJANGO_SECRET_KEY',
            'DEBUG',
            'DJANGO_SUPERUSER_USERNAME',
            'DJANGO_SUPERUSER_PASSWORD',
        ]

        for var in important_vars:
            value = os.environ.get(var, 'NOT SET')
            if var in [
                'DJANGO_SECRET_KEY',
                'DATABASE_URL',
                'DJANGO_SUPERUSER_PASSWORD',
            ]:
                display_value = (
                    f"{'*' * min(10, len(value))}..."
                    if value != 'NOT SET'
                    else 'NOT SET'
                )
            else:
                display_value = value
            self.stdout.write(f'   {var}: {display_value}')

        self.stdout.write('\n🎯 Debug Session Complete!')
        self.stdout.write(
            '📝 Check the above output for any issues marked with ❌'
        )
