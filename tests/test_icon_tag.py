from django.template import Context, Template


def test_icon_renders_svg():
    template = Template("{% load icon_tags %}{% icon 'plus' %}")
    rendered = template.render(Context())
    assert "<svg" in rendered and "</svg>" in rendered


def test_icon_fallback():
    template = Template("{% load icon_tags %}{% icon 'nonexistent-icon' %}")
    rendered = template.render(Context())
    assert "<svg" in rendered


def test_icon_without_aria_label_is_hidden():
    template = Template("{% load icon_tags %}{% icon 'plus' %}")
    rendered = template.render(Context())
    assert 'aria-hidden="true"' in rendered
    assert "aria-label" not in rendered


def test_icon_with_aria_label_includes_label():
    template = Template("{% load icon_tags %}{% icon 'plus' aria_label='Add item' %}")
    rendered = template.render(Context())
    assert 'aria-label="Add item"' in rendered
    assert "aria-hidden" not in rendered
