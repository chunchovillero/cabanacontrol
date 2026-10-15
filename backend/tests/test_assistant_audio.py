import io
import json
import wave
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from apps.assistant.audio import inspect_audio, transcribe
from apps.assistant.models import AIUsageDaily, TenantAISettings
from apps.assistant.providers import ProviderUnavailable

pytestmark = pytest.mark.django_db(transaction=True)


def wav(seconds=1):
    content = io.BytesIO()
    with wave.open(content, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 8000 * seconds)
    return content.getvalue()


def test_real_probe_accepts_wav_rejects_fake_and_overlong(tmp_path):
    path = tmp_path / "fictitious.wav"
    path.write_bytes(wav())
    assert inspect_audio(path) == (1, "wav")
    path.write_bytes(b"not audio")
    with pytest.raises(ValidationError):
        inspect_audio(path)
    path.write_bytes(wav(61))
    with pytest.raises(ValidationError):
        inspect_audio(path)


@pytest.mark.parametrize(
    "streams,duration",
    [([{"codec_type": "video"}], "2"), ([{"codec_type": "audio"}], "nan"), ([], "2")],
)
def test_probe_rejects_video_and_invalid_duration(tmp_path, streams, duration):
    with patch("apps.assistant.audio.subprocess.run") as probe:
        probe.return_value.stdout = json.dumps(
            {"streams": streams, "format": {"duration": duration, "format_name": "mp4"}}
        ).encode()
        with pytest.raises(ValidationError):
            inspect_audio(tmp_path / "new")
        assert probe.call_args.kwargs["shell"] is False
        assert probe.call_args.kwargs["timeout"] == 5


def test_oversize_never_calls_provider(identities):
    upload = SimpleUploadedFile("fictitious.wav", b"x" * (5 * 1024 * 1024 + 1))
    with patch("apps.assistant.providers.AsyncOpenAI") as sdk:
        with pytest.raises(ValidationError):
            transcribe(actor=identities["owner"], tenant=identities["tenant_a"], upload=upload)
        sdk.assert_not_called()


def test_provider_error_retains_quota_and_removes_only_new_temp(identities, settings):
    settings.AI_ENABLED = True
    settings.OPENAI_API_KEY = "test-not-real"
    settings.OPENAI_TEXT_MODEL = "test"
    settings.OPENAI_TRANSCRIPTION_MODEL = "test"
    settings.AI_PRICE_INPUT_USD_PER_MILLION = "1"
    settings.AI_PRICE_OUTPUT_USD_PER_MILLION = "1"
    settings.AI_PRICE_AUDIO_USD_PER_MINUTE = "0.01"
    TenantAISettings.objects.create(tenant=identities["tenant_a"], enabled=True, voice_enabled=True)
    upload = SimpleUploadedFile("dictado.wav", wav(), content_type="audio/wav")
    paths = []
    original = inspect_audio

    def capture(path):
        paths.append(path)
        return original(path)

    with (
        patch("apps.assistant.audio.inspect_audio", side_effect=capture),
        patch("apps.assistant.providers.AsyncOpenAI") as sdk,
    ):
        sdk.side_effect = RuntimeError("secret response must never appear")
        with pytest.raises(ProviderUnavailable) as error:
            transcribe(actor=identities["owner"], tenant=identities["tenant_a"], upload=upload)
    assert "secret" not in str(error.value)
    assert paths and not paths[0].exists()
    usage = AIUsageDaily.objects.get(tenant=identities["tenant_a"])
    assert usage.requests == 1 and usage.audio_seconds == 1
