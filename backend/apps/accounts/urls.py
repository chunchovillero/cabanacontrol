from django.urls import path

from apps.accounts.onboarding import RegistrationView
from apps.accounts.profile import ProfileView
from apps.accounts.views import (
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetView,
)

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("register/", RegistrationView.as_view(), name="auth-register"),
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password-reset/", PasswordResetView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
