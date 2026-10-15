"""Deterministic provider, available only in the explicitly isolated E2E database."""

import json
import re
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def simulated():
    if not settings.AI_TEST_PROVIDER:
        return False
    if not (
        settings.E2E_TEST_MODE and settings.DATABASES["default"]["NAME"] == "cabanacontrol_e2e"
    ):
        raise ImproperlyConfigured("El proveedor simulado requiere la base E2E aislada.")
    return True


class SimulatedProvider:
    def interpret(self, text, today, timezone_name, context):
        from apps.assistant.providers import Interpretation

        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        guests = re.search(r"(\d+) personas", text)
        if len(dates) == 2 and guests:
            name = "search_available_properties"
            args = {
                "check_in": dates[0],
                "check_out": dates[1],
                "guests": int(guests[1]),
                "property_id": None,
                "page": 1,
            }
        elif "llega" in text.lower():
            name = "list_arrivals"
            args = {"date": str(today + timedelta(days=1)), "page": 1}
        else:
            name, args = "clarify", {"missing": ["year"]}
        return Interpretation([(name, json.dumps(args))], 30, 20, 10)
