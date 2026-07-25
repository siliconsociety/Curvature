"""Atlas discovery exposes screens, not framework plumbing."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from curvature.atlas import atlas
from demo.app import app


def test_the_atlas_is_a_screen_whose_chart_is_the_atlas():
    client = TestClient(app)
    page = client.get("/atlas")
    assert 'id="atlas"' in page.text
    chart = client.get("/atlas", headers={"Curvature-Chart": "1"}).json()
    hrefs = {link["href"] for link in chart["affordances"]["links"]}
    assert "/" in hrefs and "/atlas" in hrefs
    assert chart["purpose"]


def test_the_atlas_skips_parameterized_and_hidden_regions():
    plain = FastAPI()

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
