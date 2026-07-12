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
            elif child is not None:
                walk(tuple(child))

    walk(element.children)
    return " ".join(" ".join(parts).split())


def _field_schema(element: Element) -> dict[str, Any] | None:
    attrs = element.attrs
    name = attrs.get("name")
    if not isinstance(name, str):
        return None
    if element.tag == "textarea":
        schema: dict[str, Any] = {"type": "string"}
    elif element.tag == "select":
        options = [
            child.attrs.get("value", _text_of(child))
            for child in element.children
            if isinstance(child, Element) and child.tag == "option"
        ]
        schema = {"type": "string", "enum": options}
    else:
        input_type = str(attrs.get("type", "text"))
        schema = dict(_FIELD_TYPES.get(input_type, {"type": "string"}))
        if input_type == "hidden" and "value" in attrs:
            schema["const"] = attrs["value"]
    if "maxlength" in attrs:
        schema["maxLength"] = int(attrs["maxlength"])
    if "minlength" in attrs:
        schema["minLength"] = int(attrs["minlength"])
    if "value" in attrs and "const" not in schema:
        schema["default"] = attrs["value"]
    return {"name": name, "required": bool(attrs.get("required")), "schema": schema}


def _walk_elements(element: Element):
    yield element
    for child in element.children:
        if isinstance(child, Element):
            yield from _walk_elements(child)
        elif isinstance(child, str | Raw | int | float) or child is None:
            continue
        else:
            for sub in child:
                if isinstance(sub, Element):
                    yield from _walk_elements(sub)


def _form_affordance(form: Element) -> dict[str, Any]:
    fields = {}
    required = []
    for element in _walk_elements(form):
        if element.tag in {"input", "textarea", "select"}:
            field = _field_schema(element)
            if field is None:
                continue
            fields[field["name"]] = field["schema"]
            if field["required"]:
                required.append(field["name"])
    submit_text = next(
        (_text_of(e) for e in _walk_elements(form) if e.tag == "button"), ""
    )
    return {
        "action": form.attrs.get("action"),
        "method": form.attrs.get("method"),
        "prompt": submit_text or None,
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
