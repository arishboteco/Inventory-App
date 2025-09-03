from collections import namedtuple

from django.template import Context, Template

Category = namedtuple("Category", ["category", "sub_category"])
Item = namedtuple("Item", ["category"])


def render(template_string, **context):
    template = Template(template_string)
    return template.render(Context(context)).strip()


def test_format_category_with_subcategory():
    item = Item(Category("Food", "Fruit"))
    output = render("{% load category_tags %}{% format_category item %}", item=item)
    assert output == "Food → Fruit"


def test_format_category_placeholder_when_missing():
    item = Item(None)
    output = render(
        "{% load category_tags %}{% format_category item True %}", item=item
    )
    assert "—" in output
