from audit.models import ViewLog


def log_view(user, candidate, kind: str = ViewLog.Kind.PROFILE) -> ViewLog:
    """The single place a ViewLog is written (rule 7). Call it on every profile/CV open."""
    return ViewLog.objects.create(user=user, candidate=candidate, kind=kind)
