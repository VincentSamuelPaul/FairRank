"""Submit-to-client and the client's decisions. Every stage change goes through candidates.services."""
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from audit.models import Notification
from audit.services import has_viewed
from candidates.models import Candidate, Stage
from candidates.services import change_stage
from portal.models import ClientDecision, InterviewSlot, Submission


class NotOpened(Exception):
    """Rule 4: the recruiter has not opened this candidate's CV."""


class Conflict(Exception):
    """The action does not fit the candidate's current state."""


def _notify(recipients, subject: str, body: str) -> None:
    Notification.objects.bulk_create(Notification(recipient=r, subject=subject, body=body) for r in recipients)


@transaction.atomic
def submit_candidate(candidate: Candidate, recruiter: User, note: str = "") -> Submission:
    """Submit to the requisition's client. Enforced here, not only in the UI (rule 4)."""
    if not has_viewed(recruiter, candidate):
        raise NotOpened("Open the CV before submitting this candidate.")
    if hasattr(candidate, "submission") or candidate.stage not in (Stage.SOURCED, Stage.SCREENED):
        raise Conflict("This candidate has already been submitted.")
    sub = Submission.objects.create(candidate=candidate, submitted_by=recruiter, note=note)
    change_stage(candidate, Stage.SUBMITTED, recruiter, "Submitted to client")
    _notify(
        User.objects.filter(role=Role.CLIENT, client_org=candidate.requisition.client_org),
        f"New candidate for {candidate.requisition.title}",
        "A new candidate is ready for your review in the FairRank portal.",
    )
    return sub


@transaction.atomic
def client_decide(candidate: Candidate, client: User, decision: str, reason: str = "") -> ClientDecision:
    """A human decision by the client. Shortlist or reject (reason required); never driven by a score."""
    if candidate.stage not in (Stage.SUBMITTED, Stage.SHORTLISTED):
        raise Conflict("A decision was already made for this candidate.")
    if decision == ClientDecision.Decision.REJECT and not reason.strip():
        raise ValueError("A reason is required to reject a candidate.")
    sub = candidate.submission
    row = ClientDecision.objects.create(submission=sub, decision=decision, reason=reason.strip(), decided_by=client)
    to_stage = Stage.SHORTLISTED if decision == ClientDecision.Decision.SHORTLIST else Stage.REJECTED
    change_stage(candidate, to_stage, client, reason.strip())
    if sub.submitted_by:
        _notify([sub.submitted_by], f"Client {decision}ed a candidate for {candidate.requisition.title}", reason.strip())
    return row


@transaction.atomic
def propose_slot(candidate: Candidate, client: User, starts_at, duration_minutes: int = 30, note: str = "") -> InterviewSlot:
    """Propose an interview time. This moves the candidate to the interview stage, which unmasks contacts (A7)."""
    if candidate.stage not in (Stage.SUBMITTED, Stage.SHORTLISTED, Stage.INTERVIEW):
        raise Conflict("Interviews can only be proposed for submitted or shortlisted candidates.")
    if starts_at <= timezone.now():
        raise ValueError("Pick a time in the future.")
    slot = InterviewSlot.objects.create(submission=candidate.submission, starts_at=starts_at,
                                        duration_minutes=duration_minutes, note=note, proposed_by=client)
    change_stage(candidate, Stage.INTERVIEW, client, "Interview slot proposed")
    sub = candidate.submission
    if sub.submitted_by:
        _notify([sub.submitted_by], f"Interview proposed for {candidate.requisition.title}",
                f"Proposed {starts_at:%d %b %Y %H:%M}.")
    return slot


def respond_slot(slot: InterviewSlot, status: str) -> InterviewSlot:
    slot.status = status
    slot.save(update_fields=["status"])
    return slot
