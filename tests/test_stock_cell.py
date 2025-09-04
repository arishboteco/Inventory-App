import re
from types import SimpleNamespace

import pytest
from django.template.loader import render_to_string


@pytest.mark.django_db
def test_stock_cell_zero_renders_without_template_markers(item_factory):
    item = item_factory(current_stock=0)
    page_obj = SimpleNamespace(object_list=[item])
    html = render_to_string("inventory/_items_table.html", {"page_obj": page_obj})
    match = re.search(r'<td data-col="stock"[^>]*>(.*?)</td>', html, re.DOTALL)
    assert match is not None
    stock_content = match.group(1).strip()
    assert stock_content == "0"
    assert "{{" not in stock_content
    assert "{%" not in stock_content
