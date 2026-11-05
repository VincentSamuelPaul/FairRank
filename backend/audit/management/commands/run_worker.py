"""Placeholder worker. The Job handlers and polling loop land on Friday."""
import time

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the background job worker (placeholder until Friday)."

    def handle(self, *args, **options):
        self.stdout.write("worker started: no job handlers registered yet")
        while True:
            time.sleep(30)
