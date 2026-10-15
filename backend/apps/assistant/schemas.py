from datetime import date as Date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AvailabilityArgs(StrictModel):
    check_in: Date = Field(strict=True)
    check_out: Date = Field(strict=True)
    guests: int = Field(ge=1, le=32767, strict=True)
    property_id: UUID | None = None
    page: int = Field(default=1, ge=1, le=10000, strict=True)


class ArrivalsArgs(StrictModel):
    date: Date = Field(strict=True)
    page: int = Field(default=1, ge=1, le=10000, strict=True)


class BalancesArgs(StrictModel):
    as_of_date: Date = Field(strict=True)
    page: int = Field(default=1, ge=1, le=10000, strict=True)


class CollectionsArgs(StrictModel):
    start_date: Date = Field(strict=True)
    end_date: Date = Field(strict=True)
    page: int = Field(default=1, ge=1, le=10000, strict=True)


class WhatsAppArgs(AvailabilityArgs):
    property_id: UUID


class ClarifyArgs(StrictModel):
    missing: list[
        Literal["year", "dates", "guests", "property", "current_balances", "unsupported"]
    ] = Field(min_length=1, max_length=6)


TOOL_SCHEMAS = {
    "search_available_properties": AvailabilityArgs,
    "list_arrivals": ArrivalsArgs,
    "list_outstanding_balances": BalancesArgs,
    "summarize_collections": CollectionsArgs,
    "prepare_whatsapp_message": WhatsAppArgs,
    "clarify": ClarifyArgs,
}


def function_definitions():
    tools = []
    for name, model in TOOL_SCHEMAS.items():
        schema = model.model_json_schema()
        schema["required"] = list(schema["properties"])
        for prop in schema["properties"].values():
            prop.pop("default", None)
        tools.append(
            {
                "type": "function",
                "name": name,
                "description": name.replace("_", " "),
                "parameters": schema,
                "strict": True,
            }
        )
    return tools
