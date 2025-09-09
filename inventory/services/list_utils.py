"""Shared helpers for filtering, sorting, pagination and CSV export.

These utilities centralise common logic used by list views across the
application (items, suppliers, goods received notes and purchase orders).
They operate on Django QuerySets and standard ``request.GET`` parameters to
produce filtered and sorted querysets, paginated results and CSV exports.
"""

from __future__ import annotations

import csv
from typing import Any, Callable, Dict, Iterable, Mapping, Sequence, Tuple, List

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

    # Helper to convert repeated or comma-separated values into a list
    def _values_for(param_name: str) -> List[str]:
        values = []
        # Include repeated query params, e.g. ?status=open&status=pending
        for v in request.GET.getlist(param_name):
            if v is None:
                continue
            # Support comma-separated values in a single param as well
            parts = [p.strip() for p in str(v).split(",")]
            values.extend([p for p in parts if p])
        return values

    # Known Django lookup suffixes to detect and adapt __in semantics
    LOOKUP_SUFFIXES = {
        "exact",
        "iexact",
        "contains",
        "icontains",
        "startswith",
        "istartswith",
        "endswith",
        "iendswith",
        "in",
        "gt",
        "gte",
        "lt",
        "lte",
        "range",
        "date",
        "year",
        "month",
        "day",
        "week",
        "week_day",
        "hour",
        "minute",
        "second",
        "isnull",
        "regex",
        "iregex",
    }

    for param, lookup in (filter_fields or {}).items():
        values = _values_for(param)
        if not values:
            # Preserve echo value for templates (use empty string if none)
            params[param] = (request.GET.get(param) or "").strip()
            continue

        # If a single value, keep the provided lookup as-is
        if len(values) == 1:
            raw_val = values[0]
            # Normalize booleans
            low = raw_val.lower()
            if low in {"true", "1", "yes", "on"}:
                norm_val: Any = True
            elif low in {"false", "0", "no", "off"}:
                norm_val = False
            else:
                norm_val = raw_val
            qs = qs.filter(**{lookup: norm_val})
        else:
            # Multiple values: coerce to an __in lookup on the base path
            parts = lookup.split("__")
            # If last part is a lookup suffix, drop it to keep the field path
            if parts[-1] in LOOKUP_SUFFIXES:
                base_path = "__".join(parts[:-1]) if len(parts) > 1 else parts[0]
            else:
                base_path = lookup
            in_lookup = f"{base_path}__in"
            qs = qs.filter(**{in_lookup: values})

        # For params echo-back, join multiple values with commas for stability
        params[param] = ",".join(values)

    allowed_sorts_set = set(allowed_sorts or [])
    allowed_sorts_set.add(default_sort)

    # Support multiple sort/direction pairs; fall back to single if none
    sorts = [s.strip() for s in request.GET.getlist("sort") if s and s.strip()]
    dirs = [d.strip().lower() for d in request.GET.getlist("direction") if d]

    # If no repeated params, respect single values
    if not sorts:
        single_sort = (request.GET.get("sort") or default_sort).strip()
        sorts = [single_sort]
    if not dirs:
        single_dir = (request.GET.get("direction") or default_direction).strip().lower()
        dirs = [single_dir]

    # Pair the sorts with directions (pad/truncate), keeping last occurrence
    paired: List[Tuple[str, str]] = []
    for idx, s in enumerate(sorts):
        d = dirs[idx] if idx < len(dirs) else default_direction
        d = d if d in {"asc", "desc"} else default_direction
        if s in allowed_sorts_set:
            paired.append((s, d))

    # De-duplicate keeping the last direction for each sort while preserving order
    seen = {}
    for s, d in paired:
        seen[s] = d  # last one wins
    ordered_unique: List[Tuple[str, str]] = []
    for s in [] if not paired else [p[0] for p in paired]:
        if s in seen:
            ordered_unique.append((s, seen.pop(s)))
    # If empty after filtering, use default
    if not ordered_unique:
        ordered_unique = [(default_sort, default_direction)]

    ordering_fields = [s if d == "asc" else f"-{s}" for s, d in ordered_unique]
    qs = qs.order_by(*ordering_fields)

    # Backward compatible single sort/direction for templates (primary sort)
    params.update({
        "sort": ordered_unique[0][0],
        "direction": ordered_unique[0][1],
    })
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
