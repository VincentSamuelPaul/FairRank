import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from accounts.models import Role, User

pytestmark = pytest.mark.django_db


def csrf_token(api) -> str:
    api.get(reverse("auth-csrf"))
    return api.cookies["csrftoken"].value


def login(api, email: str, password: str):
    return api.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(api),
    )


def test_me_requires_authentication(api):
    assert api.get(reverse("auth-me")).status_code == 403


def test_login_without_csrf_is_rejected(api, recruiter):
    res = api.post(reverse("auth-login"), {"email": recruiter.email, "password": "pw-recruiter-1"}, format="json")
    assert res.status_code == 403


def test_login_me_logout_flow(api, recruiter):
    res = login(api, "REC@example.com", "pw-recruiter-1")  # email is case-insensitive
    assert res.status_code == 200
    assert res.json()["role"] == "recruiter"
    assert "password" not in res.json()
    assert api.cookies["sessionid"]["httponly"]

    me = api.get(reverse("auth-me"))
    assert me.status_code == 200
    assert me.json()["email"] == "rec@example.com"

    # logout needs the rotated CSRF token
    out = api.post(reverse("auth-logout"), HTTP_X_CSRFTOKEN=api.cookies["csrftoken"].value)
    assert out.status_code == 204
    assert api.get(reverse("auth-me")).status_code == 403


def test_logout_without_csrf_is_rejected(api, recruiter):
    login(api, recruiter.email, "pw-recruiter-1")
    assert api.post(reverse("auth-logout")).status_code == 403


def test_bad_credentials_same_message_for_unknown_user(api, recruiter):
    wrong_pw = login(api, recruiter.email, "nope")
    unknown = login(api, "ghost@example.com", "nope")
    assert wrong_pw.status_code == unknown.status_code == 400
    assert wrong_pw.json() == unknown.json()


def test_client_me_includes_org(api, client_user_a):
    login(api, client_user_a.email, "pw-client-a1")
    body = api.get(reverse("auth-me")).json()
    assert body["role"] == "client"
    assert body["client_org"]["name"] == "Org A"


def test_client_role_requires_org_in_db(org_a):
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create([User(email="x@example.com", full_name="X", role=Role.CLIENT)])
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.bulk_create(
            [User(email="y@example.com", full_name="Y", role=Role.RECRUITER, client_org=org_a)]
        )


def test_session_endpoint_is_200_for_everyone_and_never_leaks(api, auth, recruiter):
    anon = api.get("/api/auth/session/")
    assert anon.status_code == 200 and anon.json() == {"user": None}
    me = auth(recruiter).get("/api/auth/session/").json()["user"]
    assert me["email"] == recruiter.email and "password" not in me
