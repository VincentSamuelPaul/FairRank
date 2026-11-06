"""Duplicate detection: exact email, exact phone, identical file, or near-identical name with a
near-identical phone (one slipped digit). Matches are FLAGGED, never merged or dropped."""
from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

from candidates.models import Candidate, CVFile

NAME_SIMILARITY = 90  # token_sort_ratio, 0-100


@dataclass
class DuplicateMatch:
    candidate: Candidate
    reason: str


def find_duplicate(candidate: Candidate, sha256: str = "") -> DuplicateMatch | None:
    """Earliest other active candidate that looks like the same person. Same requisition wins."""
    others = Candidate.objects.active().exclude(pk=candidate.pk).filter(created_at__lte=candidate.created_at)
    scopes = [others.filter(requisition=candidate.requisition), others.exclude(requisition=candidate.requisition)]
    for pool in scopes:
        match = _match_in(pool, candidate, sha256)
        if match:
            return match
    return None


def _match_in(pool, candidate: Candidate, sha256: str) -> DuplicateMatch | None:
    pool = pool.order_by("created_at")
    if candidate.email_normalized:
        hit = pool.filter(email_normalized=candidate.email_normalized).first()
        if hit:
            return DuplicateMatch(hit, "same email")
    if candidate.phone_normalized:
        hit = pool.filter(phone_normalized=candidate.phone_normalized).first()
        if hit:
            return DuplicateMatch(hit, "same phone")
    if sha256:
        file_hit = CVFile.objects.filter(sha256=sha256, candidate__in=pool).order_by("candidate__created_at").first()
        if file_hit:
            return DuplicateMatch(file_hit.candidate, "identical file")
    if candidate.full_name and candidate.phone_normalized:
        for other in pool.exclude(phone_normalized="").exclude(full_name=""):
            if (
                fuzz.token_sort_ratio(candidate.full_name.lower(), other.full_name.lower()) >= NAME_SIMILARITY
                and Levenshtein.distance(candidate.phone_normalized, other.phone_normalized) <= 1
            ):
                return DuplicateMatch(other, "near-identical name and phone")
    return None
