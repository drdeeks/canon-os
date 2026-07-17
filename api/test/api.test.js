"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { createApp, SERVICE_NAME } = require("../src/app");
const { createInMemoryUserStore } = require("../src/auth/user-store");

const ACCESS_SECRET = "test-access-secret";
const REFRESH_SECRET = "test-refresh-secret";

let server;
let baseUrl;
let userStore;

test.before(async () => {
  userStore = createInMemoryUserStore();
  server = http.createServer(createApp({
    userStore,
    accessTokenSecret: ACCESS_SECRET,
    refreshTokenSecret: REFRESH_SECRET,
  }));
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

test("POST /api/v1/auth/register hashes a password and issues JWTs", async () => {
  const response = await fetch(`${baseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      email: "creator@example.com",
      password: "a-long-test-password",
      name: "Canon Creator",
    }),
  });

  assert.equal(response.status, 201);
  const body = await response.json();
  assert.match(body.user_id, /^[0-9a-f-]{36}$/);
  assert.equal(jwt.verify(body.access_token, ACCESS_SECRET).token_type, "access");
  assert.equal(jwt.verify(body.refresh_token, REFRESH_SECRET).token_type, "refresh");
  assert.equal(jwt.decode(body.access_token).email, "creator@example.com");
  assert.equal(body.password, undefined);
  assert.notEqual((await userStore.findByEmail("creator@example.com")).passwordHash, body.password, "password hashes are never returned");
  assert.equal(
    await bcrypt.compare("a-long-test-password", (await userStore.findByEmail("creator@example.com")).passwordHash),
    true,
  );
});

test("POST /api/v1/auth/login returns fresh JWTs for a registered account", async () => {
  const response = await fetch(`${baseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: "creator@example.com", password: "a-long-test-password" }),
  });

  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(jwt.verify(body.access_token, ACCESS_SECRET).token_type, "access");
  assert.equal(jwt.verify(body.refresh_token, REFRESH_SECRET).token_type, "refresh");
});

test("auth rejects duplicate accounts, invalid credentials, and invalid input", async () => {
  const duplicate = await fetch(`${baseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      email: "creator@example.com",
      password: "a-long-test-password",
      name: "Duplicate",
    }),
  });
  assert.equal(duplicate.status, 409);

  const invalidCredentials = await fetch(`${baseUrl}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: "creator@example.com", password: "wrong-password" }),
  });
  assert.equal(invalidCredentials.status, 401);
  assert.deepEqual(await invalidCredentials.json(), { error: "Invalid email or password." });

  const invalidRegistration = await fetch(`${baseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: "invalid", password: "short", name: "" }),
  });
  assert.equal(invalidRegistration.status, 400);
});
