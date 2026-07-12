import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from curvature import Anomaly, respond
from curvature import html as h
from curvature.gate.findings import Finding
from curvature.satellites import Satellite, capture, captured, constellation_checks


def shell(*fragments):
    return h.html(h.body(h.main(*fragments)))


def make_satellite(name="beacon", **overrides):
    router = APIRouter()

    @router.get("/status")
    async def status(request: Request):
        return respond(request, h.div("aloft", id=f"{name}-status"), shell=shell)

    defaults = {"name": name, "version": "0.1.0", "router": router}
    return Satellite(**{**defaults, **overrides})


def test_capture_mounts_the_declared_orbit():
    app = FastAPI()
    capture(app, make_satellite(), orbit="/beacon")
    response = TestClient(app).get("/beacon/status")
    assert response.status_code == 200
    assert "aloft" in response.text


def test_captured_reports_the_constellation():
    app = FastAPI()
    capture(app, make_satellite("beacon"), orbit="/beacon")
    capture(app, make_satellite("pulse"), orbit="/pulse")
    assert captured(app) == {"beacon": "/beacon", "pulse": "/pulse"}


def test_a_satellite_cannot_be_captured_twice():
    app = FastAPI()
    capture(app, make_satellite(), orbit="/beacon")
    with pytest.raises(Anomaly, match="C-800"):
        capture(app, make_satellite(), orbit="/elsewhere")


def test_an_orbit_cannot_be_shared():
    app = FastAPI()
    capture(app, make_satellite("beacon"), orbit="/shared")
    with pytest.raises(Anomaly, match="C-802"):
        capture(app, make_satellite("pulse"), orbit="/shared")


def test_the_root_is_not_an_orbit():
    app = FastAPI()
    with pytest.raises(Anomaly, match="C-802"):
        capture(app, make_satellite(), orbit="/")


def test_orbits_must_be_paths():
    app = FastAPI()
    with pytest.raises(Anomaly, match="C-802"):
        capture(app, make_satellite(), orbit="beacon")


def test_manifests_are_frozen_and_closed():
    satellite = make_satellite()
    with pytest.raises(ValidationError):
        satellite.name = "renamed"
    with pytest.raises(ValidationError):
        Satellite(name="x", version="1", surprise=True)


def test_satellite_names_are_lower_snake():
    with pytest.raises(ValidationError):
        Satellite(name="Beacon", version="1")


def test_mass_accumulates_across_the_constellation():
    def check_a(root):
        return [Finding("ANOM-900", "x", None, "a")]

    def check_b(root):
        return [Finding("ANOM-901", "y", None, "b")]

    app = FastAPI()
    capture(app, make_satellite("beacon", checks=(check_a,)), orbit="/beacon")
    capture(app, make_satellite("pulse", checks=(check_b,)), orbit="/pulse")
    gathered = constellation_checks(app)
    assert len(gathered) == 2
    assert [f.rule for fn in gathered for f in fn(None)] == ["ANOM-900", "ANOM-901"]


def test_a_massless_satellite_is_legal():
    app = FastAPI()
    capture(app, make_satellite(checks=()), orbit="/beacon")
    assert constellation_checks(app) == []


def test_capture_order_is_meaningless():
    def routes(app):
        client = TestClient(app)
        return (client.get("/beacon/status").status_code,
                client.get("/pulse/status").status_code)

    forward, backward = FastAPI(), FastAPI()
    capture(forward, make_satellite("beacon"), orbit="/beacon")
    capture(forward, make_satellite("pulse"), orbit="/pulse")
    capture(backward, make_satellite("pulse"), orbit="/pulse")
    capture(backward, make_satellite("beacon"), orbit="/beacon")
    assert routes(forward) == routes(backward) == (200, 200)
