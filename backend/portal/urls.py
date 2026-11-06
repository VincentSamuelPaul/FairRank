from django.urls import path

from portal import views

urlpatterns = [
    path("portal/requisitions/", views.PortalRequisitionsView.as_view(), name="portal-requisitions"),
    path("portal/requisitions/<uuid:pk>/", views.PortalRequisitionView.as_view(), name="portal-requisition"),
    path("portal/candidates/", views.PortalCandidatesView.as_view(), name="portal-candidates"),
    path("portal/candidates/<uuid:pk>/", views.PortalCandidateView.as_view(), name="portal-candidate"),
    path("portal/candidates/<uuid:pk>/decision/", views.PortalDecisionView.as_view(), name="portal-decision"),
    path("portal/candidates/<uuid:pk>/slots/", views.PortalSlotView.as_view(), name="portal-slot"),
    path("slots/<int:pk>/respond/", views.SlotRespondView.as_view(), name="slot-respond"),
    path("reports/agreement/", views.AgreementReportView.as_view(), name="agreement-report"),
    path("pipeline/summary/", views.PipelineSummaryView.as_view(), name="pipeline-summary"),
]
