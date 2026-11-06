from audit.models import ViewLog


def log_view(user, candidate, kind: str = ViewLog.Kind.PROFILE) -> ViewLog:
    """The single place a ViewLog is written (rule 7). Call it on every profile/CV open."""
    return ViewLog.objects.create(user=user, candidate=candidate, kind=kind)


def has_viewed(user, candidate) -> bool:
    """True if this user has opened the candidate's profile or CV (rule 4: open before submit)."""
    return ViewLog.objects.filter(user=user, candidate=candidate).exists()
