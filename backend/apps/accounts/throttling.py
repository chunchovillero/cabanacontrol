from datetime import timedelta
from hashlib import sha256
from hmac import new as hmac_new
from math import ceil

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled

from apps.accounts.models import AuthThrottleBucket


def consume_limit(scope: str, identity: str, limit: int, *, window_seconds=None):
    key = hmac_new(settings.SECRET_KEY.encode(), f"{scope}:{identity}".encode(), sha256).hexdigest()
    now = timezone.now()
    seconds = settings.AUTH_THROTTLE_SECONDS if window_seconds is None else window_seconds
    with transaction.atomic():
        AuthThrottleBucket.objects.get_or_create(
            key=key,
            defaults={"expires_at": now + timedelta(seconds=seconds)},
        )
        bucket = AuthThrottleBucket.objects.select_for_update().get(key=key)
        if bucket.expires_at <= now:
            bucket.count = 0
            bucket.expires_at = now + timedelta(seconds=seconds)
        if bucket.count >= limit:
            wait = max(1, ceil((bucket.expires_at - now).total_seconds()))
        else:
            bucket.count += 1
            bucket.save(update_fields=["count", "expires_at"])
            wait = None
    if wait:
        raise Throttled(
            wait=wait, detail="Demasiados intentos. Espera unos minutos e intenta nuevamente."
        )


def limit_auth_request(request, scope: str, email: str | None = None):
    # No confiar en X-Forwarded-For enviado por el cliente.
    ip = request.META.get("REMOTE_ADDR", "unknown")
    consume_limit(f"{scope}:ip", ip, settings.LOGIN_IP_LIMIT)
    if email:
        consume_limit(f"{scope}:account", email.strip().lower(), settings.LOGIN_ACCOUNT_LIMIT)
