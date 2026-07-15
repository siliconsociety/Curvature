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

## Release flow

For each Curvature release:

1. Curvature publishes the runtime and a release-specific note below.
2. A consumer updates only Curvature in its lockfile.
3. The consumer applies any named source migration.
4. The consumer runs its complete gate and exercises affected browser or
   deployment surfaces.
5. The consumer commits the lockfile and migrations, then deploys explicitly.

Framework CI proves a fresh stranger app. Consumer CI proves the existing app;
both are required evidence because scaffolds diverge as soon as owners use them.

## 0.2.5

Live streams now close when their declaring root disappears or changes stream,
and clean generator completion stops EventSource reconnection. This is a
package-only runtime update. Applications using Live need no source migration:
update the lockfile, run the gate, exercise a live screen in a real browser,
and deploy the new package so the versioned `curvature.js` URL changes.
