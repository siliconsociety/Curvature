import asyncio

from curvature.introspect import fetch_chart
from demo.app import app


def test_the_resident_reads_the_house_chart():
    chart = asyncio.run(fetch_chart(app, "/"))
    assert chart is not None and chart["chart"] == "curvature/1"
    assert chart["affordances"]["forms"][0]["action"] == "/tasks"


def test_query_strings_reach_the_region():
    chart = asyncio.run(fetch_chart(app, "/", query="status=done"))
    assert (
        chart["affordances"]["forms"][0]["fields"]["properties"]["status"]
    ) == {"const": "done", "type": "string"}


def test_missing_regions_return_none():
    assert asyncio.run(fetch_chart(app, "/nowhere")) is None


def test_non_chart_regions_return_none():
    assert asyncio.run(fetch_chart(app, "/static/tarmac.css")) is None


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
