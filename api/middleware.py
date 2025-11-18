from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponseForbidden


class CustomCsrfMiddleware(CsrfViewMiddleware):
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip CSRF checks for specific API endpoints
        exempt_paths = [
            "/api/token/",
            "/api/token/refresh/",
            "/login/",
            "/register/",
        ]
        if request.path in exempt_paths:
            return None  # Skip CSRF check
        return super().process_view(request, view_func, view_args, view_kwargs)
