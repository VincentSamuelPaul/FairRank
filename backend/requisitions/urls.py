from django.urls import path

from requisitions import views

urlpatterns = [
    path("client-orgs/", views.ClientOrgListView.as_view(), name="client-orgs"),
    path("requisitions/", views.RequisitionListView.as_view(), name="requisitions"),
    path("requisitions/<uuid:pk>/", views.RequisitionDetailView.as_view(), name="requisition-detail"),
    path("requisitions/<uuid:pk>/scorecard/", views.ScorecardView.as_view(), name="scorecard"),
    path("requisitions/<uuid:pk>/rescore/", views.RescoreView.as_view(), name="requisition-rescore"),
    path("requisitions/<uuid:pk>/candidates/", views.RankedListView.as_view(), name="ranked-list"),
    path("requisitions/<uuid:pk>/uploads/", views.UploadView.as_view(), name="uploads"),
    path("requisitions/<uuid:pk>/pipeline/", views.PipelineView.as_view(), name="pipeline"),
]
