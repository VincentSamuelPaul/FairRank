import mimetypes

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import StaffReadRecruiterWrite
from audit import jobs
from audit.models import ViewLog
from audit.services import log_view
from candidates.models import Candidate
from candidates.presenters import staff_detail, staff_queryset
from candidates.serializers import DeletionSerializer, StageMoveSerializer, SubmitSerializer
from candidates.services import StageMoveNotAllowed, delete_candidate, recruiter_move
from portal import services as portal_services


def _candidate(pk) -> Candidate:
    """Staff-side lookup: active candidates only (deleted ones are gone from every list and page)."""
    return get_object_or_404(Candidate.objects.active().select_related("requisition__client_org"), pk=pk)


def _detail_response(candidate: Candidate, user) -> Response:
    card = candidate.requisition.current_scorecard
    fresh = staff_queryset(candidate.requisition, card).get(pk=candidate.pk)
    return Response(staff_detail(fresh, card, user))


class CandidateDetailView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        candidate = _candidate(pk)
        log_view(request.user, candidate, ViewLog.Kind.PROFILE)  # rule 7: every open is logged
        return _detail_response(candidate, request.user)


class CandidateCVView(APIView):
    """The original uploaded file. Opening it is logged like opening the profile."""

    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        candidate = _candidate(pk)
        cv = candidate.cv_files.order_by("id").first()
        if cv is None or not cv.file:
            return Response({"detail": "No file."}, status=status.HTTP_404_NOT_FOUND)
        log_view(request.user, candidate, ViewLog.Kind.CV)
        resp = FileResponse(cv.file.open("rb"), content_type=cv.content_type or mimetypes.guess_type(cv.original_name)[0])
        resp["Content-Disposition"] = f'inline; filename="{cv.original_name or "cv"}"'
        return resp


class SubmitView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def post(self, request, pk):
        candidate = _candidate(pk)
        ser = SubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            portal_services.submit_candidate(candidate, request.user, ser.validated_data["note"])
        except portal_services.NotOpened as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except portal_services.Conflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return _detail_response(candidate, request.user)


class StageView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def post(self, request, pk):
        candidate = _candidate(pk)
        ser = StageMoveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            recruiter_move(candidate, ser.validated_data["stage"], request.user, ser.validated_data["reason"])
        except StageMoveNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return _detail_response(candidate, request.user)


class RescoreCandidateView(APIView):
    """Retry scoring (after a failure, or on request). Queued for the worker."""

    permission_classes = [StaffReadRecruiterWrite]

    def post(self, request, pk):
        candidate = _candidate(pk)
        card = candidate.requisition.current_scorecard
        if card is None or not hasattr(candidate, "profile"):
            return Response({"detail": "Nothing to score yet."}, status=status.HTTP_409_CONFLICT)
        jobs.enqueue("score_candidate", {"candidate_id": str(candidate.pk), "scorecard_id": card.pk, "force": True})
        return Response({"queued": True}, status=status.HTTP_202_ACCEPTED)


class DeletionView(APIView):
    """Deletion on request (DPDP). Wipes the file, text and parsed fields; leaves a tombstone."""

    permission_classes = [StaffReadRecruiterWrite]

    def post(self, request, pk):
        candidate = _candidate(pk)
        ser = DeletionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tomb = delete_candidate(candidate, ser.validated_data["requester"], request.user)
        return Response({"deleted": True, "tombstone": {"candidate_id": str(tomb.candidate_id),
                                                         "deleted_at": tomb.deleted_at.isoformat()}})
