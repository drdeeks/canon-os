"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");
const { createApp, SERVICE_NAME } = require("../src/app");

let server;
let baseUrl;

test.before(async () => {
  server = http.createServer(createApp());
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  baseUrl = `http://127.0.0.1:${server.address().port}`;
});

test.after(async () => {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

test("GET /health returns an HTTP 200 liveness response", async () => {
  const response = await fetch(`${baseUrl}/health`);

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { status: "ok", service: SERVICE_NAME });
});

test("POST /graphql executes the API skeleton health query", async () => {
  const response = await fetch(`${baseUrl}/graphql`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: "{ health { status service } }" }),
  });

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    data: { health: { status: "ok", service: SERVICE_NAME } },
  });
});

test("POST /graphql rejects an empty GraphQL request", async () => {
  const response = await fetch(`${baseUrl}/graphql`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({}),
  });

  assert.equal(response.status, 400);
  assert.match((await response.json()).errors[0].message, /non-empty query/);
});
