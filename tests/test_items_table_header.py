import re
from pathlib import Path


def test_items_table_header_has_no_top_zero():
    content = Path('templates/inventory/_items_table.html').read_text()
    header = re.search(r'<thead.*?</thead>', content, re.DOTALL).group(0)
    assert 'top-0' not in header
