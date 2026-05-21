import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_logout_post_clears_authenticated_session(client, django_user_model):
    user = django_user_model.objects.create_user(username="logout_user", password="pw")
    client.force_login(user)

    assert "_auth_user_id" in client.session

    response = client.post(reverse("logout"))

    assert response.status_code in {200, 302}
    assert "_auth_user_id" not in client.session
