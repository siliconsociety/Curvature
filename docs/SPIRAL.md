# The Spiral law

Spiral is Curvature's default project-growth protocol. It gives related source
files progressively more room without letting one oversized file, a distant
subsystem, or an overcrowded directory manufacture capacity.

No configuration is required. A project with `pyproject.toml` is one Spiral
tree rooted at `.` unless it declares different boundaries or opts out.

## The geometry

The inspiration is the relationship between the surface and volume of a
sphere:

$$
A(r)=4\pi r^2
$$

$$
V(r)=\frac{4}{3}\pi r^3
$$

$$
\frac{V(r)}{A(r)}=\frac{r}{3}
$$

Volume capacity per unit surface grows linearly with radius. Curvature applies
that relationship locally and absorbs the constant `1/3` into a unit
calibration: one occupied surface unit has radius one and keeps the base
ceiling. For every non-vendored governed source file `f`, its normalized mass
is

$$
m_f=\frac{\mathrm{lines}(f)}{B_{\tau(f)}} ,
$$

where `B_τ(f)` is the stable default unit for its suffix:

| Source | One mass unit |
|---|---:|
| Python | 300 lines |
| CSS | 250 lines |
| JavaScript | 150 lines |

The occupied surface of directory `D` is

$$
A_D=\sum_{f\in\mathrm{direct}(D)}\min(1,m_f).
$$

Each file contributes in proportion to its size until it occupies one full
unit. The clamp is load-bearing: a 600-line Python file still occupies one
unit and cannot buy permission for its own excess. A tiny helper contributes
only a tiny fraction, so splitting off stubs is not a capacity exploit.

The normalized radius is

$$
R_D=\max(1,\sqrt{A_D}),
$$

and a healthy file's effective ceiling is

$$
C_f=\mathrm{round}(B_fR_D),
$$

where `B_f` is the project's ratcheted base ceiling for that language.
Grandfather exceptions remain exact pins and are never multiplied.

For the default Python base:

| Occupied local surface | Radius | Python ceiling |
|---:|---:|---:|
| 1 | 1.000 | 300 |
| 2 | 1.414 | 424 |
| 3 | 1.732 | 520 |
| 5 | 2.236 | 671 |
| 8 | 2.828 | 849 |
| 12 | 3.464 | 1,039 |

The law has no artificial growth stages and no global reservoir. Direct source
files are leaves on one local surface. Child directories are branches into new
local bodies with their own surface and radius. Code elsewhere in the project
cannot buy room here.

## The coordination bound

A directory may have at most twelve meaningful direct children. Twelve is the
three-dimensional kissing number: at most twelve equal spheres can touch one
equal central sphere without overlap. Curvature uses that natural coordination
limit as the point where a flat collection must reveal another level of
structure.

A meaningful child is either:

- a non-empty governed source file directly in the directory; or
- a direct child directory containing non-empty governed source.

Empty markers, excluded caches, and vendored source do not count. ANOM-152
reports the thirteenth child. Files directly inside a crowded directory retain
their ordinary ratcheted ceiling until the directory branches.

The inverse also matters: a branch with no leaves is structural debris.
ANOM-153 reports a source directory left with only cache archaeology or missing
tracked files. Its remedy is singular: prune the hollow directory.

Spiral measures shape; it does not move or recombine code. Turning it on never
joins previously separated files. Turning it off reapplies the ordinary
ceilings, and the next gate reports files that need attention on the ordinary
maintenance path.

## Adoption workflows

### New Curvature project

Pour the application and prove its initial geometry:

```bash
uvx --from "curvature==0.3.0" curvature new app my_app
cd my_app
uv sync
./gate.sh
```

Spiral is already active over the whole project. Add configuration only if the
project has independent source domains.

### Existing Curved project

Update the package-owned runtime and gate, then run the application's complete
proof:

```bash
uv lock --upgrade-package curvature
uv sync
./gate.sh
```

Spiral becomes active when the new gate reads the existing `pyproject.toml`.
ANOM-152 identifies flat directories ready to branch; ANOM-140 identifies
leaves beyond their local radius. Make those semantic changes as normal
reviewed edits and rerun the gate.

For unusual repositories, independent roots keep unrelated domains separate:

```toml
[tool.curvature.spiral]
roots = ["src/example", "tests"]
```

Roots must exist, stay inside the project, and not overlap.

### Existing project adopting Curvature

Add Curvature as an application dependency when using its runtime:

```bash
uv add "curvature[fastapi]>=0.3,<0.4"
```

For gate-only adoption, add it to the development group:

```bash
uv add --dev "curvature>=0.3,<0.4"
```

Run the gate to produce the migration inventory:

```bash
uv run curvature check
```

Resolve its anomalies, run the project's coverage-producing test command, then
run:

```bash
uv run curvature check
uv run curvature ratchet
```

Keep `uv run curvature check` in the project's ordinary gate or CI workflow.

## Explicit controls

The default whole-project body is equivalent to:

```toml
[tool.curvature.spiral]
enabled = true
roots = ["."]
```

To separate unrelated source domains:

```toml
[tool.curvature.spiral]
roots = ["src/example", "tests"]
```

To switch Spiral off:

```toml
[tool.curvature.spiral]
enabled = false
```

Run the complete gate after either change. Switching boundaries or disabling
Spiral changes only computed ceilings; it creates no history, hidden state, or
automatic source rewrite.
