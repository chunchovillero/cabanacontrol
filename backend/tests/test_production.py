import json
import logging
import os
import subprocess
import sys
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from config.production_logging import SafeFormatter


@pytest.mark.parametrize(
    "override,allowed",
    [
        ({}, True),
        ({"DJANGO_DEBUG": "true"}, False),
        ({"DJANGO_SECRET_KEY": "short"}, False),
        ({"DJANGO_ALLOWED_HOSTS": "*"}, False),
        ({"FRONTEND_URL": "http://localhost"}, False),
        ({"AI_TEST_PROVIDER": "true"}, False),
        ({"WHATSAPP_TEST_PROVIDER": "true"}, False),
        ({"E2E_TEST_MODE": "true"}, False),
    ],
)
def test_production_rejects_unsafe_configuration(override, allowed):
    env = {
        **os.environ,
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": "fictional-production-test-abcdefghijklmnopqrstuvwxyz0123456789",
        "DJANGO_ALLOWED_HOSTS": "localhost",
        "FRONTEND_URL": "https://localhost",
        "POSTGRES_PASSWORD": "fictional-only",
        "AI_TEST_PROVIDER": "false",
        "WHATSAPP_TEST_PROVIDER": "false",
        "E2E_TEST_MODE": "false",
        **override,
    }
    result = subprocess.run(
        [sys.executable, "-c", "import config.production"],
        env=env,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert (result.returncode == 0) == allowed


def test_production_logs_never_include_request_or_exception_data():
    record = logging.LogRecord(
        "django.request",
        logging.ERROR,
        "",
        1,
        "secret-email@example.invalid?hub.verify_token=secret",
        (),
        None,
    )
    record.status_code = 500
    record.request = {"Authorization": "secret"}
    record.exc_text = "private traceback"
    payload = SafeFormatter().format(record)
    assert json.loads(payload) == {"event": "server_error", "level": "ERROR", "status": 500}
    assert "secret" not in payload
    assert "traceback" not in payload


def test_worker_heartbeat_updates_only_successful_cycles(tmp_path, monkeypatch):
    heartbeat = tmp_path / "heartbeat"
    monkeypatch.setenv("WHATSAPP_WORKER_HEARTBEAT", str(heartbeat))
    with patch("apps.whatsapp.management.commands.whatsapp_worker.run_once", return_value=False):
        call_command("whatsapp_worker", once=True)
    assert heartbeat.exists()
    original = heartbeat.stat().st_mtime_ns
    with patch(
        "apps.whatsapp.management.commands.whatsapp_worker.run_once", side_effect=RuntimeError
    ):
        call_command("whatsapp_worker", once=True)
    assert heartbeat.stat().st_mtime_ns == original


@pytest.mark.django_db
def test_fixture_refuses_regular_database(monkeypatch):
    monkeypatch.setenv("P_REHEARSAL", "true")
    with pytest.raises(CommandError):
        call_command("seed_p_rehearsal")
