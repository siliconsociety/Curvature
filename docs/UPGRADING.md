# Updating Curvature applications

An application created by Curvature contains two deliberately different kinds
of code. An update must preserve that boundary.

## Package-owned runtime

The installed `curvature` package owns imports from `curvature`, the framework
gate, the closed static runtime (`curvature.js` and `live.js`), and the source
templates used for future scaffolds and pours. Existing applications update
this layer through their dependency lock:

```bash
uv lock --upgrade-package curvature
uv sync
./gate.sh
```

Commit the lockfile with any compatibility changes. Deploy from that lockfile.
The default shell continues to serve only `curvature.js` from the installed
package and keys its URL with the installed package version. That stable
entrypoint propagates the same query to `live.js`, so a runtime update moves
both browser assets without copying either into the application.

Applications that do not commit a lockfile should install an explicit
Curvature version. An unconstrained install is not an update policy.

## Application-owned source

`curvature new app`, `curvature new component`, and `curvature pour` copy code
into the application. From that moment, the application owns those files and
its own gate audits them. Curvature never silently overwrites or merges them.

A release that needs copied source to change must carry a migration note with:

- the affected scaffold or pour versions;
- the files and contract that changed;
- whether the migration is required or optional;
- a focused verification command in addition to `./gate.sh`.

Owners apply that migration as a normal reviewed change. Re-pouring over local
source is not an upgrade mechanism because it would erase application edits.

## Update flow

For each tagged Curvature version:

1. A consumer updates only Curvature in its lockfile.
2. The consumer applies any named source migration.
3. The consumer runs its complete gate and exercises affected browser or
   deployment surfaces.
4. The consumer commits the lockfile and migrations, then deploys explicitly.

Framework CI proves a fresh stranger app. Consumer CI proves the existing app;
both are required evidence because scaffolds diverge as soon as owners use them.

## 0.4.4

0.4.4 is the compatibility repair for consumers with declared Event Horizons.
Curvature now recognizes only `curvature-event-horizon/0.2` at
`app/static/vendor/<name>/event-horizon.json`. It validates the
Curvature-owned schema, directory/name agreement, contained paths and files,
fixed capabilities, and declared byte budgets. `server_contract` is a
non-empty map of string keys to string values. `budget_bytes` contains a
required positive integer `javascript` ceiling and, when `stylesheet` is
declared, a required positive integer `css` ceiling; each artifact is measured
independently. Manifest, schema, path, file, entrypoint, extra-script, and
budget violations are ANOM-120 findings. Only the exact declared entrypoint is
chartered. `network: false` grants nothing and `network: true` grants `fetch`
only; `XMLHttpRequest`, `WebSocket`, `EventSource`, and `sendBeacon` remain
forbidden and are ANOM-121 findings. False non-network capability evidence is
ANOM-123.

The 0.4.4 gate also protects repository-rendered mathematical documentation.
ANOM-124 reports syntax already observed to fail on a supported public
renderer. Use `mathrm{...}` for named functions in display equations and
backticked notation such as `B_τ(f)` or `r` inline. Existing consumers should
correct any ANOM-124 findings as an application-owned documentation migration;
new scaffolds carry the rule in their `AGENTS.md`.

Horizon-bearing consumers should remain on 0.3.2 and move directly to 0.4.4:

1. Audit each manifest against [EVENT_HORIZONS.md](EVENT_HORIZONS.md), keeping
   the exact v0.2 schema and removing extra or undeclared scripts.
2. Update Curvature in the consumer lockfile to 0.4.4.
3. Run consumer tests for the product's `server_contract` and JavaScript-off
   baseline, then run `./gate.sh` and exercise the affected browser path.

Manifest byte budgets are additional horizon bounds. They never alter the
ratchet or Spiral configuration. Curvature checks the generic fence; the
consumer owns product-specific server semantics and no-JavaScript proof.

## 0.4.3 — historical erratum

> **Warning:** The 0.4.3 statement below that existing applications need no
> source or script-tag migration is false for applications that carry Event
> Horizons.

0.4.3 intentionally removed the blanket `static/vendor` JavaScript exemption,
but did not yet interpret `event-horizon.json`. A horizon-bearing consumer
cannot safely adopt 0.4.3: its declared scripts are rejected as unchartered
and their former product capabilities are not a supported migration surface.
Remain on 0.3.2 until moving directly to 0.4.4. This erratum does not change
the package-only path for ordinary consumers without Event Horizons.

The stable `/static/lib/curvature.js?v=<version>` include now loads the
package-owned `live.js` branch with the same asset version. Navigation, swaps,
focus, pending state, and history remain in the entrypoint; declared
EventSource lifecycle lives in the branch. The boost layer also leaves
same-page fragment navigation and its history traversal to the browser, while
cross-page boosted navigation preserves fragments through redirects and
scrolls to the resolved target after swapping.

For ordinary consumers without Event Horizons, this remains a package-only
runtime update: update Curvature to 0.4.3 in the application lockfile, sync the
environment, exercise boosted and Live paths in a real browser, run `./gate.sh`,
and deploy. Horizon-bearing consumers follow the 0.4.4 path above.

## 0.4.2 (internal only; never published)

0.4.2 was a merged integration waypoint for the fragment-navigation
correction. It is not a consumer upgrade target and must never be tagged or
published; its package-owned correction ships publicly as part of 0.4.3.

## 0.4.1

`curvature new app` now removes repository-local Git environment variables
before initializing and committing the generated application. This prevents a
pour started by a parent repository hook, IDE, or automation process from
redirecting scaffold Git commands into that parent. The repair changes only the
package-owned scaffold command; existing application source needs no migration.

New applications also receive the field-report doctrine in their app-owned
`AGENTS.md`. Existing applications should adopt the same canonical block:

```markdown
## Field reports

When app work reveals a gap owned by Curvature — the app is reimplementing
framework responsibility or compensating for a missing check — identify it to
the operator and offer to file an upstream Curvature issue. Filing requires the
operator's nod. That authorization permits the upstream issue; it creates no
issue, attribution policy, or process artifact in this consumer repository. Do
not silently ship the workaround. A good report names the consumer context and
mechanism, gives a minimal reproduction, includes measurements where relevant,
records the temporary workaround and verification performed, and states desired
behavior as checkable invariants.

```

Adopt it as an application-owned migration:

1. Copy the block into the application's app-owned `AGENTS.md`.
2. Run the application's `./gate.sh`.
3. Commit the contract change as an application-owned migration.

Package upgrades never overwrite an existing application's app-owned
`AGENTS.md`.

## 0.4.0

Current Starlette test clients use `httpx2`. New Curvature applications no
longer include the deprecated `httpx` fallback in their development
dependencies. Existing applications may remove that unused fallback with
`uv remove --dev httpx`, regenerate their lock, and run `./gate.sh`. Keep
`httpx` only if application code deliberately adopted it for other HTTP work.

## 0.3.0

Spiral is now the default gate geometry. Updating an existing application may
immediately report ANOM-152 for directories with more than twelve meaningful
children or ANOM-140 for leaves beyond their local surface-derived ceiling.
These are application-owned structural migrations: branch crowded directories
by responsibility and split genuinely isolated oversized leaves.

No configuration is required for the default whole-project body. Repositories
with independent domains may declare non-overlapping `roots`; projects may set
`enabled = false` to retain ordinary ratcheted ceilings. Switching Spiral off
immediately reapplies those ceilings and reports every mismatch at the next
gate. See [SPIRAL.md](SPIRAL.md) for the equations and all three adoption
workflows.

## 0.2.5

Live streams now close when their declaring root disappears or changes stream,
and clean generator completion stops EventSource reconnection. This is a
package-only runtime update. Applications using Live need no source migration:
update the lockfile, run the gate, exercise a live screen in a real browser,
and deploy the new package so the versioned `curvature.js` URL changes.
