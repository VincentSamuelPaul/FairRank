"""Production settings: fail-fast key, secure cookies, HSTS and a public health check."""
import os
import subprocess
import sys

import pytest

BASE_ENV = {"PATH": os.environ["PATH"], "DATABASE_URL": "sqlite:///:memory:"}
PROBE = ("import django.conf as c, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; "
         "s=c.settings; print(s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE, s.SESSION_COOKIE_HTTPONLY, "
         "s.SESSION_COOKIE_SAMESITE, s.SECURE_HSTS_SECONDS>0, s.DEBUG, s.X_FRAME_OPTIONS)")


def run_settings(**env):
    return subprocess.run([sys.executable, "-c", PROBE], capture_output=True, text=True,
                          env={**BASE_ENV, **env}, cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def test_missing_secret_key_refuses_to_start():
    r = run_settings()
    assert r.returncode != 0 and "SECRET_KEY" in r.stderr


@pytest.mark.parametrize("key", ["short", "change-me-change-me-change-me-change-me"])
def test_weak_secret_key_refuses_to_start_in_production(key):
    r = run_settings(SECRET_KEY=key)
    assert r.returncode != 0 and "too weak" in r.stderr


def test_production_defaults_are_secure():
    r = run_settings(SECRET_KEY="x" * 40)
    assert r.stdout.split() == ["True", "True", "True", "Lax", "True", "False", "DENY"]


def test_blank_env_values_fall_back_to_defaults():
    """A copied .env.example has every name present but empty: that must not crash or open anything up."""
    blanks = {n: "" for n in ["DEBUG", "ALLOWED_HOSTS", "CSRF_TRUSTED_ORIGINS", "SECURE_COOKIES", "MAX_UPLOAD_BYTES",
                              "MAX_FILES_PER_BATCH", "LOGIN_RATE", "HSTS_SECONDS", "NUM_PROXIES", "CACHE_DIR",
                              "WORKER_BATCH_SIZE", "WORKER_POLL_SECONDS", "WORKER_BACKOFF_SECONDS", "LLM_PROVIDER",
                              "MEDIA_ROOT", "STATIC_ROOT"]}
    r = run_settings(SECRET_KEY="x" * 40, **blanks)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["True", "True", "True", "Lax", "True", "False", "DENY"]


def test_debug_mode_allows_dev_key_and_plain_cookies():
    r = run_settings(SECRET_KEY="dev", DEBUG="true")
    assert r.returncode == 0 and r.stdout.split()[:2] == ["False", "False"]


@pytest.mark.django_db
def test_health_endpoint_is_public_and_leaks_nothing(client):
    res = client.get("/api/health/")
    assert res.status_code == 200 and res.json() == {"status": "ok"}

