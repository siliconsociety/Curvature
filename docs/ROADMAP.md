# Roadmap

Held to the same rule as everything else here: an item earns code only
when its contract can be stated. Order is intent, not promise.

## The load-bearing principle, found 2026-07-11 (last light)

**A cambered app requires no bespoke client.** IFR is self-describing:
the projection carries its own documentation, discovery is a response
header, identity is the user's ordinary session (borrowed authority via
Auth). One generic IFR capability in any agent harness drives every
Curvature app ever poured. Per-app enduser skills are the SDK-per-
service disease and are refused. (The Valet remains the owner's alone.)

## 0.2 — the space expands, in dependency order

1. **Satellite mechanics** — C-800 capture(), manifests, ANOM-160/161.
   Nothing activates until capture exists.
2. **Auth satellite** — the proving case for capture, and the identity
   both agent stories borrow. Position (2026-07-11): own design at the
   flow and data layers, assembled standards at the crypto layer
   (argon2, PyJWT/OIDC, TOTP) — invent nothing, rent nothing. Identity
   is an explicit dependency at use sites (Depends(current_user)),
   never middleware — C-804 makes auth better, not harder. Social
   login = direct OIDC (Google/Microsoft/Apple/any issuer, one
   client, zero JS). Enterprise SAML never enters the house: a broker
   at the edge (WorkOS/Dex/authentik) translates to OIDC. Clerk-class
   JS-widget vendors are ANOM-120 on arrival, by design. Users live in
   the app's own store. Personal access tokens (minted via a form) are
   how endusers hand borrowed authority to their visiting agents.
   Passkeys deferred: navigator.credentials has no JS-off path —
   baseline is password + TOTP (pure forms); passkeys later as a
   declared enhancement. DISCOVERED CORE WORK — C-203: sessions demand
   CSRF posture in the runtime itself (SameSite=Lax + Origin check on
   writes), construction-grade, not satellite code.
3. **IFR projection** — the third render head: format, discovery
   header, one authored purpose line per screen.
4. **Concierge** — the capstone: IFR consumed first-party + satellite
   packaging + a small-model client + the confirm-vs-do policy.

## 0.2 — also in the bay

- **Event horizon doctrine (C-7xx).** The declared enclave for 60fps work:
  a fenced, vendored widget with a byte budget and a named owner,
  embedded in a curved page. The gate learns to count horizons and
  refuse undeclared ones. This closes the only honest technical gap
  between Curvature and consumer-scale surfaces.
- **Server push (C-5xx extension).** Live updates as server-pushed
  fragment swaps over SSE — same id-swap protocol curvature.js already
  speaks, the server stays the only author of the DOM. Chat-class apps
  become possible without a word of app JS.
- **`curvature new app`.** The quickstart IS a scaffold: one command pours
  a running curved app (shell, first component, gate.sh, ratchet.toml,
  AGENTS.md). The README quickstart then fits in five lines.
- **`curvature new demo`.** Pit Board as a scaffold, not a package payload:
  extras deliver dependencies, only a pour delivers code. The demo
  arrives editable, which is what a demo is for.
- **ANOM-150/151** as specced: orphan CSS selectors, registry patterns.
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
  what Curvature will not pretend to do.
- **PyPI.** Names `curvature` and `curvatureworks` verified free 2026-07-11.
  The ritual since Fortuna's day: 2FA mandatory, token- or
  trusted-publisher-based (`uv publish` handles both); trusted
  publishing wants a public CI identity, tokens work from a laptop.

## The lurking act — two agents, one substrate

The UI state already lives server-side as a typed Element tree of real
forms and real links. That tree IS a capability surface, and it feeds
two distinct architectures (clarified 2026-07-11, RS/F5):

1. **The visiting agent.** A third render head — content-negotiated
   alongside page and fragment — hands any outside agent the same truth
   the pixels get: what this screen is for (orientation), what state it
   shows, which actions it affords, with typed fields and constraints.
   Working name: **IFR mode** — same aircraft, flown on instruments.
2. **The resident agent.** An intelligence that ships WITH the app and
   IS an interface to it: "switch to dark mode," "fill this form from
   this document." Lives server-side where the state lives; consumes
   the same projection as a first-party client; speaks human (text or
   voice) to the user. Orientation flows outward — the app's own mind
   telling the user where they are — which is the honest version of the
   accessibility lane. Drafts consequential actions for the user to
   confirm; performs reversible preferences directly (the authorship
   principle as an action-policy gradient).

Key economics: against a declared capability surface, intent-matching
is constrained decoding into typed slots — a small-model problem, not
a frontier-model problem. The projection is what makes the resident
affordable.

The staffing chart (2026-07-11, late): **Concierge** is front of house —
ships with the app, serves guests within their own authority. **Valet**
is the owner's personal agent — a skill in the owner's harness, not a
satellite; handed the master keys with valet mode locked on (gate,
ratchet, ledger — the keys work, everything is recorded). Guests may
bring their own staff: visiting agents speaking IFR with borrowed guest
authority. Three roles, one substrate, three trust boundaries.
