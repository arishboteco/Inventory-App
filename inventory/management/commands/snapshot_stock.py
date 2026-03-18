"""Management command to take a daily stock snapshot.

Usage:
    python manage.py snapshot_stock

Schedule daily at midnight via Django Q or cron:
    Schedule.objects.create(
        func='inventory.services.snapshot_service.take_daily_stock_snapshot',
        schedule_type=Schedule.DAILY,
        next_run=midnight_today,
    )
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Take a daily stock snapshot for all active items"

    def handle(self, *args, **kwargs):
        from inventory.services.snapshot_service import take_daily_stock_snapshot

        count = take_daily_stock_snapshot()
        self.stdout.write(
            self.style.SUCCESS(f"Stock snapshot taken: {count} items recorded.")
        )
