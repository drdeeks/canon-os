# Independent Review — Phase 00, Step 05: JWT register/login

## Scope and requirement

The active chain item is `PHASE-0.5 auth (JWT register/login)`, with the
`token issued` validation gate and `FEAT_USER_MGMT` feature flag. In the
authoritative Foundation table this JWT deliverable is labelled `PHASE-0.4`
(the following table row labels RBAC as `PHASE-0.5`); the supplied active-item
label and builder evidence use the chain-step naming. This review assesses the
specified JWT register/login deliverable and its token-issued gate, not the
subsequent RBAC item.

Part IV section 4.3 requires:

- `POST /api/v1/auth/register` accepting `{ email, password, name }` and
  returning `{ user_id, access_token, refresh_token }`.
- `POST /api/v1/auth/login` accepting `{ email, password }` and returning
  `{ access_token, refresh_token }`.

## Independent inspection

- `api/src/app.js` registers both versioned endpoints in the runnable Express
  application and delegates them to a dedicated authentication service.
- `api/src/auth/service.js` validates requests, bcrypt-hashes registration
  passwords, authenticates with bcrypt comparison, and signs distinct access
  and refresh tokens using HS256. Access tokens expire in 15 minutes and
  refresh tokens in 7 days.
- `api/src/auth/user-store.js` uses parameterized PostgreSQL queries when
  `DATABASE_URL` is configured. Its columns and returned fields agree with the
  existing V001 `users` schema; the local in-memory store supports isolated
  HTTP tests.
- In production, missing either JWT secret causes application construction to
  fail; no production default secret is used.

## Reviewer-run verification

- `cd api && npm test` — passed: 6/6 Node HTTP integration tests. The suite
  exercised registration, login, independent JWT verification with different
  access/refresh secrets, bcrypt storage, duplicate account rejection,
  invalid-credential rejection, and malformed registration rejection.
- `NODE_ENV=production node -e '... createApp() ...'` — passed: application
  construction rejected absent JWT secrets with the expected configuration
  error.
- `node --check src/app.js`, `node --check src/auth/service.js`, and
  `node --check src/auth/user-store.js` — passed.
- Independent live persistence probe — passed. The reviewer started a
  disposable `postgres:15-alpine` container, applied
  `db/migrations/V001__init_schema.sql` using `psql -v ON_ERROR_STOP=1`, and
  launched the actual Express app configured with that database. A live HTTP
  registration returned HTTP 201 and exactly `user_id`, `access_token`, and
  `refresh_token`; both tokens verified as HS256 with their respective secrets,
  had the expected access/refresh token types and the returned user ID as
  `sub`, and were distinct. A live HTTP login using the same email with
  different case returned HTTP 200 and exactly the two required tokens. A
  direct PostgreSQL query confirmed normalized email storage, a bcrypt hash
  rather than the submitted password, and a populated `last_login_at` after
  login. The disposable container was removed after the probe.
- `git diff --check` — passed before this review record was added.

## Finding

The required register and login REST contracts are implemented in the runnable
service. The validation gate was independently demonstrated against both the
in-memory test path and the configured PostgreSQL persistence path; no
external integration is claimed.

VERDICT: PASS
