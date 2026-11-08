"""Background worker: drains the Job table in small batches (rate-limit friendly).

    python manage.py run_worker          # loop forever
    python manage.py run_worker --once   # drain what is due, then exit (tests, cron)
"""
import logging
import time
from pathlib import Path
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from audit import jobs
from audit.models import Job

log = logging.getLogger(__name__)
HEARTBEAT = Path("/tmp/worker.alive")  # touched every loop; the Docker healthcheck checks its age


def ensure_weekly_report_job() -> None:
    """A8: once a week, queue the AI-vs-recruiter agreement report for the delivery head."""
    since = timezone.now() - timedelta(days=7)
    if not Job.objects.filter(kind="weekly_agreement_report", created_at__gte=since).exists():
        jobs.enqueue("weekly_agreement_report")


class Command(BaseCommand):
    help = "Run the background job worker."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process due jobs then exit")

    def handle(self, *args, **options):
        self.stdout.write("worker started")
        while True:
            HEARTBEAT.touch()
            ensure_weekly_report_job()
            ran = jobs.run_pending()
            if options["once"] and ran == 0:
                return
            if ran == 0:
                time.sleep(settings.WORKER_POLL_SECONDS)
