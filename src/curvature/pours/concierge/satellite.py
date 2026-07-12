"""The Concierge manifest. Capture it in your app assembly:

    from curvature.satellites import capture
    from satellites.concierge.satellite import concierge

    capture(app, concierge, orbit="/concierge")

Mount the ask box on any screen by including it in a fragment:

    from satellites.concierge.components.concierge_desk import AskBoxProps, ask_box

    ask_box(AskBoxProps(context="/"))

The Concierge is front of house: it reads the house's own charts,
drafts real forms, and never fires one. The human's submit is the
finger on the button, always.
"""

from __future__ import annotations

from satellites.concierge.routes import router

from curvature.satellites import Satellite

concierge = Satellite(
    name="concierge",
    version="0.1.0",
    router=router,
    components=("concierge_desk",),
)
