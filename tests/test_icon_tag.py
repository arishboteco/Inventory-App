from django.template import Context, Template


def test_icon_renders_svg():
    template = Template("{% load icon_tags %}{% icon 'plus' %}")
    rendered = template.render(Context())
    assert '<svg' in rendered and '</svg>' in rendered


def test_icon_fallback():
    template = Template("{% load icon_tags %}{% icon 'nonexistent-icon' %}")
    rendered = template.render(Context())
    assert '<svg' in rendered
