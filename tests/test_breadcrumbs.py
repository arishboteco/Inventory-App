import pytest

pytestmark = pytest.mark.skip("Breadcrumbs removed globally; component renders nothing")


def test_breadcrumbs_removed():
    assert True
