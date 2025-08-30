import subprocess
from shutil import which

from django.contrib.staticfiles.management.commands.collectstatic import (
    Command as CollectstaticCommand,
)


class Command(CollectstaticCommand):
    """Collect static files and build frontend assets."""

    def handle(self, *args, **options):
        package_manager = "npm" if which("npm") else "yarn" if which("yarn") else None
        if package_manager:
            self.stdout.write("Building frontend assets...")
            subprocess.run([package_manager, "run", "build"], check=True)
        else:
            self.stdout.write(self.style.WARNING("npm/yarn not found. Skipping frontend build."))
        super().handle(*args, **options)
