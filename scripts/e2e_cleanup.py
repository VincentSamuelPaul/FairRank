"""Remove ONLY the requisitions the browser end-to-end run created (titles starting "E2E") and everything under them.
Run inside the web container:  docker compose exec -T web python manage.py shell < scripts/e2e_cleanup.py
Seed data is never touched. (Candidate -> Requisition is PROTECT, so the candidates go first.)"""
from candidates.models import Candidate
from requisitions.models import Requisition

removed = 0
for req in Requisition.objects.filter(title__startswith="E2E"):
    removed += Candidate.objects.filter(requisition=req).delete()[0]
    req.scorecards.all().delete()
    req.delete()
print("e2e cleanup: removed", Requisition.objects.filter(title__startswith="E2E").count(), "E2E requisitions left;", removed, "rows deleted under them")
