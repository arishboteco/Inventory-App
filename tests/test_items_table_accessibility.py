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


def test_inline_item_create_marks_required_fields():
    content = Path("templates/inventory/_item_create_bare.html").read_text()
    assert "Name<span" in content
    assert "Unit<span" in content


def test_items_search_has_placeholder_and_reset_control():
    content = Path("templates/inventory/items_list.html").read_text()
    assert "Search items by nan" not in content
    assert "Search items..." in content or "Search items…" in content
    filter_bar = Path("templates/components/filter_bar.html").read_text()
    assert "Reset" in filter_bar


def test_no_dropdown_filter_controls_present():
    content = Path("templates/inventory/_items_table.html").read_text()
    # Assert removed filter triggers are not present anymore
    assert "data-filter-btn" not in content
    for label in [
        "Filter Name",
        "Filter Category",
        "Filter Unit",
        "Filter Stock Status",
        "Filter Departments",
        "Filter Status",
    ]:
        assert f'aria-label="{label}"' not in content
