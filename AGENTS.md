# AGENTS.md — the canonical documentation

You are maintaining a Curvature codebase. This file is written for you, the
agent, and it is the primary documentation of this framework — the
README is the courtesy translation for humans. Read this once per
session; everything else you need is enforced, not remembered.

## What this is

Curvature is a contract that ships a runtime. Server-rendered Python web
apps: FastAPI routes, components as typed functions, real links and real
forms, one small closed client layer for the AJAX feel. The application must
work with JavaScript switched off — that is not a feature, it is the
architecture (SPEC.md C-202).

## The one command that matters

```bash
./gate.sh        # ruff + pyright + pytest with coverage + curvature check
```

Green means done. Red means not done. There is no third state, and
"the finding seems wrong" is a conversation to have with the human, not
a thing to route around. `curvature check` findings are called
**anomalies** and each one names the invariant it serves — read the
message; it tells you the fix.

## How to add a component

1. `uv run curvature new component <dir>/components/<name>` — the scaffold
   pours the file pair (component + test) already on-curve. Its CSS, if
   any, lives beside it.
2. Define the interface first — a `Props` model:

```python
from curvature import Element, Props
from curvature import html as h


class LapCounterProps(Props):
    lap: int
    total: int


def lap_counter(props: LapCounterProps) -> Element:
    return h.span(f"{props.lap}/{props.total}", class_="lap-counter", id="lap-counter")
```

3. Write its test in `tests/` — render it with props, assert on the
   markup. Components are pure functions; their tests need no app.

Rules the gate will hold you to: the first parameter is a Props subclass
(ANOM-110); text is escaped unless you write `raw()`, and every `raw()` is
counted out loud; the file stays under its line ceiling (ANOM-140). Split an
overloaded component. Spiral is active by default: substantial direct
neighbors let a healthy branch earn a larger computed ceiling, while crowded
directories must branch and hollow branches must be pruned; never widen the
ratchet by hand.

## How to add a route

Reads render; writes redirect. No exceptions you can grant yourself.

```python
@app.get("/laps")
async def laps(request: Request, status: str = "all"):
    props = LapListProps(...)          # build typed props from state
    return respond(
        request, lap_list(props), shell=shell,
        purpose="Review and filter recorded laps",
    )


@app.post("/laps")
async def create_lap(title: Annotated[str, Form()]):
    board.add(title.strip())
    return redirect("/laps")           # POST -> redirect -> GET, always
```

- `respond()` needs every fragment root to carry an `id` — that id is
  how the boost layer swaps it in place.
- A mutating route that renders is an anomaly (ANOM-131). A genuine JSON
  endpoint carries `# curvature: json-endpoint` with a reason in review.
- Forms are real forms (`action=`, `method=`); links are real links.
  The constructors refuse anything else, so you will not get far
  trying.

## What you must never do

- **Never write application JavaScript.** The framework owns a closed client
  layer: the stable `curvature.js` entrypoint provides navigation and swaps,
  and its package-owned `live.js` branch provides declared Live lifecycle.
  Neither grants client authority to applications. If a behavior seems to need
  JS, it belongs on the server or in native HTML (`<details>`, `<dialog>`,
  `popover`, CSS `:has()`). A consumer `.js` file is an anomaly on sight
  (ANOM-120).
- **Never edit `ratchet.toml`.** `curvature ratchet` is the only hand on
  the mechanism. Ceilings fall, floors rise; a loosened bound is caught
  against git history (ANOM-142) and will not survive review.
- **Never bypass the gate.** No skipping tests, no weakening an
  assertion to get green, no deleting a check that fired. If the gate
  blocks work you believe is correct, stop and say so in your report.
- **Never add a template language, a bundler, a client state store, or
  a plugin registry.** Their absence is a design decision with a
  paragraph in MANIFESTO.md, not an oversight.

The repository is the agent control plane. `AGENTS.md`, the gate, and the
checked-in scripts are sufficient; ordinary Curvature work requires no
framework-specific agent skill.

## GitHub keeps the time

Issues hold intake and durable technical discussion. An open pull request is
active work; a merged pull request and its release are shipped work. When a
field report starts the work, post the maintainer technical position on its
issue before implementation. Record agreement, disagreement, scope corrections,
and unresolved questions so the reasoning remains visible.

## Field reports

When work on a Curvature consumer reveals a framework-owned gap, identify it to
the operator and offer to file an upstream Curvature issue. Filing requires the
operator's nod. That authorization permits the upstream issue; it creates no
issue, attribution policy, or process artifact in the consumer repository. A
good report names the consumer context and mechanism, gives a minimal
reproduction, includes measurements where relevant, records the temporary
workaround and verification performed, and states desired behavior as checkable
invariants.

Every GitHub message authored by an agent in the Curvature repository carries
model attribution: issue bodies, pull request descriptions, reviews, and
comments, including ordinary maintainer work. Put the signature at the end of
the authored message and immediately before any bot-managed footer. Commit
messages remain ordinary Git history.

This is Curvature repository policy, not part of the framework contract.
Consumer repositories and other manifolds poured with Curvature do not inherit
it unless they independently opt in.

Before an attributed upstream GitHub write, verify identity from the active
task or harness, or from an explicit Factory launch packet; either is
authoritative for that run. `~/.codex/config.toml` alone describes a default
and does not prove the active model. When identity is verified as
`gpt-5.6-luna`, render `— GPT-5.6 Luna (<role>)`; for `gpt-5.6-sol`, render
`— GPT-5.6 Sol (<role>)`. Substitute the exact assigned role without
normalizing or inventing it. Reasoning effort and speed or service tier stay
out of the public signature. If identity cannot be verified, stop before the
upstream GitHub write and ask the operator. Never publish an unidentified-model
fallback.

Model identity is a qualification-ledger key, not complete provenance; the
report's context, mechanism, reproduction, measurements, workaround, and
verification remain the causal record.

## When you finish

Run `./gate.sh`. If it is green and coverage rose, run `curvature ratchet`
and commit the tightened file with your change. Report what you built,
what the gate said, and anything you disclosed-worthy: shortcuts,
doubts, failed attempts that shaped the result. Candor is cheap;
discovery is not.

## Vocabulary

| word | meaning |
|------|---------|
| anomaly | a contract violation; a region where the geometry fails to steer |
| boost | the enhancement layer; intercepted real navigation |
| fragment | an id-carrying subtree, swappable by the boost layer |
| shell | the combinator that pours the document around fragments |
| ratchet | a bound that moves one way (ceilings fall, floors rise) |
| grandfather | pinning an over-ceiling file at its high-water mark |
| Spiral | default local surface-and-volume growth with a twelve-neighbor bound |
| hollow branch | a source directory with no leaves and evidence of removed code; prune it |
| Manifold | the design tokens; the poured surface |
| live | server-pushed fragment swaps over SSE; declared with data-live |
| chart | the machine-legible projection of a screen (agents read charts, not pixels) |
| atlas | the screen linking every readable region; its chart is the machine atlas |
| the geometry holds | `curvature check` exit 0 |
