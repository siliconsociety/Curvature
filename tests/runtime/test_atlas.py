"""Atlas discovery exposes screens, not framework plumbing."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from curvature.atlas import atlas


def test_the_atlas_is_a_screen_whose_chart_is_the_atlas(chart_app):
    client = TestClient(chart_app)
    page = client.get("/atlas")
    assert 'id="atlas"' in page.text
    chart = client.get("/atlas", headers={"Curvature-Chart": "1"}).json()
    hrefs = {link["href"] for link in chart["affordances"]["links"]}
    assert "/" in hrefs and "/atlas" in hrefs
    assert chart["purpose"]


def test_the_atlas_skips_parameterized_hidden_and_mounted_regions(tmp_path):
    plain = FastAPI()
    plain.mount("/assets", StaticFiles(directory=tmp_path))

    @plain.get("/items/{item_id}")
    async def item(item_id: str): ...  # curvature: json-endpoint (fixture)

    @plain.get("/whole")
    async def whole(): ...  # curvature: json-endpoint (fixture)

    @plain.get("/healthz", include_in_schema=False)
    async def health(): ...  # curvature: json-endpoint (fixture)

    markup = str(atlas(plain))
    assert 'href="/whole"' in markup
    assert "{item_id}" not in markup
    assert "/healthz" not in markup
    assert "/assets" not in markup
