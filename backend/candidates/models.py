import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from requisitions.models import Requisition


class Stage(models.TextChoices):
    SOURCED = "sourced", "Sourced"
    SCREENED = "screened", "Screened"
    SUBMITTED = "submitted", "Submitted"
    SHORTLISTED = "shortlisted", "Shortlisted"
    INTERVIEW = "interview", "Interview"
    OFFERED = "offered", "Offered"
    JOINED = "joined", "Joined"
    REJECTED = "rejected", "Rejected"  # human (client) decision only; never set from a score


class CandidateQuerySet(models.QuerySet):
    def active(self) -> "CandidateQuerySet":
        """Excludes candidates deleted on request."""
        return self.filter(deleted_at__isnull=True)

    def visible_to(self, user) -> "CandidateQuerySet":
        """The only way client-facing code may fetch candidates (rule 5).

        Clients: only candidates with a Submission to their org. Internal roles: all active.
        Anyone else (anonymous, unknown role): nothing. Deleted candidates never appear.
        """
        from accounts.models import Role

        qs = self.active()
        if not getattr(user, "is_authenticated", False):
            return qs.none()
        if user.role == Role.CLIENT:
            if user.client_org_id is None:
                return qs.none()
            return qs.filter(submission__isnull=False, requisition__client_org_id=user.client_org_id)
        if user.role in (Role.RECRUITER, Role.DELIVERY_HEAD):
            return qs
        return qs.none()


class Candidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # A11: a candidate record is one CV screened against one requisition
    requisition = models.ForeignKey(Requisition, on_delete=models.PROTECT, related_name="candidates")
    external_id = models.CharField(max_length=30, blank=True)  # e.g. CND-91022
    full_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email_normalized = models.CharField(max_length=254, blank=True, db_index=True)
    phone_normalized = models.CharField(max_length=15, blank=True, db_index=True)
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.SOURCED)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = CandidateQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["requisition", "stage"])]

    def __str__(self) -> str:
        return self.external_id or str(self.id)


class CVFile(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PARSED = "parsed", "Parsed"
        NEEDS_REVIEW = "needs_review", "Needs manual review"  # scanned / empty text (A3)
        DUPLICATE = "duplicate", "Duplicate"
        FAILED = "failed", "Failed"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="cv_files")
    file = models.FileField(upload_to="cvs/%Y/%m/", blank=True)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.QUEUED)
    error = models.CharField(max_length=500, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)


class ParsedProfile(models.Model):
    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name="profile")
    raw_text = models.TextField(blank=True)
    text_hash = models.CharField(max_length=64, blank=True, db_index=True)  # cv_hash for the LLM cache
    current_role = models.CharField(max_length=200, blank=True)
    experience_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    notice_days = models.PositiveSmallIntegerField(null=True, blank=True)
    location = models.CharField(max_length=120, blank=True)
    current_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_ctc = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class Consent(models.Model):
    """A5: recorded on upload by the recruiter on the candidate's behalf."""

    class Source(models.TextChoices):
        RECRUITER_ON_BEHALF = "recruiter_on_behalf", "Recorded by recruiter on candidate's behalf"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="consents")
    source = models.CharField(max_length=30, choices=Source.choices, default=Source.RECRUITER_ON_BEHALF)
    purpose = models.CharField(max_length=60, default="hiring_use_only")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    recorded_at = models.DateTimeField(default=timezone.now)


class Tombstone(models.Model):
    """A6: proof a candidate was deleted, holding no personal data."""

    candidate_id = models.UUIDField(unique=True)
    deleted_at = models.DateTimeField(default=timezone.now)
    requester = models.CharField(max_length=120, default="candidate")
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )


class StageEvent(models.Model):
    """Every pipeline stage change is logged (who, from, to, when)."""

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="stage_events")
    from_stage = models.CharField(max_length=12, choices=Stage.choices)
    to_stage = models.CharField(max_length=12, choices=Stage.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reason = models.CharField(max_length=500, blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["changed_at"]
