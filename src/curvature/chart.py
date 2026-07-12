"""The chart — the third render head (C-900..C-902).

In differential geometry a chart maps a region of a manifold into
coordinates. Here it maps a screen into machine-legible capability:
what this region is for (the authored purpose), what it shows
(headings), and what it affords (links, and forms with their fields as
JSON Schema). Agents read the chart; pixels are for people. The chart
is DERIVED from the same Element tree the humans get — there is no
second source of truth to drift (C-901).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from curvature.html import Element, Raw

CHART_VERSION = "curvature/1"
HEADINGS = frozenset({"h1", "h2", "h3", "h4"})

_FIELD_TYPES: dict[str, dict[str, Any]] = {
    "number": {"type": "number"},
    "range": {"type": "number"},
    "checkbox": {"type": "boolean"},
    "email": {"type": "string", "format": "email"},
    "url": {"type": "string", "format": "uri"},
    "date": {"type": "string", "format": "date"},
    "time": {"type": "string", "format": "time"},
    "password": {"type": "string", "writeOnly": True},
}


def _text_of(element: Element) -> str:
    parts: list[str] = []

    def walk(children: tuple) -> None:
        for child in children:
            if isinstance(child, Element):
                walk(child.children)
            elif isinstance(child, Raw):
                continue
            elif isinstance(child, str):
                parts.append(child)
            elif isinstance(child, int | float):
                parts.append(str(child))

    walk(element.children)
    return " ".join(" ".join(parts).split())


def _field_schema(element: Element) -> dict[str, Any] | None:
    attrs = element.attrs
    name = attrs.get("name")
    if not isinstance(name, str) or attrs.get("disabled"):
        return None
    if element.tag == "textarea":
        schema: dict[str, Any] = {"type": "string"}
    elif element.tag == "select":
        options = [
            child.attrs.get("value", _text_of(child))
            for child in element.children
            if isinstance(child, Element) and child.tag == "option"
        ]
        item_schema: dict[str, Any] = {"type": "string", "enum": options}
        schema = (
            {"type": "array", "items": item_schema, "uniqueItems": True}
            if attrs.get("multiple")
            else item_schema
        )
    else:
        input_type = str(attrs.get("type", "text"))
        schema = dict(_FIELD_TYPES.get(input_type, {"type": "string"}))
        if input_type == "hidden" and "value" in attrs:
            schema["const"] = attrs["value"]
    for attribute, keyword in (("maxlength", "maxLength"), ("minlength", "minLength")):
        value = attrs.get(attribute)
        if isinstance(value, str | int | float) and not isinstance(value, bool):
            schema[keyword] = int(value)
    for attribute, keyword in (("min", "minimum"), ("max", "maximum"), ("step", "multipleOf")):
        value = attrs.get(attribute)
        if isinstance(value, str | int | float) and not isinstance(value, bool):
            schema[keyword] = float(value)
    pattern = attrs.get("pattern")
    if isinstance(pattern, str):
        schema["pattern"] = pattern
    if "value" in attrs and "const" not in schema:
        schema["default"] = attrs["value"]
    return {"name": name, "required": bool(attrs.get("required")), "schema": schema}


def _walk_elements(element: Element):
    yield element
    for child in element.children:
        if isinstance(child, Element):
            yield from _walk_elements(child)


def _group_schema(elements: list[Element]) -> dict[str, Any] | None:
    schemas = [field["schema"] for element in elements if (field := _field_schema(element))]
    if not schemas:
        return None
    input_types = {str(element.attrs.get("type", "text")) for element in elements}
    if input_types == {"radio"}:
        values = [element.attrs.get("value", "on") for element in elements]
        schema: dict[str, Any] = {"type": "string", "enum": values}
        selected = next((element.attrs.get("value", "on") for element in elements
                         if element.attrs.get("checked")), None)
        if selected is not None:
            schema["default"] = selected
        return schema
    if input_types == {"checkbox"} and len(elements) > 1:
        return {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [element.attrs.get("value", "on") for element in elements],
            },
            "uniqueItems": True,
        }
    if len(schemas) == 1:
        return schemas[0]
    return {"type": "array", "items": schemas[0]}


def _submitter(element: Element) -> dict[str, Any] | None:
    if element.attrs.get("disabled"):
        return None
    if element.tag == "button":
        input_type = str(element.attrs.get("type", "submit"))
        prompt = _text_of(element)
    elif element.tag == "input" and str(element.attrs.get("type")) in {"submit", "image"}:
        input_type = str(element.attrs.get("type"))
        prompt = str(element.attrs.get("value", "Submit"))
    else:
        return None
    if input_type != "submit":
        return None
    result: dict[str, Any] = {"prompt": prompt or None}
    name = element.attrs.get("name")
    if isinstance(name, str):
        result["name"] = name
        result["value"] = element.attrs.get("value", "")
    return result


def _form_affordance(form: Element) -> dict[str, Any]:
    controls: dict[str, list[Element]] = defaultdict(list)
    required: set[str] = set()
    submitters: list[dict[str, Any]] = []
    for element in _walk_elements(form):
        if element.tag in {"input", "textarea", "select"}:
            field = _field_schema(element)
            if field is None:
                continue
            controls[field["name"]].append(element)
            if field["required"]:
                required.add(field["name"])
        if submitter := _submitter(element):
            submitters.append(submitter)
    fields = {
        name: schema
        for name, elements in controls.items()
        if (schema := _group_schema(elements)) is not None
    }
    return {
        "action": form.attrs.get("action"),
        "method": form.attrs.get("method"),
        "enctype": form.attrs.get("enctype", "application/x-www-form-urlencoded"),
        "prompt": submitters[0]["prompt"] if submitters else None,
        "submitters": submitters,
        "fields": {
            "type": "object",
            "properties": fields,
            "required": sorted(required),
        },
    }


def build_chart(
    fragments: tuple[Element, ...], *, url: str, purpose: str | None
) -> dict[str, Any]:
    """One screen, mapped to coordinates: derived, never hand-authored."""
    links: list[dict[str, Any]] = []
    forms: list[dict[str, Any]] = []
    headings: list[str] = []
    for fragment in fragments:
        for element in _walk_elements(fragment):
            if element.tag == "a":
                links.append({"text": _text_of(element), "href": element.attrs.get("href")})
            elif element.tag == "form":
                forms.append(_form_affordance(element))
            elif element.tag in HEADINGS:
                headings.append(_text_of(element))
    return {
        "chart": CHART_VERSION,
        "url": url,
        "purpose": purpose,
        "headings": headings,
        "fragments": [fragment.id for fragment in fragments],
        "affordances": {"links": links, "forms": forms},
    }
