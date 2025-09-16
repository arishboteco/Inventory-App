from __future__ import annotations

from typing import Iterable

from fpdf import FPDF

from .models import Indent, IndentItem
from .services.units_service import UnitsService


class IndentPDF(FPDF):
    def header(self):
        # Centered title matching sample
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 10, "Material Indent Request", align="C", ln=1)
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", size=9)
        self.set_text_color(120, 120, 120)
        page_str = (
            f"Page {self.page_no()}/{getattr(self, 'alias_nb_pages_str', '{nb}')}"
        )
        self.cell(0, 10, page_str, align="R")


def _text(
    pdf: FPDF, label: str, value: str, w_label=40, w_value=None, ln=1, align_value="L"
):
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(w_label, 7, f"{label}:")
    pdf.set_font("Helvetica", size=11)
    if w_value is None:
        pdf.cell(0, 7, value, ln=ln, align=align_value)
    else:
        pdf.cell(w_value, 7, value, ln=ln, align=align_value)


def _table_header(pdf: FPDF, col_widths):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_draw_color(160, 160, 160)
    headers = ["Item", "Qty", "Unit", "Note"]
    for h, w in zip(headers, col_widths):
        pdf.cell(w, 9, h, border=1, align="C", fill=True)
    pdf.ln(9)


def _table_row(pdf: FPDF, name: str, qty: str, unit: str, note: str, col_widths):
    pdf.set_font("Helvetica", size=11)
    pdf.set_draw_color(200, 200, 200)
    # Item name (may wrap)
    x0 = pdf.get_x()
    y0 = pdf.get_y()
    pdf.multi_cell(col_widths[0], 8, name, border=1)
    h = pdf.get_y() - y0
    pdf.set_xy(x0 + col_widths[0], y0)
    pdf.cell(col_widths[1], h, str(qty), border=1, align="R")
    pdf.cell(col_widths[2], h, unit or "", border=1, align="C")
    pdf.cell(col_widths[3], h, note or "-", border=1)
    # Move cursor to start of next line below the tallest cell height
    pdf.set_xy(pdf.l_margin, y0 + h)


def _section_row(pdf: FPDF, text: str, page_width: float, bold: bool = True):
    pdf.set_draw_color(160, 160, 160)
    pdf.set_font("Helvetica", "B" if bold else "", 11)
    # Use multi_cell to avoid clipping long labels
    pdf.multi_cell(page_width, 9, text, border=1)


def _kv_at(
    pdf: FPDF,
    x: float,
    y: float,
    label: str,
    value: str,
    w_label: float,
    w_value: float,
    h: float = 7,
):
    pdf.set_xy(x, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(w_label, h, f"{label}:")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(w_value, h, str(value))


def generate_indent_pdf(indent: Indent, items: Iterable[IndentItem]) -> bytes:
    """Generate a clean, printable PDF for an indent with details and items table."""
    pdf = IndentPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # MRN and meta details in two columns
    mrn = getattr(indent, "mrn", None) or str(getattr(indent, "pk", ""))
    req_by = getattr(indent, "requested_by", "") or "-"
    dept_obj = getattr(indent, "department", None)
    dept = getattr(dept_obj, "name", None) or str(dept_obj or "-")
    date_required = getattr(indent, "date_required", "") or "-"
    notes = getattr(indent, "notes", "") or ""

    # Two-column baseline layout with absolute positioning to avoid overlap
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_width = page_width / 2
    left_x = pdf.l_margin
    right_x = left_x + col_width
    y_start = pdf.get_y()
    row_h = 8
    # Left column rows
    _kv_at(pdf, left_x, y_start, "MRN", str(mrn), 30, col_width - 30, h=row_h)
    _kv_at(
        pdf,
        left_x,
        y_start + row_h,
        "Department",
        str(dept),
        30,
        col_width - 30,
        h=row_h,
    )
    # Right column rows
    _kv_at(
        pdf, right_x, y_start, "Requested By", str(req_by), 35, col_width - 35, h=row_h
    )
    _kv_at(
        pdf,
        right_x,
        y_start + row_h,
        "Date Required",
        str(date_required),
        35,
        col_width - 35,
        h=row_h,
    )
    # Advance below the tallest row-block
    pdf.set_y(y_start + (row_h * 2))
    if notes:
        pdf.ln(2)
        _text(pdf, "Notes", str(notes))

    # Extra breathing room before the table to avoid overlap with borders
    pdf.ln(10)

    # Items table (Item, Qty, Unit, Note) with category grouping
    page_width = pdf.w - pdf.l_margin - pdf.r_margin
    col_widths = [
        page_width * 0.53,
        page_width * 0.12,
        page_width * 0.12,
        page_width * 0.23,
    ]
    _table_header(pdf, col_widths)

    if not items:
        pdf.set_font("Helvetica", size=11)
        pdf.cell(0, 8, "No items.", ln=1)
    else:
        # Group by Category and Sub-Category like the sample
        def cat_of(it):
            cat = getattr(getattr(it, "item", None), "category", None)
            main = getattr(cat, "category", None) or "Unknown"
            sub = getattr(cat, "sub_category", None) or ""
            return str(main), str(sub)

        grouped = {}
        for line in items:
            main, sub = cat_of(line)
            grouped.setdefault(main, {}).setdefault(sub, []).append(line)

        for main in sorted(grouped.keys()):
            # Category row
            if pdf.get_y() > (pdf.h - pdf.b_margin - 25):
                pdf.add_page()
                _table_header(pdf, col_widths)
            _section_row(pdf, f"Category: {main}", page_width)
            pdf.ln(1)
            for sub in sorted(grouped[main].keys()):
                if sub:
                    if pdf.get_y() > (pdf.h - pdf.b_margin - 20):
                        pdf.add_page()
                        _table_header(pdf, col_widths)
                    pdf.set_font("Helvetica", "B", 11)
                    pdf.cell(page_width, 8, f"  Sub-Category: {sub}", ln=1, border="")
                    pdf.ln(1)
                for line in grouped[main][sub]:
                    name = getattr(getattr(line, "item", None), "name", None)
                    if name is None:
                        name = str(getattr(line, "item", ""))
                    qty_raw = getattr(line, "requested_qty", "")
                    try:
                        qty_val = float(qty_raw)
                        qty = f"{qty_val:.3f}"
                    except Exception:
                        qty = str(qty_raw)
                    unit_display = ""
                    try:
                        unit_id = getattr(getattr(line, "item", None), "unit_id", None)
                        if unit_id:
                            unit_display = (
                                UnitsService.get_purchase_unit_display(int(unit_id))
                                or ""
                            )
                    except Exception:
                        unit_display = ""
                    note = getattr(line, "notes", "") or "-"
                    if pdf.get_y() > (pdf.h - pdf.b_margin - 20):
                        pdf.add_page()
                        _table_header(pdf, col_widths)
                    _table_row(pdf, str(name), qty, unit_display, str(note), col_widths)

    # Signature block
    pdf.ln(10)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(page_width / 2, 6, "Requested By: ______________________", ln=0)
    pdf.cell(page_width / 2, 6, "Approved By:  ______________________", ln=1, align="R")

    return bytes(pdf.output())
