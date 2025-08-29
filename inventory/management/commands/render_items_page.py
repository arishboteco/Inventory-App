from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.urls import reverse

from inventory.views.items import ItemsListView


class Command(BaseCommand):
    help = "Render Items pages (cards and table) to /tmp for quick manual inspection."

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

        # Cards layout
        req_cards = rf.get(reverse("items_list"))
        req_cards.user = user
        resp_cards = ItemsListView.as_view()(req_cards)
        path_cards = "/tmp/items_cards.html"
        with open(path_cards, "wb") as f:
            f.write(resp_cards.rendered_content.encode("utf-8"))
        self.stdout.write(self.style.SUCCESS(f"Rendered cards layout to {path_cards}"))

        # Table layout
        req_table = rf.get(f"{reverse('items_list')}?layout=table")
        req_table.user = user
        resp_table = ItemsListView.as_view()(req_table)
        path_table = "/tmp/items_table.html"
        with open(path_table, "wb") as f:
            f.write(resp_table.rendered_content.encode("utf-8"))
        self.stdout.write(self.style.SUCCESS(f"Rendered table layout to {path_table}"))

