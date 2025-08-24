"""Shared helpers for filtering, sorting, pagination and CSV export.

These utilities centralise common logic used by list views across the
application (items, suppliers, goods received notes and purchase orders).
They operate on Django QuerySets and standard ``request.GET`` parameters to
produce filtered and sorted querysets, paginated results and CSV exports.
"""

from __future__ import annotations

import csv
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence, Tuple

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse

FilterMapping = Mapping[str, str]


def apply_filters_sort(
    request: HttpRequest,
    qs: QuerySet,
    *,
    search_fields: Sequence[str] | None = None,
    filter_fields: FilterMapping | None = None,
    allowed_sorts: Iterable[str] | None = None,
    default_sort: str = "id",
    default_direction: str = "asc",
) -> Tuple[QuerySet, Dict[str, Any]]:
    """Return queryset filtered and sorted based on ``request`` parameters.

    Parameters
    ----------
    request:
        The current request whose ``GET`` parameters are inspected.
    qs:
        Base queryset to operate on.
    search_fields:
        Iterable of field names for ``q`` full-text search using
        ``icontains`` lookups.
    filter_fields:
        Mapping of GET parameter names to ORM field lookups for exact matching
        (e.g. ``{"status": "status", "start": "created__gte"}``).
    allowed_sorts:
        Iterable of field names allowed for sorting.
    default_sort:
        Field to sort by if the provided value is invalid or missing.
    default_direction:
        ``"asc"`` or ``"desc"`` for default order direction.

    Returns
    -------
    Tuple[QuerySet, Dict[str, Any]]
        The filtered and sorted queryset plus a dictionary of the resolved
        parameters that can be fed back into templates.
    """

    params: Dict[str, Any] = {}

    if search_fields:
        q = (request.GET.get("q") or "").strip()
        if q:
            conditions = Q()
            for field in search_fields:
                conditions |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(conditions)
        params["q"] = q

    for param, lookup in (filter_fields or {}).items():
        value = (request.GET.get(param) or "").strip()
        if value:
            qs = qs.filter(**{lookup: value})
        params[param] = value

    allowed_sorts = set(allowed_sorts or [])
    allowed_sorts.add(default_sort)
    sort = (request.GET.get("sort") or default_sort).strip()
    direction = (request.GET.get("direction") or default_direction).strip().lower()
    if sort not in allowed_sorts:
        sort = default_sort
    if direction not in {"asc", "desc"}:
        direction = default_direction
    ordering = sort if direction == "asc" else f"-{sort}"
    qs = qs.order_by(ordering)
    params.update({"sort": sort, "direction": direction})
    return qs, params


def paginate(
    request: HttpRequest,
    qs: QuerySet,
    *,
    default_page_size: int = 25,
    page_param: str = "page",
    page_size_param: str = "page_size",
):
    """Paginate ``qs`` based on ``request`` parameters."""

    try:
        per_page = int(request.GET.get(page_size_param, default_page_size))
    except (TypeError, ValueError):
        per_page = default_page_size
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get(page_param)
    page_obj = paginator.get_page(page_number)
    return page_obj, per_page


def export_as_csv(
    qs: Iterable[Any],
    headers: Sequence[str],
    row_builder: Callable[[Any], Sequence[Any]],
    filename: str,
) -> HttpResponse:
    """Return ``HttpResponse`` with ``qs`` exported as CSV."""

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f"attachment; filename={filename}"
    writer = csv.writer(response)
    writer.writerow(list(headers))
    for obj in qs:
        writer.writerow(list(row_builder(obj)))
    return response


def build_querystring(
    request: HttpRequest, exclude: Sequence[str] | None = None
) -> str:
    """Return querystring for ``request.GET`` excluding certain keys."""

    params = request.GET.copy()
    for key in exclude or ("page",):
        params.pop(key, None)
    return params.urlencode()
