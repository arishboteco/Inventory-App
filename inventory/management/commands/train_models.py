from django.core.management.base import BaseCommand

from inventory.services import ml


class Command(BaseCommand):
    """Train forecasting and ABC models from stock transaction data."""

    help = "Update forecasting models and classifications."

    def handle(self, *args, **options):
        forecasts = ml.train_models()
        classifications = ml.abc_classification()
        self.stdout.write(
            self.style.SUCCESS(
                f"Trained {len(forecasts)} models and classified {len(classifications)} items."
            )
        )
