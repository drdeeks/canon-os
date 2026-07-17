# Independent Review — Phase 00, Step 06: user management (RBAC)

## Scope and requirement

Reviewed the active chain item `PHASE-0.6 user mgmt (RBAC)` under
`FEAT_USER_MGMT`, whose validation gate is `role enforced`. The Foundation
table in `blueprint.md` has an off-by-one phase label for this row
(`PHASE-0.5`), while the authoritative active chain, checklist data, supplied
evidence, and this review use `PHASE-0.6`; the deliverable and gate are the
same.

The blueprint security requirements specify the three RBAC roles: Admin,
Manager, and Viewer. This review assessed whether those roles are enforced by
the runnable user-management API, rather than whether the files merely exist.

## Independent inspection

- `api/src/auth/authorization.js` verifies only HS256 access JWTs with the
  access-token secret, rejects refresh tokens, retrieves the current user by
  token subject, rejects inactive/missing/invalid-role records, and applies
  explicit role middleware.
- `api/src/app.js` protects `GET /api/v1/users/me` for an authenticated user,
  allows user listing only to Admin or Manager, and allows role changes only
  to Admin. The role-update payload is limited to `admin`, `manager`, or
  `viewer` and a missing target returns 404.
- Authorization uses the role retrieved from the user store on every protected
  request, rather than trusting the role claim embedded in an earlier token.
- `api/src/auth/user-store.js` supplies password-safe user lists and supports
  role updates through parameterized PostgreSQL queries when `DATABASE_URL` is
  set. The existing V001 schema constrains `users.role` to the same three
  values.

## Reviewer-run verification

- `cd api && npm test` — passed: 8/8 Node HTTP integration tests. The RBAC
  cases demonstrated unauthenticated list rejection (401), Viewer list denial
  (403), Manager list access (200), Manager role-change denial (403), Admin
  role update (200), and immediate use of the promoted user's persisted role
  on its already-issued token. The suite also rejected a refresh token on a
  protected route, an unsupported role, and a missing role-change target.
- `node --check src/app.js`, `node --check src/auth/service.js`,
  `node --check src/auth/user-store.js`, and
  `node --check src/auth/authorization.js` — passed.
- PostgreSQL-backed live probe — passed. The reviewer started a disposable
  `postgres:16-alpine` container, applied
  `db/migrations/V001__init_schema.sql` with `psql -v ON_ERROR_STOP=1`, and
  ran the actual Express app with `DATABASE_URL` set to that database. Live
  HTTP requests demonstrated Viewer 403, Manager 200, Admin role update 200,
  then the originally issued Viewer token receiving 200 after its stored role
  was promoted. The disposable database container was removed after the
  probe.
- `git diff --check -- api` — passed before this review record was added.

## Finding

The required Admin, Manager, and Viewer roles are enforced by the running API,
including the configured PostgreSQL persistence path. The `role enforced`
validation gate is demonstrably satisfied; no external integration is claimed.

VERDICT: PASS
