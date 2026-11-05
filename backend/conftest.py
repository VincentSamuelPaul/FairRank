import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import ClientOrg, Role, User


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()  # throttle counters live in the cache


@pytest.fixture
def api() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def org_a(db) -> ClientOrg:
    return ClientOrg.objects.create(name="Org A")


@pytest.fixture
def org_b(db) -> ClientOrg:
    return ClientOrg.objects.create(name="Org B")


@pytest.fixture
def recruiter(db) -> User:
    return User.objects.create_user("rec@example.com", "pw-recruiter-1", full_name="Rec", role=Role.RECRUITER)


@pytest.fixture
def delivery_head(db) -> User:
    return User.objects.create_user("head@example.com", "pw-head-1", full_name="Head", role=Role.DELIVERY_HEAD)


@pytest.fixture
def client_user_a(org_a) -> User:
    return User.objects.create_user(
        "hm-a@example.com", "pw-client-a1", full_name="HM A", role=Role.CLIENT, client_org=org_a
    )
