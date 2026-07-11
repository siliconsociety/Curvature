# Camber

*Pour the road so the car steers itself.*

A web framework for code that agents maintain. Server-rendered Python,
components as typed functions, real links and real forms, one small
boost script for the single-page feel — and a gate that makes the
maintainable path the only path that builds.

Camber's design center is the maintainer nobody watches: the coding
agent in its forty-third session, at 2 a.m., doing whatever the shape of
the code suggests. Frameworks built for humans enforce their discipline
through culture. Camber's discipline is machine-checked — every
invariant in [SPEC.md](SPEC.md) names the check that enforces it, and
violations are reported by `camber check` as **off-camber findings**.
The canonical documentation is [AGENTS.md](AGENTS.md); this README is
the courtesy translation. The argument for all of it is the
[MANIFESTO](MANIFESTO.md).

## The shape of it

```python
from camber import Element, Props, redirect, respond
from camber import html as h


class LapProps(Props):
    title: str
    done: bool


def lap(props: LapProps) -> Element:
    return h.li(props.title, class_="lap done" if props.done else "lap", id="lap")
```

- **Components** are functions of frozen, closed pydantic props. The UI
  is just Python: typed by pyright, measured by coverage, tested by
  pytest without a browser in sight.
- **The app works with JavaScript off.** Reads render full pages; writes
  are POST → redirect → GET through real forms. Your test suite drives
  it with httpx — which executes no JS — so the degraded path is the
  tested path, permanently.
- **camber.js** (91 lines, the only script) boosts working links and
  forms into fragment swaps. Same route, same render, one header of
  difference. Every failure path is real navigation.
- **The ratchet only tightens.** File ceilings fall, the coverage floor
  rises, and `camber ratchet` is the only hand on the mechanism. The
  10,000-line file is never written because week two's gate refuses the
  sediment while the split is still cheap.

## Try it

```bash
git clone <this repo> && cd Camber
uv sync
./gate.sh                              # ruff + pytest + camber check
uv run uvicorn demo.app:app --reload   # Pit Board, the demo
```

Then turn JavaScript off and use the demo again. Nothing changes. That
is the whole point.

## Status

Day one (2026-07-11). The contract, runtime, gate, and demo are real and
self-hosting — this repo passes its own gate. The spec is versioned and
arguable; argue by issue.

MIT. Built by Robert Sharp, with Claude Fable 5 on its last day on the
subscription — read the manifesto and you'll see why that detail
belongs in a README.
