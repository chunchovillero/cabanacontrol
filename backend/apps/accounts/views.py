from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    CsrfSerializer,
    EmailSerializer,
    LoginSerializer,
    MessageSerializer,
    PasswordResetConfirmSerializer,
    SessionSerializer,
)
from apps.accounts.services import (
    confirm_password_reset,
    password_reset_user,
    request_password_reset,
    sign_in,
    sign_out,
)
from apps.accounts.throttling import limit_auth_request


def csrf_failure(request, reason=""):
    return JsonResponse(
        {
            "error": {
                "code": "csrf_failed",
                "details": {"detail": "Verificación CSRF fallida. Recarga e intenta nuevamente."},
            }
        },
        status=403,
    )


class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=CsrfSerializer)
    def get(self, request):
        response = Response({"csrf_token": get_token(request)})
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=LoginSerializer, responses=SessionSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        limit_auth_request(request, "login", serializer.validated_data["email"])
        user = sign_in(request, **serializer.validated_data)
        return Response(SessionSerializer(user, context={"request": request}).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        sign_out(request)
        return Response(status=204)


class MeView(APIView):
    @extend_schema(responses=SessionSerializer)
    def get(self, request):
        response = Response(SessionSerializer(request.user, context={"request": request}).data)
        response["Cache-Control"] = "no-store"
        return response


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=EmailSerializer, responses=MessageSerializer)
    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        limit_auth_request(request, "password_reset", email)
        request_password_reset(email)
        return Response(
            {
                "detail": (
                    "Si el correo corresponde a una cuenta activa, "
                    "recibirás instrucciones para recuperar el acceso."
                )
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=PasswordResetConfirmSerializer, responses=MessageSerializer)
    def post(self, request):
        limit_auth_request(request, "password_reset_confirm")
        serializer = PasswordResetConfirmSerializer(data=request.data)
        # Primera validación de estructura; validar nuevamente con usuario para similitud.
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = password_reset_user(data["uid"], data["token"])
        serializer = PasswordResetConfirmSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        confirm_password_reset(user, data["token"], data["password"])
        return Response(
            {"detail": "Contraseña actualizada. Inicia sesión con tu nueva contraseña."}
        )
