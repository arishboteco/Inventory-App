from django.urls import reverse
from django.views.generic import TemplateView

from ...forms.item_forms import ItemForm
from ...forms.bulk_forms import BulkUploadForm
from ...models import Item
from ...models.departments import Department
from ...services.units_service import UnitsService
from ...services.categories_service import CategoriesService
from ...services import kpis


class AddItemModalView(TemplateView):
    template_name = "components/add_item_modal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = ItemForm()
        ctx["departments_for_form"] = Department.objects.all().order_by("name")
        ctx["inline_units"] = UnitsService.get_unit_choices_for_forms()
        ctx["inline_categories"] = CategoriesService.get_category_choices_for_forms()
        return ctx


class BulkUploadModalView(TemplateView):
    template_name = "components/bulk_upload_modal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bulk_form"] = BulkUploadForm()
        return ctx


class ItemsMetricsModalView(TemplateView):
    template_name = "components/items_metrics_modal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            pending_po_counts = kpis.pending_po_status_counts()
            pending_orders = sum(pending_po_counts.values())
        except Exception:  # pragma: no cover
            pending_orders = 0
        try:
            total_value = kpis.stock_value()
        except Exception:  # pragma: no cover
            total_value = 0
        ctx.update(
            {
                "stats": {
                    "low_stock_count": kpis.low_stock_count(),
                    "pending_orders": pending_orders,
                    "total_value": total_value,
                },
                "items_count": Item.objects.count(),
                "items_list_url": reverse("items_list"),
                "po_list_url": reverse("purchase_orders_list"),
            }
        )
        return ctx
