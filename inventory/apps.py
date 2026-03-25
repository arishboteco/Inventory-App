import os
import threading
import time

import requests
from django.apps import AppConfig


def _keep_alive():
    """Ping the app every 5 minutes so Render never lets it sleep."""
    url = os.environ.get("KEEP_ALIVE_URL", "https://inventory-app-kguo.onrender.com/")
    while True:
        time.sleep(300)  # wait first so startup completes before first ping
        try:
            resp = requests.get(url, timeout=10)
            print(f"[keep-alive] {resp.status_code} {url}")
        except Exception as exc:
            print(f"[keep-alive] error: {exc}")


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"

    def ready(self):
        # Only start the keep-alive thread in the main web process,
        # not during manage.py commands (migrate, collectstatic, etc.)
        if os.environ.get("RUN_MAIN") != "true" and not os.environ.get(
            "DISABLE_KEEP_ALIVE"
        ):
            t = threading.Thread(target=_keep_alive, daemon=True, name="keep-alive")
            t.start()
