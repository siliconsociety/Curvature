# Event Horizons

Curvature's ordinary application space is server-rendered and works with
JavaScript switched off (C-202). An **Event Horizon** is an explicit,
exceptional enclave for product behavior that cannot tolerate a round trip:
for example, a canvas editor, a map, or a collaborative cursor. It is not a
general application-JavaScript escape hatch.

## One law, two registries

Client authority has one Curvature-owned law and two charter registries:

- The framework registry is enumerated by [SPEC.md](../SPEC.md): the package
  owns `curvature.js` and `live.js`, each with a fixed role.
- The consumer registry is declared by valid Event Horizon manifests. A
  manifest is interpreted under this Curvature-owned schema; consumer JSON
  cannot invent capabilities or change the law.

Unchartered JavaScript remains an anomaly. A bare `static/vendor` path grants
no authority. A valid manifest grants authority only to its exact declared
entrypoint.

## The v0.2 manifest

Curvature recognizes `curvature-event-horizon/0.2` only at:

```text
app/static/vendor/<name>/event-horizon.json
```

The directory name must equal `name`. The schema contains the following
fields; every field except the explicitly marked `stylesheet` is required:

| Field | Shape and meaning |
| --- | --- |
| `spec` | The exact string `curvature-event-horizon/0.2`. Other versions fail predictably. |
| `name` | A non-empty horizon name and one path component; it must match `<name>`. |
| `purpose` | A non-empty human description of the latency-critical behavior. |
| `entrypoint` | A relative JavaScript path contained by the horizon directory. The file must exist, and only this file is chartered. |
| `server_contract` | A non-empty map whose keys and values are strings. Curvature validates its shape; consumer tests prove the product semantics. |
| `capabilities` | An object with the fixed boolean keys below. Unknown capability names fail. |
| `budget_bytes` | An object with a required positive integer `javascript` ceiling and no extra keys. If `stylesheet` is declared, it also requires a positive integer `css` ceiling. Each artifact is measured independently at the vendor fence. |
| `stylesheet` | Optional relative path to an existing stylesheet contained by the horizon directory. It grants no script authority. |

The required capability keys are `network`, `storage`, and
`html_injection`. `history` and `local_time` may be declared as additional
boolean keys; an omitted optional key is false. No other key is part of v0.2.

For example, this manifest declares a small instrument editor with network
access and local storage:

```json
{
  "spec": "curvature-event-horizon/0.2",
  "name": "instrument-runtime",
  "purpose": "Edit instrument readings without a round trip between keystrokes.",
  "entrypoint": "instrument-runtime.js",
  "server_contract": {
    "read": "GET /instruments/{id}",
    "write": "POST /instruments/{id}/readings"
  },
  "capabilities": {
    "network": true,
    "storage": true,
    "html_injection": false,
    "history": false,
    "local_time": false
  },
  "budget_bytes": {
    "javascript": 24576,
    "css": 8192
  },
  "stylesheet": "instrument-runtime.css"
}
```

### Capability semantics

The capability vocabulary is deliberately closed. A `true` value opts into
the named v0.2 category; it does not authorize a consumer to add a related
browser primitive under a new name.

- `network: false` grants no network primitive. `network: true` grants
  `fetch` only.
- `XMLHttpRequest`, `WebSocket`, `EventSource`, and `sendBeacon` are
  forbidden to consumer horizons in v0.2, regardless of `network`.
- `storage` and `html_injection` are explicit opt-ins to those named product
  behaviors; `false` means the horizon has no such authority.
- `history` and `local_time` are optional explicit opt-ins. Absent or false
  means no history or local-time authority.

The non-network check is deliberately textual and predictable. It recognizes:

- `localStorage`, `sessionStorage`, `indexedDB`, and `document.cookie` as
  storage evidence;
- `innerHTML`, `outerHTML`, `insertAdjacentHTML`, and `document.write` as HTML
  injection evidence;
- `history.pushState` and `history.replaceState` as history evidence;
- `Intl.DateTimeFormat`, `toLocaleString`, `toLocaleDateString`, and
  `toLocaleTimeString` as local-time evidence.

Like Curvature's other token checks, a line may carry a reasoned
`curvature-allow:` pragma when enforcement code or a test must name forbidden
evidence. The gate reports that pragma census.

The manifest does not replace the server contract. Consumer tests must prove
the product-specific meaning of `server_contract` and must retain a working
JavaScript-off baseline for the surrounding application and the horizon's
server path.

## Enforcement boundary

At the fence, Curvature validates the generic contract: the exact manifest
location and schema version, directory/name agreement, relative path
containment, required files, fixed capabilities, and per-artifact byte
ceilings. A path that escapes the horizon directory, a missing declared file,
an unknown capability, or an over-budget artifact is invalid. These manifest,
schema, path, file, entrypoint, extra-script, and budget violations are
ANOM-120 findings.

`budget_bytes.javascript` measures the declared entrypoint, and
`budget_bytes.css` measures the declared stylesheet when present. Each is an
additional bound; neither edits, raises, or lowers `ratchet.toml`, file
ceilings, coverage floors, or Spiral configuration. The vendored horizon is
governed at its own fence by byte geometry.

Curvature proves this generic boundary. Consumer tests prove the product's
server semantics, browser behavior, and JavaScript-off path. A valid manifest
is therefore a typed constitution, not a free-form permission document.

Malformed or missing manifests, entrypoint mismatches, and budget breaches
fail deterministically as ANOM-120 findings and identify the declared field
and observed violation. Network evidence is ANOM-121. Evidence of
`storage`, `html_injection`, `history`, or `local_time` when that capability is
false (or omitted, for an optional key) is ANOM-123. A missing valid manifest
leaves every consumer script unchartered.

## Versioning

The schema version is exact, not advisory. Curvature accepts v0.2 only; an
unknown `spec` fails rather than falling back to a nearby schema or treating
the manifest as an opaque exemption. A future schema must ship with an
explicit migration path, a new recognized version, and consumer verification
before existing manifests are changed. Until then, keep a horizon on the
last supported version.

## Upgrade flow

0.4.3 removed the old blanket `static/vendor` exemption without reading these
manifests. It was not a safe target for horizon-bearing consumers. Those
consumers remain on 0.3.2 and move directly to the repaired 0.4.4 release:

1. Keep each horizon at `curvature-event-horizon/0.2` and audit its manifest
   against this reference.
2. Ensure the declared entrypoint and optional stylesheet stay inside the
   named directory, exist, and leave no extra or undeclared JavaScript beside
   the entrypoint.
3. Update only Curvature in the consumer lockfile to 0.4.4, then run the
   consumer tests for its server contract and JavaScript-off baseline.
4. Run `./gate.sh`, exercise the affected browser path, and deploy from the
   reviewed lockfile.

Consumers without Event Horizons can update normally to 0.4.4 as a
package-only change. See [UPGRADING.md](UPGRADING.md) for the historical
erratum and the complete 0.4.4 path.
