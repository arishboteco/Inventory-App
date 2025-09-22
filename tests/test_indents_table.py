import pytest
from django.urls import reverse

from inventory.models import Department, Indent


@pytest.mark.django_db
def test_indents_table_prefetches_department(client, django_assert_num_queries):
    """The indents table should not issue per-row department queries."""

    dept_a = Department.objects.create(name="Logistics")
    dept_b = Department.objects.create(name="Procurement")

    indents = [
        Indent(mrn=f"MRN-{idx}", department=dept)
        for idx, dept in enumerate([dept_a, dept_b, dept_a, dept_b], start=1)
    ]
    Indent.objects.bulk_create(indents)

    url = reverse("indents_table")

    with django_assert_num_queries(3):
        response = client.get(url)

    assert response.status_code == 200
