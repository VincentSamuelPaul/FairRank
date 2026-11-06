"""A1/A2: weighted total from scorecard weights; Strong >= 75, Possible 50-74, Weak < 50."""
from decimal import Decimal

import pytest

from screening.models import Score
from screening.services import band_for, weighted_total, score_candidate
from requisitions.services import save_scorecard


def test_weighted_total_uses_weights():
    # (100*3 + 50*3 + 0*1) / 7
    assert weighted_total([(100, 3), (50, 3), (0, 1)]) == Decimal("64.29")
    assert weighted_total([(80, 1)]) == Decimal("80.00")
    assert weighted_total([]) == Decimal("0.00")


@pytest.mark.parametrize("total,band", [
    ("100", Score.Band.STRONG), ("75", Score.Band.STRONG), ("74.99", Score.Band.POSSIBLE),
    ("50", Score.Band.POSSIBLE), ("49.99", Score.Band.WEAK), ("0", Score.Band.WEAK),
])
def test_band_thresholds(total, band):
    assert band_for(Decimal(total)) == band


@pytest.mark.django_db
def test_changing_weights_changes_the_total(req_a, make_candidate, recruiter):
    cand = make_candidate(req_a, score=False)
    v1 = score_candidate(cand)
    cards = [{"name": c.name, "description": "", "weight": 1, "is_must_have": c.is_must_have} for c in req_a.current_scorecard.criteria.all()]
    cards[2]["weight"] = 10  # location now dominates
    v2 = score_candidate(cand, save_scorecard(req_a, recruiter, cards))
    assert v1.status == v2.status == Score.Status.SCORED
    assert v1.total_score != v2.total_score
    assert v1.scorecard.version == 1 and v2.scorecard.version == 2  # old score kept for the old version


@pytest.mark.django_db
def test_scoring_is_cached_by_cv_hash_and_scorecard(req_a, make_candidate, monkeypatch):
    first = make_candidate(req_a)
    calls = []
    import screening.services as svc

    real = svc.call_llm
    monkeypatch.setattr(svc, "call_llm", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    again = score_candidate(first)  # same CV, same scorecard: no new LLM call
    assert calls == [] and again.pk == first.scores.first().pk
    twin = make_candidate(req_a, score=False)
    score_candidate(twin)  # identical CV text for another record: served from cache
    assert calls == []
