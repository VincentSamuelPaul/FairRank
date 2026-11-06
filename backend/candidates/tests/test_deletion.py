"""Rule 8 / A6: deletion wipes file, text and parsed fields, leaves a tombstone, and removes the
candidate from every list and from client portals."""
import pytest
from django.core.files.base import ContentFile

from audit.services import log_view
from candidates.models import Candidate, Tombstone
from candidates.services import delete_candidate
from portal.services import submit_candidate
from screening.models import CriterionScore, Score

pytestmark = pytest.mark.django_db


def test_deletion_wipes_everything_and_leaves_a_tombstone(auth, recruiter, delivery_head, client_user_a, req_a, make_candidate):
    cand = make_candidate(req_a)
    cv = cand.cv_files.first()
    cv.file.save("x.pdf", ContentFile(b"%PDF-fake"), save=True)
    path = cv.file.path
    log_view(recruiter, cand)
    submit_candidate(cand, recruiter)
    assert len(auth(client_user_a).get("/api/portal/candidates/").json()) == 1

    res = auth(recruiter).post(f"/api/candidates/{cand.pk}/delete/", {"requester": "candidate by email", "confirm": True}, format="json")
    assert res.status_code == 200, res.content

    cand.refresh_from_db()
    assert cand.deleted_at is not None
    assert (cand.full_name, cand.email, cand.phone, cand.external_id) == ("", "", "", "")
    assert not hasattr(cand, "profile") and not cand.cv_files.exists()
    assert not Score.objects.filter(candidate=cand).exists() and CriterionScore.objects.count() == 0
    import os

    assert not os.path.exists(path)
    tomb = Tombstone.objects.get(candidate_id=cand.pk)
    assert tomb.requester == "candidate by email" and tomb.deleted_at and tomb.processed_by == recruiter

    # gone from lists, search, detail, pipeline and the client portal
    api = auth(recruiter)
    assert api.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"] == []
    assert api.get(f"/api/candidates/{cand.pk}/").status_code == 404
    assert api.get(f"/api/requisitions/{req_a.pk}/pipeline/").json()["columns"][2]["candidates"] == []
    assert not Candidate.objects.visible_to(recruiter).filter(pk=cand.pk).exists()
    assert auth(client_user_a).get("/api/portal/candidates/").json() == []
    assert auth(client_user_a).get(f"/api/portal/candidates/{cand.pk}/").status_code == 404


def test_deletion_is_idempotent_and_requires_confirmation(auth, recruiter, req_a, make_candidate):
    cand = make_candidate(req_a)
    assert auth(recruiter).post(f"/api/candidates/{cand.pk}/delete/", {"confirm": False}, format="json").status_code == 400
    first = delete_candidate(cand, "candidate", recruiter)
    assert delete_candidate(cand, "someone else", recruiter).pk == first.pk
    assert Tombstone.objects.count() == 1
