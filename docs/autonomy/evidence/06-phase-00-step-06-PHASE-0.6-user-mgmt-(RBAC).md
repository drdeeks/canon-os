# PHASE 0.6 — user mgmt (RBAC): builder evidence

## Requirement

`PHASE-0.6` in `blueprint.md` Part VI requires **user mgmt (RBAC)** under
`FEAT_USER_MGMT`, after `PHASE-0.5`. The validation gate is **role enforced**.
The security requirements in Part I define the three required roles: **Admin**,
**Manager**, and **Viewer**.

The implemented access policy is deliberately narrow to this phase's user
management scope:

- Any authenticated role may read its own user identity at `GET /api/v1/users/me`.
- Admin and Manager may list password-safe user records at `GET /api/v1/users`.
- Only Admin may change a user role at `PATCH /api/v1/users/:userId/role`.

Every protected request verifies an HS256 access JWT and then retrieves the
current user record. Authorization therefore uses the current persisted role,
not a potentially stale JWT claim. Refresh tokens are rejected.

## Files changed

- `api/src/auth/authorization.js` — access-token authentication, role constants,
  and reusable Admin/Manager/Viewer authorization middleware.
- `api/src/auth/service.js` — includes a user's role in newly issued JWT claims.
- `api/src/auth/user-store.js` — adds current-user lookup, password-safe user
  listing, and role update methods for both in-memory and PostgreSQL stores.
- `api/src/app.js` — exposes the protected user identity, listing, and
  administrator-only role-update routes.
- `api/test/api.test.js` — integration coverage proving Viewer denial, Manager
  listing access, Admin-only role changes, immediate enforcement after a role
  update, refresh-token denial, invalid-role rejection, and missing-user handling.
- `api/README.md` — documents the RBAC API contract and bearer-token behavior.

## Commands run with results

```text
cd api && npm test
Result: 8 passed, 0 failed. HTTP integration tests exercised all three roles
and protected-route rejection paths.

cd api && node --check src/app.js && node --check src/auth/service.js &&
node --check src/auth/user-store.js && node --check src/auth/authorization.js
Result: passed.

cd api && git diff --check
Result: passed.
```

## Known limitations

- This phase adds only the RBAC user-management boundary. It does not add OAuth,
  refresh-token exchange, invitations, or organization/tenant membership; those
  are outside this chain item.
- The development fallback remains an in-memory user store. Deployment must set
  `DATABASE_URL` to persist the existing V001 `users` table.
- No account bootstrap flow is introduced here; an administrator must exist via
  controlled deployment/database provisioning before administrator-only role
  management is available in a fresh persistent environment.

builder_status: ready_for_independent_review
