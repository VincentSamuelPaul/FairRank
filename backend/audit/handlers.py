"""Job handlers. Imported lazily by audit.jobs.run_job so the registry fills on first use."""
from audit.jobs import register
from audit.models import Job


@register("process_cv")
def process_cv_job(payload: dict, job: Job) -> None:
    from candidates.services import process_cv

    process_cv(payload["candidate_id"])


@register("score_candidate")
def score_candidate_job(payload: dict, job: Job) -> None:
    from candidates.models import Candidate
    from candidates.services import after_scoring
    from screening.services import score_candidate

    candidate = Candidate.objects.active().select_related("requisition").filter(pk=payload["candidate_id"]).first()
    if candidate is None or not hasattr(candidate, "profile"):
        return  # deleted while queued: nothing to do
    scorecard = None
    if payload.get("scorecard_id"):
        from requisitions.models import Scorecard

        scorecard = Scorecard.objects.filter(pk=payload["scorecard_id"]).first()
    score = score_candidate(candidate, scorecard, final_attempt=job.attempts >= job.max_attempts,
                            force=bool(payload.get("force")))
    after_scoring(candidate, score)


@register("weekly_agreement_report")
def weekly_agreement_report_job(payload: dict, job: Job) -> None:
    from portal.reports import send_weekly_report

    send_weekly_report()
