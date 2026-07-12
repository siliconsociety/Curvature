"""The Concierge's two faces: the ask box (mount it on any screen) and
the drafts view. Every draft is a REAL form or a REAL link — the human
fires it, the Concierge only prepared it."""

from __future__ import annotations

from satellites.concierge.resolver import Draft

from curvature import Element, Props
from curvature import html as h


class AskBoxProps(Props):
    context: str = "/"
    placeholder: str = "Ask the app…"


class DraftsProps(Props):
    utterance: str
    context: str
    drafts: tuple[Draft, ...]


class DraftFormProps(Props):
    draft: Draft


def ask_box(props: AskBoxProps) -> Element:
    return h.form(
        h.input_(type="text", name="q", placeholder=props.placeholder,
                 required=True, maxlength=300, autocomplete="off"),
        h.input_(type="hidden", name="context", value=props.context),
        h.button("Ask", class_="concierge-ask"),
        action="/concierge",
        method="get",
        class_="concierge-box",
        id="concierge-box",
    )


def _draft_form(props: DraftFormProps) -> Element:
    draft = props.draft
    inputs = []
    for name, schema in draft.schema_properties.items():
        value = draft.values.get(name)
        if "const" in schema:
            inputs.append(h.input_(type="hidden", name=name, value=value))
            continue
        inputs.append(h.label(name.replace("_", " ").title(), for_=f"draft-{name}"))
        inputs.append(h.input_(
            type="text", name=name, id=f"draft-{name}", value=value,
        ))
    return h.form(
        inputs,
        h.button(draft.prompt, class_="concierge-fire"),
        action=draft.action or "/",
        method=draft.method or "post",
        class_="concierge-draft",
    )


def drafts_view(props: DraftsProps) -> Element:
    body: list[Element] = []
    for draft in props.drafts:
        if draft.kind == "form":
            body.append(h.li(_draft_form(DraftFormProps(draft=draft)), class_="draft"))
        else:
            body.append(h.li(
                h.a(draft.prompt, href=draft.href or "/"), class_="draft draft-link"
            ))
    return h.section(
        h.h2("The concierge suggests"),
        h.p(f"For: “{props.utterance}”", class_="concierge-echo"),
        h.ul(body, class_="concierge-drafts") if body
        else h.p("Nothing on this screen matches that. Try the atlas.", class_="empty"),
        h.p(h.a("Back", href=props.context), class_="concierge-back"),
        id="concierge-drafts",
    )
