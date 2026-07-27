# Project direction and release archive

GitHub issues hold intake and technical discussion, open pull requests show
active work, and merged pull requests plus releases record what shipped.
This file records longer-lived decisions that would otherwise be easy to
misremember.

## Current direction (2026-07-25)

- Curvature is an alpha contract and runtime being hardened for production;
  a deployed consumer is evidence of deployability, not proof of readiness.
- Native HTML is the baseline. The boost enhances links and GET forms only;
  mutating forms stay native and complete through POST-redirect-GET.
- Chart and Atlas remain the general machine-readable interface. They are
  useful without imposing a resident-agent product policy.
- Concierge was removed. A no-UI or resident-agent product may still be a
  worthwhile separate project, but it is not nearly free and does not belong
  in the framework contract yet.
- Offline replay was removed. A generic service worker cannot safely infer
  authorization, invalidation, or secret-handling policy.
- Auth pours one hardened SQLite implementation behind a protocol seam.
  Unfinished JSON and Mongo implementations were removed. New stores must
  arrive with atomicity and cross-process behavior proved by the poured test
  contract.
- Satellite manifests now declare only what capture enforces: identity,
  router, and components. Assets, mass, and rule-pack claims were removed.
- Spiral is the default project geometry in 0.3.0. Direct leaves occupy local
  surface, healthy capacity grows by radius, and twelve meaningful neighbors
  force a semantic branch.
- Repository instructions, the gate, and checked-in verification scripts are
  the complete agent control plane. Consumer agents need no framework-specific
  skill for ordinary edits.

## Next evidence

- Green gates on Python 3.12, 3.13, and 3.14.
- Run `scripts/verify-package.sh` to build both artifacts, install them into
  clean environments, scaffold a stranger app, pour Auth, and run its gate.
- Keep the public site on the latest released framework and verify its HTML,
  Chart, security headers, and health endpoint against the live deployment.
- Publish performance and operational measurements only when reproducible.
- Admit an event-horizon design only after a concrete product needs client
  physics that native HTML and server rendering cannot provide.
