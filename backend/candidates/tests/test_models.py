"""Model-level guarantees: DB constraints and the visible_to manager (rules 2, 5, 9)."""
import pytest
from django.db import IntegrityError, transaction

from audit.services import log_view
from candidates.models import Candidate
from portal.models import Submission
from requisitions.models import Requisition, Scorecard, ScorecardCriterion
from screening.models import CriterionScore, Score

pytestmark = pytest.mark.django_db


@pytest.fixture
def req_a(org_a, recruiter):
    return Requisition.objects.create(title="Java", client_org=org_a, created_by=recruiter, jd_text="jd")


@pytest.fixture
def req_b(org_b, recruiter):
    return Requisition.objects.create(title="KYC", client_org=org_b, created_by=recruiter, jd_text="jd")


def test_client_sees_only_submitted_candidates_of_own_org(req_a, req_b, client_user_a, recruiter):
    submitted = Candidate.objects.create(requisition=req_a, full_name="S")
    not_submitted = Candidate.objects.create(requisition=req_a, full_name="N")
    other_org = Candidate.objects.create(requisition=req_b, full_name="O")
    Submission.objects.create(candidate=submitted, submitted_by=recruiter)
    Submission.objects.create(candidate=other_org, submitted_by=recruiter)

    visible = set(Candidate.objects.visible_to(client_user_a))
    assert visible == {submitted}
    assert not_submitted not in visible and other_org not in visible


def test_recruiter_sees_all_active_but_not_deleted(req_a, recruiter, delivery_head):
    from django.utils import timezone

    live = Candidate.objects.create(requisition=req_a)
    Candidate.objects.create(requisition=req_a, deleted_at=timezone.now())
    assert set(Candidate.objects.visible_to(recruiter)) == {live}
    assert set(Candidate.objects.visible_to(delivery_head)) == {live}


def test_anonymous_sees_nothing(req_a):
    from django.contrib.auth.models import AnonymousUser

    Candidate.objects.create(requisition=req_a)
    assert not Candidate.objects.visible_to(AnonymousUser()).exists()


def test_scorecard_versions_are_unique(req_a):
    Scorecard.objects.create(requisition=req_a, version=1)
    with pytest.raises(IntegrityError), transaction.atomic():
        Scorecard.objects.create(requisition=req_a, version=1)


@pytest.fixture
def score_parts(req_a):
    cand = Candidate.objects.create(requisition=req_a)
    card = Scorecard.objects.create(requisition=req_a, version=1)
    crit = ScorecardCriterion.objects.create(scorecard=card, name="Spring Boot", weight=3, is_must_have=True)
    return cand, card, crit


def test_cannot_store_a_number_for_an_unscored_cv(score_parts):
    cand, card, _ = score_parts
    with pytest.raises(IntegrityError), transaction.atomic():
        Score.objects.create(candidate=cand, scorecard=card, status=Score.Status.NEEDS_MANUAL_REVIEW, total_score=50)
    ok = Score.objects.create(candidate=cand, scorecard=card, status=Score.Status.NEEDS_MANUAL_REVIEW)
    assert ok.total_score is None


def test_quote_only_allowed_when_verified(score_parts):
    cand, card, crit = score_parts
    score = Score.objects.create(
        candidate=cand, scorecard=card, status=Score.Status.SCORED, total_score=80, band=Score.Band.STRONG
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        CriterionScore.objects.create(
            score=score, criterion=crit, points=80, evidence_status="no_evidence", evidence_quote="invented"
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        CriterionScore.objects.create(score=score, criterion=crit, points=80, evidence_status="verified")
    CriterionScore.objects.create(
        score=score, criterion=crit, points=80, evidence_status="verified", evidence_quote="Built Spring Boot APIs"
    )


def test_log_view_writes_one_row(req_a, recruiter):
    cand = Candidate.objects.create(requisition=req_a)
    log_view(recruiter, cand)
    assert cand.view_logs.filter(user=recruiter, kind="profile").count() == 1
