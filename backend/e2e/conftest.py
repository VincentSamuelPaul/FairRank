"""Shared world for the end-to-end suites: two client orgs, every role, one scored + submitted candidate per org."""
import pytest
from rest_framework.test import APIClient

from accounts.models import Role, User
from candidates.models import Stage
from conftest import SAMPLE_CV, WEAK_CV


@pytest.fixture
def client_user_b(org_b) -> User:
    return User.objects.create_user("hm-b@example.com", "pw-client-b1", full_name="HM B", role=Role.CLIENT, client_org=org_b)


@pytest.fixture
def recruiter2(db) -> User:
    return User.objects.create_user("rec2@example.com", "pw-recruiter-2", full_name="Rec Two", role=Role.RECRUITER)


class World:
    """Handy bundle. `submit` goes through the real API (open first, then submit) so the rules are exercised, not bypassed."""

    def __init__(self, auth, recruiter, delivery_head, client_user_a, client_user_b, req_a, req_b, make_candidate):
        self.auth, self.recruiter, self.head, self.ca, self.cb = auth, recruiter, delivery_head, client_user_a, client_user_b
        self.req_a, self.req_b, self.make = req_a, req_b, make_candidate
        self.rec = auth(recruiter)
        self.anon = APIClient()

    def candidate(self, req, text=SAMPLE_CV, **kw):
        return self.make(req, text, **kw)

    def submit(self, cand, note=""):
        assert self.rec.get(f"/api/candidates/{cand.pk}/").status_code == 200  # opening logs the view
        r = self.rec.post(f"/api/candidates/{cand.pk}/submit/", {"note": note}, format="json")
        assert r.status_code == 200, r.content
        return r


@pytest.fixture
def world(auth, recruiter, delivery_head, client_user_a, client_user_b, req_a, req_b, make_candidate):
    return World(auth, recruiter, delivery_head, client_user_a, client_user_b, req_a, req_b, make_candidate)


@pytest.fixture
def submitted_a(world):
    cand = world.candidate(world.req_a)
    world.submit(cand, "Strong on Spring Boot")
    return cand


@pytest.fixture
def submitted_b(world):
    cand = world.candidate(world.req_b, WEAK_CV.replace("Mohan Lal", "Mohan Lal"))
    world.submit(cand)
    return cand


__all__ = ["Stage"]
