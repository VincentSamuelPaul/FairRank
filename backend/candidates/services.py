"""Candidate lifecycle: upload, processing, stage changes, deletion. Business logic lives here, not in views."""
import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from audit import jobs
from audit.models import Notification
from candidates.dedupe import find_duplicate
from candidates.models import Candidate, Consent, CVFile, ParsedProfile, Stage, StageEvent, Tombstone
from candidates.normalize import normalize_email, normalize_phone
from candidates.parsing import UnsupportedFile, extract_text, parse_profile, sniff_kind
from requisitions.models import Requisition
from screening.models import Score
from screening.services import MIN_CV_CHARS, mark_needs_manual_review


class UploadRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class ValidatedUpload:
    name: str
    data: bytes
    kind: str


def clean_filename(name: str) -> str:
    base = PurePosixPath((name or "cv").replace("\\", "/")).name
    return re.sub(r"[^\w.\- ]", "_", base)[:200] or "cv"


def validate_upload(name: str, data: bytes) -> ValidatedUpload:
    """Size and magic-byte checks. The extension and client content-type are never trusted."""
    if not data:
        raise UploadRejected("The file is empty.")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise UploadRejected(f"Larger than {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        kind = sniff_kind(data)
    except UnsupportedFile as exc:
        raise UploadRejected(str(exc)) from exc
    return ValidatedUpload(name=clean_filename(name), data=data, kind=kind)


@transaction.atomic
def register_upload(requisition: Requisition, user, upload: ValidatedUpload, *, external_id: str = "",
                    enqueue: bool = True) -> Candidate:
    """Store the file, record consent on the candidate's behalf (A5) and queue processing."""
    candidate = Candidate.objects.create(requisition=requisition, external_id=external_id, created_by=user)
    cv = CVFile(
        candidate=candidate, original_name=upload.name, size_bytes=len(upload.data),
        content_type="application/pdf" if upload.kind == "pdf" else
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        sha256=hashlib.sha256(upload.data).hexdigest(), uploaded_by=user,
    )
    cv.file.save(f"{candidate.pk}.{upload.kind}", ContentFile(upload.data), save=False)
    cv.save()
    Consent.objects.create(candidate=candidate, recorded_by=user)
    if enqueue:
        jobs.enqueue("process_cv", {"candidate_id": str(candidate.pk)})
    return candidate


def _text_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


def process_cv(candidate_id: str) -> None:
    """Extract text, parse the profile, flag duplicates, then queue scoring (or flag for manual review)."""
    candidate = Candidate.objects.active().select_related("requisition").filter(pk=candidate_id).first()
    cv = candidate.cv_files.order_by("id").first() if candidate else None
    if candidate is None or cv is None or not cv.file:
        return
    kind = "pdf" if cv.content_type == "application/pdf" else "docx"
    try:
        with cv.file.open("rb") as fh:
            text = extract_text(fh.read(), kind)
    except UnsupportedFile as exc:
        cv.status, cv.error = CVFile.Status.FAILED, str(exc)[:500]
        cv.save(update_fields=["status", "error"])
        return

    parsed = parse_profile(text)
    candidate.full_name = parsed.full_name
    candidate.email, candidate.phone = parsed.email, parsed.phone
    candidate.email_normalized = normalize_email(parsed.email)
    candidate.phone_normalized = normalize_phone(parsed.phone)
    ParsedProfile.objects.update_or_create(candidate=candidate, defaults={
        "raw_text": text, "text_hash": _text_hash(text), "current_role": parsed.current_role,
        "experience_years": parsed.experience_years, "skills": parsed.skills, "notice_days": parsed.notice_days,
        "location": parsed.location, "current_ctc": parsed.current_ctc, "expected_ctc": parsed.expected_ctc,
    })
    scorecard = candidate.requisition.current_scorecard

    if len(text.strip()) < MIN_CV_CHARS:  # scanned / image-only (A3): honest "unsure", no OCR
        candidate.save()
        cv.status, cv.error = CVFile.Status.NEEDS_REVIEW, "No readable text. Review the file by hand."
        cv.save(update_fields=["status", "error"])
        if scorecard:
            mark_needs_manual_review(candidate, scorecard)
        return

    match = find_duplicate(candidate, cv.sha256)
    candidate.duplicate_of = match.candidate if match else None
    candidate.save()
    cv.status = CVFile.Status.DUPLICATE if match else CVFile.Status.PARSED
    cv.error = f"Possible duplicate of {match.candidate.external_id or match.candidate.full_name or 'another record'} ({match.reason})" if match else ""
    cv.save(update_fields=["status", "error"])
    if scorecard:
        jobs.enqueue("score_candidate", {"candidate_id": str(candidate.pk), "scorecard_id": scorecard.pk})


def after_scoring(candidate: Candidate, score: Score) -> None:
    """A finished score moves sourced -> screened. This depends on the CV having been processed,
    never on how high or low the score is (rule 1)."""
    if score.status == Score.Status.SCORED and candidate.stage == Stage.SOURCED:
        change_stage(candidate, Stage.SCREENED, None, "Screened by AI")


# --- Stages ---------------------------------------------------------------------------------

# Moves a recruiter may make by hand. Submitted/shortlisted/interview/rejected come from the
# submit flow and the client's own decisions, never from here (rule 4 and rule 1).
RECRUITER_MOVES: dict[str, tuple[str, ...]] = {
    Stage.SOURCED: (Stage.SCREENED,),
    Stage.SCREENED: (Stage.SOURCED,),
    Stage.INTERVIEW: (Stage.OFFERED,),
    Stage.OFFERED: (Stage.JOINED, Stage.INTERVIEW),
}


def allowed_recruiter_moves(candidate: Candidate) -> list[str]:
    return list(RECRUITER_MOVES.get(candidate.stage, ()))


@transaction.atomic
def change_stage(candidate: Candidate, to_stage: str, user, reason: str = "") -> StageEvent | None:
    """The one place a stage changes; always logged (who, from, to, when)."""
    if candidate.stage == to_stage:
        return None
    event = StageEvent.objects.create(candidate=candidate, from_stage=candidate.stage, to_stage=to_stage,
                                      changed_by=user, reason=reason[:500])
    candidate.stage = to_stage
    candidate.save(update_fields=["stage"])
    return event


class StageMoveNotAllowed(Exception):
    pass


def recruiter_move(candidate: Candidate, to_stage: str, user, reason: str = "") -> StageEvent | None:
    if to_stage not in allowed_recruiter_moves(candidate):
        raise StageMoveNotAllowed(f"Cannot move from {candidate.stage} to {to_stage} here.")
    return change_stage(candidate, to_stage, user, reason)


# --- Deletion on request (rule 8, A6) --------------------------------------------------------

@transaction.atomic
def delete_candidate(candidate: Candidate, requester: str, processed_by) -> Tombstone:
    """Wipe file, text, parsed fields, scores and contacts. Leaves a tombstone (id, date, requester)."""
    existing = Tombstone.objects.filter(candidate_id=candidate.pk).first()
    if existing:
        return existing
    for cv in candidate.cv_files.all():
        if cv.file:
            cv.file.delete(save=False)
    candidate.cv_files.all().delete()
    ParsedProfile.objects.filter(candidate=candidate).delete()
    candidate.scores.all().delete()  # criterion scores (CV quotes) cascade
    candidate.duplicates.update(duplicate_of=None)
    Candidate.objects.filter(pk=candidate.pk).update(
        full_name="", email="", phone="", email_normalized="", phone_normalized="", external_id="",
        duplicate_of=None, deleted_at=timezone.now(),
    )
    tomb = Tombstone.objects.create(candidate_id=candidate.pk, requester=requester[:120] or "candidate",
                                    processed_by=processed_by)
    Notification.objects.create(
        recipient=processed_by, subject="Candidate data deleted",
        body=f"Candidate {candidate.pk} was deleted on request by {tomb.requester}. A tombstone was recorded.",
    )
    return tomb
