# Updating Curvature applications

An application created by Curvature contains two deliberately different kinds
of code. An update must preserve that boundary.

## Package-owned runtime

The installed `curvature` package owns imports from `curvature`, the framework
gate, static runtime assets such as `curvature.js`, and the source templates
used for future scaffolds and pours. Existing applications update this layer
through their dependency lock:

```bash
uv lock --upgrade-package curvature
uv sync
./gate.sh
```

Commit the lockfile with any compatibility changes. Deploy from that lockfile.
The default shell serves `curvature.js` from the installed package and keys its
URL with the installed package version, so a runtime update also moves the
browser asset without copying it into the application.

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
model attribution under this contract. Issues, pull requests, commits, and
ordinary artifacts in this consumer repository are explicitly excluded. When
making that attribution, use the specific model identity plus its role when
known. Never guess: read identity from the harness or configuration, ask the
operator, or use `Unidentified model (role) — operator, please amend` as the
honest fallback. Model identity is a qualification-ledger key, not complete
provenance; the report's context, mechanism, reproduction, measurements,
workaround, and verification remain the causal record.
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
