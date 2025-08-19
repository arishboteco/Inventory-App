from __future__ import annotations
from typing import Iterable

from fpdf import FPDF
from fpdf.enums import XPos, YPos

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
    pdf.set_font("Helvetica", size=12)
    title = f"Indent {indent.mrn or indent.pk}"
    pdf.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if getattr(indent, "requested_by", None):
        pdf.cell(
            0,
            10,
            f"Requested by: {indent.requested_by}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    pdf.ln(4)
    # Table header
    pdf.set_font("Helvetica", size=10)
    pdf.cell(120, 8, "Item", border=1)
    pdf.cell(30, 8, "Qty", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    for line in items:
        name = getattr(
            getattr(line, "item", None),
            "name",
            str(getattr(line, "item", "")),
        )
        qty = getattr(line, "requested_qty", "")
        pdf.cell(120, 8, str(name), border=1)
        pdf.cell(30, 8, str(qty), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())
