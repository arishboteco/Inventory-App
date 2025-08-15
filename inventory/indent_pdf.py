from __future__ import annotations
from io import BytesIO
from typing import Iterable

from fpdf import FPDF

from .models import Indent, IndentItem


def generate_indent_pdf(indent: Indent, items: Iterable[IndentItem]) -> bytes:
    """Generate a simple PDF for an indent with its items.

    Parameters
    ----------
    indent: Indent instance
    items: Iterable of IndentItem instances

    Returns
    -------
    bytes: PDF content
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    title = f"Indent {indent.mrn or indent.pk}"
    pdf.cell(0, 10, title, ln=True)
    if getattr(indent, "requested_by", None):
        pdf.cell(0, 10, f"Requested by: {indent.requested_by}", ln=True)
    pdf.ln(4)
    # Table header
    pdf.set_font("Arial", size=10)
    pdf.cell(120, 8, "Item", border=1)
    pdf.cell(30, 8, "Qty", border=1, ln=True)
    for line in items:
        name = getattr(getattr(line, "item", None), "name", str(getattr(line, "item", "")))
        qty = getattr(line, "requested_qty", "")
        pdf.cell(120, 8, str(name), border=1)
        pdf.cell(30, 8, str(qty), border=1, ln=True)
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
