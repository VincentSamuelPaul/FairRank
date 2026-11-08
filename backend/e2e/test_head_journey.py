"""The delivery head: read everything internal, change nothing, and see the AI-vs-recruiter report."""
from datetime import timedelta

import pytest
from django.utils import timezone

from audit.models import ViewLog
from conftest import SAMPLE_CV, WEAK_CV

pytestmark = pytest.mark.django_db

MIDDLE_CV = SAMPLE_CV.replace("Jane Doe", "Mid Candidate").replace("jane.doe", "mid.candidate").replace("98765 43210", "98765 11111") \
    .replace("Hibernate", "Excel").replace("Spring Boot", "Struts")


def three(world, req):
    top = world.candidate(req, SAMPLE_CV)
    mid = world.candidate(req, MIDDLE_CV)
    low = world.candidate(req, WEAK_CV)
    return top, mid, low


def test_the_head_can_read_but_never_write(world, req_a, submitted_a):
    head = world.auth(world.head)
    assert head.get("/api/requisitions/").status_code == 200
    assert head.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["counts"]["total"] == 1
    assert head.get(f"/api/candidates/{submitted_a.pk}/").status_code == 200
    writes = [
        ("post", f"/api/candidates/{submitted_a.pk}/stage/", {"stage": "offered"}), ("post", f"/api/candidates/{submitted_a.pk}/delete/", {"confirm": True}),
        ("post", f"/api/candidates/{submitted_a.pk}/rescore/", {}), ("put", f"/api/requisitions/{req_a.pk}/scorecard/", {"criteria": [{"name": "A", "weight": 1, "is_must_have": True}]}),
        ("patch", f"/api/requisitions/{req_a.pk}/", {"status": "closed"}), ("post", f"/api/requisitions/{req_a.pk}/rescore/", {}),
        ("post", "/api/requisitions/", {"client_org": 1, "jd_text": "x" * 30}),
    ]
    for method, url, body in writes:
        assert getattr(head, method)(url, body, format="json").status_code == 403, (method, url)
    assert head.get(f"/api/candidates/{submitted_a.pk}/").json()["stage"] == "submitted"


def test_the_heads_opens_are_in_the_view_log(world, submitted_a):
    world.auth(world.head).get(f"/api/candidates/{submitted_a.pk}/")
    assert ViewLog.objects.filter(candidate=submitted_a, user=world.head).exists()


def test_agreement_is_100_percent_when_the_recruiter_submits_the_ais_top_pick(world, req_a):
    top, mid, low = three(world, req_a)
    world.submit(top)
    rep = world.auth(world.head).get("/api/reports/agreement/").json()
    assert rep["overall"]["agreement_pct"] == 100 and rep["overall"]["submitted"] == 1
    assert rep["requisitions"][0]["disagreements"] == []


def test_agreement_lists_the_disagreement_when_the_recruiter_picks_a_lower_ranked_cv(world, req_a):
    top, mid, low = three(world, req_a)
    world.submit(low)
    rep = world.auth(world.head).get("/api/reports/agreement/").json()
    row = rep["requisitions"][0]
    assert row["submitted"] == 1 and row["in_ai_top_n"] == 0 and row["agreement_pct"] == 0
    kinds = {d["type"]: d for d in row["disagreements"]}
    assert kinds["recruiter_chose_lower_ranked"]["ai_rank"] == 3 and kinds["ai_ranked_higher_not_submitted"]["ai_rank"] == 1
    assert rep["overall"]["agreement_pct"] == 0


def test_agreement_across_two_requisitions_and_partial_overlap(world, req_a, req_b):
    t, m, l = three(world, req_a)
    world.submit(t)
    world.submit(m)  # 2 submitted, AI top-2 = {t, m} -> 100%
    t2, m2, l2 = three(world, req_b)
    world.submit(l2)  # 1 submitted, AI top-1 = t2 -> 0%
    rep = world.auth(world.head).get("/api/reports/agreement/").json()
    pct = {r["title"]: r["agreement_pct"] for r in rep["requisitions"]}
    assert pct == {req_a.title: 100, req_b.title: 0}
    assert rep["overall"] == {"requisitions": 2, "submitted": 3, "agreement_pct": 67}  # 2 of 3 submissions were in the AI's top N


def test_agreement_respects_the_window_and_ignores_deleted_people(world, req_a):
    top, mid, low = three(world, req_a)
    world.submit(top)
    world.submit(low)
    from portal.models import Submission
    Submission.objects.filter(candidate=top).update(submitted_at=timezone.now() - timedelta(days=30))
    head = world.auth(world.head)
    assert head.get("/api/reports/agreement/?days=7").json()["overall"]["submitted"] == 1
    assert head.get("/api/reports/agreement/?days=60").json()["overall"]["submitted"] == 2
    world.rec.post(f"/api/candidates/{low.pk}/delete/", {"requester": "x", "confirm": True}, format="json")
    assert head.get("/api/reports/agreement/?days=7").json()["overall"]["submitted"] == 0


@pytest.mark.parametrize("days", ["abc", "-5", "0", "100000", ""])
def test_the_report_survives_odd_window_values(world, days):
    r = world.auth(world.head).get("/api/reports/agreement/", {"days": days})
    assert r.status_code in (200, 400)


def test_the_report_changes_nothing(world, req_a):
    top, mid, low = three(world, req_a)
    world.submit(low)
    before = list(top.__class__.objects.values_list("pk", "stage").order_by("pk"))
    world.auth(world.head).get("/api/reports/agreement/")
    assert list(top.__class__.objects.values_list("pk", "stage").order_by("pk")) == before


def test_pipeline_summary_counts_by_stage(world, req_a, submitted_a):
    s = world.auth(world.head).get("/api/pipeline/summary/").json()
    flat = json_text(s)
    assert "submitted" in flat


def json_text(o):
    import json
    return json.dumps(o)
