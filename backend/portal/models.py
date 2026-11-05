from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from candidates.models import Candidate


class Submission(models.Model):
    """A recruiter submitted this candidate to the requisition's client.

    The open-before-submit rule (a ViewLog must exist) is enforced in the service layer.
    """

    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name="submission")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    submitted_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=500, blank=True)

    @property
    def client_org_id(self) -> int:
        return self.candidate.requisition.client_org_id


class ClientDecision(models.Model):
    class Decision(models.TextChoices):
        SHORTLIST = "shortlist", "Shortlist"
        REJECT = "reject", "Reject"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="decisions")
    decision = models.CharField(max_length=10, choices=Decision.choices)
    reason = models.CharField(max_length=500, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-decided_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(decision="reject") | ~Q(reason=""), name="reject_requires_reason"
            )
        ]


class InterviewSlot(models.Model):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="slots")
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PROPOSED)
    note = models.CharField(max_length=300, blank=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]
