import uuid

from django.conf import settings
from django.db import models

from accounts.models import ClientOrg


class Requisition(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    client_org = models.ForeignKey(ClientOrg, on_delete=models.PROTECT, related_name="requisitions")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    jd_text = models.TextField()
    location = models.CharField(max_length=120, blank=True)
    exp_min_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    exp_max_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    notice_max_days = models.PositiveSmallIntegerField(null=True, blank=True)
    ctc_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ctc_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def current_scorecard(self) -> "Scorecard | None":
        return self.scorecards.order_by("-version").first()


class Scorecard(models.Model):
    """One immutable version of a requisition's scoring criteria. Editing creates a new version."""

    class Source(models.TextChoices):
        AI = "ai", "AI-extracted from JD"
        MANUAL = "manual", "Edited by recruiter"

    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE, related_name="scorecards")
    version = models.PositiveIntegerField()
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["requisition", "version"], name="uniq_scorecard_version")
        ]
        ordering = ["requisition", "-version"]

    def __str__(self) -> str:
        return f"{self.requisition} v{self.version}"


class ScorecardCriterion(models.Model):
    scorecard = models.ForeignKey(Scorecard, on_delete=models.CASCADE, related_name="criteria")
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    # A1: default must-have = 3, nice-to-have = 1, editable by the recruiter
    weight = models.PositiveSmallIntegerField(default=1)
    is_must_have = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(weight__gte=1, weight__lte=10), name="criterion_weight_1_10")
        ]

    def __str__(self) -> str:
        return self.name
