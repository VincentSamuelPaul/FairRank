from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import Q

from candidates.models import Candidate
from requisitions.models import Scorecard, ScorecardCriterion


class Score(models.Model):
    """The result of scoring one candidate against one scorecard version.

    Scores only describe; nothing here changes a candidate's stage (no auto-reject).
    """

    class Status(models.TextChoices):
        SCORED = "scored", "Scored"
        NEEDS_MANUAL_REVIEW = "needs_manual_review", "Needs manual review"  # scan / empty text
        FAILED = "failed", "Scoring failed, retry"

    class Band(models.TextChoices):  # A2: Strong >= 75, Possible 50-74, Weak < 50
        STRONG = "strong", "Strong"
        POSSIBLE = "possible", "Possible"
        WEAK = "weak", "Weak"

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="scores")
    scorecard = models.ForeignKey(Scorecard, on_delete=models.PROTECT, related_name="scores")
    status = models.CharField(max_length=20, choices=Status.choices)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    band = models.CharField(max_length=10, choices=Band.choices, null=True, blank=True)
    cv_hash = models.CharField(max_length=64, blank=True)  # cache key = (cv_hash, scorecard version)
    model_name = models.CharField(max_length=80, blank=True)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["candidate", "scorecard"], name="uniq_score_per_scorecard"),
            # No fake scores: a number and band exist only when status is "scored".
            models.CheckConstraint(
                condition=Q(status="scored", total_score__isnull=False, band__isnull=False)
                | (~Q(status="scored") & Q(total_score__isnull=True, band__isnull=True)),
                name="score_number_only_when_scored",
            ),
        ]
        indexes = [models.Index(fields=["scorecard", "-total_score"])]


class CriterionScore(models.Model):
    class EvidenceStatus(models.TextChoices):
        VERIFIED = "verified", "Verified quote"
        NO_EVIDENCE = "no_evidence", "No evidence found"

    score = models.ForeignKey(Score, on_delete=models.CASCADE, related_name="criterion_scores")
    criterion = models.ForeignKey(ScorecardCriterion, on_delete=models.PROTECT, related_name="+")
    points = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])  # 0-100
    confidence = models.FloatField(default=1.0)  # low confidence is shown as "Unverified"
    evidence_quote = models.TextField(blank=True)
    evidence_status = models.CharField(max_length=12, choices=EvidenceStatus.choices)
    rationale = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["score", "criterion"], name="uniq_criterion_score"),
            # Rule 2: a quote exists only if it was verified against the CV text.
            models.CheckConstraint(
                condition=(Q(evidence_status="verified") & ~Q(evidence_quote=""))
                | (Q(evidence_status="no_evidence") & Q(evidence_quote="")),
                name="evidence_quote_iff_verified",
            ),
            models.CheckConstraint(condition=Q(points__lte=100), name="criterion_points_lte_100"),
        ]
