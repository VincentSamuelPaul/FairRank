from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import ClientOrg
from accounts.permissions import IsStaffRole, StaffReadRecruiterWrite
from candidates.models import Candidate, CVFile, Stage
from candidates.presenters import staff_queryset, staff_row, viewed_candidate_ids
from candidates.services import UploadRejected, allowed_recruiter_moves, register_upload, validate_upload
from requisitions.models import Requisition, Scorecard
from requisitions.serializers import (RequisitionCreateSerializer, RequisitionUpdateSerializer,
                                      ScorecardInputSerializer, UploadSerializer)
from requisitions.services import create_requisition, queue_rescore, save_scorecard

STAGE_ORDER = [Stage.SOURCED, Stage.SCREENED, Stage.SUBMITTED, Stage.SHORTLISTED, Stage.INTERVIEW, Stage.OFFERED,
               Stage.JOINED, Stage.REJECTED]


def scorecard_payload(card: Scorecard | None) -> dict | None:
    if card is None:
        return None
    return {
        "id": card.pk, "version": card.version, "source": card.source, "created_at": card.created_at.isoformat(),
        "criteria": [{"id": c.pk, "name": c.name, "description": c.description, "weight": c.weight,
                      "is_must_have": c.is_must_have} for c in card.criteria.all()],
    }


def requisition_payload(req: Requisition, *, full: bool = False) -> dict:
    card = req.current_scorecard
    data = {
        "id": str(req.pk), "title": req.title, "status": req.status, "location": req.location,
        "client": {"id": req.client_org_id, "name": req.client_org.name},
        "exp_min_years": float(req.exp_min_years) if req.exp_min_years is not None else None,
        "exp_max_years": float(req.exp_max_years) if req.exp_max_years is not None else None,
        "notice_max_days": req.notice_max_days,
        "ctc_min": float(req.ctc_min) if req.ctc_min is not None else None,
        "ctc_max": float(req.ctc_max) if req.ctc_max is not None else None,
        "created_at": req.created_at.isoformat(), "scorecard_version": card.version if card else None,
    }
    if full:
        data["jd_text"] = req.jd_text
        data["scorecard"] = scorecard_payload(card)
    return data


class ClientOrgListView(APIView):
    permission_classes = [IsStaffRole]

    def get(self, request):
        return Response([{"id": o.pk, "name": o.name} for o in ClientOrg.objects.all()])


class RequisitionListView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request):
        reqs = (Requisition.objects.select_related("client_org").annotate(
            n_total=Count("candidates", filter=Q(candidates__deleted_at__isnull=True)),
            n_submitted=Count("candidates", filter=Q(candidates__deleted_at__isnull=True,
                                                     candidates__submission__isnull=False)),
        ))
        out = []
        for r in reqs:
            item = requisition_payload(r)
            item["counts"] = {"candidates": r.n_total, "submitted": r.n_submitted}
            out.append(item)
        return Response(out)

    def post(self, request):
        ser = RequisitionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        req, warning = create_requisition(request.user, d["client_org"], d["jd_text"], d["title"])
        return Response({"requisition": requisition_payload(req, full=True), "warning": warning},
                        status=status.HTTP_201_CREATED)


class RequisitionDetailView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        req = get_object_or_404(Requisition.objects.select_related("client_org"), pk=pk)
        return Response(requisition_payload(req, full=True))

    def patch(self, request, pk):
        req = get_object_or_404(Requisition.objects.select_related("client_org"), pk=pk)
        ser = RequisitionUpdateSerializer(req, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(requisition_payload(req, full=True))


class ScorecardView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        req = get_object_or_404(Requisition, pk=pk)
        return Response(scorecard_payload(req.current_scorecard))

    def put(self, request, pk):
        """Editing creates a NEW version and queues re-scoring against it."""
        req = get_object_or_404(Requisition, pk=pk)
        ser = ScorecardInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        card = save_scorecard(req, request.user, ser.validated_data["criteria"])
        queued = queue_rescore(req, card)
        return Response({**scorecard_payload(card), "rescoring": queued})


class RescoreView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def post(self, request, pk):
        req = get_object_or_404(Requisition, pk=pk)
        card = req.current_scorecard
        if card is None:
            return Response({"detail": "Add a scorecard first."}, status=status.HTTP_409_CONFLICT)
        return Response({"queued": queue_rescore(req, card)})


def _filter_rows(qs, params):
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(external_id__icontains=q) | Q(profile__raw_text__icontains=q)
                       | Q(profile__current_role__icontains=q))
    if params.get("stage") in STAGE_ORDER:
        qs = qs.filter(stage=params["stage"])
    return qs


def _band_ok(row: dict, band: str) -> bool:
    s = row["score"]
    if band == "unscored":
        return s["state"] != "scored"
    return s["band"] == band


def _sort_key(row: dict):
    s = row["score"]
    return (0, -s["total"], row["created_at"]) if s["state"] == "scored" else (1, 0, row["created_at"])


class RankedListView(APIView):
    """The ranked list. Low scorers and unscored CVs are always included and searchable (rule 1)."""

    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        req = get_object_or_404(Requisition.objects.select_related("client_org"), pk=pk)
        card = req.current_scorecard
        everything = list(staff_queryset(req, card))
        viewed = viewed_candidate_ids(request.user, everything)
        all_rows = [staff_row(c, card, viewed) for c in everything]
        counts = {
            "total": len(all_rows),
            "strong": sum(r["score"]["band"] == "strong" for r in all_rows),
            "possible": sum(r["score"]["band"] == "possible" for r in all_rows),
            "weak": sum(r["score"]["band"] == "weak" for r in all_rows),
            "unscored": sum(r["score"]["state"] != "scored" for r in all_rows),
            "needs_review": sum(r["score"]["state"] == "needs_manual_review" for r in all_rows),
            "failed": sum(r["score"]["state"] in ("failed", "cv_failed") for r in all_rows),
            "processing": sum(r["score"]["state"] in ("processing", "pending") for r in all_rows),
            "duplicates": sum(r["duplicate_of"] is not None for r in all_rows),
        }
        wanted = {str(c.pk) for c in _filter_rows(staff_queryset(req, card), request.query_params)}
        rows = [r for r in all_rows if r["id"] in wanted]
        band = request.query_params.get("band")
        if band in ("strong", "possible", "weak", "unscored"):
            rows = [r for r in rows if _band_ok(r, band)]
        flag = request.query_params.get("flag")
        if flag == "duplicates":
            rows = [r for r in rows if r["duplicate_of"]]
        elif flag == "needs_attention":
            rows = [r for r in rows if r["score"]["state"] in ("needs_manual_review", "failed", "cv_failed")]
        rows.sort(key=_sort_key)
        return Response({"requisition": requisition_payload(req), "scorecard": scorecard_payload(card),
                         "counts": counts, "candidates": rows})


class UploadView(APIView):
    """Bulk CV upload. Each file is validated (size, magic bytes) and queued for the worker."""

    permission_classes = [StaffReadRecruiterWrite]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        req = get_object_or_404(Requisition, pk=pk)
        ser = UploadSerializer(data={"files": request.FILES.getlist("files"),
                                     "consent_confirmed": request.data.get("consent_confirmed")})
        ser.is_valid(raise_exception=True)
        accepted, rejected = [], []
        for f in ser.validated_data["files"]:
            try:
                upload = validate_upload(f.name, f.read())
            except UploadRejected as exc:
                rejected.append({"name": f.name, "reason": exc.reason})
                continue
            cand = register_upload(req, request.user, upload)
            accepted.append({"candidate_id": str(cand.pk), "name": upload.name})
        return Response({"accepted": accepted, "rejected": rejected}, status=status.HTTP_201_CREATED)

    def get(self, request, pk):
        """Per-file processing status for the given candidate ids (polled by the upload screen)."""
        req = get_object_or_404(Requisition, pk=pk)
        ids = [i for i in (request.query_params.get("ids") or "").split(",") if i][:600]
        card = req.current_scorecard
        cands = list(staff_queryset(req, card).filter(pk__in=ids)) if ids else []
        items = []
        for c in cands:
            row = staff_row(c, card, set())
            items.append({"candidate_id": row["id"], "name": row["original_name"], "full_name": row["full_name"],
                          "cv_status": row["cv_status"], "note": row["cv_note"], "score_state": row["score"]["state"],
                          "band": row["score"]["band"], "total": row["score"]["total"]})
        busy = any(i["cv_status"] == CVFile.Status.QUEUED or i["score_state"] in ("pending", "processing")
                   for i in items)
        return Response({"items": items, "in_progress": busy})


class PipelineView(APIView):
    permission_classes = [StaffReadRecruiterWrite]

    def get(self, request, pk):
        req = get_object_or_404(Requisition.objects.select_related("client_org"), pk=pk)
        card = req.current_scorecard
        rows = [staff_row(c, card, set()) for c in staff_queryset(req, card)]
        moves = {str(c.pk): allowed_recruiter_moves(c) for c in Candidate.objects.active().filter(requisition=req)}
        columns = []
        for st in STAGE_ORDER:
            cards = [{"id": r["id"], "full_name": r["full_name"] or "Unnamed", "external_id": r["external_id"],
                      "current_role": r["current_role"], "score": r["score"]["total"], "band": r["score"]["band"],
                      "state": r["score"]["state"], "allowed_moves": moves.get(r["id"], [])}
                     for r in sorted(rows, key=_sort_key) if r["stage"] == st]
            columns.append({"stage": st, "label": Stage(st).label, "candidates": cards})
        return Response({"requisition": requisition_payload(req), "columns": columns})
