from django.urls import path

from candidates import views

urlpatterns = [
    path("candidates/<uuid:pk>/", views.CandidateDetailView.as_view(), name="candidate-detail"),
    path("candidates/<uuid:pk>/cv/", views.CandidateCVView.as_view(), name="candidate-cv"),
    path("candidates/<uuid:pk>/submit/", views.SubmitView.as_view(), name="candidate-submit"),
    path("candidates/<uuid:pk>/stage/", views.StageView.as_view(), name="candidate-stage"),
    path("candidates/<uuid:pk>/rescore/", views.RescoreCandidateView.as_view(), name="candidate-rescore"),
    path("candidates/<uuid:pk>/delete/", views.DeletionView.as_view(), name="candidate-delete"),
]
