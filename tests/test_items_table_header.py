import re
from pathlib import Path


def test_items_table_header_top_zero_and_structure():
    tpl = Path("templates/inventory/_items_table.html").read_text()
    header = re.search(r"<thead.*?</thead>", tpl, re.DOTALL).group(0)
    css = Path("static/src/app.css").read_text()
    has_top_zero_class = "top-0" in header
    has_top_zero_css = (
        re.search(r"\.table-sticky\s+thead\s+th\s*{[^}]*top:\s*0", css) is not None
        or re.search(r"\.table-sticky\s+thead\s+th\s*{[^}]*@apply[^;]*top-0", css)
        is not None
    )
    assert has_top_zero_class or has_top_zero_css

    table = re.search(r"<table.*?</table>", tpl, re.DOTALL).group(0)
    assert re.search(r"<table[^>]*>\s*<thead", table)
    assert not re.search(r"<table[^>]*>\s*<tr", table)
    assert "data-sortable" in table

    assert 'data-col="rop"' not in tpl

    # Only inspect the first header row for column metadata
    first_row = re.search(r"<tr>.*?</tr>", header, re.DOTALL).group(0)
    ths = re.findall(r"<th[^>]*>.*?</th>", first_row, re.DOTALL)
    assert "data-sort" not in ths[0]
    assert "data-sort" not in ths[-1]
    for i, th in enumerate(ths[1:-1], start=1):
        assert f'data-sort="col{i}"' in th
        assert 'aria-sort="none"' in th


def test_header_filter_control_partial_exists():
    partial = Path("templates/components/header_filter_control.html").read_text()
    for attr in ["hx-get", "hx-target", "hx-include", "hx-indicator"]:
        assert attr in partial
    tpl = Path("templates/inventory/_items_table.html").read_text()
    assert "components/header_filter_control.html" in tpl
