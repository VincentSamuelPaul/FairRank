from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path

def health(request):
    """Liveness + database check for Docker healthchecks and uptime monitors. Exposes no data."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:  # noqa: BLE001 - any DB failure means unhealthy
        return JsonResponse({"status": "unhealthy"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/health/", health),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("requisitions.urls")),
    path("api/", include("candidates.urls")),
    path("api/", include("portal.urls")),
]
