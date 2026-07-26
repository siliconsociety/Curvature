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

## 0.4.3

The stable `/static/lib/curvature.js?v=<version>` include now loads the
package-owned `live.js` branch with the same asset version. Navigation, swaps,
focus, pending state, and history remain in the entrypoint; declared
EventSource lifecycle lives in the branch. The boost layer also leaves
same-page fragment navigation and its history traversal to the browser, while
cross-page boosted navigation preserves fragments through redirects and
scrolls to the resolved target after swapping.

This is a package-only runtime update. Existing applications need no source or
script-tag migration: update Curvature to 0.4.3 in the application lockfile,
sync the environment, exercise boosted and Live paths in a real browser, run
`./gate.sh`, and deploy.

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

Only upstream Curvature field reports and their substantive discussion carry
model attribution under this contract. Consumer-repository artifacts are
excluded, as are ordinary pull requests, commits, and other artifacts wherever
they live.

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
```

Adopt it as an application-owned migration:

1. Copy the block into the application's app-owned `AGENTS.md`.
2. Preserve its upstream-only attribution boundary.
3. Run the application's `./gate.sh`.
4. Commit the contract change as an application-owned migration.

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
