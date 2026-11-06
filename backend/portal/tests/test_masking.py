"""Rule 6 / A7: clients get masked contacts until the interview stage; raw values never leave the server before."""
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from audit.services import log_view
from candidates.models import Stage
from portal.services import submit_candidate

pytestmark = pytest.mark.django_db

RAW = ("jane.doe@example.com", "98765 43210", "98765")


@pytest.fixture
def submitted(recruiter, req_a, make_candidate):
    cand = make_candidate(req_a)
    log_view(recruiter, cand)
    submit_candidate(cand, recruiter)
    return cand


def assert_no_raw(payload):
    blob = json.dumps(payload)
    for raw in RAW:
        assert raw not in blob, f"{raw} leaked"


def test_contacts_are_masked_before_interview(auth, client_user_a, submitted):
    api = auth(client_user_a)
    card = api.get("/api/portal/candidates/").json()[0]
    assert card["contacts"]["masked"] is True
    assert card["contacts"]["email"] == "j•••@e•••.com" and "98765" not in card["contacts"]["phone"]
    assert_no_raw(card)
    detail = api.get(f"/api/portal/candidates/{submitted.pk}/").json()
    assert_no_raw(detail)  # includes the CV text and evidence quotes
    assert "Spring Boot" in detail["cv_text"]  # but the content is still readable
    api.post(f"/api/portal/candidates/{submitted.pk}/decision/", {"decision": "shortlist"}, format="json")
    assert_no_raw(api.get(f"/api/portal/candidates/{submitted.pk}/").json())  # shortlisted is not interview yet


def test_contacts_unmask_at_the_interview_stage(auth, client_user_a, submitted):
    api = auth(client_user_a)
    when = (timezone.now() + timedelta(days=2)).isoformat()
    res = api.post(f"/api/portal/candidates/{submitted.pk}/slots/", {"starts_at": when, "duration_minutes": 30}, format="json")
    assert res.status_code == 201
    body = res.json()
    assert body["stage"] == Stage.INTERVIEW and body["contacts"]["masked"] is False
    assert body["contacts"]["email"] == "jane.doe@example.com"


def test_client_payload_has_no_internal_fields(auth, client_user_a, submitted):
    card = auth(client_user_a).get("/api/portal/candidates/").json()[0]
    for key in ("email", "phone", "cv_status", "view_log", "consent", "duplicate_of"):
        assert key not in card
    assert "model" not in card["score"] and "error" not in card["score"]
