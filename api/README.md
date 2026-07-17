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

Feature endpoints, authentication, and authorization are deliberately deferred
to their respective blueprint chain items.
