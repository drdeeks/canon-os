# PHASE 0.5 — auth (JWT register/login): builder evidence

## Requirement

`PHASE-0.5` in `blueprint.md` Part VI requires **auth (JWT register/login)**
under `FEAT_USER_MGMT`, after the API skeleton. Its validation gate is **token
issued**. The REST contract in Part IV section 4.3 specifies:

- `POST /api/v1/auth/register` with `{ email, password, name }`, returning
  `{ user_id, access_token, refresh_token }`.
- `POST /api/v1/auth/login` with `{ email, password }`, returning
  `{ access_token, refresh_token }`.

## Files changed

- `api/src/app.js` — adds the versioned register and login routes while keeping
  the existing health and GraphQL endpoints intact.
- `api/src/auth/service.js` — validates inputs, bcrypt-hashes passwords,
  authenticates credentials, and issues separate HS256 access and refresh JWTs.
- `api/src/auth/user-store.js` — supplies an injectable in-memory store for
  local tests plus a parameterized PostgreSQL store for the V001 `users` table.
- `api/src/server.js` — fails closed in production when JWT secrets are absent.
- `api/package.json` and `api/package-lock.json` — add `bcryptjs`,
  `jsonwebtoken`, and `pg` dependencies.
- `api/test/api.test.js` — HTTP integration coverage for token issuance,
  password hashing, login, duplicate registration, invalid credentials, and
  malformed registration.
- `api/README.md` and `CHANGELOG.md` — document the contract, runtime
  configuration, and append-only change record.

## Commands run with results

```text
cd api && npm install bcryptjs jsonwebtoken pg
Result: added 29 packages; npm audit reported 0 vulnerabilities.

cd api && npm test
Result: 6 passed, 0 failed. Register and login returned JWTs whose signatures
were verified with independent access and refresh secrets.

cd api && NODE_ENV=production node -e "... createApp() ..."
Result: production JWT-secret validation: ok (startup rejects missing secrets).

cd api && node --check src/app.js && node --check src/auth/service.js &&
node --check src/auth/user-store.js
Result: passed.

cd api && git diff --check
Result: passed.
```

## Known limitations

- The refresh-token endpoint in the broader REST contract is intentionally not
  implemented here because this chain item is limited to register/login.
- Without `DATABASE_URL`, the runnable local API uses volatile in-memory users;
  deployment must supply `DATABASE_URL` to persist into the existing PostgreSQL
  V001 `users` table.
- JWT secrets must be securely supplied by deployment. Production fails closed
  if either secret is missing; development defaults exist only for local use.

builder_status: ready_for_independent_review
