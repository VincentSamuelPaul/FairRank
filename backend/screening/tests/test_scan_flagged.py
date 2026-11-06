"""Rule 9 / A3: scanned or empty-text PDFs are 'Needs manual review' with no fake score."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from audit import jobs
from candidates.models import CVFile
from candidates.parsing import extract_text
from conftest import make_blank_pdf
from screening.models import Score

pytestmark = pytest.mark.django_db


def test_blank_pdf_has_no_text():
    assert extract_text(make_blank_pdf(), "pdf") == ""


def test_scanned_pdf_is_flagged_not_scored(auth, recruiter, req_a):
    api = auth(recruiter)
    pdf = SimpleUploadedFile("scan.pdf", make_blank_pdf(), content_type="application/pdf")
    res = api.post(f"/api/requisitions/{req_a.pk}/uploads/", {"files": [pdf], "consent_confirmed": "true"}, format="multipart")
    assert res.status_code == 201, res.content
    jobs.run_pending(limit=20)

    cv = CVFile.objects.get()
    assert cv.status == CVFile.Status.NEEDS_REVIEW
    score = Score.objects.get()
    assert score.status == Score.Status.NEEDS_MANUAL_REVIEW
    assert score.total_score is None and score.band is None and not score.criterion_scores.exists()

    rows = api.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"]
    assert rows[0]["score"]["state"] == "needs_manual_review" and rows[0]["score"]["total"] is None
    assert rows[0]["next_action"]["label"] == "Review manually"  # the CV stays visible and actionable


def test_llm_failure_gives_retryable_failed_state_with_cv_visible(auth, recruiter, req_a, make_candidate, monkeypatch):
    from ai.llm import LLMInvalidOutput

    cand = make_candidate(req_a, score=False)

    def boom(*a, **k):
        raise LLMInvalidOutput("bad json twice")

    monkeypatch.setattr("screening.services.call_llm", boom)
    from screening.services import score_candidate

    score = score_candidate(cand)
    assert score.status == Score.Status.FAILED and score.total_score is None
    row = auth(recruiter).get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"][0]
    assert row["score"]["state"] == "failed" and row["next_action"]["label"] == "Retry scoring"
    detail = auth(recruiter).get(f"/api/candidates/{cand.pk}/").json()
    assert "Spring Boot" in detail["raw_text"]  # CV still readable
