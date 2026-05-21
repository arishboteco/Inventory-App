from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_modal_root_and_content_are_scrollable(client):
    response = client.get(reverse("root"))
    assert response.status_code == 200
    html = response.content.decode()
    soup = BeautifulSoup(html, "html.parser")

    modal_root = soup.find(id="modal-root")
    assert modal_root is not None
    root_classes = modal_root.get("class", [])
    assert "overflow-y-auto" in root_classes

    modal_content = soup.find(id="modal-content")
    assert modal_content is not None
    content_classes = modal_content.get("class", [])
    assert "max-h-[calc(100vh-2rem)]" in content_classes
    assert "overflow-y-auto" in content_classes
    assert "overscroll-contain" in content_classes
