"""Write the synthetic seed CVs to a folder so they can be bulk-uploaded through the UI.

    python manage.py generate_cvs ./sample_cvs
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from seed.cvgen import render
from seed.data import build_specs


class Command(BaseCommand):
    help = "Write the ~31 synthetic seed CVs (PDF/DOCX) to a directory."

    def add_arguments(self, parser):
        parser.add_argument("out_dir", type=Path)

    def handle(self, *args, out_dir: Path, **options):
        count = 0
        for spec in build_specs():
            target = out_dir / spec.key
            target.mkdir(parents=True, exist_ok=True)
            for persona, _ in spec.people:
                name, data = render(persona)
                (target / name).write_bytes(data)
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Wrote {count} CVs under {out_dir}"))
