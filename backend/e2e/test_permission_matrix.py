"""Default deny, checked exhaustively: every endpoint x every kind of caller.

Callers: anon (not signed in), rec (recruiter), head (delivery head), cA (client of org A, the candidate's org), cB (client of org B).
Where the real action is permitted the request carries an invalid body, so a permitted caller gets 400 (validation) and
nothing is changed; a forbidden caller must be stopped BEFORE validation (403) or must not be able to see the object (404).
"""
import uuid

import pytest

pytestmark = pytest.mark.django_db

DENY = {401, 403}


def S(*codes):
    return set(codes)


# (method, path with {req} {cand} {slot}, body, {caller: allowed status set})
MATRIX = [
    ("GET", "/api/auth/me/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=S(200), cB=S(200))),
    ("GET", "/api/client-orgs/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("POST", "/api/requisitions/", {}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/{req}/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("PATCH", "/api/requisitions/{req}/", {"status": "nonsense"}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/{req}/scorecard/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("PUT", "/api/requisitions/{req}/scorecard/", {"criteria": []}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/{req}/candidates/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/{req}/pipeline/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("GET", "/api/requisitions/{req}/uploads/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("POST", "/api/requisitions/{req}/uploads/", {}, dict(anon=DENY, rec=S(400, 415), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/candidates/{cand}/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
    ("GET", "/api/candidates/{cand}/cv/", None, dict(anon=DENY, rec=S(200, 404), head=S(200, 404), cA=DENY, cB=DENY)),
    ("POST", "/api/candidates/{cand}/submit/", {"note": "x" * 600}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("POST", "/api/candidates/{cand}/stage/", {}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("POST", "/api/candidates/{cand}/delete/", {}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/portal/requisitions/", None, dict(anon=DENY, rec=DENY, head=DENY, cA=S(200), cB=S(200))),
    ("GET", "/api/portal/candidates/", None, dict(anon=DENY, rec=DENY, head=DENY, cA=S(200), cB=S(200))),
    ("GET", "/api/portal/candidates/{cand}/", None, dict(anon=DENY, rec=DENY, head=DENY, cA=S(200), cB=S(404))),
    ("POST", "/api/portal/candidates/{cand}/decision/", {}, dict(anon=DENY, rec=DENY, head=DENY, cA=S(400), cB=S(404))),
    ("POST", "/api/portal/candidates/{cand}/slots/", {}, dict(anon=DENY, rec=DENY, head=DENY, cA=S(400), cB=S(404))),
    ("POST", "/api/slots/{slot}/respond/", {"status": "bogus"}, dict(anon=DENY, rec=S(400), head=DENY, cA=DENY, cB=DENY)),
    ("GET", "/api/reports/agreement/", None, dict(anon=DENY, rec=DENY, head=S(200), cA=DENY, cB=DENY)),
    ("GET", "/api/pipeline/summary/", None, dict(anon=DENY, rec=S(200), head=S(200), cA=DENY, cB=DENY)),
]


@pytest.fixture
def ids(world, submitted_a):
    from django.utils import timezone

    cl = world.auth(world.ca)
    when = (timezone.now() + timezone.timedelta(days=2)).isoformat()
    slot = cl.post(f"/api/portal/candidates/{submitted_a.pk}/slots/", {"starts_at": when, "duration_minutes": 30}, format="json")
    assert slot.status_code == 201, slot.content
    slot_id = world.auth(world.recruiter).get(f"/api/candidates/{submitted_a.pk}/").json()["submission"]["slots"][0]["id"]
    return {"req": str(world.req_a.pk), "cand": str(submitted_a.pk), "slot": slot_id}


@pytest.mark.parametrize("method,path,body,expected", MATRIX, ids=[f"{m} {p}" for m, p, _, _ in MATRIX])
def test_every_endpoint_for_every_caller(world, ids, method, path, body, expected):
    callers = {"anon": world.anon, "rec": world.auth(world.recruiter), "head": world.auth(world.head),
               "cA": world.auth(world.ca), "cB": world.auth(world.cb)}
    url = path.format(**ids)
    for who, client in callers.items():
        kwargs = {"format": "json"} if body is not None else {}
        resp = getattr(client, method.lower())(url, body, **kwargs) if body is not None else getattr(client, method.lower())(url)
        assert resp.status_code in expected[who], f"{who} {method} {url} -> {resp.status_code} {resp.content[:200]!r}"


@pytest.mark.parametrize("path", ["/api/requisitions/{u}/", "/api/candidates/{u}/", "/api/portal/candidates/{u}/", "/api/requisitions/{u}/candidates/"])
def test_unknown_ids_are_404_for_permitted_callers_and_denied_for_others(world, path):
    url = path.format(u=uuid.uuid4())
    staff_or_client = world.auth(world.ca if "/portal/" in path else world.recruiter)
    assert staff_or_client.get(url).status_code == 404
    assert world.anon.get(url).status_code in DENY


def test_malformed_ids_never_500(world):
    for bad in ("not-a-uuid", "1", "%00", "'; DROP TABLE x;--"):
        for url in (f"/api/candidates/{bad}/", f"/api/requisitions/{bad}/", f"/api/portal/candidates/{bad}/"):
            r = world.auth(world.recruiter).get(url)
            assert r.status_code in (400, 404), (url, r.status_code)


def test_methods_not_allowed_are_405_not_500(world, submitted_a):
    rec = world.auth(world.recruiter)
    assert rec.delete(f"/api/candidates/{submitted_a.pk}/").status_code == 405
    assert rec.put("/api/requisitions/").status_code == 405
    assert world.auth(world.ca).put("/api/portal/candidates/").status_code == 405


def test_logged_out_session_loses_access(world, recruiter):
    from rest_framework.test import APIClient

    c = APIClient()
    c.force_login(recruiter)
    assert c.get("/api/requisitions/").status_code == 200
    c.logout()
    assert c.get("/api/requisitions/").status_code in DENY
