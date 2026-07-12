"""Intent resolution — the swap point.

The Resolver protocol turns an utterance plus a chart into drafts. The
default is a deterministic keyword resolver: hermetic, free, honest
about its ceiling. A model-backed resolver drops into the same protocol
when the owner decides inference is worth it — against a declared
chart, intent-matching is constrained slot-filling, a small-model job.

The Concierge never executes. A draft is a proposal the human submits.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict


class Draft(BaseModel):
    """A proposed action: everything needed to render a REAL prefilled
    form (or link) for the human to fire."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str  # "form" | "link"
    prompt: str
    action: str | None = None
    method: str | None = None
    values: dict[str, str] = {}
    schema_properties: dict[str, Any] = {}
    href: str | None = None


class Resolver(Protocol):
    def resolve(self, utterance: str, chart: dict[str, Any]) -> list[Draft]: ...


def _tokens(text: str) -> set[str]:
    return {word for word in text.lower().split() if len(word) > 1}


class KeywordResolver:
    """v1: overlap scoring between the utterance and the chart's own
    words. The remainder of the utterance — what didn't match anything —
    becomes the prefill for the first required string field."""

    def resolve(self, utterance: str, chart: dict[str, Any]) -> list[Draft]:
        drafts: list[Draft] = []
        asked = _tokens(utterance)

        for form in chart["affordances"]["forms"]:
            prompt = form.get("prompt") or ""
            field_words = _tokens(" ".join(form["fields"]["properties"]))
            matched = asked & (_tokens(prompt) | field_words)
            if not matched:
                continue
            values: dict[str, str] = {}
            remainder = " ".join(
                word for word in utterance.split() if word.lower() not in matched
            ).strip()
            for name, schema in form["fields"]["properties"].items():
                required = form["fields"]["required"]
                if "const" in schema:
                    values[name] = str(schema["const"])
                elif (
                    schema.get("type") == "string"
                    and remainder
                    and (name in required or not required)
                ):
                    values[name] = remainder
                    remainder = ""
            drafts.append(Draft(
                kind="form",
                prompt=prompt or "Submit",
                action=form["action"],
                method=form["method"],
                values=values,
                schema_properties=form["fields"]["properties"],
            ))

        for link in chart["affordances"]["links"]:
            if asked & _tokens(link.get("text") or ""):
                drafts.append(Draft(
                    kind="link", prompt=link["text"], href=link["href"]
                ))

        return drafts
