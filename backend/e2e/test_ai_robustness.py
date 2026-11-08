"""When the AI is wrong or unsure: the scorer is stubbed with bad answers and the rules must still hold."""
import pytest

from ai.llm import LLMError, LLMInvalidOutput, LLMRateLimited, LLMResult
from ai.schemas import CriterionResult, CVScoring
from candidates.models import Candidate, Stage
from conftest import SAMPLE_CV
from requisitions.models import Scorecard
from screening import services as s
from screening.models import Score

pytestmark = pytest.mark.django_db


def stub(monkeypatch, make):
    calls = []

    def fake(prompt, schema, context=None):
        calls.append(prompt)
        return make(context["criteria"], prompt)
    monkeypatch.setattr(s, "call_llm", fake)
    return calls


def result(crit, **kw):
    return CriterionResult(criterion_id=crit["id"], **{"points": 90, "confidence": 1, "quote": "", "rationale": "ok", **kw})


@pytest.fixture
def cand(world, req_a):
    return world.candidate(req_a, SAMPLE_CV, score=False)


def test_a_made_up_quote_is_dropped_and_earns_nothing(cand, monkeypatch):
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(c, quote="Led a team of 40 engineers at Google") for c in cs]), model="fake"))
    score = s.score_candidate(cand)
    assert float(score.total_score) == 0
    for cs in score.criterion_scores.all():
        assert cs.evidence_status == "no_evidence" and cs.evidence_quote == "" and cs.points == 0


def test_a_real_quote_is_kept_even_if_whitespace_differs_but_case_changes_are_not_forgiven(cand, monkeypatch):
    real = "Built   Spring Boot\nmicroservices for payment workflows"  # same words, different whitespace
    fake_case = "BUILT SPRING BOOT MICROSERVICES"
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(cs[0], quote=real), result(cs[1], quote=fake_case), *[result(c) for c in cs[2:]]]), model="fake"))
    rows = {cs.criterion.name: cs for cs in s.score_candidate(cand).criterion_scores.all()}
    names = list(rows)
    assert rows[names[0]].evidence_status == "verified" and "Spring Boot" in rows[names[0]].evidence_quote
    assert rows[names[1]].evidence_status == "no_evidence"


def test_a_quote_copied_from_the_redacted_text_cannot_be_shown(cand, monkeypatch):
    seen = {}

    def make(cs, prompt):
        seen["prompt"] = prompt
        return LLMResult(data=CVScoring(results=[result(c, quote="[REDACTED] is a Senior Java Developer") for c in cs]), model="fake")
    stub(monkeypatch, make)
    score = s.score_candidate(cand)
    assert "Jane Doe" not in seen["prompt"] and "jane.doe@example.com" not in seen["prompt"] and "12 March 1991" not in seen["prompt"]  # blind scoring
    assert all(cs.evidence_quote == "" for cs in score.criterion_scores.all())


def test_a_criterion_the_scorer_forgot_is_no_evidence_not_a_crash(cand, monkeypatch):
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(cs[0], quote="Wrote Java services and tuned Hibernate queries")]), model="fake"))
    score = s.score_candidate(cand)
    states = [cs.evidence_status for cs in score.criterion_scores.order_by("criterion__order")]
    assert states[0] == "verified" and set(states[1:]) == {"no_evidence"} and score.status == Score.Status.SCORED


def test_results_for_unknown_criteria_are_ignored(cand, monkeypatch):
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[CriterionResult(criterion_id=987654, points=100, quote="Java"), *[result(c) for c in cs]]), model="fake"))
    assert s.score_candidate(cand).criterion_scores.count() == 3


def test_out_of_range_points_are_an_invalid_output_not_a_score(world, req_a):
    with pytest.raises(Exception):
        CriterionResult(criterion_id=1, points=250)
    with pytest.raises(Exception):
        CriterionResult(criterion_id=1, points=-1)
    with pytest.raises(Exception):
        CriterionResult(criterion_id=1, points=50, confidence=1.5)


def test_invalid_output_after_the_retry_becomes_scoring_failed_with_the_cv_still_readable(world, req_a, cand, monkeypatch):
    def boom(prompt, schema, context=None):
        raise LLMInvalidOutput("not json")
    monkeypatch.setattr(s, "call_llm", boom)
    score = s.score_candidate(cand)
    assert score.status == Score.Status.FAILED and score.total_score is None and "retry" in score.error.lower()
    detail = world.rec.get(f"/api/candidates/{cand.pk}/").json()
    assert detail["score"]["state"] == "failed" and detail["raw_text"].startswith("Jane Doe")
    assert Candidate.objects.get(pk=cand.pk).stage != Stage.REJECTED
    assert world.rec.post(f"/api/candidates/{cand.pk}/rescore/").status_code == 202


def test_rate_limit_is_retried_by_the_queue_and_only_fails_on_the_last_attempt(cand, monkeypatch):
    def limited(prompt, schema, context=None):
        raise LLMRateLimited("429")
    monkeypatch.setattr(s, "call_llm", limited)
    with pytest.raises(LLMRateLimited):
        s.score_candidate(cand, final_attempt=False)
    assert s.score_candidate(cand, final_attempt=True).status == Score.Status.FAILED


def test_generic_provider_errors_fail_gracefully(cand, monkeypatch):
    def broken(prompt, schema, context=None):
        raise LLMError("provider down")
    monkeypatch.setattr(s, "call_llm", broken)
    assert s.score_candidate(cand).status == Score.Status.FAILED


def test_low_confidence_shows_as_unverified_but_keeps_its_verified_quote(world, req_a, cand, monkeypatch):
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(cs[0], quote="Wrote Java services and tuned Hibernate queries", confidence=0.3), *[result(c) for c in cs[1:]]]), model="fake"))
    from candidates.services import after_scoring
    after_scoring(cand, s.score_candidate(cand))
    first = world.rec.get(f"/api/candidates/{cand.pk}/").json()["score"]["criteria"][0]
    assert first["unverified"] is True and first["evidence_status"] == "verified"


def test_identical_cv_text_on_the_same_scorecard_is_scored_once(world, req_a, monkeypatch):
    calls = stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(c, quote="Wrote Java services and tuned Hibernate queries") for c in cs]), model="fake"))
    first = world.candidate(req_a, SAMPLE_CV, score=False)
    second = world.candidate(req_a, SAMPLE_CV, score=False)
    s.score_candidate(first)
    s.score_candidate(second)
    assert len(calls) == 1  # cache by (cv hash, scorecard)
    assert s.score_candidate(first, force=True) and len(calls) == 2  # a forced retry really asks again


def test_a_new_scorecard_version_forces_a_fresh_score(world, req_a, cand, monkeypatch):
    calls = stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(c, quote="Wrote Java services and tuned Hibernate queries") for c in cs]), model="fake"))
    s.score_candidate(cand)
    from requisitions.services import save_scorecard
    card2 = save_scorecard(req_a, world.recruiter, [{"name": "Java", "weight": 2, "is_must_have": True}])
    s.score_candidate(cand, card2)
    assert len(calls) == 2 and Score.objects.filter(candidate=cand).count() == 2 and Scorecard.objects.filter(requisition=req_a).count() == 2


def test_a_score_never_moves_a_candidate_to_rejected_or_submitted(world, req_a, monkeypatch):
    stub(monkeypatch, lambda cs, p: LLMResult(data=CVScoring(results=[result(c, points=0) for c in cs]), model="fake"))
    c = world.candidate(req_a, SAMPLE_CV, score=False)
    from candidates.services import after_scoring
    after_scoring(c, s.score_candidate(c))
    c.refresh_from_db()
    assert c.stage in (Stage.SOURCED, Stage.SCREENED)
