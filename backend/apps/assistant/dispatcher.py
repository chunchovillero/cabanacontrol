import re
from datetime import timedelta

from django.core import signing
from django.db import connection, transaction
from django.utils import timezone
from pydantic import ValidationError as SchemaError

from apps.assistant.providers import ProviderUnavailable
from apps.assistant.schemas import TOOL_SCHEMAS
from apps.assistant.tools import execute
from apps.reservations.services import local_today, require_operator

SALT = "assistant-context-v1"


def read_context(token, actor, tenant):
    if not token:
        return {}
    try:
        value = signing.loads(token, salt=SALT, max_age=1800)
        if value["actor"] != str(actor.pk) or value["tenant"] != str(tenant.pk):
            raise ValueError
        return value["filters"]
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise ProviderUnavailable() from None


def dispatch(calls, *, actor, tenant, text, previous):
    results, filters = [], {}
    if not 1 <= len(calls) <= 4:
        raise ProviderUnavailable()
    parsed = []
    today = local_today(tenant)
    normalized = text.lower()
    for name, arguments in calls:
        if name not in TOOL_SCHEMAS:
            raise ProviderUnavailable()
        try:
            args = TOOL_SCHEMAS[name].model_validate_json(arguments)
        except (SchemaError, ValueError):
            raise ProviderUnavailable() from None
        # A model must not silently supply a year absent from the user's text/context.
        if name in [
            "search_available_properties",
            "prepare_whatsapp_message",
            "list_arrivals",
            "summarize_collections",
        ]:
            explicit = re.search(r"\b(?:19|20|21)\d{2}\b", text)
            relative = re.search(r"\b(hoy|mañana|pasado mañana)\b", text.lower())
            month = name == "summarize_collections" and re.search(
                r"\b(este mes|mes pasado)\b", normalized
            )
            if month:
                first = today.replace(day=1)
                args.start_date = (
                    first
                    if "este mes" in normalized
                    else (first - timedelta(days=1)).replace(day=1)
                )
                args.end_date = (
                    (first + timedelta(days=32)).replace(day=1)
                    if "este mes" in normalized
                    else first
                )
            elif not explicit and not relative and not previous.get(name):
                name = "clarify"
                args = TOOL_SCHEMAS[name](missing=["year"])
            elif relative and not explicit:
                day = today + timedelta(
                    days=2 if "pasado mañana" in normalized else 1 if "mañana" in normalized else 0
                )
                if name == "list_arrivals":
                    args.date = day
                elif (
                    name in ["search_available_properties", "prepare_whatsapp_message"]
                    and args.check_in != day
                ):
                    name, args = "clarify", TOOL_SCHEMAS["clarify"](missing=["dates"])
        if "fin de semana" in normalized and len(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)) < 2:
            name, args = "clarify", TOOL_SCHEMAS["clarify"](missing=["dates"])
        parsed.append((name, args))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        require_operator(actor, tenant)
        for name, args in parsed:
            data = execute(tenant, name, args)
            data["verified_at"] = timezone.now().isoformat()
            results.append({"tool": name, "data": data})
            if name != "clarify":
                filters[name] = args.model_dump(mode="json")
    token = signing.dumps(
        {"actor": str(actor.pk), "tenant": str(tenant.pk), "filters": filters}, salt=SALT
    )
    return {"results": results, "context": token}
