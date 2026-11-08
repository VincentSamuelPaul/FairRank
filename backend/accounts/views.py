from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.serializers import LoginSerializer, UserSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """GET sets the csrftoken cookie. The SPA calls this once before login."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set"})


# DRF exempts views from CSRF; login has no session yet so SessionAuthentication
# would skip the check. csrf_protect enforces it explicitly (prevents login CSRF).
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:  # same message for unknown user and wrong password
            return Response(
                {"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST
            )
        login(request, user)  # rotates session key and CSRF token
        return Response(UserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # CSRF enforced by SessionAuthentication

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class SessionView(APIView):
    """Who is signed in? Always 200: {"user": ...} or {"user": null}. Lets the SPA ask on first load without a 403 in the console."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data if request.user.is_authenticated else None})
