"""The Concierge's orbit. Asking is a GET — a question is not a
mutation — so C-201 never enters the conversation. The resolver reads
the context screen's chart through the house's own front door."""

from __future__ import annotations

from app.components.shell import shell
from fastapi import APIRouter, Request
from satellites.concierge.components.concierge_desk import (
    AskBoxProps,
    DraftsProps,
    ask_box,
    drafts_view,
)
from satellites.concierge.resolver import KeywordResolver

from curvature import respond
from curvature.introspect import fetch_chart

router = APIRouter()

# The swap point: replace with a model-backed Resolver when the owner
# decides inference earns its keep. The protocol stays put.
resolver = KeywordResolver()


@router.get("")
async def concierge_desk(request: Request, q: str = "", context: str = "/"):
    if not context.startswith("/"):
        context = "/"
    if not q.strip():
        return respond(
            request, ask_box(AskBoxProps(context=context)), shell=shell,
            purpose="Ask this app for something in plain words; the concierge "
                    "drafts the action and you fire it.",
        )
    chart = await fetch_chart(request.app, context)
    drafts = () if chart is None else tuple(resolver.resolve(q, chart))
    return respond(
        request,
        drafts_view(DraftsProps(utterance=q, context=context, drafts=drafts)),
        shell=shell,
        purpose="Drafts the concierge prepared from your request; every one is "
                "a real form or link that YOU fire.",
    )
