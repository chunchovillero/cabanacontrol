import json
import math
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import Throttled, ValidationError

from apps.accounts.throttling import consume_limit
from apps.assistant.models import AIUsageDaily
from apps.assistant.providers import ProviderUnavailable, call_provider
from apps.assistant.services import configuration, ready
from apps.reservations.services import local_today

MAX_BYTES = 5 * 1024 * 1024


def audio_ready():
    from apps.assistant.testing import simulated

    if simulated():
        return True
    try:
        rate = Decimal(settings.AI_PRICE_AUDIO_USD_PER_MINUTE)
        return bool(
            ready()
            and settings.OPENAI_TRANSCRIPTION_MODEL
            and rate.is_finite()
            and 0 < rate <= 1000
        )
    except (InvalidOperation, ValueError):
        return False


def inspect_audio(path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-show_packets",
                "-show_entries",
                "format=format_name,duration:stream=codec_type:packet=pts_time,duration_time",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=5,
            check=True,
            shell=False,
        )
        probe = json.loads(result.stdout)
        streams = probe["streams"]
        duration_value = probe["format"].get("duration")
        if duration_value is None or duration_value == "N/A":
            packets = probe["packets"]
            starts = [float(packet["pts_time"]) for packet in packets]
            ends = [
                float(packet["pts_time"]) + float(packet.get("duration_time", "0"))
                for packet in packets
            ]
            duration = max(ends) - min(starts)
        else:
            duration = float(duration_value)
        formats = set(probe["format"]["format_name"].split(","))
        if (
            not streams
            or any(stream["codec_type"] != "audio" for stream in streams)
            or not math.isfinite(duration)
            or not 0 < duration <= 60
            or not formats.intersection({"matroska", "webm", "mov", "mp4", "wav"})
        ):
            raise ValueError
        extension = "wav" if "wav" in formats else "webm" if "webm" in formats else "mp4"
        return math.ceil(duration), extension
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
        raise ValidationError(
            "Audio inválido. Usa WebM, MP4 o WAV, sin vídeo y hasta 60 segundos."
        ) from None


def reserve_audio(actor, tenant, seconds):
    config = configuration(tenant)
    if not audio_ready() or not config.enabled or not config.voice_enabled:
        raise ProviderUnavailable()
    consume_limit("ai:user", str(actor.pk), 6, window_seconds=60)
    consume_limit("ai:tenant", str(tenant.pk), 15, window_seconds=60)
    from apps.assistant.testing import simulated

    rate = Decimal("0.01") if simulated() else Decimal(settings.AI_PRICE_AUDIO_USD_PER_MINUTE)
    cost = (Decimal(seconds) / 60 * rate).quantize(Decimal("0.000001"), rounding="ROUND_UP")
    with transaction.atomic():
        config = configuration(tenant)
        config = type(config).objects.select_for_update().get(tenant=tenant)
        if not config.enabled or not config.voice_enabled:
            raise ProviderUnavailable()
        AIUsageDaily.objects.get_or_create(tenant=tenant, date=local_today(tenant))
        usage = AIUsageDaily.objects.select_for_update().get(
            tenant=tenant, date=local_today(tenant)
        )
        if (
            usage.requests >= config.daily_requests
            or usage.audio_seconds + seconds > config.daily_audio_seconds
            or usage.reserved_usd + cost > config.daily_budget_usd
        ):
            raise Throttled(wait=86400, detail="Se alcanzó el límite diario de dictado.")
        usage.requests += 1
        usage.audio_seconds += seconds
        usage.reserved_usd += cost
        usage.save(update_fields=["requests", "audio_seconds", "reserved_usd"])


def transcribe(*, actor, tenant, upload):
    if upload.size > MAX_BYTES or upload.size <= 0:
        raise ValidationError("El audio debe ocupar entre 1 byte y 5 MB.")
    with TemporaryDirectory(prefix="cabanacontrol-dictado-") as directory:
        path = Path(directory) / "audio"
        size = 0
        with path.open("wb") as file:
            for chunk in upload.chunks():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValidationError("El audio supera 5 MB.")
                file.write(chunk)
        seconds, extension = inspect_audio(path)
        reserve_audio(actor, tenant, seconds)
        from apps.assistant.testing import simulated

        if simulated():
            return "Dictado simulado: consulta para 2 personas; fechas por revisar."
        try:
            with path.open("rb") as file:
                response = call_provider(
                    "audio",
                    model=settings.OPENAI_TRANSCRIPTION_MODEL,
                    file=(f"dictado.{extension}", file),
                    language="es",
                    response_format="json",
                )
            text = response.text
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                raise ValueError
            return text.strip()
        except Exception:
            raise ProviderUnavailable() from None
