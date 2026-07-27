import pytest
from fastapi import FastAPI, Request
from starlette.responses import PlainTextResponse

from curvature import html as h
from curvature import respond
from curvature.atlas import atlas


@pytest.fixture
def chart_app() -> FastAPI:
    app = FastAPI()

    def shell(*fragments):
        return h.html(h.body(h.main(*fragments)))

    @app.get("/")
    async def lap_status(request: Request):
        fragment = h.section(h.h1("Lap Status"), id="lap-status")
        return respond(
            request,
            fragment,
            shell=shell,
            purpose="Review the current lap status.",
        )

    @app.get("/atlas")
    async def atlas_page(request: Request):
        return respond(
            request,
            atlas(app),
            shell=shell,
            purpose="Find every readable test region.",
        )

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return PlainTextResponse("ok")

    return app
