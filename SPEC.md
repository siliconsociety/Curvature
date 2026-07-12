# The Curvature Spec

Version 0.1 — 2026-07-11. Protocol of record for the runtime, the gate,
and every codebase that claims to be curved.

The rule of this document: **an invariant that names no enforcement is a
wish, and wishes get deleted.** Every invariant below carries an ID, a
why, and the machine that checks it. Enforcement comes in three grades,
strongest first:

- **construction** — the runtime refuses to build the violating thing;
  the code cannot express the mistake.
- **gate** — `curvature check` reports it as an anomaly; the
  build is red.
- **ratchet** — a numeric bound recorded in `ratchet.toml`, moved only by
  `curvature ratchet`, and only in the tightening direction.

## 1. Rendering

**C-100 · Components are functions of props.**
A component is a plain Python function whose single required parameter is
a `curvature.Props` subclass and whose return type is `curvature.Element`.
No classes, no registries, no context vars. *Why:* an explicit, typed,
import-traceable interface is the unit of composition — the thing every
change has a default destination inside.
*Enforcement:* gate (ANOM-110): every function in a `components/` tree that
returns `Element` must annotate its first parameter with a `Props`
subclass.

**C-101 · Props are frozen and closed.**
`Props` is a pydantic model with `frozen=True, extra="forbid"`. *Why:*
components must not mutate their inputs or accept silent extras; a typo'd
prop is a loud failure at the call site, not a quiet default downstream.
*Enforcement:* construction (the `Props` base class configures it;
subclasses inherit).

**C-102 · Markup is built, not templated.**
HTML is constructed through `curvature.html` element functions returning
`Element` trees. Text is escaped by default; raw HTML requires the
explicit `raw()` wrapper. *Why:* one language, one type checker, one
coverage report; injection safety as the default gradient.
*Enforcement:* construction (element functions escape all text children;
`raw()` is greppable and gate-counted, ANOM-122).

**C-103 · One source of truth per screen.**
The component that renders a page's full document is the same component
tree that renders its boosted fragment. Fragment and page may differ only
by the document shell. *Why:* two templates for one screen is the first
sediment layer. *Enforcement:* construction (`respond()` accepts one
body and derives both forms from it).

## 2. The web contract

**C-200 · Real links, real forms.**
Every `a` carries a real `href`; every `form` carries `action` and
`method`. There is no `onclick`, no `href="#"`, no submit-by-script.
*Why:* the anchor and the form are the only two verbs the web guarantees
without JavaScript; every behavior reachable through them is a behavior
the test suite can drive. *Enforcement:* construction (`a()` and `form()`
have required parameters; `href="#"` raises) + gate (ANOM-130: no `onclick`
or `javascript:` URLs anywhere in source).

**C-201 · Writes follow POST → redirect → GET.**
Mutating handlers return a redirect (303) to a GET view; they never
render a body. *Why:* refresh-safe, history-safe, and it forces every
state change to have a canonical, linkable after-state.
*Enforcement:* gate (ANOM-131: route functions registered for POST/PUT/
DELETE must return `Redirect`; heuristic AST check, escape hatch
documented in AGENTS.md for the rare JSON endpoint).

**C-203 · Sessions carry the CSRF posture.**
Session cookies are HttpOnly and SameSite=Lax; the session-resolving
dependency refuses writes bearing a foreign Origin header (403) before
any handler runs. Bearer-token clients carry no cookies and are
untouched. *Why:* cookies plus cross-site POST is the CSRF shape; the
defense lives in the one dependency every authenticated route already
declares. *Enforcement:* construction (the Auth satellite's session
dependency; landed 0.2).

**C-202 · The app works with JavaScript off.**
Full stop. The unboosted path is not a fallback; it is the application.
*Why:* §2 of the manifesto — the degraded path must be the tested path.
*Enforcement:* structural — the test suite drives the app through
`httpx`, which executes no JavaScript. If it isn't reachable without JS,
it isn't testable, and coverage (C-401) starves until it is.

## 3. JavaScript

**C-300 · One script.**
The only first-party JavaScript in a curved project is the vendored,
pinned `curvature.js` boost layer. *Why:* every additional script is a new
sediment bed. *Enforcement:* gate (ANOM-120: any `.js` file outside
`static/vendor/` is an anomaly; the vendor directory is pinned by
`VERSIONS.md` entry).

**C-301 · JavaScript never speaks HTTP on its own.**
No `fetch`, `XMLHttpRequest`, `WebSocket`, or `EventSource` outside
`curvature.js`. *Why:* a script that can call the server is app logic
wearing an enhancement's jacket. *Enforcement:* gate (ANOM-121: token scan
of all non-vendor JS and inline script bodies).

**C-302 · No inline script bodies.**
`script()` elements may carry `src` only. *Why:* inline script is
unauditable by ANOM-121 and untestable by anything.
*Enforcement:* construction (`script()` with a text child raises).

## 4. The ratchet

**C-400 · File ceilings.**
Every source file has a line ceiling (defaults: Python 300, CSS 250, JS
150). Existing violators are grandfathered into `ratchet.toml` at their
current size and may only shrink. *Why:* the 10,000-line file is never
written; it accretes. The ceiling forces the split while the split is
cheap. *Enforcement:* ratchet (ANOM-140) — `curvature check` fails any file
over its bound; `curvature ratchet` lowers bounds to current actuals and
never raises them.

**C-401 · Coverage floor.**
The pytest coverage percentage has a floor in `ratchet.toml`. It rises.
*Why:* see every codebase you have ever inherited.
*Enforcement:* ratchet (ANOM-141).

**C-402 · The tool is the only hand on the ratchet.**
Human edits to `ratchet.toml` that loosen any bound are anomalies.
*Why:* a ratchet with a reverse lever is a dial.
*Enforcement:* gate (ANOM-142: `curvature check` recomputes actuals; any bound
looser than the recorded tightest-known state is refused).

## 5. Fragments and the boost protocol

**C-500 · Negotiation is one header.**
A boosted request carries `Curvature-Boost: 1`. The server responds with
either the full document (header absent) or the fragment subtree(s)
(header present), from the same render (C-103). Responses set
`Vary: Curvature-Boost`. *Why:* the protocol surface between server and
boost layer must fit in one sentence, or it will grow until it is a
framework nobody chose. *Enforcement:* construction (`respond()` is the
only fragment emitter).

**C-501 · Fragments are identified subtrees.**
Every fragment root carries an `id`. The boost layer replaces the
document element with the matching `id`, for each top-level element in
the response. Anything else — a fragment without an id, an id not on the
page — triggers full navigation to the same URL. *Why:* the failure mode
of enhancement must be the working baseline, never a broken screen.
*Enforcement:* construction (`respond()` raises on id-less fragment
roots) + curvature.js (fallback navigation on any mismatch).

## 6. Project shape

**C-600 · Components live in `components/`.**
One directory per component for anything with style or breadth: the
Python module, its CSS file, its test. Small pure components may share a
module until they grow style. *Why:* co-location is what makes the
default destination (C-100) physical. *Enforcement:* gate (ANOM-150: a
component's CSS may only be in its directory; orphan selectors are
findings) — *deferred to 0.2; directory convention documented in
AGENTS.md meanwhile.*

**C-601 · Explicit imports only.**
No plugin registries, no auto-discovery, no metaclass registration, no
import-time side effects. *Why:* an agent (or a human at 2 a.m.) must be
able to answer "who calls this?" with grep.
*Enforcement:* gate (ANOM-151: no `__init_subclass__` registration
patterns, no module-scope route table mutation outside app assembly) —
*heuristic, 0.2.*

## 7. Satellites — DRAFT, lands in 0.2

Extensibility without a registry: a satellite is a body captured into
the app's gravity by explicit assembly, never discovered. The refusals
stand — there is no registry, no entry point, no import-time magic.

**C-800 · A satellite is a value, not a discovery.**
A frozen, typed manifest (name, version, routes, components, assets,
checks) validated at `capture(app, satellite, orbit=...)`. First-party
satellites are POURED — `curvature pour <name>` delivers their source
into `satellites/<name>/`, owned by the manifold and audited by its own
gate natively; third-party satellites may install from an index, where
C-801's reach applies. *Why:* "who runs in my app?" must be answerable
by grep, and only a pour delivers code. *Enforcement:* construction
(capture validates; nothing else mounts anything). **Landed in 0.2.**

**C-801 · The contract follows the code.**
`curvature check` audits captured satellites' installed source —
site-packages included — under the full anomaly index. No satellite
JavaScript; a satellite needing client physics declares an event
horizon with a budget in its manifest. *Why:* a contract that stops at
the repo boundary is a costume. *Enforcement:* gate (ANOM-160, 0.2).

**C-802 · Declared orbit only.**
Every route prefix, component, and check a satellite contributes is in
its manifest; contribution outside the declaration is an anomaly.
*Why:* the manifest is the fence. *Enforcement:* gate (ANOM-161, 0.2).

**C-803 · Satellites tighten, never flatten.**
A satellite may add gate checks (rule-packs); it may never remove,
weaken, or reorder one. *Why:* the ratchet philosophy, applied to the
rule set itself. *Enforcement:* construction (the check API is
append-only).

**C-804 · No interception, no ordering.**
Satellites cannot observe each other, wrap each other, or add global
middleware; offered capabilities are opted into explicitly at use
sites. *Why:* capture order must be meaningless by construction.
*Enforcement:* construction (the capture API has no hook surface).

Doctrine: satellites are how features audition for core. First
constellation: Concierge (the resident agent), IFR (the agent
projection), Auth, Admin, Live (SSE push), and rule-packs.

## Anomaly finding index

| ID     | Invariant | Check |
|--------|-----------|-------|
| ANOM-110 | C-100 | component signature: first param is `Props` subclass |
| ANOM-120 | C-300 | `.js` outside `static/vendor/` |
| ANOM-121 | C-301 | HTTP tokens in non-vendor JS or inline script |
| ANOM-122 | C-102 | `raw()` call census (report, warn over budget) |
| ANOM-130 | C-200 | `onclick=` / `javascript:` / `href="#"` in source |
| ANOM-131 | C-201 | mutating route returns non-redirect |
| ANOM-140 | C-400 | file lines over ceiling |
| ANOM-141 | C-401 | coverage below floor |
| ANOM-142 | C-402 | ratchet bound looser than tightest-known |

Token checks (ANOM-121, ANOM-130) honor one escape hatch: a line carrying a
`curvature-allow` pragma with a reason. Enforcement code and tests that
exercise refusals must spell the forbidden words; the pragma keeps them
buildable while staying greppable — and `curvature check` publishes the
pragma census on every run, so the escape hatch can never go quietly.

A curved repo is one where `curvature check` exits 0 and has *teeth it
can show*: the finding index above is the minimum. Projects may add
rules; they may never remove one that has fired.
