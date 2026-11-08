"""Builds the JSON the API returns. Staff payloads carry raw contacts; client payloads never do
(rule 6): they go through `client_*` builders which mask contacts until the interview stage (A7)."""
from django.db.models import Prefetch

from ai.evidence import locate_quote
from ai.redact import hide_protected_lines, mask_contacts_in_text, mask_email, mask_phone
from audit.models import ViewLog
from candidates.models import Candidate, CVFile, Stage
from candidates.services import allowed_recruiter_moves
from requisitions.models import Scorecard
from screening.models import Score
from screening.services import LOW_CONFIDENCE

UNMASKED_STAGES = {Stage.INTERVIEW, Stage.OFFERED, Stage.JOINED}  # A7


def staff_queryset(requisition, scorecard: Scorecard | None):
    return (
        Candidate.objects.active().filter(requisition=requisition)
        .select_related("profile", "submission", "duplicate_of", "requisition")
        .prefetch_related(
            Prefetch("scores", queryset=Score.objects.filter(scorecard=scorecard).prefetch_related(
                "criterion_scores__criterion")),
            "cv_files",
        )
    )


def _profile(c: Candidate):
    return getattr(c, "profile", None)


def _cv(c: Candidate) -> CVFile | None:
    files = list(c.cv_files.all())
    return files[0] if files else None


def _score(c: Candidate, scorecard: Scorecard | None) -> Score | None:
    if scorecard is None:
        return None
    return next((s for s in c.scores.all() if s.scorecard_id == scorecard.id), None)


def score_state(c: Candidate, scorecard: Scorecard | None) -> str:
    cv, score = _cv(c), _score(c, scorecard)
    if cv is not None and cv.status == CVFile.Status.FAILED:
        return "cv_failed"
    if score is not None:
        return score.status
    if scorecard is None:
        return "no_scorecard"
    if cv is None or cv.status == CVFile.Status.QUEUED or _profile(c) is None:
        return "processing"
    return "pending"


def criteria_payload(score: Score | None, raw_text: str | None = None, *, mask: bool = False) -> list[dict]:
    if score is None or score.status != Score.Status.SCORED:
        return []
    out = []
    for cs in sorted(score.criterion_scores.all(), key=lambda x: (x.criterion.order, x.criterion_id)):
        verified = cs.evidence_status == cs.EvidenceStatus.VERIFIED
        quote = mask_contacts_in_text(cs.evidence_quote) if mask else cs.evidence_quote
        item = {
            "criterion_id": cs.criterion_id, "name": cs.criterion.name, "weight": cs.criterion.weight,
            "is_must_have": cs.criterion.is_must_have, "points": cs.points, "confidence": round(cs.confidence, 2),
            "unverified": verified and cs.confidence < LOW_CONFIDENCE,
            "evidence_status": cs.evidence_status, "quote": quote, "rationale": cs.rationale,
        }
        if raw_text is not None and verified and not mask:
            item["span"] = locate_quote(raw_text, cs.evidence_quote)
        out.append(item)
    return out


def score_payload(c: Candidate, scorecard: Scorecard | None, raw_text: str | None = None, *, mask: bool = False,
                  internal: bool = True) -> dict:
    score = _score(c, scorecard)
    state = score_state(c, scorecard)
    criteria = criteria_payload(score, raw_text, mask=mask)
    payload = {
        "state": state,
        "total": float(score.total_score) if score and score.total_score is not None else None,
        "band": score.band if score else None,
        "criteria": criteria,
        "missing_must_haves": [x["name"] for x in criteria if x["is_must_have"] and x["evidence_status"] == "no_evidence"],
        "scorecard_version": scorecard.version if scorecard else None,
    }
    if internal:
        payload["model"] = score.model_name if score else ""
        payload["error"] = score.error if score and score.status != Score.Status.SCORED else (_cv(c).error if state == "cv_failed" else "")
    return payload


def next_action(c: Candidate, state: str, viewed: bool) -> dict:
    if state == "processing":
        return {"code": "wait", "label": "Processing…"}
    if state == "cv_failed":
        return {"code": "fix_file", "label": "Unreadable file: upload again"}
    if c.stage in (Stage.SUBMITTED, Stage.SHORTLISTED, Stage.INTERVIEW, Stage.OFFERED, Stage.JOINED, Stage.REJECTED):
        label = {
            Stage.SUBMITTED: "Awaiting client", Stage.SHORTLISTED: "Client shortlisted",
            Stage.INTERVIEW: "Interview stage", Stage.OFFERED: "Offer stage", Stage.JOINED: "Joined",
            Stage.REJECTED: "Rejected by client",
        }[c.stage]
        return {"code": "track", "label": label}
    if state == "failed":
        return {"code": "retry", "label": "Retry scoring"}
    if state == "pending":
        return {"code": "wait", "label": "Scoring…"}
    if not viewed:
        return {"code": "open", "label": "Review manually" if state == "needs_manual_review" else "Open CV"}
    return {"code": "submit", "label": "Submit to client"}


def staff_row(c: Candidate, scorecard: Scorecard | None, viewed_ids: set) -> dict:
    p, cv = _profile(c), _cv(c)
    payload = score_payload(c, scorecard)
    dup = c.duplicate_of
    return {
        "id": str(c.pk), "external_id": c.external_id, "full_name": c.full_name, "email": c.email, "phone": c.phone,
        "current_role": p.current_role if p else "",
        "experience_years": float(p.experience_years) if p and p.experience_years is not None else None,
        "notice_days": p.notice_days if p else None, "location": p.location if p else "",
        "skills": p.skills if p else [], "stage": c.stage,
        "cv_status": cv.status if cv else "none", "cv_note": cv.error if cv else "",
        "original_name": cv.original_name if cv else "",
        "duplicate_of": ({"id": str(dup.pk), "external_id": dup.external_id, "full_name": dup.full_name,
                          "same_requisition": dup.requisition_id == c.requisition_id} if dup else None),
        "score": payload, "viewed": c.pk in viewed_ids, "submitted": hasattr(c, "submission"),
        "next_action": next_action(c, payload["state"], c.pk in viewed_ids),
        "created_at": c.created_at.isoformat(),
    }


def viewed_candidate_ids(user, candidates) -> set:
    return set(ViewLog.objects.filter(user=user, candidate__in=candidates).values_list("candidate_id", flat=True))


def staff_detail(c: Candidate, scorecard: Scorecard | None, user) -> dict:
    row = staff_row(c, scorecard, viewed_candidate_ids(user, [c]))
    p = _profile(c)
    raw = p.raw_text if p else ""
    row["score"] = score_payload(c, scorecard, raw)
    sub = getattr(c, "submission", None)
    logs = list(c.view_logs.select_related("user").all()[:10])
    row.update({
        "raw_text": raw,
        "cv_file_url": f"/api/candidates/{c.pk}/cv/" if _cv(c) and _cv(c).file else None,
        "cv_file_kind": ("pdf" if _cv(c) and _cv(c).content_type == "application/pdf" else "docx") if _cv(c) else None,
        "requisition": {"id": str(c.requisition_id), "title": c.requisition.title,
                        "client": c.requisition.client_org.name},
        "consent": [{"source": k.get_source_display(), "purpose": k.purpose, "recorded_at": k.recorded_at.isoformat(),
                     "recorded_by": k.recorded_by.full_name if k.recorded_by else ""} for k in c.consents.all()],
        "view_log": {"total": c.view_logs.count(),
                     "recent": [{"user": v.user.full_name, "kind": v.kind, "at": v.viewed_at.isoformat()} for v in logs]},
        "stage_events": [{"from": e.from_stage, "to": e.to_stage, "at": e.changed_at.isoformat(), "reason": e.reason,
                          "by": e.changed_by.full_name if e.changed_by else "System"} for e in c.stage_events.all()],
        "allowed_moves": allowed_recruiter_moves(c),
        "can_submit": row["viewed"] and c.stage in (Stage.SOURCED, Stage.SCREENED) and sub is None,
        "submission": ({"submitted_at": sub.submitted_at.isoformat(), "note": sub.note,
                        "decisions": [{"decision": d.decision, "reason": d.reason, "at": d.decided_at.isoformat()}
                                      for d in sub.decisions.all()],
                        "slots": [slot_payload(s) for s in sub.slots.all()]} if sub else None),
    })
    return row


def slot_payload(s) -> dict:
    return {"id": s.pk, "starts_at": s.starts_at.isoformat(), "duration_minutes": s.duration_minutes,
            "status": s.status, "note": s.note}


# --- client-facing ----------------------------------------------------------------------------

def client_contacts(c: Candidate) -> dict:
    if c.stage in UNMASKED_STAGES:
        return {"email": c.email, "phone": c.phone, "masked": False}
    return {"email": mask_email(c.email), "phone": mask_phone(c.phone), "masked": True}


def client_card(c: Candidate, scorecard: Scorecard | None, *, detail: bool = False) -> dict:
    p, sub = _profile(c), c.submission
    decisions = list(sub.decisions.all())
    last = decisions[0] if decisions else None
    card = {
        "id": str(c.pk), "full_name": c.full_name, "current_role": p.current_role if p else "",
        "experience_years": float(p.experience_years) if p and p.experience_years is not None else None,
        "notice_days": p.notice_days if p else None, "location": p.location if p else "",
        "skills": (p.skills if p else [])[:8], "stage": c.stage, "contacts": client_contacts(c),
        "score": score_payload(c, scorecard, mask=True, internal=False),
        "requisition": {"id": str(c.requisition_id), "title": c.requisition.title},
        "submitted_at": sub.submitted_at.isoformat(), "recruiter_note": sub.note,
        "decision": ({"decision": last.decision, "reason": last.reason, "at": last.decided_at.isoformat()} if last else None),
        "slots": [slot_payload(s) for s in sub.slots.all()],
    }
    if detail:
        text = hide_protected_lines(p.raw_text) if p else ""  # A20
        card["cv_text"] = text if c.stage in UNMASKED_STAGES else mask_contacts_in_text(text)
    return card
