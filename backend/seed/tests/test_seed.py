import pytest
from django.core.management import call_command

from accounts.models import ClientOrg, Role, User
from candidates.models import Candidate

pytestmark = pytest.mark.django_db


def test_seed_creates_demo_data_and_is_idempotent():
    call_command("seed")
    call_command("seed")  # second run changes nothing
    assert User.objects.filter(role=Role.RECRUITER).count() == 2
    assert User.objects.filter(role=Role.DELIVERY_HEAD).count() == 1
    assert ClientOrg.objects.count() == 2
    for org in ClientOrg.objects.all():
        assert User.objects.filter(role=Role.CLIENT, client_org=org).count() == 1
    assert Candidate.objects.count() == 3
    assert set(Candidate.objects.values_list("external_id", flat=True)) == {"CND-91022", "CND-91047", "CND-91088"}
    assert Candidate.objects.get(external_id="CND-91022").profile.notice_days == 60
