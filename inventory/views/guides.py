from django.views.generic import TemplateView


class WorkflowGuideView(TemplateView):
    """Display the Inventory Pro workflow handbook within the UI."""

    template_name = "guides/workflow_guide.html"
