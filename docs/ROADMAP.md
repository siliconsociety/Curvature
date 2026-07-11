# Roadmap

Held to the same rule as everything else here: an item earns code only
when its contract can be stated. Order is intent, not promise.

## 0.2 — the road widens

- **Islands doctrine (C-7xx).** The declared enclave for 60fps work:
  a fenced, vendored widget with a byte budget and a named owner,
  embedded in a cambered page. The gate learns to count islands and
  refuse undeclared ones. This closes the only honest technical gap
  between Camber and consumer-scale surfaces.
- **Server push (C-5xx extension).** Live updates as server-pushed
  fragment swaps over SSE — same id-swap protocol camber.js already
  speaks, the server stays the only author of the DOM. Chat-class apps
  become possible without a word of app JS.
- **`camber new app`.** The quickstart IS a scaffold: one command pours
  a running cambered app (shell, first component, gate.sh, ratchet.toml,
  AGENTS.md). The README quickstart then fits in five lines.
- **OC-150/151** as specced: orphan CSS selectors, registry patterns.
- **Deployment doc.** The boring truth: uvicorn workers behind a
  reverse proxy, one container, fragment-cache headers. Publish it so
  nobody invents a k8s ritual for a monolith.

## 0.3 — the proof

- **Honest benchmarks.** Render cost, fragment cache hit behavior,
  requests-per-core against an equivalent SPA + JSON API. Publish the
  numbers whatever they say; the architecture argument is only worth
  what it measures.
- **Offline posture.** The genuine weak flank of server-owned logic.
  Investigate service-worker page caching for read paths; state loudly
  what Camber will not pretend to do.
- **PyPI.** Names `camber` and `camberworks` verified free 2026-07-11.
  The ritual since Fortuna's day: 2FA mandatory, token- or
  trusted-publisher-based (`uv publish` handles both); trusted
  publishing wants a public CI identity, tokens work from a laptop.

## The lurking act — the agent projection

The UI state already lives server-side as a typed Element tree of real
forms and real links. That tree IS a capability surface. A third render
head — content-negotiated alongside page and fragment — would hand an
agent the same truth the pixels get: what this screen is for
(orientation), what state it shows, which actions it affords, with
typed fields and constraints. Voice and accessibility fall out of the
same projection. Working name in the house vocabulary: **IFR mode** —
same aircraft, flown on instruments.
