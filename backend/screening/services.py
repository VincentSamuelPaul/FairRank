"""Scoring pipeline: redact -> LLM -> verify evidence -> weight -> band -> save.

Nothing in this module changes a candidate's stage based on the score value (rule 1).
"""
import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from ai import prompts
from ai.evidence import cap_weak_evidence, verify_quote
from ai.llm import LLMError, LLMRateLimited, call_llm
from ai.redact import redact_for_scoring
from ai.schemas import CriterionResult, CVScoring
from candidates.models import Candidate
from requisitions.models import Scorecard
from screening.models import CriterionScore, Score

log = logging.getLogger(__name__)

STRONG_MIN = Decimal("75")  # A2
POSSIBLE_MIN = Decimal("50")
LOW_CONFIDENCE = 0.5  # below this a criterion is shown as "Unverified"
MIN_CV_CHARS = 50  # fewer extracted characters than this = scanned / empty (A3)


def band_for(total: Decimal) -> str:
    if total >= STRONG_MIN:
        return Score.Band.STRONG
    if total >= POSSIBLE_MIN:
        return Score.Band.POSSIBLE
    return Score.Band.WEAK


def weighted_total(points_and_weights: list[tuple[int, int]]) -> Decimal:
    """Weighted mean of 0-100 points, to 2 dp (A1: weights come from the scorecard)."""
    total_weight = sum(w for _, w in points_and_weights)
    if total_weight == 0:
        return Decimal("0.00")
    raw = Decimal(sum(p * w for p, w in points_and_weights)) / Decimal(total_weight)
    return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_criterion(result: CriterionResult | None, cv_text: str, name: str = "") -> tuple[int, float, str, str, str]:
    """Apply rule 2 to one LLM result -> (points, confidence, quote, evidence_status, rationale).

    An unverifiable quote is dropped and the criterion is marked "No evidence found". With no
    verified quote a criterion earns 0 points (A15): the score never rests on an unshown claim.
    """
    if result is None:
        return 0, 0.0, "", CriterionScore.EvidenceStatus.NO_EVIDENCE, "The scorer returned nothing for this criterion"
    quote = verify_quote(cv_text, result.quote)
    if quote is None:
        return 0, result.confidence, "", CriterionScore.EvidenceStatus.NO_EVIDENCE, result.rationale
    points, conf, kind = cap_weak_evidence(name, result.points, result.confidence, quote)
    why = result.rationale
    if (points, conf) != (result.points, result.confidence):
        why = f"{why} (Capped: the only evidence is a {'job title' if kind == 'title' else 'skills list'}, not work described in the CV.)".strip()
    return points, conf, quote, CriterionScore.EvidenceStatus.VERIFIED, why


def build_criterion_rows(scorecard: Scorecard, scoring: CVScoring, cv_text: str) -> list[dict]:
    by_id = {r.criterion_id: r for r in scoring.results}
    rows = []
    for criterion in scorecard.criteria.all():
        points, conf, quote, status, why = resolve_criterion(by_id.get(criterion.id), cv_text, criterion.name)
        rows.append({
            "criterion": criterion, "points": points, "confidence": conf,
            "evidence_quote": quote, "evidence_status": status, "rationale": why[:500],
        })
    return rows


def _criteria_payload(scorecard: Scorecard) -> list[dict]:
    return [
        {"id": c.id, "name": c.name, "description": c.description, "is_must_have": c.is_must_have}
        for c in scorecard.criteria.all()
    ]


def _save(candidate: Candidate, scorecard: Scorecard, **fields) -> Score:
    with transaction.atomic():
        score, _ = Score.objects.update_or_create(candidate=candidate, scorecard=scorecard, defaults=fields)
        score.criterion_scores.all().delete()
        return score


def mark_needs_manual_review(candidate: Candidate, scorecard: Scorecard) -> Score:
    """Scanned / empty-text CV: no fake score (rule 9, A3)."""
    return _save(candidate, scorecard, status=Score.Status.NEEDS_MANUAL_REVIEW, total_score=None, band=None,
                 cv_hash="", model_name="", error="No readable text in the file (scanned or image-only).")


def _cached(candidate: Candidate, scorecard: Scorecard, cv_hash: str) -> Score | None:
    """Cache by (cv_hash, scorecard): a finished score for the same CV text on this scorecard."""
    return (
        Score.objects.filter(scorecard=scorecard, cv_hash=cv_hash, status=Score.Status.SCORED)
        .exclude(candidate=candidate).order_by("id").first()
    )


def score_candidate(candidate: Candidate, scorecard: Scorecard | None = None, *, final_attempt: bool = True,
                    force: bool = False) -> Score:
    """Score one candidate's CV against a scorecard version.

    LLM failure after the retry -> a stored "failed" Score (CV stays visible, user can retry).
    If `final_attempt` is False a rate-limit is re-raised so the job queue backs off and retries.
    """
    scorecard = scorecard or candidate.requisition.current_scorecard
    if scorecard is None:
        raise ValueError("Requisition has no scorecard")
    profile = candidate.profile
    cv_text = profile.raw_text
    if len(cv_text.strip()) < MIN_CV_CHARS:
        return mark_needs_manual_review(candidate, scorecard)

    existing = Score.objects.filter(candidate=candidate, scorecard=scorecard).first()
    if not force and existing and existing.status == Score.Status.SCORED and existing.cv_hash == profile.text_hash:
        return existing
    if not force:
        hit = _cached(candidate, scorecard, profile.text_hash)
        if hit is not None:
            return _copy_score(hit, candidate)

    redacted = redact_for_scoring(cv_text, candidate.full_name)
    criteria = _criteria_payload(scorecard)
    try:
        result = call_llm(
            prompts.scoring_prompt(redacted, criteria), CVScoring,
            context={"cv_text": redacted, "criteria": criteria, "original_text": cv_text},
        )
    except LLMRateLimited:
        if not final_attempt:
            raise
        return _failed(candidate, scorecard, profile.text_hash, "The AI service is busy. Please retry.")
    except LLMError as exc:
        log.warning("Scoring failed for %s: %s", candidate.pk, exc)
        return _failed(candidate, scorecard, profile.text_hash, "The AI could not score this CV. Please retry.")

    rows = build_criterion_rows(scorecard, result.data, cv_text)  # verified against the ORIGINAL text
    total = weighted_total([(r["points"], r["criterion"].weight) for r in rows])
    with transaction.atomic():
        score = _save(candidate, scorecard, status=Score.Status.SCORED, total_score=total, band=band_for(total),
                      cv_hash=profile.text_hash, model_name=result.model, error="")
        CriterionScore.objects.bulk_create(CriterionScore(score=score, **r) for r in rows)
    return score


def _failed(candidate: Candidate, scorecard: Scorecard, cv_hash: str, message: str) -> Score:
    return _save(candidate, scorecard, status=Score.Status.FAILED, total_score=None, band=None,
                 cv_hash=cv_hash, model_name="", error=message)


def _copy_score(source: Score, candidate: Candidate) -> Score:
    with transaction.atomic():
        score = _save(candidate, source.scorecard, status=source.status, total_score=source.total_score,
                      band=source.band, cv_hash=source.cv_hash, model_name=source.model_name, error="")
        CriterionScore.objects.bulk_create(
            CriterionScore(score=score, criterion_id=c.criterion_id, points=c.points, confidence=c.confidence,
                           evidence_quote=c.evidence_quote, evidence_status=c.evidence_status, rationale=c.rationale)
            for c in source.criterion_scores.all()
        )
    return score
