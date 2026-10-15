import os
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.whatsapp.worker import run_once


class Command(BaseCommand):
    help = "Procesa la cola durable de WhatsApp; no habilita conexiones reales."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            close_old_connections()
            try:
                worked = run_once()
                heartbeat = os.environ.get("WHATSAPP_WORKER_HEARTBEAT")
                if heartbeat:
                    Path(heartbeat).touch()
            except Exception:
                # Only emit a constant operational marker, without PII or credentials.
                self.stderr.write("whatsapp_worker_retry")
                worked = False
            if options["once"]:
                return
            if not worked:
                time.sleep(2)
