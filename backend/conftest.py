import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.models import ClientOrg, Role, User


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()  # throttle counters live in the cache


@pytest.fixture
def api() -> APIClient:
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def org_a(db) -> ClientOrg:
    return ClientOrg.objects.create(name="Org A")


@pytest.fixture
def org_b(db) -> ClientOrg:
    return ClientOrg.objects.create(name="Org B")


@pytest.fixture
def recruiter(db) -> User:
    return User.objects.create_user("rec@example.com", "pw-recruiter-1", full_name="Rec", role=Role.RECRUITER)


@pytest.fixture
def delivery_head(db) -> User:
    return User.objects.create_user("head@example.com", "pw-head-1", full_name="Head", role=Role.DELIVERY_HEAD)


@pytest.fixture
def client_user_a(org_a) -> User:
    return User.objects.create_user(
        "hm-a@example.com", "pw-client-a1", full_name="HM A", role=Role.CLIENT, client_org=org_a
    )


# --- domain fixtures ---------------------------------------------------------------------------

import io  # noqa: E402

from rest_framework.test import APIClient as _APIClient  # noqa: E402

SAMPLE_CV = """Jane Doe
Senior Java Developer
Email: jane.doe@example.com
Phone: +91 98765 43210
Gender: Female
Date of Birth: 12 March 1991
Marital Status: Married
Photo: attached
Total Experience: 6 years
Notice Period: 30 days
Location: Noida
Technical Skills: Java, Spring Boot, Hibernate
Summary
She is a Senior Java Developer with 6 years of experience.
Experience
Senior Java Developer, Brightwave Systems (2020 - Present)
- Built Spring Boot microservices for payment workflows
- Wrote Java services and tuned Hibernate queries
- Mentored two junior Java developers on code reviews
"""

WEAK_CV = """Mohan Lal
Operations Associate
Email: mohan.lal@example.com
Phone: +91 91234 56780
Total Experience: 1 years
Notice Period: 90 days
Location: Pune
Technical Skills: Excel
- Prepared Excel sheets for the operations team
"""


def make_pdf(lines: list[str]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 16
    c.save()
    return buf.getvalue()


def make_blank_pdf() -> bytes:
    """A page with a drawn box but no text: what a scan looks like to a text extractor."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.rect(50, 50, 400, 600)
    c.save()
    return buf.getvalue()


def make_docx(lines: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    for line in lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.fixture
def auth():
    """Return a function giving an API client authenticated as `user` (CSRF not enforced)."""

    def _auth(user):
        client = _APIClient()
        client.force_authenticate(user)
        return client

    return _auth


@pytest.fixture
def make_req(db, recruiter):
    from requisitions.services import save_scorecard

    def _make(org, title="Senior Java Developer"):
        from requisitions.models import Requisition

        req = Requisition.objects.create(title=title, client_org=org, created_by=recruiter, jd_text="jd " * 10,
                                         location="Noida")
        save_scorecard(req, recruiter, [
            {"name": "Java", "description": "", "weight": 3, "is_must_have": True},
            {"name": "Spring Boot", "description": "", "weight": 3, "is_must_have": True},
            {"name": "Based in or willing to work in Noida", "description": "", "weight": 1, "is_must_have": False},
        ])
        return req

    return _make


@pytest.fixture
def req_a(make_req, org_a):
    return make_req(org_a)


@pytest.fixture
def req_b(make_req, org_b):
    return make_req(org_b, "KYC Analyst")


@pytest.fixture
def make_candidate(db, recruiter):
    """Create a parsed candidate for a requisition and (optionally) score it with the real pipeline."""
    from candidates.models import Candidate, Consent, CVFile, ParsedProfile
    from candidates.normalize import normalize_email, normalize_phone
    from candidates.parsing import parse_profile
    from candidates.services import _text_hash, after_scoring
    from screening.services import score_candidate

    def _make(req, text=SAMPLE_CV, *, score=True, stage=None, external_id=""):
        parsed = parse_profile(text)
        cand = Candidate.objects.create(
            requisition=req, external_id=external_id, full_name=parsed.full_name, email=parsed.email,
            phone=parsed.phone, email_normalized=normalize_email(parsed.email), phone_normalized=normalize_phone(parsed.phone),
            created_by=recruiter)
        ParsedProfile.objects.create(candidate=cand, raw_text=text, text_hash=_text_hash(text),
                                     current_role=parsed.current_role, experience_years=parsed.experience_years,
                                     skills=parsed.skills, notice_days=parsed.notice_days, location=parsed.location)
        CVFile.objects.create(candidate=cand, original_name="cv.pdf", content_type="application/pdf",
                              sha256=_text_hash(text), status=CVFile.Status.PARSED)
        Consent.objects.create(candidate=cand, recorded_by=recruiter)
        if score:
            after_scoring(cand, score_candidate(cand))
        if stage:
            Candidate.objects.filter(pk=cand.pk).update(stage=stage)
        cand.refresh_from_db()
        return cand

    return _make
