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
`AGENTS.md`. Existing applications should adopt that clause deliberately:
instruct agents to identify framework-owned gaps to the operator and offer an
upstream Curvature issue, file only with the operator's nod, and never create a
corresponding issue, attribution policy, or process artifact in the consumer
repository. A report should carry its context, mechanism, minimal reproduction,
measurements where relevant, temporary workaround, desired behavior as
checkable invariants, and verification.

Scope attribution only to upstream Curvature field reports and substantive
discussion, never consumer-repository issues, pull requests, commits, or
ordinary artifacts. Use the specific model identity plus role when known; read
it from the harness or configuration or ask the operator, and never guess. When
identity remains unavailable, use an honest unidentified-model fallback for the
operator to amend. Model identity is a qualification-ledger key, not complete
provenance, so it does not replace the report body.

This is an application-owned contract migration: package upgrades never
overwrite an existing application's `AGENTS.md`. Review and add the clause
locally, then run `./gate.sh`.

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
