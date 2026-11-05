"""Idempotent demo data: users, client orgs, the example JD with a v1 scorecard,
and the three sample candidates from the brief. All data is synthetic (A9, A14)."""
import os
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import ClientOrg, Role, User
from candidates.models import Candidate, Consent, ParsedProfile, Stage
from candidates.normalize import normalize_email, normalize_phone
from requisitions.models import Requisition, Scorecard, ScorecardCriterion

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

JD_TEXT = "Senior Java Developer, 5-8 years, Spring Boot, Noida, notice up to 60 days"

# name, weight (A1: must-have 3, nice-to-have 1), must-have
SCORECARD_V1 = [
    ("Java", "Hands-on Java development", 3, True),
    ("Spring Boot", "Builds services with Spring Boot", 3, True),
    ("5-8 years of experience", "Total experience between 5 and 8 years", 3, True),
    ("Notice period up to 60 days", "Can join within 60 days", 3, True),
    ("Based in or willing to work in Noida", "Location fit", 1, False),
]

# external_id, name, role, years, skills, notice, email, phone  (email/phone invented: A14)
CANDIDATES = [
    ("CND-91022", "Ritika Bansal", "Senior Java Developer", "6.5",
     ["Java", "Spring Boot", "microservices"], 60, "ritika.bansal@example.com", "+91 90000 00001"),
    ("CND-91047", "Arjun Rawat", "KYC Analyst", "3.0",
     ["KYC", "AML checks", "Excel"], 30, "arjun.rawat@example.com", "+91 90000 00002"),
    ("CND-91088", "Pooja Nair", "Java Developer", "4.0",
     ["Java", "Hibernate", "REST APIs"], 90, "pooja.nair@example.com", "+91 90000 00003"),
]


class Command(BaseCommand):
    help = "Create idempotent demo users, the example JD and the sample candidates."

    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get("SEED_PASSWORD") or DEFAULT_PASSWORD
        orgs = {name: ClientOrg.objects.get_or_create(name=name)[0] for name in ORGS}
        users = {email: self._user(email, name, role, orgs.get(org), password) for email, name, role, org in USERS}
        req = self._requisition(users["recruiter1@companya.example"], orgs[ORGS[0]])
        for row in CANDIDATES:
            self._candidate(req, users["recruiter1@companya.example"], row)
        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} users, {len(orgs)} client orgs, 1 requisition, {len(CANDIDATES)} candidates."
        ))

    def _user(self, email, name, role, org, password) -> User:
        user, created = User.objects.get_or_create(
            email=email, defaults={"full_name": name, "role": role, "client_org": org}
        )
        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user

    def _requisition(self, recruiter: User, org: ClientOrg) -> Requisition:
        req, created = Requisition.objects.get_or_create(
            title="Senior Java Developer",
            client_org=org,
            defaults={
                "created_by": recruiter,
                "jd_text": JD_TEXT,
                "location": "Noida",
                "exp_min_years": Decimal("5"),
                "exp_max_years": Decimal("8"),
                "notice_max_days": 60,
            },
        )
        if created:
            card = Scorecard.objects.create(
                requisition=req, version=1, source=Scorecard.Source.AI, created_by=recruiter
            )
            ScorecardCriterion.objects.bulk_create(
                ScorecardCriterion(scorecard=card, name=n, description=d, weight=w, is_must_have=m, order=i)
                for i, (n, d, w, m) in enumerate(SCORECARD_V1)
            )
        return req

    def _candidate(self, req: Requisition, recruiter: User, row) -> None:
        ext_id, name, role, years, skills, notice, email, phone = row
        if Candidate.objects.filter(requisition=req, external_id=ext_id).exists():
            return
        cand = Candidate.objects.create(
            requisition=req, external_id=ext_id, full_name=name, email=email, phone=phone,
            email_normalized=normalize_email(email), phone_normalized=normalize_phone(phone),
            stage=Stage.SOURCED, created_by=recruiter,
        )
        ParsedProfile.objects.create(
            candidate=cand, current_role=role, experience_years=Decimal(years), skills=skills,
            notice_days=notice,
        )
        Consent.objects.create(candidate=cand, recorded_by=recruiter)
