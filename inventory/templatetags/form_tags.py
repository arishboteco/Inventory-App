from django import template

register = template.Library()


@register.filter
def add_class(field, css_class: str) -> str:
    """Add CSS classes to a form field's widget."""
    if not hasattr(field, 'field'):
        # If it's not a form field, return it as-is
        return field
    existing = field.field.widget.attrs.get("class", "")
    classes = f"{existing} {css_class}".strip()
    return field.as_widget(attrs={"class": classes})


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
