import pytest
from django.utils import timezone

from audit import jobs
from audit.models import Job

pytestmark = pytest.mark.django_db


def test_failing_job_backs_off_then_fails(settings):
    settings.WORKER_BACKOFF_SECONDS = 60
    job = jobs.enqueue("no_such_handler", max_attempts=2)
    assert jobs.run_pending() == 1
    job.refresh_from_db()
    assert job.status == Job.Status.QUEUED and job.attempts == 1 and job.run_after > timezone.now()
    assert jobs.run_pending() == 0  # not due yet: exponential backoff
    Job.objects.filter(pk=job.pk).update(run_after=timezone.now())
    jobs.run_pending()
    job.refresh_from_db()
    assert job.status == Job.Status.FAILED and "No handler" in job.last_error


def test_batch_size_limits_work_per_tick(settings):
    settings.WORKER_BATCH_SIZE = 2
    for _ in range(5):
        jobs.enqueue("weekly_agreement_report")
    assert jobs.run_pending() == 2
    assert Job.objects.filter(status=Job.Status.QUEUED).count() == 3


def test_stale_running_jobs_are_requeued():
    job = jobs.enqueue("weekly_agreement_report")
    Job.objects.filter(pk=job.pk).update(status=Job.Status.RUNNING, locked_at=timezone.now() - timezone.timedelta(hours=1))
    assert jobs.requeue_stale() == 1


def test_rate_limit_is_retried_by_the_queue_then_fails_gracefully(req_a, make_candidate, monkeypatch, settings):
    from ai.llm import LLMRateLimited
    from screening.models import Score

    settings.WORKER_BACKOFF_SECONDS = 3600  # a real backoff, so the retry is not due within the same batch
    cand = make_candidate(req_a, score=False)
    monkeypatch.setattr("screening.services.call_llm", lambda *a, **k: (_ for _ in ()).throw(LLMRateLimited("429")))
    jobs.enqueue("score_candidate", {"candidate_id": str(cand.pk)}, max_attempts=2)
    jobs.run_pending()
    assert not Score.objects.exists()  # first attempt: re-queued with backoff, nothing saved
    Job.objects.update(run_after=timezone.now())
    jobs.run_pending()  # final attempt: honest failed state
    assert Score.objects.get().status == Score.Status.FAILED
