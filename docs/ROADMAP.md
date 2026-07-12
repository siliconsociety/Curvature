# Roadmap

**The living roadmap IS Pit Board** — one page:
`uv run uvicorn demo.app:app --reload --timeout-graceful-shutdown 1`,
then `/`. The timing tower
streams itself (Live), its data in git at `demo/data/roadmap.json`
(diffs are the changelog), its chart served to agents. This file is
the founding archive; it no longer tracks state.

---

Held to the same rule as everything else here: an item earns code only
when its contract can be stated. Order is intent, not promise — and a
version number is a RELEASE (whatever is green when the button is
pressed), never a container a feature is owed to. The ledger below says
what shipped; the queue says what's next, in dependency order.

## Shipped

- **0.1.0** (2026-07-11): the founding — contract (SPEC C-1xx..6xx),
  runtime (typed components, built markup, one-header fragments),
  curvature.js, the gate with the one-way ratchet, `new app` /
  `new component` scaffolds, Pit Board, AGENTS.md-first docs.
  Steerability lab #1 passed (Luna, zero JS).
- **0.2.0** (2026-07-12, unpublished — the button is the owner's):
  satellites (capture, manifests, mass, C-800..804), `curvature pour`
  with Auth as the first poured satellite (stdlib scrypt, hashed
  session tokens, revolving-door store: sqlite/jsonfile behind a
  seven-verb protocol), C-203 construction-grade, ANOM-131 follows
  assigned redirects, httpx2, warning-free suite.

## The load-bearing principle, found 2026-07-11 (last light)

**A cambered app requires no bespoke client.** IFR is self-describing:
the projection carries its own documentation, discovery is a response
header, identity is the user's ordinary session (borrowed authority via
Auth). One generic IFR capability in any agent harness drives every
Curvature app ever poured. Per-app enduser skills are the SDK-per-
service disease and are refused. (The Valet remains the owner's alone.)

## Decision block — awaiting the owner (2026-07-11, EOD)

1. Crew & timing for 0.2: Fable-now vs Codex-crew-tomorrow (specs are
   fence-ready; Valet skill is the handbook either way).
2. Blessed persistence default for poured manifolds: SQLite (stranger-
   correct, F5 rec) vs Mongo (owner-fluent); Auth forces the choice.
3. Satellite naming: exact-match underscores (curvature_auth both
   sides, F5 rec) vs bare words vs hyphen-quirk (refused by owner law).
4. C-203 CSRF posture sign-off: SameSite=Lax + Origin check on writes,
   construction-grade, no token plumbing (F5 rec).
5. IFR format: JSON Schema for form affordances in a minimal envelope
   (F5 rec).
6. Vocabulary ruling: Manifold = the app itself (the space that has the
   curvature); mass = what alters it (a satellite's checks are its
   mass; tighten-only = no negative mass); tokens file would rename
   (surface.css candidate). Proposed, awaiting the mouth test.

## The queue, in dependency order

1. ~~Satellite mechanics~~ — SHIPPED 0.2.0 (ANOM-160/161 audits still
   queued).
2. ~~Auth skeleton~~ — SHIPPED 0.2.0. Still queued from the Auth
   position: OIDC social login, TOTP, personal access tokens for
   visiting agents, the Mongo store satellite. Position (2026-07-11): own design at the
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
3. ~~The chart~~ — SHIPPED (C-900..902; Chart/Atlas ratified on
   sight). Queued from it: the atlas endpoint, ANOM-170 (chart-serving
   screens must author a purpose).
3b. **The roadmap-manifold** (owner's ruling, 2026-07-12): this file's
   replacement is a Curvature app — the living roadmap IS the pit
   board, converged with the website-as-manifold, chart-native from
   birth so agents read Curvature's roadmap through Curvature's own
   projection. This markdown becomes seed data, then a pointer.
4. **Concierge** — the capstone: IFR consumed first-party + satellite
   packaging + a small-model client + the confirm-vs-do policy.

## Also in the bay (no dependency ordering)

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

## Further out

- **Honest benchmarks.** Render cost, fragment cache hit behavior,
  requests-per-core against an equivalent SPA + JSON API. Publish the
  numbers whatever they say; the architecture argument is only worth
  what it measures.
- **Offline posture (owner's Socratic pass, 2026-07-12).** The worst
  way: rebuild the entire client-heap inside a service worker — shadow
  database in IndexedDB, sync queues, conflict resolution — the app
  implemented twice, the second copy invisible to the gate and
  untestable JS-off by definition. The inverse, what's left: **offline
  is a cache, never a database.** Reads: a sanctioned pure-replay
  worker (cache pages on visit, serve them when unreachable, banner
  the staleness) — it never decides, only replays, C-301 in spirit.
  Writes offline: refused loudly, and the refusal is PROMISED in the
  manifesto — it is the fence that keeps every write on the server,
  which is what makes one-source-of-truth, the chart, and C-202
  coherent. Market honesty: JS-gated storage (localStorage/IndexedDB/
  OPFS) is indeed the only client persistence the platform offers —
  there is no declarative offline; almost no sites have real offline;
  web users do not expect it (the dinosaur game is a cultural
  institution precisely because offline means dead). The promise is
  worth more than the feature.
- **The website.** Curvature's site is a manifold — built with
  Curvature, docs rendered from this repo's markdown, dogfood and demo
  in one. Hosting rides on the deployment doc.
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
