from django.views.generic import TemplateView

WORKFLOW_CHECKLIST = [
    'Submit a new indent and verify its status changes to "Submitted".',
    'Approve the indent and verify the status changes to "Approved".',
    "Run the Consolidation Planner — confirm a draft PO is created per supplier.",
    "Review the draft PO, confirm supplier and quantities, then mark it as Approved.",
    "Record a goods receipt (GRN) against the PO — verify stock levels update automatically.",
    'Fulfil the indent and verify its status changes to "Completed".',
    "Record an ad-hoc stock movement (receive, adjust, or wastage) and verify it appears in Stock Movements.",
]


class WorkflowGuideView(TemplateView):
    """Display the Inventory Pro workflow handbook within the UI."""

    template_name = "guides/workflow_guide.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["checklist_items"] = WORKFLOW_CHECKLIST
        return ctx
