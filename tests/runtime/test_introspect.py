import asyncio

from curvature.introspect import fetch_chart


def test_server_side_tooling_reads_the_public_chart(chart_app):
    chart = asyncio.run(fetch_chart(chart_app, "/"))
    assert chart is not None and chart["chart"] == "curvature/1"
    assert chart["affordances"]["forms"] == []
    assert "Lap Status" in chart["headings"]


def test_query_strings_reach_the_region(chart_app):
    chart = asyncio.run(fetch_chart(chart_app, "/atlas", query="unused=1"))
    assert chart is not None and chart["fragments"] == ["atlas"]


def test_missing_regions_return_none(chart_app):
    assert asyncio.run(fetch_chart(chart_app, "/nowhere")) is None


def test_non_chart_regions_return_none(chart_app):
    assert asyncio.run(fetch_chart(chart_app, "/healthz")) is None


def test_non_json_two_hundreds_return_none():
    from fastapi import FastAPI
    from starlette.responses import HTMLResponse

    plain = FastAPI()

    @plain.get("/page")
    async def page():
        return HTMLResponse("<p>no chart here</p>")

    assert asyncio.run(fetch_chart(plain, "/page")) is None


def test_json_without_a_chart_key_returns_none():
    from fastapi import FastAPI

    plain = FastAPI()

    @plain.get("/api")
    async def api():
        return {"just": "json"}  # curvature: json-endpoint (read-only fixture)

    assert asyncio.run(fetch_chart(plain, "/api")) is None
