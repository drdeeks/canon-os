# Canon OS API

Phase 0.4 introduces the Node.js API boundary. It uses Express for HTTP routing
and GraphQL for the initial query contract.

```bash
cd api
npm install
npm test
npm start
```

`GET /health` is the liveness gate and returns HTTP 200 with the API service
identity. `POST /graphql` accepts a JSON GraphQL request; the initial query is:

```graphql
{ health { status service } }
```

## Authentication

Phase 0.5 provides the following contract from the blueprint:

```text
POST /api/v1/auth/register  { email, password, name }
POST /api/v1/auth/login     { email, password }
```

Registration returns `201` with `{ user_id, access_token, refresh_token }`;
login returns `200` with `{ access_token, refresh_token }`. Passwords are
hashed with bcrypt and access/refresh JWTs use separate HS256 signing keys.

## Role-based access control

Phase 0.6 enforces the blueprint's `admin`, `manager`, and `viewer` roles.
Every access token is verified against the current user record, so a role change
takes effect on the next protected request rather than waiting for an older JWT
to expire.

```text
GET   /api/v1/users/me                 any authenticated role
GET   /api/v1/users                    admin or manager
PATCH /api/v1/users/:userId/role       admin only, { role }
```

Protected routes require `Authorization: Bearer <access_token>`. Refresh tokens
cannot access them. User-management responses never include password hashes.

Set `DATABASE_URL` to persist users in the existing PostgreSQL `users` table.
Without it, the server uses an in-memory store suitable only for local
development and tests. Production requires both `JWT_ACCESS_SECRET` and
`JWT_REFRESH_SECRET`; development uses non-production defaults for a runnable
local API.
