# The Curvature Spec

Version 0.4 — 2026-07-26. Protocol of record for the runtime, the gate,
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
*Enforcement:* gate (ANOM-110) checks the locally visible shape: every
`Element`-returning function in a `components/` tree with a positional
parameter must annotate the first one with a name ending in `Props`.
Pyright then resolves the actual type. ANOM-110 is structural guidance, not
a Python type resolver.

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
PATCH/DELETE, including literal `methods=[...]`, must return `redirect()`
on every visible return path; a rare JSON endpoint needs the documented
pragma plus a written reason). This is deliberately predictable AST
analysis, not a proof of arbitrary Python control flow.

**C-203 · Sessions carry the CSRF posture.**
Auth configuration explicitly declares allowed origins and whether cookies
are Secure; production has no permissive default. Every browser write in
the poured Auth routes, authenticated or not, requires a matching Origin or
Referer. Session cookies are HttpOnly and SameSite=Lax. Bearer-token clients
carry no cookies and are untouched. *Why:* cookies plus cross-site POST is
the CSRF shape, including login and registration. *Enforcement:*
construction in the Auth route dependencies and integration tests poured
into a fresh app.

**C-202 · The app works with JavaScript off.**
Full stop. The unboosted path is not a fallback; it is the application.
*Why:* §2 of the manifesto — the degraded path must be the tested path.
*Enforcement:* structural — the test suite drives the app through
`httpx`, which executes no JavaScript. If it isn't reachable without JS,
it isn't testable, and coverage (C-401) starves until it is. An Event Horizon
is an exceptional latency enclave; it does not remove the consumer's
server-contract or JavaScript-off proof obligation.

## 3. Framework client layer

**C-300 · Client authority is closed and chartered.**
Ordinary application client code is zero. Curvature supplies a closed
framework registry of package-owned public entries, each with one declared
role. The 0.4.4 framework set is:

- `curvature.js` — the stable consumer-facing include; owns fetch navigation,
  fragment swapping, focus, pending state, and history.
- `live.js` — loaded by the stable entrypoint; owns the lifecycle of
  EventSource streams declared by Live roots.

A new framework client capability is a spec amendment argued by issue, not an
ordinary refactor. Private implementation leaves may split an existing
capability without changing its authority, but are not part of the current
two-entry package. Consumer entries form a second registry under this same
law: only a valid Curvature-owned Event Horizon manifest at
`app/static/vendor/<name>/event-horizon.json` can charter one, and only its
exact declared entrypoint is admitted. A bare `static/vendor` path grants no
JavaScript authority. *Why:* two explicit registries preserve bounded
ownership without restoring the 0.3.2 blanket exemption. *Enforcement:* gate
(ANOM-120 reports manifest, schema, path, file, entrypoint, extra-script, and
budget violations and rejects consumer, counterfeit, missing, extra,
unchartered, or entrypoint-mismatched scripts) plus package and scaffold
proofs of the exact framework set and stable include. Framework ownership
means exact filesystem identity with the
Curvature package executing the gate; a project name or lookalike path is not
evidence. This is a bounded local identity check, not a claim of cryptographic
provenance. `static/vendor` continues to mark third-party review policy for
CSS and geometry, but its JavaScript authority comes only from the Event
Horizon schema.

**C-301 · Network authority follows the charter.**
Permission is per capability, not per file format or registry: `curvature.js`
may use `fetch` for navigation; `live.js` may use `EventSource` for declared
Live streams. A consumer Event Horizon with `network: false` gets no network
primitive; `network: true` grants `fetch` only. `XMLHttpRequest`, `WebSocket`,
`EventSource`, and `sendBeacon` are never granted to a v0.2 consumer horizon,
and one entry does not inherit another entry's protocol. *Why:* enumeration
is not a blanket license to speak every protocol. *Enforcement:* gate
(ANOM-121 scans framework entries and valid consumer horizons against their
declared network authority). The predictable textual scan
recognizes direct and `window`/`globalThis` calls across ordinary whitespace
plus simple `const`/`let`/`var` aliases. It is not a JavaScript parser; dynamic
property access and arbitrary data flow remain outside its stated evidence.

**C-305 · Event Horizon manifests are typed constitutions.**
An exceptional consumer enclave is valid only when its manifest declares the
exact `curvature-event-horizon/0.2` schema at
`app/static/vendor/<name>/event-horizon.json`. The required fields are
`spec`, `name`, `purpose`, `entrypoint`, `server_contract`, `capabilities`,
and `budget_bytes`; `stylesheet` is optional. `server_contract` is a non-empty
map of string keys to string values. `budget_bytes` is an object with a
required positive integer `javascript` ceiling and no extra keys; when
`stylesheet` is declared, it also requires a positive integer `css` ceiling.
Each artifact is measured independently. The required capability keys are
`network`, `storage`, and `html_injection`; `history` and `local_time` are
optional, and unknown capability names or schema versions fail. Declared paths
must remain inside the horizon directory and declared files must exist. These
manifest, schema, path, file, entrypoint, extra-script, and budget violations
are ANOM-120. Network evidence is ANOM-121. Evidence of `storage`,
`html_injection`, `history`, or `local_time` when its manifest capability is
false (or omitted, for an optional key) is ANOM-123. The byte ceilings are
additional bounds; they never change ratchet or Spiral configuration.
Curvature validates this generic fence.
Consumer tests prove the product-specific server contract and JavaScript-off
baseline. *Why:* a manifest must be a narrow constitution interpreted by
Curvature, not consumer JSON that silently invents authority.

**C-304 · Obligations are medium-blind; evidence is medium-aware.**
Every maintained artifact must have a declared role, evidence appropriate to
its medium, and a bounded growth model whose units and topology are defined
before enforcement. No language or format grants authority by itself.
Architectural obligations may therefore be medium-blind; checks cannot pretend
their evidence is. Python types, browser semantics, CSS selectors, and source
line mass remain honestly different measurements. Repository-rendered Markdown
uses display math from the portable public macro register and backticked inline
notation. *Enforcement:* contract review plus each medium's named checks;
ANOM-124 rejects math tokens observed to fail on a supported public renderer.
General Markdown and figure geometry are not otherwise claimed here: their
units and topology remain undefined.

**C-303 · Offline replay is not a framework feature.**
Curvature ships no service worker and caches no authenticated pages or
one-time secrets in the browser. *Why:* a generic replay cache cannot know
the authorization and invalidation rules of an application; pretending it
can breaks the one-source-of-truth claim. *Enforcement:* the sanctioned
framework set in ANOM-120 contains only `curvature.js` and `live.js`, neither
chartered for a service worker or replay cache. A consumer Event Horizon may
declare only the fixed v0.2 capabilities in its own product enclave; that is
not a Curvature offline feature.

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
never raises them. The default Spiral protocol (C-602) derives a larger
effective ceiling from a file's healthy local body without changing the
ratcheted base or creating a grandfather exception.

**C-401 · Coverage floor.**
The pytest coverage percentage has a floor in `ratchet.toml`. It rises.
*Why:* see every codebase you have ever inherited.
*Enforcement:* ratchet (ANOM-141).

**C-402 · The tool is the only hand on the ratchet.**
Human edits to `ratchet.toml` that loosen any bound are anomalies.
*Why:* a ratchet with a reverse lever is a dial.
*Enforcement:* gate (ANOM-142: `curvature check` recomputes actuals; any bound
looser than the recorded tightest-known state is refused).

**C-403 · Versions move like ratchets.**
Every released version has a `v{version}` tag; a tagged version with commits
past it is stale and must be bumped before anything else lands. *Why:* the bump
is the release step everyone forgets — so it is not remembered, it is checked.
*Enforcement:* gate (ANOM-143: tag-for-current-version exists and HEAD has
moved past it; silent where git or the tag is absent).

## 5. Fragments and the boost protocol

**C-500 · Negotiation is one header.**
A boosted request carries `Curvature-Boost: 1`. The server responds with
either the full document (header absent) or the fragment subtree(s)
(header present), from the same render (C-103). Responses set
`Vary: Curvature-Boost`. *Why:* the protocol surface between server and
boost layer must fit in one sentence, or it will grow until it is a
framework nobody chose. *Enforcement:* construction (`respond()` is the
only fragment emitter). The framework boosts links and GET forms only;
mutating forms use native navigation and PRG. Same-document links with a
non-empty fragment stay native, including their back/forward traversal.
Cross-document boosts retain the fragment through redirects and scroll to its
decoded element id or legacy named anchor after swapping.

**C-501 · Fragments are identified subtrees.**
Every fragment root carries an `id`. The boost layer replaces the
document element with the matching `id`, for each top-level element in
the response. Anything else — a fragment without an id, an id not on the
page — triggers full navigation to the same URL. *Why:* the failure mode
of enhancement must be the working baseline, never a broken screen.
*Enforcement:* construction (`respond()` raises on id-less fragment
roots) + curvature.js (fallback navigation on any mismatch). During an
identified swap, response `autofocus` wins; otherwise a focused element
inside a replaced root is restored only when the replacement contains
the same focusable `id`, without deliberately moving the viewport.

**C-502 · Live is the boost swap flowing downhill.**
A `data-live="<stream>"` attribute opens one EventSource per stream URL;
the server pushes rendered fragments over SSE (`curvature.live`), and
the boost layer swaps them by id under the same law as everything else
(C-501) — with one inversion: missing targets are SKIPPED, never
navigated, because an enhancement stream must not hijack the page it
decorates. Live regions are display surfaces; don't stream a form
someone might be typing into. JS-off degradation is already honest:
reads render whole, refresh is the fallback. *Why:* chat-class
liveness without a word of app JS or a gram of client state.
The source belongs to its current `data-live` root: replacing that root
with the same id and stream transfers ownership, while removing it or
changing its stream closes and unregisters the source. Clean generator
completion sends `event: curvature-end`; the boost layer closes the source
and retires that root so EventSource does not reconnect. A later render of
the live root is a new owner and opens exactly one fresh source. Failures and
interrupted connections retain native EventSource retry behavior.
*Enforcement:* construction (sse_event refuses anonymous fragments and
live_stream emits the terminal event) + browser coverage of ownership,
cleanup, terminal completion, return, and duplicate prevention.

**C-503 · A boosted form keeps native submitter semantics.**
For an explicitly declared submitter override, `formaction`, `formmethod`,
and `formtarget` replace the owning form's corresponding values. An absent
attribute and a null submitter fall back to the form. Curvature enhances only
same-origin GET submissions targeting the current browsing context; every
other submission remains native. The successful submitter is included in the
query. *Why:* enhancement must not reinterpret working HTML, and application
code must not need a second form interceptor to recover browser semantics.
*Enforcement:* browser coverage of submitter overrides, form fallback,
off-target and mutating submissions, null-submitter submission, and the
no-JavaScript path.

**C-504 · Pending means intent in flight.**
An enhanced form submission synchronously marks its form with `aria-busy` and
marks both form and submitter with `data-curvature-pending`. The navigation
that created those marks owns them: success, failure, or abort clears them,
and an older completion cannot clear a newer navigation's state. Pending is
an annotation of operator intent, never optimistic system truth. *Why:* slow
work needs immediate acknowledgement without inventing client state or a
correction path. *Enforcement:* browser coverage of success, HTTP fallback,
network failure, and superseded navigation.

## 6. Project shape

**C-600 · Components live in `components/`.**
One directory per component for anything with style or breadth: the
Python module, its CSS file, its test. Small pure components may share a
module until they grow style. *Why:* co-location is what makes the
default destination (C-100) physical. *Enforcement:* gate (ANOM-150,
landed: orphan class selectors — defined in project CSS, referenced
nowhere in project markup — are findings; vendored CSS exempt).

**C-601 · Explicit imports only.**
No plugin registries, no auto-discovery, no metaclass registration, no
import-time side effects. *Why:* an agent (or a human at 2 a.m.) must be
able to answer "who calls this?" with grep.
*Enforcement:* gate (ANOM-151, landed: `__init_subclass__` and
`metaclass=` are findings — the manifold refuses invisible machinery).

**C-602 · Spiral growth follows local surface and volume.**
Spiral is on by default for projects with `pyproject.toml`. For each direct
source file, normalized mass is its physical lines divided by the stable
default ceiling for its suffix. A directory's occupied surface is
`A = Σ min(1, mass)` over those direct leaves, its normalized radius is
`R = max(1, √A)`, and each healthy leaf receives
`round(ratcheted base × R)`. Child directories form independent local bodies;
distant project mass cannot inflate a leaf, and a leaf's contribution is
clamped so it cannot buy its own excess. Every directory has a
twelve-meaningful-child coordination bound. Crowded directories keep their
ordinary file ceilings until they branch. Explicit non-overlapping roots may
separate unrelated domains; `enabled = false` opts out without creating
history or exceptions. *Why:* volume capacity per surface grows with the
radius of a sphere, while the three-dimensional kissing number supplies a
natural local coordination limit. Mature projects gain room without teaching
the trunk to accept unlimited leaves. *Enforcement:* gate (ANOM-140 applies
the effective ceiling; ANOM-152 reports invalid Spiral configuration and
directories over the coordination bound).

**C-603 · Hollow branches are pruned.**
A source directory with no meaningful files is an anomaly when the workspace
retains evidence that code occupied it: orphaned Python cache artifacts or
paths tracked at `HEAD` that are now absent. An empty directory without such
evidence may be an intentional runtime boundary; an empty package marker is a
real file. *Why:* dead branches preserve a false map of the project and make
agents search responsibilities that no longer exist. Evidence identifies the
debris; the gate directs one action. *Enforcement:* gate (ANOM-153 reports the
highest hollow branch beneath a live ancestor; its sole remedy is to prune that
directory).

## 7. Satellites

Extensibility without a registry: a satellite is a body captured into
the app's gravity by explicit assembly, never discovered. The refusals
stand — there is no registry, no entry point, no import-time magic.

**C-800 · A satellite is a value, not a discovery.**
A frozen, typed manifest (name, version, router, components) captured with
`capture(app, satellite, orbit=...)`. First-party
satellites are POURED — `curvature pour <name>` delivers their source
into `satellites/<name>/`, owned by the manifold and audited by its own
gate natively; third-party satellites may install from an index, where
C-801's reach applies. *Why:* "who runs in my app?" must be answerable
by grep, and only a pour delivers code. *Enforcement:* construction
(capture validates; nothing else mounts anything). **Landed in 0.2.**

**C-801 · Installed satellite audits are explicit.**
`curvature audit <package>` applies the source-shape checks to an installed
package when the owner invokes it. Poured satellites need no special path:
their source and tests belong to the app and its ordinary gate. *Why:* audit
reach must be real, but `capture()` must not imply an invisible plugin
registry. *Enforcement:* the audit command walks the named installed
package. It does not claim automatic discovery of captured packages.

**C-802 · Declared orbit only.**
The orbit is explicit at capture, and each named component must match the
satellite's `components/` directory.
*Why:* the manifest is the fence. *Enforcement:* gate (ANOM-161, landed: a manifest's declared components must match its components/ directory — ghosts and stowaways are findings).

**C-803 · A manifest declares only what capture enforces.**
Satellites do not advertise assets, mass, or rule-packs. Those fields were
removed until a real enforcement path exists. *Why:* an unenforced manifest
is documentation wearing a type annotation. *Enforcement:* construction:
the manifest type has no such fields.

**C-804 · No interception, no ordering.**
Satellites cannot observe each other, wrap each other, or add global
middleware; offered capabilities are opted into explicitly at use
sites. *Why:* capture order must be meaningless by construction.
*Enforcement:* construction (the capture API has no hook surface).

Doctrine: satellites are how features audition for core. Auth is the first
poured satellite. Chart/Atlas and Live are runtime capabilities. Concierge
was removed: resident-agent product policy is not part of Curvature's web
contract.

## 8. The chart — LANDED 0.3-line, 2026-07-12

**C-900 · Negotiation is one header, third head.**
A request carrying `Curvature-Chart: 1` receives the chart: the
machine-legible projection of the same screen — purpose, headings,
fragment ids, and affordances (links; forms as JSON Schema). HTML
responses advertise availability (`Curvature-Chart: available`) so
visiting agents discover it on first contact. *Why:* agents are
clients without eyes; a cambered app requires no bespoke client.
*Enforcement:* construction (`respond()` is the only chart emitter).

**C-901 · Charts are derived, never authored.**
The chart is computed from the same Element tree the pixels come from.
There is no chart template, no chart override, no second source of
truth to drift. *Why:* C-103's law extended to the third head.
*Enforcement:* construction (build_chart takes the fragments,
nothing else).

**C-902 · Purpose is the one authored line.**
`respond(..., purpose=...)` carries the single human-written sentence
of orientation a derivation cannot supply: what this screen is FOR.
*Why:* the first job of the agent-facing surface is orientation.
*Enforcement:* runtime (chart negotiation refuses an empty purpose) and
gate (ANOM-170: app `respond()` calls without a non-empty authored purpose
are anomalies).

**C-903 · The atlas is a screen.**
The enumeration of a manifold's readable regions is an ordinary
fragment of real links (`curvature.atlas.atlas(app)`), mounted on an
ordinary route. Its machine form needs no format of its own: the
atlas's chart IS the atlas. *Why:* one mechanism, three heads, zero
parallel protocols. *Enforcement:* construction (the atlas is built
from app routes; there is nothing to hand-maintain).

## Anomaly finding index

| ID     | Invariant | Check |
|--------|-----------|-------|
| ANOM-110 | C-100 | component signature: first annotation name ends in `Props` |
| ANOM-120 | C-300 | unchartered/counterfeit/missing framework script or Event Horizon manifest/schema/path/file/entrypoint/extra-script/budget violation |
| ANOM-121 | C-301 | network token outside an exact framework or Event Horizon charter |
| ANOM-122 | C-102 | `raw()` call census (report, warn over budget) |
| ANOM-123 | C-305 | false non-network Event Horizon capability evidence |
| ANOM-124 | C-304 | Markdown math token rejected by a supported public renderer |
| ANOM-130 | C-200 | `onclick=` / `javascript:` / `href="#"` in source |
| ANOM-131 | C-201 | mutating route returns non-redirect |
| ANOM-140 | C-400 | file lines over ceiling |
| ANOM-141 | C-401 | coverage below floor |
| ANOM-142 | C-402 | ratchet bound looser than tightest-known |
| ANOM-143 | C-403 | tagged version with commits past its tag |
| ANOM-150 | C-600 | orphan CSS class selector |
| ANOM-151 | C-601 | registration magic (__init_subclass__, metaclass) |
| ANOM-152 | C-602 | invalid Spiral configuration or directory over branch span |
| ANOM-153 | C-603 | hollow source branch retaining evidence of removed leaves |
| ANOM-161 | C-802 | satellite manifest disagrees with its directory |
| ANOM-170 | C-902 | respond() without an authored purpose |

Token checks (ANOM-121, ANOM-123, ANOM-130) honor one escape hatch: a line
carrying a `curvature-allow` pragma with a reason. Enforcement code and tests
that exercise refusals must spell the forbidden words; the pragma keeps them
buildable while staying greppable — and `curvature check` reports the pragma
census on every run, so the escape hatch can never go quietly.

A curved repo is one where `curvature check` exits 0 and has *teeth it
can show*: the finding index above is the framework minimum. A green gate
means these declared checks passed; it is not a claim that static analysis
proved every semantic property of arbitrary Python.
