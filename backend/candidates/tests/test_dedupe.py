import pytest

from candidates.dedupe import find_duplicate
from candidates.models import Candidate
from candidates.normalize import normalize_email, normalize_phone

pytestmark = pytest.mark.django_db


def mk(req, name, email, phone, **kw):
    return Candidate.objects.create(requisition=req, full_name=name, email=email, phone=phone,
                                    email_normalized=normalize_email(email), phone_normalized=normalize_phone(phone), **kw)


def test_same_email_is_flagged(req_a):
    first = mk(req_a, "Asha Rao", "Asha.Rao@Example.com", "+91 90000 11111")
    second = mk(req_a, "A. Rao", " asha.rao@example.com ", "+91 90000 22222")
    match = find_duplicate(second)
    assert match.candidate == first and match.reason == "same email"


def test_same_phone_in_different_format_is_flagged(req_a):
    first = mk(req_a, "Vik Shah", "vik1@example.com", "+91 98765 43210")
    second = mk(req_a, "Vikram S", "vik2@example.com", "09876543210")
    assert find_duplicate(second).candidate == first


def test_near_identical_name_and_phone_is_flagged(req_a):
    first = mk(req_a, "Priyanka Sharma", "p1@example.com", "+91 98765 43210")
    second = mk(req_a, "Priyanka  Sharma.", "p2@example.com", "+91 98765 43211")  # one digit off
    match = find_duplicate(second)
    assert match.candidate == first and "name and phone" in match.reason


def test_different_people_are_not_flagged(req_a):
    mk(req_a, "Priyanka Sharma", "p1@example.com", "+91 98765 43210")
    other = mk(req_a, "Rohit Verma", "r@example.com", "+91 91111 22222")
    assert find_duplicate(other) is None


def test_similar_name_with_a_different_phone_is_not_flagged(req_a):
    mk(req_a, "Priyanka Sharma", "p1@example.com", "+91 98765 43210")
    other = mk(req_a, "Priyanka Sharma", "p9@example.com", "+91 90000 99999")
    assert find_duplicate(other) is None


def test_duplicate_is_flagged_not_dropped_through_the_pipeline(auth, recruiter, req_a):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from audit import jobs
    from conftest import SAMPLE_CV, make_docx, make_pdf

    api = auth(recruiter)
    files = [SimpleUploadedFile("a.pdf", make_pdf(SAMPLE_CV.splitlines())), SimpleUploadedFile("b.docx", make_docx(SAMPLE_CV.splitlines()))]
    assert api.post(f"/api/requisitions/{req_a.pk}/uploads/", {"files": files, "consent_confirmed": "true"}, format="multipart").status_code == 201
    jobs.run_pending(limit=50)
    rows = api.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"]
    assert len(rows) == 2  # nothing dropped
    flagged = [r for r in rows if r["duplicate_of"]]
    assert len(flagged) == 1 and flagged[0]["cv_status"] == "duplicate" and flagged[0]["duplicate_of"]["same_requisition"]
