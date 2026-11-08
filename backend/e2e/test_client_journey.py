"""The client hiring manager's journey, and every way it must NOT leak: isolation, masking, human decisions, slots."""
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from audit.models import Notification
from candidates.models import Candidate, Stage
from conftest import SAMPLE_CV, WEAK_CV

pytestmark = pytest.mark.django_db

EMAIL, PHONE = "jane.doe@example.com", "+91 98765 43210"


def future(days=2):
    return (timezone.now() + timedelta(days=days)).isoformat()


@pytest.fixture
def cl(world):
    return world.auth(world.ca)


def test_a_client_sees_only_what_was_submitted_to_their_org(world, cl, req_a, req_b, submitted_a, submitted_b):
    unsubmitted = world.candidate(req_a, WEAK_CV.replace("Mohan Lal", "Not Yet").replace("mohan.lal", "not.yet"))
    cards = cl.get("/api/portal/candidates/").json()
    assert [c["id"] for c in cards] == [str(submitted_a.pk)]                      # not the unsubmitted one, not org B's
    assert cl.get(f"/api/portal/candidates/{unsubmitted.pk}/").status_code == 404
    assert cl.get(f"/api/portal/candidates/{submitted_b.pk}/").status_code == 404
    other = world.auth(world.cb)
    assert [c["id"] for c in other.get("/api/portal/candidates/").json()] == [str(submitted_b.pk)]
    reqs = cl.get("/api/portal/requisitions/").json()
    assert [r["id"] for r in reqs] == [str(req_a.pk)] and cl.get(f"/api/portal/requisitions/{req_b.pk}/").status_code == 404


def test_contacts_stay_masked_until_the_interview_stage_everywhere_in_the_payload(world, cl, submitted_a):
    base = f"/api/portal/candidates/{submitted_a.pk}/"
    for stage_step in ("submitted", "shortlisted"):
        body = json.dumps(cl.get(base).json())
        assert EMAIL not in body and "98765 43210" not in body and "9876543210" not in body, stage_step
        card = cl.get(base).json()
        assert card["contacts"]["masked"] is True and "•" in card["contacts"]["email"] + card["contacts"]["phone"] or "*" in card["contacts"]["email"]
        if stage_step == "submitted":
            assert cl.post(base + "decision/", {"decision": "shortlist"}, format="json").status_code == 200
    assert cl.post(base + "slots/", {"starts_at": future(), "duration_minutes": 45}, format="json").status_code == 201
    card = cl.get(base).json()
    assert card["stage"] == "interview" and card["contacts"]["masked"] is False and card["contacts"]["email"] == EMAIL


def test_the_client_payload_never_contains_blind_fields_or_other_orgs_data(world, cl, submitted_a, submitted_b):
    body = json.dumps(cl.get(f"/api/portal/candidates/{submitted_a.pk}/").json())
    for secret in ("12 March 1991", "Married", "Female", "Photo: attached"):
        assert secret not in body, secret
    assert str(submitted_b.pk) not in json.dumps(cl.get("/api/portal/candidates/").json())


def test_shortlist_then_reject_is_allowed_but_double_decisions_are_not(world, cl, submitted_a):
    base = f"/api/portal/candidates/{submitted_a.pk}/decision/"
    assert cl.post(base, {"decision": "shortlist"}, format="json").status_code == 200
    again = cl.post(base, {"decision": "shortlist"}, format="json")
    assert again.status_code == 409, "shortlisting an already shortlisted candidate must not create a second decision"
    from portal.models import ClientDecision
    assert ClientDecision.objects.filter(submission__candidate=submitted_a).count() == 1
    rej = cl.post(base, {"decision": "reject", "reason": "Notice period too long"}, format="json")
    assert rej.status_code == 200 and rej.json()["stage"] == "rejected"
    assert cl.post(base, {"decision": "shortlist"}, format="json").status_code == 409  # decided: final
    assert Candidate.objects.get(pk=submitted_a.pk).stage == Stage.REJECTED


@pytest.mark.parametrize("payload", [{"decision": "reject"}, {"decision": "reject", "reason": ""}, {"decision": "reject", "reason": "   \n\t "},
                                     {"decision": "reject", "reason": "x" * 501}, {"decision": "maybe"}, {}, {"decision": ["reject"]}])
def test_a_rejection_needs_a_real_reason_and_decisions_are_validated(world, cl, submitted_a, payload):
    r = cl.post(f"/api/portal/candidates/{submitted_a.pk}/decision/", payload, format="json")
    assert r.status_code == 400
    assert Candidate.objects.get(pk=submitted_a.pk).stage == Stage.SUBMITTED  # nothing changed


def test_the_recruiter_sees_the_reason_and_is_notified(world, cl, submitted_a):
    cl.post(f"/api/portal/candidates/{submitted_a.pk}/decision/", {"decision": "reject", "reason": "Wrong domain"}, format="json")
    detail = world.rec.get(f"/api/candidates/{submitted_a.pk}/").json()
    assert detail["stage"] == "rejected" and detail["submission"]["decisions"][-1]["reason"] == "Wrong domain"
    assert Notification.objects.filter(recipient=world.recruiter, subject__icontains="rejected").exists()
    assert detail["stage_events"][-1]["to"] == "rejected" and detail["stage_events"][-1]["reason"] == "Wrong domain"


@pytest.mark.parametrize("payload,ok", [
    ({"duration_minutes": 30}, False), ({"starts_at": "garbage"}, False), ({"starts_at": future(), "duration_minutes": 10}, False),
    ({"starts_at": future(), "duration_minutes": 241}, False), ({"starts_at": future(), "duration_minutes": 0}, False),
    ({"starts_at": future(), "duration_minutes": 30, "note": "n" * 301}, False),
    ({"starts_at": (timezone.now() - timedelta(minutes=1)).isoformat()}, False),
    ({"starts_at": future(), "duration_minutes": 15}, True), ({"starts_at": future(30), "duration_minutes": 240, "note": "Panel, video link"}, True),
])
def test_interview_slot_validation(world, cl, submitted_a, payload, ok):
    r = cl.post(f"/api/portal/candidates/{submitted_a.pk}/slots/", payload, format="json")
    assert (r.status_code == 201) is ok, r.content
    assert Candidate.objects.get(pk=submitted_a.pk).stage == (Stage.INTERVIEW if ok else Stage.SUBMITTED)


def test_slots_after_a_rejection_or_for_unsubmitted_people_are_refused(world, cl, submitted_a):
    cl.post(f"/api/portal/candidates/{submitted_a.pk}/decision/", {"decision": "reject", "reason": "No"}, format="json")
    assert cl.post(f"/api/portal/candidates/{submitted_a.pk}/slots/", {"starts_at": future()}, format="json").status_code == 409


def test_a_second_slot_is_allowed_and_the_recruiter_can_confirm_or_decline(world, cl, submitted_a):
    base = f"/api/portal/candidates/{submitted_a.pk}/slots/"
    assert cl.post(base, {"starts_at": future(2)}, format="json").status_code == 201
    assert cl.post(base, {"starts_at": future(3)}, format="json").status_code == 201
    slots = world.rec.get(f"/api/candidates/{submitted_a.pk}/").json()["submission"]["slots"]
    assert len(slots) == 2 and all(s["status"] == "proposed" for s in slots)
    assert world.rec.post(f"/api/slots/{slots[0]['id']}/respond/", {"status": "confirmed"}, format="json").status_code == 200
    assert world.rec.post(f"/api/slots/{slots[1]['id']}/respond/", {"status": "declined"}, format="json").status_code == 200
    assert world.rec.post(f"/api/slots/{slots[1]['id']}/respond/", {"status": "proposed"}, format="json").status_code == 400
    assert world.auth(world.head).post(f"/api/slots/{slots[0]['id']}/respond/", {"status": "confirmed"}, format="json").status_code == 403
    assert world.rec.post("/api/slots/999999/respond/", {"status": "confirmed"}, format="json").status_code == 404
    final = cl.get(f"/api/portal/candidates/{submitted_a.pk}/").json()
    assert {s["status"] for s in final["slots"]} == {"confirmed", "declined"}


def test_client_b_cannot_act_on_org_as_candidate(world, submitted_a):
    other = world.auth(world.cb)
    assert other.post(f"/api/portal/candidates/{submitted_a.pk}/decision/", {"decision": "shortlist"}, format="json").status_code == 404
    assert other.post(f"/api/portal/candidates/{submitted_a.pk}/slots/", {"starts_at": future()}, format="json").status_code == 404
    assert Candidate.objects.get(pk=submitted_a.pk).stage == Stage.SUBMITTED


def test_a_client_never_reaches_staff_screens_or_data(world, cl, submitted_a, req_a):
    for url in (f"/api/candidates/{submitted_a.pk}/", f"/api/requisitions/{req_a.pk}/candidates/", "/api/requisitions/", "/api/reports/agreement/",
                f"/api/requisitions/{req_a.pk}/pipeline/", "/api/pipeline/summary/", "/api/client-orgs/"):
        assert cl.get(url).status_code == 403, url


def test_new_submissions_notify_the_orgs_hiring_managers_only(world, req_a, req_b):
    from accounts.models import User
    Notification.objects.all().delete()
    world.submit(world.candidate(req_a))
    recipients = set(Notification.objects.values_list("recipient__email", flat=True))
    assert recipients == {world.ca.email} and User.objects.get(email=world.cb.email).pk not in Notification.objects.values_list("recipient_id", flat=True)


def test_a_deleted_candidate_vanishes_from_the_client_portal_at_once(world, cl, submitted_a):
    assert len(cl.get("/api/portal/candidates/").json()) == 1
    world.rec.post(f"/api/candidates/{submitted_a.pk}/delete/", {"requester": "candidate", "confirm": True}, format="json")
    assert cl.get("/api/portal/candidates/").json() == [] and cl.get(f"/api/portal/candidates/{submitted_a.pk}/").status_code == 404
    assert cl.post(f"/api/portal/candidates/{submitted_a.pk}/decision/", {"decision": "shortlist"}, format="json").status_code == 404


def test_protected_attribute_lines_are_hidden_in_the_clients_cv_text(world, cl, submitted_a):
    text = cl.get(f"/api/portal/candidates/{submitted_a.pk}/").json()["cv_text"]
    assert "Gender: [hidden]" in text and "Date of Birth: [hidden]" in text and "Marital Status: [hidden]" in text and "Photo: [hidden]" in text
    assert "Jane Doe" in text and "Senior Java Developer" in text  # the name and the work history stay
    assert "Spring Boot" in text  # and the evidence a client reads
    from candidates.models import ParsedProfile
    assert "12 March 1991" in ParsedProfile.objects.get(candidate=submitted_a).raw_text  # the stored CV is untouched
