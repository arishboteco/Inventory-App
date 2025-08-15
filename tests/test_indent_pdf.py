from types import SimpleNamespace

from inventory.indent_pdf import generate_indent_pdf


def test_generate_indent_pdf_basic():
    indent = SimpleNamespace(mrn="MRN1", pk=1, requested_by="Alice")
    item = SimpleNamespace(item=SimpleNamespace(name="Sugar"), requested_qty=5)
    pdf = generate_indent_pdf(indent, [item])
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100
