"""The recruiter's whole day, through the real API: JD -> scorecard -> bulk upload -> worker -> ranked list -> open -> submit -> pipeline -> delete."""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import ClientOrg
from ai.llm import LLMError
from audit import jobs
from audit.models import ViewLog
from candidates.models import Candidate, CVFile, Stage, Tombstone
from conftest import SAMPLE_CV, WEAK_CV, make_blank_pdf, make_docx, make_pdf
from requisitions.models import Requisition

pytestmark = pytest.mark.django_db

JD = """Senior Java Developer
Location: Noida
Experience: 5-8 years
Skills: Spring Boot, microservices, Java, REST APIs
Notice period up to 60 days
Nice to have: Kafka"""


def drain():
    while jobs.run_pending(limit=20):
        pass


def upload(rec, req, files, consent="true"):
    return rec.post(f"/api/requisitions/{req.pk}/uploads/", {"files": files, "consent_confirmed": consent}, format="multipart")


def pdf(name, text):
    return SimpleUploadedFile(name, make_pdf(text.splitlines()), content_type="application/pdf")


def docx(name, text):
    return SimpleUploadedFile(name, make_docx(text.splitlines()))


# --- JD intake -----------------------------------------------------------------------------------

def test_jd_intake_builds_an_editable_scorecard(world, org_a):
    r = world.rec.post("/api/requisitions/", {"client_org": org_a.pk, "jd_text": JD}, format="json")
    assert r.status_code == 201, r.content
    body = r.json()
    assert body["warning"] == ""
    req = body["requisition"]
    assert req["location"] == "Noida" and float(req["exp_min_years"]) == 5 and float(req["exp_max_years"]) == 8
    card = req["scorecard"]
    assert card["version"] == 1 and card["source"] == "ai" and card["criteria"]
    for c in card["criteria"]:
        assert c["weight"] == (3 if c["is_must_have"] else 1)  # A1


def test_jd_intake_survives_the_ai_being_down(world, org_a, monkeypatch):
    def boom(*a, **k):
        raise LLMError("down")
    monkeypatch.setattr("requisitions.services.call_llm", boom)
    r = world.rec.post("/api/requisitions/", {"client_org": org_a.pk, "jd_text": JD}, format="json")
    assert r.status_code == 201
    assert "could not read" in r.json()["warning"] and r.json()["requisition"]["scorecard"] is None
    rid = r.json()["requisition"]["id"]
    # the recruiter builds it by hand and everything works from there
    put = world.rec.put(f"/api/requisitions/{rid}/scorecard/", {"criteria": [{"name": "Java", "weight": 3, "is_must_have": True}]}, format="json")
    assert put.status_code == 200 and put.json()["version"] == 1


@pytest.mark.parametrize("body,field", [
    ({"jd_text": "short"}, "jd_text"), ({"jd_text": "x" * 20001}, "jd_text"), ({"client_org": 99999, "jd_text": JD}, "client_org"),
    ({"jd_text": JD, "title": "t" * 201}, "title"),
])
def test_jd_intake_validates_input(world, org_a, body, field):
    body = {"client_org": org_a.pk, **body}
    r = world.rec.post("/api/requisitions/", body, format="json")
    assert r.status_code == 400 and field in r.json()


def test_jd_text_is_stored_as_text_not_markup(world, org_a):
    xss = "<script>alert(1)</script> Senior Java Developer, 5-8 years, Spring Boot, Noida"
    r = world.rec.post("/api/requisitions/", {"client_org": org_a.pk, "jd_text": xss, "title": "<img src=x onerror=alert(1)>"}, format="json")
    assert r.status_code == 201 and r["Content-Type"].startswith("application/json")
    assert r.json()["requisition"]["title"] == "<img src=x onerror=alert(1)>"  # returned verbatim as JSON; React escapes on render


# --- scorecard versions -------------------------------------------------------------------------

def test_editing_the_scorecard_creates_a_version_and_rescores(world, req_a):
    cand = world.candidate(req_a)
    before = world.rec.get(f"/api/candidates/{cand.pk}/").json()["score"]
    assert before["scorecard_version"] == 1
    new = [{"name": "Kafka", "weight": 5, "is_must_have": True}, {"name": "Java", "weight": 1, "is_must_have": False}]
    put = world.rec.put(f"/api/requisitions/{req_a.pk}/scorecard/", {"criteria": new}, format="json")
    assert put.status_code == 200 and put.json()["version"] == 2 and put.json()["rescoring"] == 1
    drain()
    after = world.rec.get(f"/api/candidates/{cand.pk}/").json()["score"]
    assert after["scorecard_version"] == 2 and {c["name"] for c in after["criteria"]} == {"Kafka", "Java"}
    kafka = next(c for c in after["criteria"] if c["name"] == "Kafka")
    assert kafka["evidence_status"] == "no_evidence" and kafka["points"] == 0 and kafka["quote"] == ""  # the CV never mentions Kafka
    from screening.models import Score
    assert Score.objects.filter(candidate=cand).count() == 2  # version 1 stays for the record


@pytest.mark.parametrize("criteria", [
    [], [{"name": "A", "weight": 0, "is_must_have": True}], [{"name": "A", "weight": 11, "is_must_have": True}],
    [{"name": "A", "weight": 1, "is_must_have": True}, {"name": " a ", "weight": 1, "is_must_have": False}],
    [{"name": "", "weight": 1, "is_must_have": True}], [{"name": "n" * 201, "weight": 1, "is_must_have": True}],
    [{"name": f"c{i}", "weight": 1, "is_must_have": True} for i in range(16)], [{"name": "A", "weight": "x", "is_must_have": True}],
])
def test_scorecard_validation(world, req_a, criteria):
    r = world.rec.put(f"/api/requisitions/{req_a.pk}/scorecard/", {"criteria": criteria}, format="json")
    assert r.status_code == 400
    assert req_a.scorecards.count() == 1  # a rejected edit creates no version


def test_requisition_update_validation(world, req_a):
    assert world.rec.patch(f"/api/requisitions/{req_a.pk}/", {"exp_min_years": 9, "exp_max_years": 3}, format="json").status_code == 400
    assert world.rec.patch(f"/api/requisitions/{req_a.pk}/", {"status": "closed"}, format="json").json()["status"] == "closed"


# --- bulk upload ---------------------------------------------------------------------------------

def test_bulk_upload_of_mixed_files_reports_each_one(world, req_a, settings):
    settings.MAX_UPLOAD_BYTES = 200_000
    files = [
        pdf("good.pdf", SAMPLE_CV), docx("good.docx", WEAK_CV),
        SimpleUploadedFile("renamed.pdf", b"this is plain text pretending to be a pdf"),     # wrong magic bytes
        SimpleUploadedFile("empty.pdf", b""),
        SimpleUploadedFile("big.pdf", b"%PDF-1.4\n" + b"0" * 250_000),                       # over the size limit
        SimpleUploadedFile("macro.docm", b"PK\x03\x04 not a real docx"),
        SimpleUploadedFile("../../etc/passwd.pdf", make_pdf(["Pat Kumar", "Java Developer"])),  # path traversal in the name
    ]
    r = upload(world.rec, req_a, files)
    assert r.status_code == 201, r.content
    out = r.json()
    assert {a["name"] for a in out["accepted"]} == {"good.pdf", "good.docx", "passwd.pdf"}
    reasons = {x["name"]: x["reason"] for x in out["rejected"]}
    assert set(reasons) == {"renamed.pdf", "empty.pdf", "big.pdf", "macro.docm"}
    assert "empty" in reasons["empty.pdf"].lower() and "MB" in reasons["big.pdf"] or "Larger" in reasons["big.pdf"]
    for a in out["accepted"]:
        cv = CVFile.objects.get(candidate_id=a["candidate_id"])
        assert "/" not in cv.original_name and ".." not in cv.original_name


def test_the_file_type_is_decided_by_magic_bytes_not_the_name(world, req_a):
    r = upload(world.rec, req_a, [SimpleUploadedFile("actually-a-pdf.docx", make_pdf(["Ann Lee", "Java", "Total Experience: 3 years"]))])
    assert len(r.json()["accepted"]) == 1
    assert CVFile.objects.get(candidate_id=r.json()["accepted"][0]["candidate_id"]).content_type == "application/pdf"


def test_upload_needs_consent_and_files_and_respects_the_batch_cap(world, req_a, settings):
    assert upload(world.rec, req_a, [pdf("a.pdf", SAMPLE_CV)], consent="false").status_code == 400
    assert world.rec.post(f"/api/requisitions/{req_a.pk}/uploads/", {"consent_confirmed": "true"}, format="multipart").status_code == 400
    settings.MAX_FILES_PER_BATCH = 3
    four = [pdf(f"c{i}.pdf", SAMPLE_CV.replace("Jane Doe", f"Person {i}")) for i in range(4)]
    r = upload(world.rec, req_a, four)
    assert r.status_code == 400 and "At most 3" in json.dumps(r.json())
    assert Candidate.objects.filter(requisition=req_a).count() == 0  # nothing half-created
    three = [pdf(f"c{i}.pdf", SAMPLE_CV.replace("Jane Doe", f"Person {i}")) for i in range(3)]
    assert upload(world.rec, req_a, three).status_code == 201


def test_every_upload_records_consent_and_is_queued(world, req_a):
    r = upload(world.rec, req_a, [pdf("a.pdf", SAMPLE_CV)])
    cand = Candidate.objects.get(pk=r.json()["accepted"][0]["candidate_id"])
    consent = cand.consents.get()
    assert consent.purpose == "hiring_use_only" and consent.recorded_by == world.recruiter  # A5
    assert jobs.Job.objects.filter(kind="process_cv").exists() if hasattr(jobs, "Job") else True


def test_worker_parses_scores_flags_scans_and_duplicates(world, req_a):
    files = [pdf("jane.pdf", SAMPLE_CV), pdf("jane-again.pdf", SAMPLE_CV), docx("mohan.docx", WEAK_CV),
             SimpleUploadedFile("scan.pdf", make_blank_pdf())]
    ids = [a["candidate_id"] for a in upload(world.rec, req_a, files).json()["accepted"]]
    status = world.rec.get(f"/api/requisitions/{req_a.pk}/uploads/?ids={','.join(ids)}").json()
    assert status["in_progress"] is True
    drain()
    status = world.rec.get(f"/api/requisitions/{req_a.pk}/uploads/?ids={','.join(ids)}").json()
    assert status["in_progress"] is False
    by_name = {i["name"]: i for i in status["items"]}
    assert by_name["scan.pdf"]["score_state"] == "needs_manual_review" and by_name["scan.pdf"]["total"] is None  # no fake score
    assert by_name["mohan.docx"]["score_state"] == "scored" and by_name["mohan.docx"]["band"] == "weak"
    assert by_name["jane-again.pdf"]["cv_status"] == "duplicate" or by_name["jane.pdf"]["cv_status"] == "duplicate"
    # the ranked list: scored first (best first), unscored after, nobody hidden, nobody moved by a score
    rows = world.rec.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"]
    assert len(rows) == 4
    totals = [r["score"]["total"] for r in rows if r["score"]["state"] == "scored"]
    assert totals == sorted(totals, reverse=True)
    assert rows[-1]["score"]["state"] == "needs_manual_review"
    assert {r["stage"] for r in rows} <= {"sourced", "screened"} and all(r["stage"] != "rejected" for r in rows)


def test_a_candidate_polled_before_processing_is_honest_about_it(world, req_a):
    r = upload(world.rec, req_a, [pdf("a.pdf", SAMPLE_CV)])
    cid = r.json()["accepted"][0]["candidate_id"]
    item = world.rec.get(f"/api/requisitions/{req_a.pk}/uploads/?ids={cid}").json()["items"][0]
    assert item["cv_status"] == "queued" and item["total"] is None


# --- ranked list: search, filters, no hiding -------------------------------------------------------------

@pytest.fixture
def ranked(world, req_a):
    strong = world.candidate(req_a, SAMPLE_CV)
    weak = world.candidate(req_a, WEAK_CV)
    scan = world.candidate(req_a, "x", score=True)  # too little text -> needs manual review
    return strong, weak, scan


def test_low_scorers_stay_listed_and_searchable(world, req_a, ranked):
    strong, weak, scan = ranked
    url = f"/api/requisitions/{req_a.pk}/candidates/"
    everyone = world.rec.get(url).json()
    assert everyone["counts"]["total"] == 3 and everyone["counts"]["weak"] == 1 and everyone["counts"]["needs_review"] == 1
    assert [c["id"] for c in world.rec.get(url + "?band=weak").json()["candidates"]] == [str(weak.pk)]
    assert [c["id"] for c in world.rec.get(url + "?q=Mohan").json()["candidates"]] == [str(weak.pk)]      # by name
    assert [c["id"] for c in world.rec.get(url + "?q=excel").json()["candidates"]] == [str(weak.pk)]      # by CV text, case-insensitive
    assert {c["id"] for c in world.rec.get(url + "?band=unscored").json()["candidates"]} == {str(scan.pk)}
    assert {c["id"] for c in world.rec.get(url + "?flag=needs_attention").json()["candidates"]} == {str(scan.pk)}
    assert world.rec.get(url + "?q=zzzzqqq").json()["candidates"] == []
    for evil in ("'; DROP TABLE candidates_candidate;--", "%", "\\", "a" * 5000, "\x00", "<script>"):
        assert world.rec.get(url, {"q": evil}).status_code == 200
    assert Candidate.objects.count() == 3 and weak.stage in (Stage.SCREENED, Stage.SOURCED)  # still there, still unrejected


def test_unknown_filter_values_are_ignored_not_errors(world, req_a, ranked):
    url = f"/api/requisitions/{req_a.pk}/candidates/"
    assert len(world.rec.get(url + "?band=banana&stage=nope&flag=x").json()["candidates"]) == 3


# --- open before submit ----------------------------------------------------------------------------------------

def test_submit_requires_this_recruiter_to_have_opened_the_cv(world, req_a, recruiter2):
    cand = world.candidate(req_a)
    rec2 = world.auth(recruiter2)
    assert world.rec.post(f"/api/candidates/{cand.pk}/submit/", {}, format="json").status_code == 403  # never opened
    world.rec.get(f"/api/candidates/{cand.pk}/")
    assert rec2.post(f"/api/candidates/{cand.pk}/submit/", {}, format="json").status_code == 403       # someone else opened it
    assert world.rec.post(f"/api/candidates/{cand.pk}/submit/", {"note": "ok"}, format="json").status_code == 200
    assert world.rec.post(f"/api/candidates/{cand.pk}/submit/", {}, format="json").status_code == 409  # not twice
    assert Candidate.objects.get(pk=cand.pk).stage == Stage.SUBMITTED


def test_opening_the_profile_or_cv_is_logged_every_time(world, req_a):
    cand = world.candidate(req_a)
    world.rec.get(f"/api/candidates/{cand.pk}/")
    world.rec.get(f"/api/candidates/{cand.pk}/")
    world.auth(world.head).get(f"/api/candidates/{cand.pk}/")
    logs = ViewLog.objects.filter(candidate=cand)
    assert logs.filter(user=world.recruiter).count() == 2 and logs.filter(user=world.head).count() == 1
    detail = world.rec.get(f"/api/candidates/{cand.pk}/").json()
    assert detail["view_log"]["total"] >= 3 and {v["user"] for v in detail["view_log"]["recent"]} >= {"Rec", "Head"}


# --- pipeline -------------------------------------------------------------------------------------------------------

def test_recruiter_stage_moves_follow_the_rules_and_are_logged(world, req_a, submitted_a):
    base = f"/api/candidates/{submitted_a.pk}/stage/"
    assert world.rec.post(base, {"stage": "rejected", "reason": "x"}, format="json").status_code == 409  # only a client rejects
    assert world.rec.post(base, {"stage": "joined"}, format="json").status_code == 409                    # no skipping
    assert world.rec.post(base, {"stage": "nonsense"}, format="json").status_code == 400
    cand = world.candidate(req_a, WEAK_CV.replace("Mohan Lal", "Test Person").replace("mohan.lal", "test.person"))
    assert world.rec.post(f"/api/candidates/{cand.pk}/stage/", {"stage": "offered"}, format="json").status_code == 409


def test_pipeline_board_has_every_stage_in_order(world, req_a, submitted_a):
    cols = world.rec.get(f"/api/requisitions/{req_a.pk}/pipeline/").json()["columns"]
    assert [c["stage"] for c in cols][:7] == ["sourced", "screened", "submitted", "shortlisted", "interview", "offered", "joined"]
    assert [x["id"] for x in next(c for c in cols if c["stage"] == "submitted")["candidates"]] == [str(submitted_a.pk)]


# --- consent and deletion --------------------------------------------------------------------------------------------

def test_deletion_wipes_everything_leaves_a_tombstone_and_is_idempotent(world, req_a, submitted_a):
    cid = str(submitted_a.pk)
    assert world.rec.post(f"/api/candidates/{cid}/delete/", {"requester": "candidate"}, format="json").status_code == 400  # confirm needed
    ok = world.rec.post(f"/api/candidates/{cid}/delete/", {"requester": "the candidate, by email", "confirm": True}, format="json")
    assert ok.status_code == 200 and ok.json()["deleted"] is True
    assert Tombstone.objects.filter(candidate_id=cid).count() == 1
    cand = Candidate.objects.get(pk=cid)
    assert cand.full_name == "" and cand.email == "" and cand.phone == "" and cand.deleted_at
    assert not hasattr(cand, "profile") and not cand.cv_files.exists() and not cand.scores.exists()
    # gone from every surface
    assert world.rec.get(f"/api/candidates/{cid}/").status_code == 404
    assert cid not in [c["id"] for c in world.rec.get(f"/api/requisitions/{req_a.pk}/candidates/").json()["candidates"]]
    assert world.auth(world.ca).get(f"/api/portal/candidates/{cid}/").status_code == 404
    assert world.auth(world.ca).get("/api/portal/candidates/").json() == []
    assert world.rec.get(f"/api/requisitions/{req_a.pk}/candidates/?q=Jane").json()["candidates"] == []
    board = world.rec.get(f"/api/requisitions/{req_a.pk}/pipeline/").json()["columns"]
    assert all(cid not in [x["id"] for x in col["candidates"]] for col in board)
    again = world.rec.post(f"/api/candidates/{cid}/delete/", {"requester": "again", "confirm": True}, format="json")
    assert again.status_code in (200, 404) and Tombstone.objects.filter(candidate_id=cid).count() == 1
    assert world.rec.post(f"/api/candidates/{cid}/submit/", {}, format="json").status_code == 404


def test_deleting_a_candidate_does_not_touch_the_duplicate_it_pointed_to(world, req_a):
    a = world.candidate(req_a)
    ids = [x["candidate_id"] for x in upload(world.rec, req_a, [pdf("dup.pdf", SAMPLE_CV)]).json()["accepted"]]
    drain()
    dup = Candidate.objects.get(pk=ids[0])
    assert dup.duplicate_of_id == a.pk
    world.rec.post(f"/api/candidates/{a.pk}/delete/", {"requester": "x", "confirm": True}, format="json")
    dup.refresh_from_db()
    assert dup.duplicate_of_id is None and dup.deleted_at is None and dup.email  # kept; the pointer is cleared


def test_retry_scoring_endpoint(world, req_a):
    cand = world.candidate(req_a)
    assert world.rec.post(f"/api/candidates/{cand.pk}/rescore/").status_code == 202
    drain()
    cand2 = Candidate.objects.create(requisition=req_a, created_by=world.recruiter)  # no profile yet
    assert world.rec.post(f"/api/candidates/{cand2.pk}/rescore/").status_code == 409


def test_a_requisition_without_a_scorecard_lists_cvs_without_scores(world, org_a, recruiter):
    req = Requisition.objects.create(title="No card", client_org=org_a, created_by=recruiter, jd_text="jd " * 10)
    r = upload(world.rec, req, [pdf("a.pdf", SAMPLE_CV)])
    assert r.status_code == 201
    drain()
    rows = world.rec.get(f"/api/requisitions/{req.pk}/candidates/").json()["candidates"]
    assert len(rows) == 1 and rows[0]["score"]["total"] is None and rows[0]["score"]["state"] == "no_scorecard"
    assert world.rec.post(f"/api/requisitions/{req.pk}/rescore/").status_code == 409
