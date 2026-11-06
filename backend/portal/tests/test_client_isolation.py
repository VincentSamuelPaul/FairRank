"""Rule 5: a client sees only candidates submitted to their org. Another org's data is a 404."""
import pytest

from accounts.models import Role, User
from audit.services import log_view
from portal.services import submit_candidate

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_user_b(org_b):
    return User.objects.create_user("hm-b@example.com", "pw-client-b1", full_name="HM B", role=Role.CLIENT, client_org=org_b)


@pytest.fixture
def setup(recruiter, req_a, req_b, make_candidate):
    cand_a = make_candidate(req_a)
    cand_b = make_candidate(req_b)
    unsubmitted_a = make_candidate(req_a)
    for c in (cand_a, cand_b):
        log_view(recruiter, c)
        submit_candidate(c, recruiter)
    return cand_a, cand_b, unsubmitted_a


def test_client_a_gets_404_for_client_bs_candidate_and_requisition(auth, client_user_a, req_b, setup):
    cand_a, cand_b, _ = setup
    api = auth(client_user_a)
    assert api.get(f"/api/portal/candidates/{cand_b.pk}/").status_code == 404
    assert api.post(f"/api/portal/candidates/{cand_b.pk}/decision/", {"decision": "shortlist"}, format="json").status_code == 404
    assert api.post(f"/api/portal/candidates/{cand_b.pk}/slots/", {"starts_at": "2099-01-01T10:00:00Z"}, format="json").status_code == 404
    assert api.get(f"/api/portal/requisitions/{req_b.pk}/").status_code == 404
    assert api.get(f"/api/portal/candidates/?requisition={req_b.pk}").json() == []
    assert api.get(f"/api/portal/candidates/{cand_a.pk}/").status_code == 200


def test_client_sees_only_submitted_candidates_of_own_org(auth, client_user_a, setup):
    cand_a, cand_b, unsubmitted_a = setup
    ids = {c["id"] for c in auth(client_user_a).get("/api/portal/candidates/").json()}
    assert ids == {str(cand_a.pk)}
    assert auth(client_user_a).get(f"/api/portal/candidates/{unsubmitted_a.pk}/").status_code == 404  # same org, not submitted


def test_client_cannot_use_staff_endpoints(auth, client_user_a, req_a, setup):
    cand_a, _, _ = setup
    api = auth(client_user_a)
    for url in (f"/api/requisitions/{req_a.pk}/", f"/api/requisitions/{req_a.pk}/candidates/", f"/api/candidates/{cand_a.pk}/",
                f"/api/candidates/{cand_a.pk}/cv/", "/api/requisitions/", "/api/reports/agreement/", "/api/pipeline/summary/"):
        assert api.get(url).status_code == 403, url
    assert api.post(f"/api/candidates/{cand_a.pk}/submit/", {}, format="json").status_code == 403


def test_recruiters_and_anonymous(auth, api, recruiter, setup, req_a):
    assert auth(recruiter).get("/api/portal/candidates/").status_code == 403  # portal is for clients
    assert api.get(f"/api/requisitions/{req_a.pk}/").status_code == 403  # anonymous: default deny


def test_client_org_filter_in_queryset(client_user_a, setup):
    from candidates.models import Candidate

    cand_a, cand_b, unsubmitted = setup
    assert set(Candidate.objects.visible_to(client_user_a)) == {cand_a}
