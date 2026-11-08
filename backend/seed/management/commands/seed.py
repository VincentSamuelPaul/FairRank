"""Idempotent demo data: users, client orgs, three JDs with scorecards, ~31 synthetic CVs pushed
through the REAL upload -> parse -> dedupe -> score pipeline (offline provider, so scores are
pre-computed and the demo works without LLM quota), plus some client activity.
All data is synthetic (A9, A14)."""
import os
import shutil
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test.utils import override_settings
from django.utils import timezone

from accounts.models import ClientOrg, Role, User
from ai import offline
from audit import jobs
from audit.services import log_view
from candidates.models import Candidate, Stage
from candidates.services import process_cv, recruiter_move, register_upload, validate_upload
from portal import services as portal
from portal.models import ClientDecision, Submission
from requisitions.models import Requisition, Scorecard
from requisitions.services import MUST_HAVE_WEIGHT, NICE_TO_HAVE_WEIGHT, save_scorecard
from screening.models import Score
from seed.cvgen import render
from seed.data import Spec, build_specs

DEFAULT_PASSWORD = "FairRank-demo-1"
ORGS = ["Northwind IT Services", "Meridian Bank Operations"]
USERS = [
    # email, full name, role, org
    ("recruiter1@companya.example", "Asha Verma", Role.RECRUITER, None),
    ("recruiter2@companya.example", "Rohan Mehta", Role.RECRUITER, None),
    ("head@companya.example", "Kavita Rao", Role.DELIVERY_HEAD, None),
    ("manager@northwind.example", "Neel Kapoor", Role.CLIENT, ORGS[0]),
    ("manager@meridian.example", "Sana Iqbal", Role.CLIENT, ORGS[1]),
]


class Command(BaseCommand):
    help = "Create idempotent demo users, JDs, ~31 synthetic CVs with cached scores, and some client activity."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Wipe the database and uploaded CV files first, then seed (demo/dev only).")

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()
        password = os.environ.get("SEED_PASSWORD") or DEFAULT_PASSWORD
        orgs = {n: ClientOrg.objects.get_or_create(name=n)[0] for n in ORGS}
        users = {e: self._user(e, n, r, orgs.get(o), password) for e, n, r, o in USERS}
        recruiter = users["recruiter1@companya.example"]
        with override_settings(LLM_PROVIDER="offline"):  # seed scores never depend on a live LLM
            reqs = {spec.key: self._requisition(spec, recruiter, orgs[ORGS[spec.org_index]]) for spec in build_specs()}
            specs = {s.key: s for s in build_specs()}
            added = sum(self._cvs(specs[k], reqs[k], recruiter) for k in reqs)
            jobs.run_pending(limit=10_000)
        activity = self._activity(reqs, users)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} users, {len(orgs)} client orgs, {len(reqs)} requisitions, "
            f"{added} new CVs, {activity} client/pipeline events."
        ))

    def _reset(self) -> None:
        """Drop all rows and every uploaded file so the result is exactly what a fresh seed produces."""
        call_command("flush", interactive=False, verbosity=0)
        media = Path(settings.MEDIA_ROOT)
        if media.is_dir():
            shutil.rmtree(media / "cvs", ignore_errors=True)
        self.stdout.write("Reset: database flushed and uploaded CVs removed.")

    def _user(self, email, name, role, org, password) -> User:
        user, created = User.objects.get_or_create(email=email, defaults={"full_name": name, "role": role, "client_org": org})
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user

    def _requisition(self, spec: Spec, recruiter: User, org: ClientOrg) -> Requisition:
        req, created = Requisition.objects.get_or_create(
            title=spec.title, client_org=org,
            defaults={"created_by": recruiter, "jd_text": spec.jd, "location": spec.location,
                      "exp_min_years": Decimal(str(spec.exp[0])), "exp_max_years": Decimal(str(spec.exp[1])),
                      "notice_max_days": spec.notice},
        )
        if created or req.current_scorecard is None:
            criteria = (
                [{"name": n, "description": d, "weight": w, "is_must_have": m} for n, d, w, m in spec.scorecard]
                if spec.scorecard else
                [{"name": c.name, "description": c.description, "is_must_have": c.is_must_have,
                  "weight": MUST_HAVE_WEIGHT if c.is_must_have else NICE_TO_HAVE_WEIGHT}
                 for c in offline.extract_jd(spec.jd).criteria]
            )
            save_scorecard(req, recruiter, criteria, source=Scorecard.Source.AI)
        return req

    def _cvs(self, spec: Spec, req: Requisition, recruiter: User) -> int:
        existing = set(Candidate.objects.filter(requisition=req).exclude(external_id="").values_list("external_id", flat=True))
        # drop v0 rows (brief candidates created without a CV by the first seed version)
        Candidate.objects.filter(requisition=req, cv_files__isnull=True).delete()
        added = 0
        for persona, ext_id in spec.people:
            if ext_id in existing and Candidate.objects.filter(requisition=req, external_id=ext_id, cv_files__isnull=False).exists():
                continue
            name, data = render(persona)
            cand = register_upload(req, recruiter, validate_upload(name, data), external_id=ext_id, enqueue=False)
            process_cv(str(cand.pk))  # parse + dedupe; queues scoring
            added += 1
        return added

    def _ranked(self, req: Requisition) -> list[Candidate]:
        card = req.current_scorecard
        scores = (Score.objects.filter(scorecard=card, status=Score.Status.SCORED, candidate__deleted_at__isnull=True)
                  .select_related("candidate").order_by("-total_score", "candidate__created_at"))
        return [s.candidate for s in scores]

    def _activity(self, reqs: dict[str, Requisition], users: dict[str, User]) -> int:
        """Submissions, client decisions and pipeline moves, so every screen has something to show."""
        if Submission.objects.exists():
            return 0
        rec = users["recruiter1@companya.example"]
        clients = {"java": users["manager@northwind.example"], "kyc": users["manager@meridian.example"],
                   "retail": users["manager@northwind.example"]}
        future = timezone.now() + timedelta(days=3)

        def submit(c: Candidate) -> Candidate:
            log_view(rec, c)  # rule 4: the recruiter opened it first
            portal.submit_candidate(c, rec, "Strong match on the must-haves.")
            c.refresh_from_db()
            return c

        count = 0
        java = self._ranked(reqs["java"])
        picks = java[:3] + java[5:6]  # one recruiter pick sits below the AI's top 3: a visible disagreement
        s1, s2, s3, s4 = (submit(c) for c in picks)
        cj = clients["java"]
        portal.client_decide(s1, cj, ClientDecision.Decision.SHORTLIST)
        s1.refresh_from_db()
        portal.propose_slot(s1, cj, future.replace(hour=11, minute=0, second=0, microsecond=0), 45, "Panel round 1")
        s1.refresh_from_db()
        recruiter_move(s1, Stage.OFFERED, rec, "Offer released")
        portal.client_decide(s2, cj, ClientDecision.Decision.SHORTLIST)
        portal.propose_slot(s2, cj, (future + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0), 30)
        portal.client_decide(s3, cj, ClientDecision.Decision.REJECT, "Needs deeper Kafka experience for this role.")
        count += 7

        kyc = self._ranked(reqs["kyc"])
        k1, k2, k3 = (submit(c) for c in kyc[:3])
        ck = clients["kyc"]
        portal.client_decide(k1, ck, ClientDecision.Decision.SHORTLIST)
        k1.refresh_from_db()
        portal.propose_slot(k1, ck, future.replace(hour=15, minute=30, second=0, microsecond=0), 30)
        k1.refresh_from_db()
        recruiter_move(k1, Stage.OFFERED, rec)
        k1.refresh_from_db()
        recruiter_move(k1, Stage.JOINED, rec, "Joined")
        portal.client_decide(k2, ck, ClientDecision.Decision.SHORTLIST)
        count += 5

        for c in self._ranked(reqs["retail"])[:2]:
            submit(c)
            count += 1
        return count
