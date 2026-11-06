"""JD intake and scorecard versioning."""
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Max

from accounts.models import ClientOrg
from ai import prompts
from ai.llm import LLMError, call_llm
from ai.schemas import JDExtraction
from audit import jobs
from candidates.models import Candidate, CVFile
from requisitions.models import Requisition, Scorecard, ScorecardCriterion
from screening.services import mark_needs_manual_review

log = logging.getLogger(__name__)
MUST_HAVE_WEIGHT, NICE_TO_HAVE_WEIGHT = 3, 1  # A1


def _dec(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


@transaction.atomic
def save_scorecard(requisition: Requisition, user, criteria: list[dict], source: str = Scorecard.Source.MANUAL) -> Scorecard:
    """Scorecards are immutable: every edit is a new version, so old scores stay explainable."""
    last = requisition.scorecards.aggregate(m=Max("version"))["m"] or 0
    card = Scorecard.objects.create(requisition=requisition, version=last + 1, source=source, created_by=user)
    ScorecardCriterion.objects.bulk_create(
        ScorecardCriterion(scorecard=card, name=c["name"].strip(), description=c.get("description", "").strip(),
                           weight=c["weight"], is_must_have=c["is_must_have"], order=i)
        for i, c in enumerate(criteria)
    )
    return card


def create_requisition(user, client_org: ClientOrg, jd_text: str, title: str = "") -> tuple[Requisition, str]:
    """Create a requisition and ask the AI for a v1 scorecard. Returns (requisition, warning).

    If extraction fails the requisition is still created (with no scorecard) so the recruiter can
    build the scorecard by hand: the AI being down never blocks the work.
    """
    warning = ""
    extraction: JDExtraction | None = None
    try:
        extraction = call_llm(prompts.jd_prompt(jd_text), JDExtraction, context={"jd_text": jd_text}).data
    except LLMError as exc:
        log.warning("JD extraction failed: %s", exc)
        warning = "The AI could not read this JD. Add the criteria yourself in the scorecard editor."
    with transaction.atomic():
        req = Requisition.objects.create(
            title=(title or (extraction.title if extraction else "") or "Untitled requisition")[:200],
            client_org=client_org, created_by=user, jd_text=jd_text,
            location=extraction.location if extraction else "",
            exp_min_years=_dec(extraction.exp_min_years) if extraction else None,
            exp_max_years=_dec(extraction.exp_max_years) if extraction else None,
            notice_max_days=extraction.notice_max_days if extraction else None,
            ctc_min=_dec(extraction.ctc_min) if extraction else None,
            ctc_max=_dec(extraction.ctc_max) if extraction else None,
        )
        if extraction:
            save_scorecard(req, user, [
                {"name": c.name, "description": c.description,
                 "weight": MUST_HAVE_WEIGHT if c.is_must_have else NICE_TO_HAVE_WEIGHT, "is_must_have": c.is_must_have}
                for c in extraction.criteria
            ], source=Scorecard.Source.AI)
    return req, warning


def queue_rescore(requisition: Requisition, scorecard: Scorecard, *, force: bool = False) -> int:
    """Score every readable candidate against `scorecard` (needed after a scorecard edit)."""
    queued = 0
    for c in Candidate.objects.active().filter(requisition=requisition).select_related("profile"):
        profile = getattr(c, "profile", None)
        cv = c.cv_files.order_by("id").first()
        if profile is None or cv is None or cv.status in (CVFile.Status.QUEUED, CVFile.Status.FAILED):
            continue
        if cv.status == CVFile.Status.NEEDS_REVIEW:
            mark_needs_manual_review(c, scorecard)
            continue
        jobs.enqueue("score_candidate", {"candidate_id": str(c.pk), "scorecard_id": scorecard.pk, "force": force})
        queued += 1
    return queued
