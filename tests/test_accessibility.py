import re

import pytest
from django.template.loader import render_to_string
from django.test import RequestFactory


def find_unlabeled_role_imgs(html: str):
    pattern = re.compile(r"<[^>]*role=\"img\"[^>]*>")
    tags = pattern.findall(html)
    unlabeled = []
    for tag in tags:
        if not any(
            attr in tag
            for attr in ["aria-label", "aria-labelledby", "aria-hidden", "title"]
        ):
            unlabeled.append(tag)
    return unlabeled


def assert_no_unlabeled_role_img(html: str):
    unlabeled = find_unlabeled_role_imgs(html)
    assert not unlabeled, f"Unlabeled role=img elements found: {unlabeled}"


@pytest.mark.django_db
def test_top_nav_has_no_unlabeled_role_img(django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    rf = RequestFactory()
    request = rf.get("/")
    request.user = user
    html = render_to_string("components/top_nav.html", request=request)
    assert_no_unlabeled_role_img(html)


@pytest.mark.django_db
def test_kpi_card_icons_are_hidden():
    html = render_to_string(
        "components/kpi_card.html",
        {"icon": "plus", "color": "blue", "label": "Items", "value": 5},
    )
    assert_no_unlabeled_role_img(html)


def test_action_menu_icons_are_hidden():
    html = render_to_string(
        "components/action_menu.html",
        {"view_url": "#", "edit_url": "#", "approve_url": "#"},
    )
    assert_no_unlabeled_role_img(html)
