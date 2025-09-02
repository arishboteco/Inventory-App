from django import template
from django.utils.html import conditional_escape, format_html

register = template.Library()


@register.simple_tag
def format_category(item, show_placeholder=False):
    """Return a safe "Category → Subcategory" string for an item.

    If the item has no category and ``show_placeholder`` is True, a muted dash is
    returned. When ``show_placeholder`` is False, an empty string is returned in
    this case. Values are escaped to prevent HTML injection.
    """
    category_obj = getattr(item, "category", None)
    if not category_obj:
        if show_placeholder:
            return format_html('<span class="text-gray-400">—</span>')
        return ""

    category = conditional_escape(getattr(category_obj, "category", ""))
    subcategory = getattr(category_obj, "sub_category", "")
    if subcategory:
        subcategory = conditional_escape(subcategory)
        return format_html("{} → {}", category, subcategory)
    return category
