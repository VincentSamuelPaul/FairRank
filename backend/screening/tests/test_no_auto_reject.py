"""Rule 1: scores label, never remove. No code path changes status from a score alone."""
import pytest

from candidates.models import Candidate, Stage
from conftest import WEAK_CV

pytestmark = pytest.mark.django_db


def test_low_score_leaves_status_unchanged_and_candidate_searchable(auth, recruiter, req_a, make_candidate):
    strong = make_candidate(req_a)
    weak = make_candidate(req_a, WEAK_CV)
    from screening.models import Score

    s_strong, s_weak = Score.objects.get(candidate=strong), Score.objects.get(candidate=weak)
    assert s_weak.band == Score.Band.WEAK and s_strong.total_score > s_weak.total_score

    # Same stage regardless of score; nobody was rejected or hidden.
    assert strong.stage == weak.stage == Stage.SCREENED
    assert not Candidate.objects.filter(stage=Stage.REJECTED).exists()
    assert weak in Candidate.objects.visible_to(recruiter)

    api = auth(recruiter)
    rows = api.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"]
    assert [r["full_name"] for r in rows] == ["Jane Doe", "Mohan Lal"]  # ranked, weak one still listed
    assert api.get(f"/api/requisitions/{req_a.pk}/candidates/?q=Mohan").json()["candidates"][0]["full_name"] == "Mohan Lal"
    assert len(api.get(f"/api/requisitions/{req_a.pk}/candidates/?band=weak").json()["candidates"]) == 1


def test_no_endpoint_lets_a_recruiter_reject(auth, recruiter, req_a, make_candidate):
    weak = make_candidate(req_a, WEAK_CV)
    res = auth(recruiter).post(f"/api/candidates/{weak.pk}/stage/", {"stage": "rejected"}, format="json")
    assert res.status_code == 409  # "rejected" is a client-only, human decision
    res = auth(recruiter).post(f"/api/candidates/{weak.pk}/stage/", {"stage": "submitted"}, format="json")
    assert res.status_code == 409  # submitting goes through the open-before-submit flow only
    weak.refresh_from_db()
    assert weak.stage == Stage.SCREENED
