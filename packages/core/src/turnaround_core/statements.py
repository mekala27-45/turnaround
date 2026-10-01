"""The statement that appears on every surface.

Written once here. The story, the memo, every page of the site, every API response
and every rendered document read it from this module, and a gate checks each surface.
"""

from __future__ import annotations

PROJECT = "turnaround"

STATEMENT = (
    "Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather "
    "from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the "
    "public record; no individual traveler appears. The findings are a portfolio analysis, not an "
    "official ranking and not travel advice."
)

WEATHER_ATTRIBUTION = "Weather data by Open-Meteo.com, CC BY 4.0."


def statement_markdown() -> str:
    """The statement as a Markdown block quote, for documents."""
    return f"> {STATEMENT}"


def statement_payload() -> dict[str, str]:
    """The statement as a JSON-ready mapping, for API response bodies."""
    return {"statement": STATEMENT}


def contains_statement(text: str) -> bool:
    """True when the statement appears verbatim, allowing for line wrapping."""
    flat = " ".join(text.split())
    return " ".join(STATEMENT.split()) in flat
