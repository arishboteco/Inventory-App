from pathlib import Path


def read_template(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_filter_bar_exposes_clear_filters_control():
    content = read_template("templates/components/filter_bar.html")

    assert "Clear filters" in content
    assert 'aria-label="Clear all table filters"' in content
    assert 'title="Clear all table filters"' in content


def test_multi_filter_lists_pass_reset_href_to_shared_filter_bar():
    templates = [
        "templates/inventory/indents_list.html",
        "templates/inventory/suppliers_list.html",
        "templates/inventory/purchase_orders/list.html",
        "templates/inventory/recipes/list.html",
    ]

    for template_path in templates:
        content = read_template(template_path)
        assert "reset_href=" in content, f"{template_path} must wire clear filters"


def test_purchase_order_action_icons_have_labels_and_tooltips():
    table = read_template("templates/inventory/purchase_orders/_table.html")
    cards = read_template("templates/inventory/purchase_orders/_cards.html")

    for content in [table, cards]:
        assert 'title="Edit purchase order' in content
        assert 'aria-label="Edit purchase order' in content
        assert 'title="Receive goods for purchase order' in content
        assert 'aria-label="Receive goods for purchase order' in content


def test_recipe_action_icons_have_labels_and_tooltips():
    content = read_template("templates/inventory/recipes/_recipes_table.html")

    for label in [
        "View recipe",
        "Edit recipe",
        "Open recipe details",
        "Delete recipe",
    ]:
        assert f'title="{label}' in content
        assert f'aria-label="{label}' in content


def test_column_menu_icon_buttons_have_labels_and_tooltips():
    templates = [
        "templates/inventory/_suppliers_table.html",
        "templates/inventory/_indents_table.html",
        "templates/inventory/purchase_orders/_table.html",
    ]

    for template_path in templates:
        content = read_template(template_path)
        assert 'aria-label="Show or hide table columns"' in content
        assert 'title="Show or hide table columns"' in content
