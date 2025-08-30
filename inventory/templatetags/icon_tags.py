"""Template tags for rendering Heroicons SVGs."""
from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def icon(name, css_class="w-5 h-5", variant="outline", size=24, aria_label=None):
    """Return an SVG icon from the Heroicons set.

    Args:
        name: Icon filename without extension.
        css_class: CSS classes applied to the SVG element.
        variant: "outline" or "solid" style from Heroicons.
        size: Icon size directory (20 or 24).
        aria_label: Optional aria-label for accessibility.
    """
    variant_str = variant.encode("utf-8").decode("utf-8")
    base_dir = Path(settings.BASE_DIR) / "node_modules" / "heroicons" / str(size) / variant_str
    svg_path = base_dir / f"{name}.svg"
    if not svg_path.exists():
        svg_path = base_dir / "question-mark-circle.svg"
        if not svg_path.exists():
            return ""
    svg = svg_path.read_text()
    attrs = f'class="{css_class}" role="img"'
    if aria_label:
        attrs += f' aria-label="{aria_label}"'
    svg = svg.replace("<svg", f"<svg {attrs}", 1)
    return mark_safe(svg)
