import re
from pathlib import Path


def test_item_rows_have_striping_class():
    content = Path("templates/inventory/_items_table.html").read_text()
    assert "odd:bg-gray-50" in content


def test_column_menu_has_accessibility_attrs():
    content = Path("templates/inventory/items_list.html").read_text()
    btn_match = re.search(r"<button[^>]*data-col-menu-button[^>]*>", content)
    assert btn_match, "Column menu button not found"
    btn = btn_match.group(0)
    assert 'title="Show/Hide Columns"' in btn
    assert 'aria-controls="columns-menu"' in btn
    assert 'aria-label="Show/Hide Columns"' in btn


def test_filter_controls_have_labels_and_ids():
    content = Path("templates/inventory/_items_table.html").read_text()
    pairs = [
        ("filter-q", "Filter Name"),
        ("filter-category", "Filter Category"),
        ("filter-unit", "Filter Unit"),
        ("filter-stock-status", "Filter Stock Status"),
        ("filter-department", "Filter Departments"),
        ("filter-active", "Filter Status"),
    ]
    for fid, label in pairs:
        assert f'id="{fid}"' in content
        assert f'<label for="{fid}" class="sr-only">{label}</label>' in content
