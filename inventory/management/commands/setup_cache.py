from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create cache table for database caching'

    def handle(self, *args, **options):
        try:
            call_command('createcachetable')
            self.stdout.write(
                self.style.SUCCESS('✅ Cache table created successfully!')
            )
        except Exception as e:
            # If cache table already exists or there's an error, that's okay
            self.stdout.write(
                self.style.WARNING(f'⚠️  Cache table creation: {e}')
            )
