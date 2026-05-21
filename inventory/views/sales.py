from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import redirect, render

from ..forms.sales_forms import POSMenuItemMappingForm, POSSalesImportForm
from ..models import POSMenuItemMapping, SaleTransaction
from ..services import pos_sales_import_service


def pos_sales_import(request):
    if request.method == "POST":
        action = (request.POST.get("action") or "upload").strip().lower()
        if action == "map":
            mapping_form = POSMenuItemMappingForm(request.POST)
            import_form = POSSalesImportForm()
            if mapping_form.is_valid():
                mapping = mapping_form.save()
                updated_rows = pos_sales_import_service.apply_mapping_to_unmapped_sales(
                    mapping
                )
                messages.success(
                    request,
                    f"Mapping saved. Linked {updated_rows} existing imported row(s).",
                    extra_tags="toast",
                )
                return redirect("pos_sales_import")
            messages.error(request, "Please correct mapping form errors.")
        else:
            import_form = POSSalesImportForm(request.POST, request.FILES)
            mapping_form = POSMenuItemMappingForm(
                initial={"is_active": True},
            )
            if import_form.is_valid():
                uploaded = import_form.cleaned_data["file"]
                try:
                    result = pos_sales_import_service.import_pos_sales_csv(
                        uploaded,
                        request.user,
                    )
                    messages.success(
                        request,
                        (
                            "Imported "
                            f"{result['imported_count']} row(s). "
                            f"Unmapped: {result['unmapped_count']}. "
                            f"Net Sales: Rs. {result['total_net_sales']:.2f}"
                        ),
                        extra_tags="toast",
                    )
                    for error_text in result["errors"][:10]:
                        messages.warning(request, error_text)
                    return redirect("pos_sales_import")
                except ValueError as exc:
                    messages.error(request, str(exc), extra_tags="toast")
            else:
                messages.error(request, "Please upload a valid CSV file.")
    else:
        import_form = POSSalesImportForm()
        mapping_form = POSMenuItemMappingForm(initial={"is_active": True})

    recent_sales = (
        SaleTransaction.objects.filter(source=SaleTransaction.Source.POS_CSV)
        .select_related("recipe")
        .order_by("-sale_date", "-sale_id")
    )
    paginator = Paginator(recent_sales, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    mappings = POSMenuItemMapping.objects.select_related("recipe").order_by(
        "pos_item_name"
    )[:100]
    unmapped_items = pos_sales_import_service.unmapped_sales_summary()

    return render(
        request,
        "inventory/sales/pos_sales_import.html",
        {
            "import_form": import_form,
            "mapping_form": mapping_form,
            "page_obj": page_obj,
            "mappings": mappings,
            "unmapped_items": unmapped_items,
        },
    )
