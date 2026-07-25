# Spiral

Spiral is Curvature's optional protocol for projects whose total growth has
outgrown one fixed file ceiling. It lets cohesive files grow slowly while
keeping every directory locally navigable.

Enable it per source tree in `pyproject.toml`:

```toml
[tool.curvature.spiral]
enabled = true
roots = ["app"]
```

Multiple roots are independent:

```toml
[tool.curvature.spiral]
roots = ["src/example", "tests"]
```

The `src/example` tree cannot buy room with test code, and the test tree
cannot buy room with application code. Roots must exist, stay inside the
project, and not overlap. The table's presence enables Spiral unless
`enabled = false` is explicit.

Removing the table or setting `enabled = false` immediately restores the
ordinary ratcheted ceilings. The next `curvature check` reports every file
that no longer fits. Spiral records no high-water marks and creates no
grandfather exceptions.

## Mass

Spiral measures source, not files. For each non-vendored governed file:

```text
file mass = physical lines / default ceiling for its suffix
tree mass = sum of file mass
```

The default ceilings define one unit:

| Source | One mass unit |
|---|---:|
| Python | 300 lines |
| CSS | 250 lines |
| JavaScript | 150 lines |

Twenty 15-line Python files and one 300-line Python file therefore have the
same mass. Their shape is different, which the branch law measures
separately. Empty files, excluded directories, and `static/vendor/` do not
contribute.

The tree's **Spiral scale** is the greatest Fibonacci threshold not exceeding
its mass:

```text
scale(M) = max { F ∈ 1, 2, 3, 5, 8, 13, 21, 34, ... | F ≤ M }
```

Discrete thresholds keep ordinary edits from continuously moving the limit.

## Leaf growth

A tree stays at its ordinary ceilings through scale 13. Beyond that:

```text
growth(scale) = √(scale / 13)
healthy leaf ceiling = round(ratcheted ceiling × growth)
```

For the default Python ceiling:

| Spiral scale | Python ceiling |
|---:|---:|
| 13 | 300 |
| 21 | 381 |
| 34 | 485 |
| 55 | 617 |
| 89 | 785 |
| 144 | 998 |
| 233 | 1,270 |

The sequence has no final cap. When project mass advances by approximately
the golden ratio, local file capacity advances by its square root. The other
square root of growth must be carried by the tree's structure.

Grandfather exceptions remain exact pins; Spiral does not multiply them.

## Branch growth

A directory may have at most 13 meaningful direct children. Eight is the
comfortable target; when a branch crosses 13, `8 + 5` is the suggested
partition, not a required naming scheme.

A meaningful child is either:

- a non-empty governed source file directly in the directory; or
- a direct child directory containing non-empty governed source.

The branch span never rises with total project mass. Total capacity grows
without bound through recursive branching, not through ever larger sibling
lists.

ANOM-152 reports crowded directories. Files whose immediate directory is
crowded retain the ordinary ratcheted ceiling until that directory branches.
A one-file component directory is healthy and receives the tree's full
scaled ceiling.

Spiral does not move files, infer architecture, recombine prior splits, or
grandfather the files it permits to grow. It supplies the gradient; the
maintainer still names the branches.
