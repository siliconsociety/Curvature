# Deploying a manifold

Written from life: this is how curvature-site
(github.com/siliconsociety/curvature-site) reaches the world. The
boring truth in four files — if your ritual is bigger than this,
you're deploying a monolith like it owes you money.

## The shape

A manifold is uvicorn serving FastAPI, state in its store, static files
mounted. Horizontal scale is more processes; there
is no client-heap tax to amortize and no build step to run.

## Heroku (or any Procfile host)

```
# Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`.python-version` (poured by the scaffold) selects the runtime.
`heroku create && git push heroku main`. Done. Better: connect the
GitHub repo with **auto-deploy → "wait for CI to pass"** — then Heroku
only ever builds commits the public gate has blessed. Proven in
production 2026-07-12, roughly 82 seconds after it would have helped.

## Any box with a proxy

```
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

behind Caddy or nginx. Two notes the defaults get wrong:

- **Auth is explicit**: capture Auth with `AuthConfig(allowed_origins=(
  "https://your-domain.example",), secure_cookies=True)`. There is no
  permissive production default. Put the same canonical origin at the
  proxy and application boundary.
- **Shared state**: the poured SQLite store is a safe single-host baseline,
  with WAL, busy timeouts, database-backed OIDC/TOTP challenges, rate
  limits, and sessions. Multiple workers must open the same durable SQLite
  file. Heroku's ephemeral filesystem is demo-only; production Auth needs a
  persistent volume or a store implementation with the same protocol and
  atomic guarantees.
- **SSE behind nginx**: Live streams already send
  `X-Accel-Buffering: no`; if you strip headers at the proxy, don't
  strip that one.

## The dev loop

Live streams hold connections open, and uvicorn's graceful shutdown
waits for open connections — so `--reload` without a bound hangs on
every file change. Run dev servers with
`--timeout-graceful-shutdown 1`. Production restarts are already
bounded (SIGTERM then SIGKILL); this is a laptop concern.

## What there isn't

No container orchestration requirement, no sidecar, no bundler stage,
no asset pipeline. There is also no production Mongo adapter hiding behind
the pour: unfinished stores were removed rather than advertised. The gate
runs in CI or a pre-push hook the same way it runs on a laptop:
`./gate.sh`.
