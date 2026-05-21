from __future__ import annotations

from datetime import date, timedelta

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from inventory.services.variance_service import build_variance_report


def _parse_date(raw_value: str, fallback: date) -> date:
    raw = (raw_value or "").strip()
    if not raw:
        return fallback
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return fallback


def variance_report(request):
    today = timezone.localdate()
    default_start = today - timedelta(days=6)
    start_date = _parse_date(request.GET.get("start_date", ""), default_start)
    end_date = _parse_date(request.GET.get("end_date", ""), today)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    show_mode = (request.GET.get("show") or "all").strip().lower()
    allowed_modes = {"all", "leakage_only", "unmapped_only"}
    if show_mode not in allowed_modes:
        show_mode = "all"

    report = build_variance_report(start_date, end_date)
    rows = report["rows"]
    if show_mode == "leakage_only":
        rows = [row for row in rows if row.variance_value > 0]
    elif show_mode == "unmapped_only":
        rows = [row for row in rows if row.is_unmapped_candidate]

    paginator = Paginator(rows, 30)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "inventory/recovery/variance_report.html",
        {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "show_mode": show_mode,
            "summary": report["summary"],
            "page_obj": page_obj,
            "visible_count": len(rows),
        },
    )
