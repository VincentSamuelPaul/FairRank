"""Client portal API. Every candidate lookup goes through Candidate.objects.visible_to(user) (rule 5):
another org's candidate or requisition is a 404, not a 403, so existence is not revealed."""
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsClient, IsDeliveryHead, IsRecruiter, IsStaffRole
from audit.models import ViewLog
from audit.services import log_view
from candidates.models import Candidate, Stage
from candidates.presenters import client_card
from portal import reports, services
from portal.models import InterviewSlot
from portal.serializers import DecisionSerializer, SlotResponseSerializer, SlotSerializer
from requisitions.models import Requisition
from requisitions.views import STAGE_ORDER


def _client_candidates(user):
    return (Candidate.objects.visible_to(user)
            .select_related("profile", "submission", "requisition")
            .prefetch_related("scores__criterion_scores__criterion", "submission__decisions", "submission__slots"))


def _card(candidate: Candidate, *, detail: bool = False) -> dict:
    return client_card(candidate, candidate.requisition.current_scorecard, detail=detail)


def _own_requisitions(user):
    return Requisition.objects.filter(client_org_id=user.client_org_id).select_related("client_org")


class PortalRequisitionsView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        reqs = _own_requisitions(request.user).annotate(
            n=Count("candidates", filter=Q(candidates__submission__isnull=False, candidates__deleted_at__isnull=True)),
            n_pending=Count("candidates", filter=Q(candidates__stage=Stage.SUBMITTED, candidates__deleted_at__isnull=True)),
        )
        return Response([{"id": str(r.pk), "title": r.title, "location": r.location, "status": r.status,
                          "submitted": r.n, "awaiting_decision": r.n_pending} for r in reqs if r.n > 0])


class PortalRequisitionView(APIView):
    permission_classes = [IsClient]

    def get(self, request, pk):
        r = get_object_or_404(_own_requisitions(request.user), pk=pk)
        return Response({"id": str(r.pk), "title": r.title, "location": r.location, "status": r.status})


class PortalCandidatesView(APIView):
    permission_classes = [IsClient]

    def get(self, request):
        qs = _client_candidates(request.user)
        req_id = request.query_params.get("requisition")
        if req_id:
            qs = qs.filter(requisition_id=req_id)
        cards = [_card(c) for c in qs.order_by("-submission__submitted_at")]
        cards.sort(key=lambda c: -(c["score"]["total"] if c["score"]["total"] is not None else -1))
        return Response(cards)


class PortalCandidateView(APIView):
    permission_classes = [IsClient]

    def get(self, request, pk):
        candidate = get_object_or_404(_client_candidates(request.user), pk=pk)
        log_view(request.user, candidate, ViewLog.Kind.PROFILE)  # rule 7
        return Response(_card(candidate, detail=True))


class PortalDecisionView(APIView):
    permission_classes = [IsClient]

    def post(self, request, pk):
        candidate = get_object_or_404(_client_candidates(request.user), pk=pk)
        ser = DecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            services.client_decide(candidate, request.user, ser.validated_data["decision"], ser.validated_data["reason"])
        except services.Conflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        candidate = get_object_or_404(_client_candidates(request.user), pk=pk)
        return Response(_card(candidate, detail=True))


class PortalSlotView(APIView):
    permission_classes = [IsClient]

    def post(self, request, pk):
        candidate = get_object_or_404(_client_candidates(request.user), pk=pk)
        ser = SlotSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            services.propose_slot(candidate, request.user, d["starts_at"], d["duration_minutes"], d["note"])
        except services.Conflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        candidate = get_object_or_404(_client_candidates(request.user), pk=pk)
        return Response(_card(candidate, detail=True), status=status.HTTP_201_CREATED)


class SlotRespondView(APIView):
    """Recruiter confirms or declines a slot the client proposed (mock scheduling)."""

    permission_classes = [IsRecruiter]

    def post(self, request, pk):
        slot = get_object_or_404(InterviewSlot, pk=pk)
        ser = SlotResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.respond_slot(slot, ser.validated_data["status"])
        return Response({"id": slot.pk, "status": slot.status})


class AgreementReportView(APIView):
    permission_classes = [IsDeliveryHead]

    def get(self, request):
        try:
            days = max(1, min(90, int(request.query_params.get("days", 7))))
        except ValueError:
            days = 7
        return Response(reports.agreement_report(days))


class PipelineSummaryView(APIView):
    """Stage counts per requisition, for the delivery head's overview."""

    permission_classes = [IsStaffRole]

    def get(self, request):
        out = []
        for req in Requisition.objects.select_related("client_org"):
            counts = {st: 0 for st in STAGE_ORDER}
            for stage in Candidate.objects.active().filter(requisition=req).values_list("stage", flat=True):
                counts[stage] += 1
            out.append({"id": str(req.pk), "title": req.title, "client": req.client_org.name, "status": req.status,
                        "counts": counts, "total": sum(counts.values())})
        return Response(out)
