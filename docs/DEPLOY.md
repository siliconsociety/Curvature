# Deploying a manifold

Written from life: this is how curvature-site
(github.com/siliconsociety/curvature-site) reaches the world. The
boring truth in four files — if your ritual is bigger than this,
you're deploying a monolith like it owes you money.

## The shape

A manifold is one process: uvicorn serving FastAPI, state in its
store, static files mounted. Horizontal scale is more processes; there
is no client-heap tax to amortize and no build step to run.

## Heroku (or any Procfile host)

```
# Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`.python-version` (poured by the scaffold) selects the runtime.
`heroku create && git push heroku main`. Done.

## Any box with a proxy

```
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
```

behind Caddy or nginx. Two notes the defaults get wrong:

- **TLS cookies**: flip `secure=False` to `True` in the Auth
  satellite's `start_session` the day you have HTTPS. The comment in
  the source says exactly this; the deploy is when it comes due.
- **SSE behind nginx**: Live streams already send
  `X-Accel-Buffering: no`; if you strip headers at the proxy, don't
  strip that one.

## What there isn't

No container orchestration requirement, no sidecar, no bundler stage,
no asset pipeline. `sqlite` ships in the dyno's filesystem (ephemeral
on Heroku — fine for demos; give real data a volume or the Mongo
satellite). The gate runs in CI or a pre-push hook the same way it
runs on a laptop: `./gate.sh`.
