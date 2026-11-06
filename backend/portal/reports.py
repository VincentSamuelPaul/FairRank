"""AI-vs-recruiter agreement report for the delivery head (A8).

Question answered: of the candidates recruiters submitted in the window, how many were in the AI's
top N for that requisition (N = number submitted)? Disagreements are listed so they can be reviewed.
This is a sample for human review; nothing here changes any candidate.
"""
from datetime import timedelta

from django.utils import timezone

from accounts.models import Role, User
from audit.models import Notification
from candidates.models import Candidate, Stage
from portal.models import Submission
from requisitions.models import Requisition
from screening.models import Score

ACCEPTED = {Stage.SHORTLISTED, Stage.INTERVIEW, Stage.OFFERED, Stage.JOINED}


def _ranked(requisition: Requisition) -> list[tuple[Candidate, Score]]:
    card = requisition.current_scorecard
    if card is None:
        return []
    scores = (Score.objects.filter(scorecard=card, status=Score.Status.SCORED, candidate__deleted_at__isnull=True)
              .select_related("candidate").order_by("-total_score", "candidate__created_at"))
    return [(s.candidate, s) for s in scores]


def _person(c: Candidate, rank: int | None, score: Score | None) -> dict:
    return {"candidate_id": str(c.pk), "name": c.full_name or "Unnamed", "external_id": c.external_id,
            "ai_rank": rank, "score": float(score.total_score) if score else None, "band": score.band if score else None}


def agreement_report(days: int = 7, now=None) -> dict:
    now = now or timezone.now()
    since = now - timedelta(days=days)
    subs = (Submission.objects.filter(submitted_at__gte=since, candidate__deleted_at__isnull=True)
            .select_related("candidate", "candidate__requisition", "candidate__requisition__client_org"))
    by_req: dict[Requisition, list[Submission]] = {}
    for s in subs:
        by_req.setdefault(s.candidate.requisition, []).append(s)

    rows, total_n, total_overlap = [], 0, 0
    for req, req_subs in sorted(by_req.items(), key=lambda kv: kv[0].title):
        ranked = _ranked(req)
        rank_of = {c.pk: (i + 1, sc) for i, (c, sc) in enumerate(ranked)}
        chosen = {s.candidate_id: s.candidate for s in req_subs}
        n = len(chosen)
        top = {c.pk: (i + 1, sc, c) for i, (c, sc) in enumerate(ranked[:n])}
        overlap = len(set(top) & set(chosen))
        disagreements = [
            {"type": "recruiter_chose_lower_ranked", **_person(c, *(rank_of.get(c.pk) or (None, None)))}
            for c in chosen.values() if c.pk not in top
        ] + [
            {"type": "ai_ranked_higher_not_submitted", **_person(c, rank, sc)}
            for pk, (rank, sc, c) in top.items() if pk not in chosen
        ]
        rows.append({
            "requisition_id": str(req.pk), "title": req.title, "client": req.client_org.name,
            "submitted": n, "in_ai_top_n": overlap, "agreement_pct": round(100 * overlap / n) if n else None,
            "disagreements": disagreements,
        })
        total_n, total_overlap = total_n + n, total_overlap + overlap

    return {
        "window_days": days, "generated_at": now.isoformat(),
        "overall": {"requisitions": len(rows), "submitted": total_n,
                    "agreement_pct": round(100 * total_overlap / total_n) if total_n else None},
        "requisitions": rows,
        "acceptance_by_band": _acceptance(subs),
    }


def _acceptance(subs) -> list[dict]:
    out = []
    for band in (Score.Band.STRONG, Score.Band.POSSIBLE, Score.Band.WEAK, None):
        group = []
        for s in subs:
            card = s.candidate.requisition.current_scorecard
            sc = Score.objects.filter(candidate=s.candidate, scorecard=card, status=Score.Status.SCORED).first() if card else None
            if (sc.band if sc else None) == band:
                group.append(s.candidate.stage)
        out.append({"band": band or "unscored", "submitted": len(group),
                    "accepted": sum(st in ACCEPTED for st in group),
                    "rejected": sum(st == Stage.REJECTED for st in group),
                    "pending": sum(st == Stage.SUBMITTED for st in group)})
    return out


def send_weekly_report() -> int:
    """Weekly job: compute the report and 'email' a summary to delivery heads (mock, A10)."""
    report = agreement_report(7)
    overall = report["overall"]
    pct = "n/a" if overall["agreement_pct"] is None else f"{overall['agreement_pct']}%"
    body = (f"Last 7 days: {overall['submitted']} submissions across {overall['requisitions']} requisitions. "
            f"Recruiter choices matched the AI's top picks {pct} of the time. Open the report for details.")
    heads = list(User.objects.filter(role=Role.DELIVERY_HEAD))
    Notification.objects.bulk_create(Notification(recipient=h, subject="Weekly AI vs recruiter agreement", body=body)
                                     for h in heads)
    return len(heads)
