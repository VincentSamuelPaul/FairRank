from django.urls import path

from accounts import views

urlpatterns = [
    path("csrf/", views.CsrfView.as_view(), name="auth-csrf"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("session/", views.SessionView.as_view(), name="auth-session"),
    path("me/", views.MeView.as_view(), name="auth-me"),
]
