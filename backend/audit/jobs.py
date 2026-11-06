"""Database-backed job queue (no Celery/Redis). `run_pending` is what `manage.py run_worker` loops on.

CV processing is queued and handled in small batches; a failing job backs off exponentially.
"""
import logging
from collections.abc import Callable
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from audit.models import Job

log = logging.getLogger(__name__)
HANDLERS: dict[str, Callable[[dict, Job], None]] = {}
STALE_AFTER = timedelta(minutes=10)


def register(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn

    return deco


def enqueue(kind: str, payload: dict | None = None, *, run_after=None, max_attempts: int = 3) -> Job:
    return Job.objects.create(kind=kind, payload=payload or {}, max_attempts=max_attempts,
                              run_after=run_after or timezone.now())


def claim_next() -> Job | None:
    with transaction.atomic():
        job = (
            Job.objects.select_for_update(skip_locked=True)
            .filter(status=Job.Status.QUEUED, run_after__lte=timezone.now())
            .order_by("id").first()
        )
        if job is None:
            return None
        job.status, job.locked_at, job.attempts = Job.Status.RUNNING, timezone.now(), job.attempts + 1
        job.save(update_fields=["status", "locked_at", "attempts", "updated_at"])
        return job


def requeue_stale() -> int:
    """A worker that died mid-job leaves it RUNNING; put those back."""
    return Job.objects.filter(status=Job.Status.RUNNING, locked_at__lt=timezone.now() - STALE_AFTER).update(
        status=Job.Status.QUEUED, locked_at=None)


def run_job(job: Job) -> None:
    from audit import handlers  # noqa: F401  (registers handlers)

    handler = HANDLERS.get(job.kind)
    try:
        if handler is None:
            raise LookupError(f"No handler for job kind {job.kind!r}")
        handler(job.payload, job)
    except Exception as exc:  # noqa: BLE001 - any failure is recorded and retried with backoff
        log.warning("Job %s (%s) failed on attempt %s: %s", job.pk, job.kind, job.attempts, exc)
        job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        job.locked_at = None
        if job.attempts >= job.max_attempts:
            job.status = Job.Status.FAILED
        else:
            job.status = Job.Status.QUEUED
            delay = float(settings.WORKER_BACKOFF_SECONDS) * (2 ** (job.attempts - 1))
            job.run_after = timezone.now() + timedelta(seconds=delay)
        job.save()
        return
    job.status, job.locked_at = Job.Status.DONE, None
    job.save(update_fields=["status", "locked_at", "updated_at"])


def run_pending(limit: int | None = None) -> int:
    """Process up to `limit` due jobs (default: one batch). Returns how many ran."""
    limit = limit or int(settings.WORKER_BATCH_SIZE)
    requeue_stale()
    done = 0
    while done < limit:
        job = claim_next()
        if job is None:
            break
        run_job(job)
        done += 1
    return done
