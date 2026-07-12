"""Satellites — explicit route bundles without a registry (C-800..C-804).

A satellite is captured by explicit assembly, never discovered. The manifest
is a frozen value; capture() is the only way in; there are no hooks, ordering,
interception, or aspirational fields the runtime does not consume.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from curvature.errors import Anomaly


class Satellite(BaseModel):
    """The manifest: a value, not a discovery. Everything a satellite
    contributes is declared here; contribution outside the declaration
    is an anomaly (C-802)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True, frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    version: str = Field(min_length=1, max_length=40)
    router: Any = None
    components: tuple[str, ...] = ()


def _constellation(app: Any) -> dict[str, tuple[str, Satellite]]:
    existing = getattr(app.state, "curvature_constellation", None)
    if existing is None:
        existing = {}
        app.state.curvature_constellation = existing
    return existing


def capture(app: Any, satellite: Satellite, *, orbit: str) -> None:
    """Place a satellite in its declared orbit. Explicit, greppable,
    order-independent: each satellite gets its own route prefix and
    cannot see, wrap, or intercept anything else (C-804)."""
    if not orbit.startswith("/") or orbit.rstrip("/") == "":
        raise Anomaly(
            f"orbit {orbit!r} is an anomaly (C-802): a satellite orbits a "
            "real path prefix like '/auth', never the root"
        )
    constellation = _constellation(app)
    if satellite.name in constellation:
        raise Anomaly(
            f"satellite {satellite.name!r} is already captured (C-800): "
            "one body, one orbit"
        )
    normalized = orbit.rstrip("/")
    occupied = {taken_orbit for taken_orbit, _ in constellation.values()}
    if normalized in occupied:
        raise Anomaly(
            f"orbit {normalized!r} is already occupied (C-802): "
            "two satellites cannot share a prefix"
        )
    if satellite.router is not None:
        app.include_router(satellite.router, prefix=normalized)
    constellation[satellite.name] = (normalized, satellite)


def captured(app: Any) -> dict[str, str]:
    """The constellation: satellite name -> orbit. What grep confirms,
    this reports."""
    return {name: orbit for name, (orbit, _) in _constellation(app).items()}
