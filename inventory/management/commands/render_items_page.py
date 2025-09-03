from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.urls import reverse

from inventory.views.items.list import ItemsListView


class Command(BaseCommand):
    help = "Render Items table page to /tmp for quick manual inspection."

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.create_user(
                username="devviewer",
                password="devviewer",
                is_staff=True,
                is_superuser=True,
            )

        rf = RequestFactory()

        req = rf.get(reverse("items_list"))
        req.user = user
        resp = ItemsListView.as_view()(req)
        path = "/tmp/items_table.html"
        with open(path, "wb") as f:
            f.write(resp.rendered_content.encode("utf-8"))
        self.stdout.write(self.style.SUCCESS(f"Rendered items table to {path}"))
