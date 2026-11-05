from django.conf import settings
from django.db import models
from django.utils import timezone

from candidates.models import Candidate


class ViewLog(models.Model):
    """Who opened which candidate profile/CV, and when. Write via audit.services.log_view only."""

    class Kind(models.TextChoices):
        PROFILE = "profile", "Profile"
        CV = "cv", "CV file"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="view_logs")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["user", "candidate"])]
        ordering = ["-viewed_at"]


class Job(models.Model):
    """Database-backed queue, drained by `manage.py run_worker`."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=60)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    run_after = models.DateTimeField(default=timezone.now)  # exponential backoff pushes this out
    locked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "run_after"])]
        ordering = ["id"]


class Notification(models.Model):
    """A10: email/SMS are mocked; every 'send' is just a row here."""

    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    channel = models.CharField(max_length=5, choices=Channel.choices, default=Channel.EMAIL)
    subject = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
