"""Template tags for rendering Heroicons SVGs."""

from pathlib import Path

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


FALLBACK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="currentColor" stroke-width="1.5">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M12 16.5h.008v.008H12v-.008Zm0-2.258a2.25 2.25 0 0 1 '
    '1.516-2.132 2.25 2.25 0 1 0-3.032-2.117" />'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M12 3.75a8.25 8.25 0 1 0 0 16.5 8.25 8.25 0 0 0 0-16.5Z" />'
    "</svg>"
)


@register.simple_tag
def icon(name, css_class="w-5 h-5", variant="outline", size=24, aria_label=None):
    """Return an SVG icon from the Heroicons set.

    Args:
        name: Icon filename without extension.
        css_class: CSS classes applied to the SVG element.
        variant: "outline" or "solid" style from Heroicons.
        size: Icon size directory (20 or 24).
        aria_label: Optional aria-label for accessibility. If omitted, the icon
            is marked ``aria-hidden="true"`` so screen readers ignore it.
    """
    variant_str = variant.encode("utf-8").decode("utf-8")
    base_dir = (
        Path(settings.BASE_DIR) / "node_modules" / "heroicons" / str(size) / variant_str
    )
    svg_path = base_dir / f"{name}.svg"
    if not svg_path.exists():
        svg_path = base_dir / "question-mark-circle.svg"
    if svg_path.exists():
        svg = svg_path.read_text().replace(' aria-hidden="true"', "")
    else:
        svg = FALLBACK_SVG
    attrs = f'class="{css_class}" role="img"'
    if aria_label:
        attrs += f' aria-label="{aria_label}"'
    else:
        attrs += ' aria-hidden="true"'
    svg = svg.replace("<svg", f"<svg {attrs}", 1)
    return mark_safe(svg)
