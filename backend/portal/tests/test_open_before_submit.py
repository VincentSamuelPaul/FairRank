"""Rule 4: a recruiter can submit only after opening the CV. Enforced on the server."""
import pytest

from accounts.models import Role, User
from audit.models import ViewLog
from candidates.models import Stage
from portal.models import Submission

pytestmark = pytest.mark.django_db


def test_submit_without_view_is_403(auth, recruiter, req_a, make_candidate):
    cand = make_candidate(req_a)
    res = auth(recruiter).post(f"/api/candidates/{cand.pk}/submit/", {}, format="json")
    assert res.status_code == 403
    assert not Submission.objects.exists()
    cand.refresh_from_db()
    assert cand.stage == Stage.SCREENED


def test_opening_the_profile_logs_a_view_and_unlocks_submit(auth, recruiter, req_a, make_candidate):
    cand = make_candidate(req_a)
    api = auth(recruiter)
    detail = api.get(f"/api/candidates/{cand.pk}/").json()
    assert detail["can_submit"] is True and detail["next_action"]["code"] == "submit"
    assert ViewLog.objects.filter(user=recruiter, candidate=cand, kind="profile").count() == 1
    res = api.post(f"/api/candidates/{cand.pk}/submit/", {"note": "Great fit"}, format="json")
    assert res.status_code == 200 and res.json()["stage"] == Stage.SUBMITTED
    assert api.post(f"/api/candidates/{cand.pk}/submit/", {}, format="json").status_code == 409  # not twice


def test_another_recruiters_view_does_not_count(auth, recruiter, req_a, make_candidate):
    other = User.objects.create_user("rec2@example.com", "pw-recruiter-2", full_name="R2", role=Role.RECRUITER)
    cand = make_candidate(req_a)
    auth(other).get(f"/api/candidates/{cand.pk}/")  # someone else opened it
    assert auth(recruiter).post(f"/api/candidates/{cand.pk}/submit/", {}, format="json").status_code == 403


def test_every_open_is_logged_including_the_cv_file(auth, recruiter, req_a, make_candidate):
    from django.core.files.base import ContentFile

    cand = make_candidate(req_a)
    cv = cand.cv_files.first()
    cv.file.save("x.pdf", ContentFile(b"%PDF-1.4 x"), save=True)
    api = auth(recruiter)
    api.get(f"/api/candidates/{cand.pk}/")
    api.get(f"/api/candidates/{cand.pk}/")
    resp = api.get(f"/api/candidates/{cand.pk}/cv/")
    assert resp.status_code == 200
    kinds = list(ViewLog.objects.filter(candidate=cand).values_list("kind", flat=True))
    assert sorted(kinds) == ["cv", "profile", "profile"]
    recent = api.get(f"/api/candidates/{cand.pk}/").json()["view_log"]
    assert recent["total"] == 4 and recent["recent"][0]["user"] == recruiter.full_name


def test_client_opening_a_candidate_is_logged_too(auth, recruiter, client_user_a, req_a, make_candidate):
    from audit.services import log_view
    from portal.services import submit_candidate

    cand = make_candidate(req_a)
    log_view(recruiter, cand)
    submit_candidate(cand, recruiter)
    auth(client_user_a).get(f"/api/portal/candidates/{cand.pk}/")
    assert ViewLog.objects.filter(user=client_user_a, candidate=cand).count() == 1
