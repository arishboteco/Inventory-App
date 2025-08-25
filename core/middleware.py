import re

from django.conf import settings
from django.contrib.auth.views import redirect_to_login


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to the login page."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [re.compile(expr) for expr in getattr(settings, "LOGIN_EXEMPT_URLS", [])]

    def __call__(self, request):
        if not request.user.is_authenticated:
            path = request.path_info.lstrip("/")
            for pattern in self.exempt_urls:
                if pattern.match(path):
                    return self.get_response(request)
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)
