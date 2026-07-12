# The Curvature Manifesto

*The right path is free fall.*

> Structure tells agents how to move; the gate tells structure how to
> curve. — after Wheeler

## The observation

Somewhere in the last few years, writing code stopped being the expensive
part. An agent will produce ten thousand lines before lunch and apologize
for the delay. Draining the ocean is an afternoon chore now.

So look at what actually fails. Not the first week — the first week is
always beautiful. Week twelve is where codebases go to silt up: the
JavaScript file that absorbed one more handler every day until it hit ten
thousand lines, the stylesheet nobody dares delete from, the template that
knows too much. None of it was written by fools. All of it was written by
maintainers — human and machine — doing the locally reasonable thing,
following the gradient the codebase laid out for them.

Agents follow gradients perfectly. That is the whole problem, and the whole
opportunity.

## The failure of convention

Every framework you have ever loved was a social contract. Rails had
conventions, Django had its apps, React had components — and every one of
them enforced its discipline the only way that existed at the time: docs,
code review, culture, shame. That worked, roughly, when maintainers attended
the culture.

Your new maintainer does not attend the culture. It is brilliant, tireless,
and it reads nothing twice. At 2 a.m. in its forty-third session it will do
whatever the shape of the code suggests, and if the shape suggests
*append here*, it appends. The contract in the docs is not the contract.
The gradient is the contract.

Entropy doesn't read the docs. Neither does the thing maintaining your code.

## The inversion

Curvature is not a framework with a linter attached. It is the inversion:
**a contract that happens to ship a runtime.**

Every invariant Curvature cares about is written down next to the machine that
enforces it. If a rule cannot be checked, it is not a rule — it is a wish,
and Curvature does not ship wishes. Convention over configuration was a bet on
human culture. **Constraint over convention** is a bet on verification.

The name is the design. Einstein's whole move was this: gravity is not a
force, it is geometry — a falling body isn't being pushed, it is
following the straightest available line through space that something
massive has curved. That is precisely the relationship Curvature wants
with your agents. You do not resist the force — you shape the space it
falls through. A monk does not stop the opponent's strike; he turns its
strength into the throw. The agent's tirelessness, its literalism, its
perfect gradient-following: Curvature does not fight these. It curves
the space so that free fall *is* the discipline. A banked corner, if you
want it at human scale, is just curved space poured in asphalt: the car
steers itself because the road got there first.

And when the code's path deviates from what the geometry demands, we
have a word for it — the word astronomy used when Mercury's orbit
refused to match Newton: an **anomaly**. Explaining that anomaly took
curvature; it always does. The gate does not report "errors"; it
reports anomalies, each one naming the invariant whose geometry the
observed path escaped.

## The tenets

**1. The server owns the logic.** All of it. State, rules, decisions live
in Python, in one place, testable with one toolchain. If a behavior matters,
it is not implemented in the browser.

**2. The web is the platform.** Real links. Real forms. POST, redirect,
GET. Every page renders whole and every action completes with JavaScript
switched off — not as nostalgia, but because a server-rendered app whose
tests drive real forms through real URLs is an app whose degraded path is
its *tested* path. We had this once. We are taking it back.

**3. JavaScript annotates; it never decides.** The boost layer — the only
JavaScript Curvature ships — intercepts working links and working forms and
swaps fragments instead of navigating. Enhancement, by definition:
everything it touches already works without it. App logic in the browser is
an anomaly, and the gate knows what a `fetch` call looks like.

**4. The UI is typed Python.** Components are functions of props; props are
pydantic models. Your markup logic is type-checked by the same tools as
your API, tested by the same pytest, measured by the same coverage. There
is no second language for the sediment to hide in.

**5. One source of truth per screen.** The component that renders the full
page renders the fragment. Boosted and unboosted requests differ by one
header, never by one template.

**6. Ratchets only tighten.** Coverage floors rise. File ceilings fall.
The numbers live in a file the tooling owns, and the tooling turns the
mechanism one way. The day a file nears its ceiling, the gate forces the
split *while the split is still cheap*. Structure decays wherever the gate
is silent, so the gate is not silent.

**7. Documentation is written for the maintainer.** The maintainer is an
agent. AGENTS.md is the canonical documentation; the README is a courtesy
translation for humans. Curvature is, as far as we know, the first framework
to declare this out loud — every framework that survives the next decade
will do the same, and will pretend it always had.

## The refusals

No bundler. No build step. No client-side state store. No plugin registry.
No mixin. No configuration sprawl. No abstraction admitted before the
second concrete need. Each refusal is load-bearing: every artifact Curvature
does not have is an artifact that cannot silt up.

## Who this is for

Anyone whose interface is, honestly described, state on a server that
people read and change. That is admin panels and personal tools — and it
is also most of the consumer web, which spent fifteen years shipping a
runtime to every phone to reimplement what the server already knew. The
industry has begun conceding this quietly: server components arrived in
the very framework that taught the world to leave the server, carrying
more machinery and less conviction.

The honest boundary is not scale. It is the latency class of a single
interaction: rendering happens where the state lives, so work that
cannot tolerate a round-trip — the 60fps enclave of canvas editors,
maps, collaborative cursors — belongs past an **event horizon**: a
declared, fenced, vendored boundary beyond which different physics
apply and the gate's sight deliberately ends, with its budget and its
contract enforced at the horizon itself (event horizon doctrine, spec
0.2). Most
applications are five percent past the horizon and ninety-five percent
ordinary space, and ordinary space is faster, cheaper, and testable
with JavaScript off.

Heavy traffic is not the argument against curvature; it is the argument
for it — more mass wants more geometry. The client-heap taxes scale
with your users: bundles, hydration, API chatter, and a UI state no one
but the pixels can see. A curved app scales with requests, caches as
HTML, and keeps its entire capability surface on the server, legible to
any client you point at it — including the ones arriving next, which do
not have eyes.

The space is curved for whoever maintains it after you stop looking.
Nobody is looking at week twelve. The geometry has to do it.
