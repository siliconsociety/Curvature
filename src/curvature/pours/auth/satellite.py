"""The Auth manifest. Capture it in your app assembly:

    from pathlib import Path

    from curvature.satellites import capture
    from satellites.auth.satellite import auth
    from satellites.auth.sessions import AuthConfig
    from satellites.auth.store import choose

    app.state.auth_store = choose(Path("data"))
    app.state.auth_config = AuthConfig(
        allowed_origins=frozenset({"https://your.app"}),
        secure_cookies=True,
    )
    capture(app, auth, orbit="/auth")

Both lines explicit, both greppable. Identity is then a declared
dependency wherever you want it:

    from satellites.auth.sessions import CurrentUser

    @app.get("/garage")
    async def garage(request: Request, user: CurrentUser): ...
"""

from __future__ import annotations

from fastapi import APIRouter
from satellites.auth.routes import router as base_router
from satellites.auth.routes_oidc import router as oidc_router
from satellites.auth.routes_totp import router as totp_router

from curvature.satellites import Satellite

router = APIRouter()
router.include_router(base_router)
router.include_router(totp_router)
router.include_router(oidc_router)

auth = Satellite(
    name="auth",
    version="0.2.0",
    router=router,
    components=("auth_forms", "token_desk", "totp_desk"),
)
