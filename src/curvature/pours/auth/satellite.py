"""The Auth manifest. Capture it in your app assembly:

    from pathlib import Path

    from curvature.satellites import capture
    from satellites.auth.satellite import auth
    from satellites.auth.store import choose

    app.state.auth_store = choose(Path("data"))
    capture(app, auth, orbit="/auth")

Both lines explicit, both greppable. Identity is then a declared
dependency wherever you want it:

    from satellites.auth.sessions import CurrentUser

    @app.get("/garage")
    async def garage(request: Request, user: CurrentUser): ...
"""

from __future__ import annotations

from satellites.auth.routes import router

from curvature.satellites import Satellite

auth = Satellite(
    name="auth",
    version="0.1.0",
    router=router,
    components=("auth_forms", "token_desk"),
)
