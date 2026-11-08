import pytest
from django.core.management import call_command

from accounts.models import ClientOrg, Role, User
from candidates.models import Candidate, CVFile, Stage
from portal.models import Submission
from requisitions.models import Requisition
from screening.models import Score

pytestmark = pytest.mark.django_db


def test_seed_creates_demo_data_and_is_idempotent():
    call_command("seed")
    counts = (Candidate.objects.count(), Submission.objects.count(), Score.objects.count())
    call_command("seed")  # second run changes nothing
    assert (Candidate.objects.count(), Submission.objects.count(), Score.objects.count()) == counts

    assert User.objects.filter(role=Role.RECRUITER).count() == 2
    assert User.objects.filter(role=Role.DELIVERY_HEAD).count() == 1
    assert ClientOrg.objects.count() == 2
    for org in ClientOrg.objects.all():
        assert User.objects.filter(role=Role.CLIENT, client_org=org).count() == 1
    assert Requisition.objects.count() == 3
    assert Candidate.objects.count() == 31

    brief = {c.external_id: c for c in Candidate.objects.filter(external_id__in=["CND-91022", "CND-91047", "CND-91088"])}
    assert set(brief) == {"CND-91022", "CND-91047", "CND-91088"}
    assert brief["CND-91022"].full_name == "Ritika Bansal" and brief["CND-91022"].profile.notice_days == 60
    assert float(brief["CND-91088"].profile.experience_years) == 4.0 and brief["CND-91088"].profile.notice_days == 90
    assert brief["CND-91047"].profile.current_role == "KYC Analyst"

    # every state the UI must handle exists in the seed
    assert CVFile.objects.filter(status=CVFile.Status.NEEDS_REVIEW).count() == 1  # the scanned CV
    assert CVFile.objects.filter(status=CVFile.Status.DUPLICATE).count() == 1
    assert Score.objects.filter(status=Score.Status.SCORED).count() == 30
    assert {Score.Band.STRONG, Score.Band.POSSIBLE, Score.Band.WEAK} <= set(Score.objects.values_list("band", flat=True))
    stages = set(Candidate.objects.values_list("stage", flat=True))
    assert {Stage.SCREENED, Stage.SUBMITTED, Stage.SHORTLISTED, Stage.INTERVIEW, Stage.OFFERED, Stage.JOINED, Stage.REJECTED} <= stages

    # the sample candidates rank sensibly for the example JD
    java = Requisition.objects.get(title="Senior Java Developer")
    ritika, arjun = (Score.objects.get(candidate=brief[k], scorecard=java.current_scorecard) for k in ("CND-91022", "CND-91047"))
    assert ritika.band == Score.Band.STRONG and arjun.band == Score.Band.WEAK and arjun.candidate.deleted_at is None


@pytest.mark.django_db(transaction=True)
def test_seed_reset_removes_non_seed_rows_and_files(settings, tmp_path):
    """--reset gives exactly what a fresh seed produces: extra requisitions and orphan uploads are gone."""
    settings.MEDIA_ROOT = str(tmp_path)
    call_command("seed")
    from requisitions.models import Requisition
    extra = Requisition.objects.first()
    Requisition.objects.create(title="Scratch test requisition", client_org=extra.client_org, created_by=extra.created_by)
    (tmp_path / "cvs").mkdir(exist_ok=True)
    (tmp_path / "cvs" / "orphan.pdf").write_bytes(b"%PDF-1.4")
    call_command("seed", "--reset")
    assert not Requisition.objects.filter(title="Scratch test requisition").exists()
    assert not (tmp_path / "cvs" / "orphan.pdf").exists()
    assert Requisition.objects.count() == 3


def test_seed_scores_never_use_a_live_provider(settings):
    """Seeded scores are all offline-heuristic, whatever LLM provider the environment is configured with."""
    settings.LLM_PROVIDER = "groq"
    settings.GROQ_API_KEY = ""
    call_command("seed")
    models = set(Score.objects.exclude(model_name="").values_list("model_name", flat=True))
    assert models == {"offline-heuristic-v1"}
