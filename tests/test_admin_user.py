import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_admin_user_exists_and_can_login(client):
    User = get_user_model()
    assert User.objects.filter(username="admin").exists()
    client.logout()
    assert client.login(username="admin", password="admin")
