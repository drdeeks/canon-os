# Low-Credit Product Strategy

Current constraint: use remaining credits only where they improve a shippable
product path.

Prioritize a working commercial-generation product over broad blueprint
coverage:

1. Preserve chain honesty. Do not mark a step complete without independent
   review.
2. Repair active failed reviews before starting new scope.
3. Prefer the smallest production-quality path that proves the validation gate.
4. Reuse existing architecture and tests; avoid rewrites, scaffolding, and
   future-phase polish.
5. For product readiness, favor:
   - upload or select brand input;
   - extract brand palette/DNA;
   - generate script/storyboard;
   - render or assemble a downloadable media artifact;
   - expose local/API model routing;
   - package social-channel handoff honestly.
6. Defer non-product breadth when the chain permits it: advanced analytics,
   full social OAuth, billing, provider marketplace polish, and optional
   automation can follow after the commercial-generation path works.

The autonomous runner enforces this by injecting credit-conservative builder
and reviewer instructions while keeping independent review and chain validation
intact.
