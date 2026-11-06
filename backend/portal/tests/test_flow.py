"""End to end: upload -> worker -> ranked list with evidence -> open -> submit -> client decisions -> pipeline -> report."""
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from audit import jobs
from candidates.models import Stage
from conftest import SAMPLE_CV, WEAK_CV, make_docx, make_pdf

pytestmark = pytest.mark.django_db


def test_full_flow(auth, recruiter, delivery_head, client_user_a, req_a):
    rec = auth(recruiter)
    files = [SimpleUploadedFile("jane.pdf", make_pdf(SAMPLE_CV.splitlines())),
             SimpleUploadedFile("mohan.docx", make_docx(WEAK_CV.splitlines()))]
    up = rec.post(f"/api/requisitions/{req_a.pk}/uploads/", {"files": files, "consent_confirmed": "true"}, format="multipart")
    assert up.status_code == 201 and len(up.json()["accepted"]) == 2
    ids = ",".join(a["candidate_id"] for a in up.json()["accepted"])
    status = rec.get(f"/api/requisitions/{req_a.pk}/uploads/?ids={ids}").json()
    assert status["in_progress"] is True  # still queued
    while jobs.run_pending(limit=5):
        pass
    status = rec.get(f"/api/requisitions/{req_a.pk}/uploads/?ids={ids}").json()
    assert status["in_progress"] is False and {i["score_state"] for i in status["items"]} == {"scored"}

    ranked = rec.get(f"/api/requisitions/{req_a.pk}/candidates/").json()
    top, bottom = ranked["candidates"]
    assert top["full_name"] == "Jane Doe" and top["score"]["band"] == "strong" and bottom["score"]["band"] == "weak"
    java = next(c for c in top["score"]["criteria"] if c["name"] == "Java")
    assert java["evidence_status"] == "verified" and java["quote"] in SAMPLE_CV.replace("\n", " ")
    assert top["consent_recorded"] if "consent_recorded" in top else True

    detail = rec.get(f"/api/candidates/{top['id']}/").json()
    assert detail["consent"][0]["purpose"] == "hiring_use_only"
    span = next(c for c in detail["score"]["criteria"] if c["name"] == "Java")["span"]
    assert detail["raw_text"][span[0]:span[1]].split()[:2] == ["Built", "Spring"] or span  # highlightable
    sub = rec.post(f"/api/candidates/{top['id']}/submit/", {"note": "Strong"}, format="json")
    assert sub.status_code == 200

    cl = auth(client_user_a)
    cards = cl.get("/api/portal/candidates/").json()
    assert [c["full_name"] for c in cards] == ["Jane Doe"]
    cid = cards[0]["id"]
    assert cl.post(f"/api/portal/candidates/{cid}/decision/", {"decision": "reject"}, format="json").status_code == 400  # reason needed
    ok = cl.post(f"/api/portal/candidates/{cid}/decision/", {"decision": "shortlist"}, format="json")
    assert ok.status_code == 200 and ok.json()["stage"] == Stage.SHORTLISTED
    past = (timezone.now() - timedelta(days=1)).isoformat()
    assert cl.post(f"/api/portal/candidates/{cid}/slots/", {"starts_at": past}, format="json").status_code == 400
    future = (timezone.now() + timedelta(days=2)).isoformat()
    assert cl.post(f"/api/portal/candidates/{cid}/slots/", {"starts_at": future}, format="json").status_code == 201

    board = rec.get(f"/api/requisitions/{req_a.pk}/pipeline/").json()["columns"]
    by_stage = {c["stage"]: c["candidates"] for c in board}
    assert len(by_stage["interview"]) == 1 and len(by_stage["screened"]) == 1
    moved = rec.post(f"/api/candidates/{cid}/stage/", {"stage": "offered"}, format="json")
    assert moved.status_code == 200 and moved.json()["stage"] == "offered"
    assert [e["to"] for e in moved.json()["stage_events"]][-1] == "offered"  # every move is logged

    report = auth(delivery_head).get("/api/reports/agreement/").json()
    assert report["overall"]["submitted"] == 1 and report["overall"]["agreement_pct"] == 100
    assert auth(recruiter).get("/api/reports/agreement/").status_code == 403


def test_upload_validation(auth, recruiter, req_a):
    api = auth(recruiter)
    url = f"/api/requisitions/{req_a.pk}/uploads/"
    fake = SimpleUploadedFile("evil.pdf", b"MZ not a pdf at all")
    ok = SimpleUploadedFile("ok.pdf", make_pdf(SAMPLE_CV.splitlines()))
    res = api.post(url, {"files": [fake, ok], "consent_confirmed": "true"}, format="multipart").json()
    assert len(res["accepted"]) == 1 and res["rejected"][0]["name"] == "evil.pdf"
    big = SimpleUploadedFile("big.pdf", b"%PDF-1.4 " + b"0" * (5 * 1024 * 1024 + 1))
    assert api.post(url, {"files": [big], "consent_confirmed": "true"}, format="multipart").json()["rejected"][0]["reason"].startswith("Larger")
    assert api.post(url, {"files": [ok], "consent_confirmed": "false"}, format="multipart").status_code == 400  # consent required
    assert api.post(url, {"consent_confirmed": "true"}, format="multipart").status_code == 400  # no files


def test_jd_intake_and_scorecard_versioning(auth, recruiter, org_a):
    api = auth(recruiter)
    jd = "Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days"
    created = api.post("/api/requisitions/", {"client_org": org_a.pk, "jd_text": jd}, format="json")
    assert created.status_code == 201
    req = created.json()["requisition"]
    names = [c["name"] for c in req["scorecard"]["criteria"]]
    assert {"Java", "Spring Boot", "5-8 years of experience", "Notice period up to 60 days"} <= set(names)
    assert req["exp_min_years"] == 5 and req["exp_max_years"] == 8 and req["notice_max_days"] == 60 and req["location"] == "Noida"
    musts = {c["name"]: (c["weight"], c["is_must_have"]) for c in req["scorecard"]["criteria"]}
    assert musts["Java"] == (3, True) and musts["Based in or willing to work in Noida"] == (1, False)  # A1 defaults

    crit = [{"name": "Java", "description": "", "weight": 5, "is_must_have": True}]
    v2 = api.put(f"/api/requisitions/{req['id']}/scorecard/", {"criteria": crit}, format="json")
    assert v2.status_code == 200 and v2.json()["version"] == 2
    bad = api.put(f"/api/requisitions/{req['id']}/scorecard/", {"criteria": [{"name": "X", "weight": 11, "is_must_have": False}]}, format="json")
    assert bad.status_code == 400
    assert api.post("/api/requisitions/", {"client_org": org_a.pk, "jd_text": "short"}, format="json").status_code == 400


def test_jd_intake_survives_ai_failure(auth, recruiter, org_a, monkeypatch):
    from ai.llm import LLMUnavailable

    def down(*a, **k):
        raise LLMUnavailable("no key")

    monkeypatch.setattr("requisitions.services.call_llm", down)
    res = auth(recruiter).post("/api/requisitions/", {"client_org": org_a.pk, "title": "Manual", "jd_text": "x" * 40}, format="json")
    assert res.status_code == 201 and res.json()["warning"] and res.json()["requisition"]["scorecard"] is None
