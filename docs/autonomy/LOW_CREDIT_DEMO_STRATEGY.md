# Low-Credit Demo Strategy

Current constraint: finish the strongest hackathon demo with limited remaining credits.

Prioritize a working vertical slice over broad blueprint coverage:

1. Preserve chain honesty. Do not mark a step complete without independent review.
2. Repair active failed reviews before starting new scope.
3. Prefer the smallest production-quality path that proves the validation gate.
4. Reuse existing architecture and tests; avoid rewrites, scaffolding, and future-phase polish.
5. For demo readiness, favor:
   - upload or select brand input;
   - extract brand palette/DNA;
   - generate script/storyboard;
   - render or assemble a downloadable media artifact;
   - show dashboard/API health and review evidence.
6. Defer non-demo breadth when the chain permits it: social integrations, advanced analytics,
   provider marketplace polish, and optional automation can follow after the demo slice works.

The autonomous runner enforces this by injecting credit-conservative builder and reviewer
instructions while keeping independent review and chain validation intact.
