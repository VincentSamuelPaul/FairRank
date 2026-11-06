"""Rule 2: a quote is shown only if it is an exact substring of the CV text (whitespace-normalised)."""
import pytest

from ai.evidence import locate_quote, verify_quote
from ai.schemas import CriterionResult, CVScoring
from screening.models import CriterionScore, Score
from screening.services import score_candidate

CV = "Built Spring Boot microservices\nfor payment workflows.\nWrote   Java services."


def test_real_quote_is_kept():
    assert verify_quote(CV, "Wrote Java services.") == "Wrote Java services."


def test_whitespace_normalised_match_works():
    assert verify_quote(CV, "Built Spring Boot microservices for payment workflows.") is not None
    assert verify_quote(CV, "Wrote Java    services.") is not None


def test_invented_quote_is_dropped():
    assert verify_quote(CV, "Led a team of 40 engineers at Google") is None


def test_case_and_wording_must_match_exactly():
    assert verify_quote(CV, "built spring boot microservices") is None  # only whitespace is normalised
    assert verify_quote(CV, "Built Spring Boot services") is None


def test_empty_or_tiny_quotes_are_rejected():
    assert verify_quote(CV, "") is None and verify_quote(CV, "  ") is None and verify_quote(CV, "ab") is None


def test_locate_quote_gives_span_in_original_text():
    start, end = locate_quote(CV, "microservices for payment")
    assert CV[start:end].split() == ["microservices", "for", "payment"]


@pytest.mark.django_db
def test_invented_quote_never_reaches_the_database(monkeypatch, req_a, make_candidate):
    cand = make_candidate(req_a, score=False)
    java, spring, noida = list(req_a.current_scorecard.criteria.all())

    def fake_llm(prompt, schema, context=None):
        from ai.llm import LLMResult

        return LLMResult(model="fake", data=CVScoring(results=[
            CriterionResult(criterion_id=java.id, points=90, confidence=0.9, quote="Wrote Java services and tuned\nHibernate queries"),
            CriterionResult(criterion_id=spring.id, points=95, confidence=0.9, quote="Architected Spring Boot at Google scale"),
            CriterionResult(criterion_id=noida.id, points=100, confidence=0.9, quote="Location: Noida"),
        ]))

    monkeypatch.setattr("screening.services.call_llm", fake_llm)
    score = score_candidate(cand)
    rows = {c.criterion_id: c for c in score.criterion_scores.all()}
    assert rows[java.id].evidence_status == CriterionScore.EvidenceStatus.VERIFIED
    assert rows[java.id].evidence_quote == "Wrote Java services and tuned Hibernate queries"
    invented = rows[spring.id]
    assert invented.evidence_status == CriterionScore.EvidenceStatus.NO_EVIDENCE
    assert invented.evidence_quote == "" and invented.points == 0  # nothing unverified is displayed or credited
    assert score.status == Score.Status.SCORED
