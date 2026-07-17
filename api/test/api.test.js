"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { createApp, SERVICE_NAME } = require("../src/app");
const { createInMemoryUserStore } = require("../src/auth/user-store");
const { createInMemoryAssetStore } = require("../src/storage/asset-store");

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
    assetStore: createInMemoryAssetStore(),
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

async function registerUser(email, name) {
  const response = await fetch(`${baseUrl}/api/v1/auth/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password: "a-long-test-password", name }),
  });
  assert.equal(response.status, 201);
  return response.json();
}

function bearer(token) {
  return { authorization: `Bearer ${token}` };
}

test("RBAC enforces viewer, manager, and admin permissions from the current user role", async () => {
  const viewer = await registerUser("viewer@example.com", "Viewer User");
  const manager = await registerUser("manager@example.com", "Manager User");
  const admin = await registerUser("admin@example.com", "Admin User");
  const viewerRecord = await userStore.findByEmail("viewer@example.com");
  const managerRecord = await userStore.findByEmail("manager@example.com");
  const adminRecord = await userStore.findByEmail("admin@example.com");
  await userStore.updateRole(managerRecord.id, "manager");
  await userStore.updateRole(adminRecord.id, "admin");

  const unauthenticated = await fetch(`${baseUrl}/api/v1/users`);
  assert.equal(unauthenticated.status, 401);

  const viewerList = await fetch(`${baseUrl}/api/v1/users`, { headers: bearer(viewer.access_token) });
  assert.equal(viewerList.status, 403);

  const managerList = await fetch(`${baseUrl}/api/v1/users`, { headers: bearer(manager.access_token) });
  assert.equal(managerList.status, 200);
  const managerUsers = (await managerList.json()).users;
  assert.equal(managerUsers.some((user) => user.email === "viewer@example.com"), true);
  assert.equal(managerUsers.some((user) => "passwordHash" in user), false);

  const managerRoleChange = await fetch(`${baseUrl}/api/v1/users/${viewerRecord.id}/role`, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...bearer(manager.access_token) },
    body: JSON.stringify({ role: "manager" }),
  });
  assert.equal(managerRoleChange.status, 403);

  const adminRoleChange = await fetch(`${baseUrl}/api/v1/users/${viewerRecord.id}/role`, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...bearer(admin.access_token) },
    body: JSON.stringify({ role: "manager" }),
  });
  assert.equal(adminRoleChange.status, 200);
  assert.equal((await adminRoleChange.json()).user.role, "manager");

  const promotedViewerList = await fetch(`${baseUrl}/api/v1/users`, { headers: bearer(viewer.access_token) });
  assert.equal(promotedViewerList.status, 200, "authorization uses the updated stored role");
});

test("RBAC rejects refresh tokens, malformed roles, and missing users", async () => {
  const admin = await registerUser("admin-validation@example.com", "Admin Validation");
  const adminRecord = await userStore.findByEmail("admin-validation@example.com");
  await userStore.updateRole(adminRecord.id, "admin");

  const refreshAttempt = await fetch(`${baseUrl}/api/v1/users/me`, { headers: bearer(admin.refresh_token) });
  assert.equal(refreshAttempt.status, 401);

  const invalidRole = await fetch(`${baseUrl}/api/v1/users/${adminRecord.id}/role`, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...bearer(admin.access_token) },
    body: JSON.stringify({ role: "owner" }),
  });
  assert.equal(invalidRole.status, 400);

  const missingUser = await fetch(`${baseUrl}/api/v1/users/38b6efdb-39fe-4b8f-a9e4-0405c65eb400/role`, {
    method: "PATCH",
    headers: { "content-type": "application/json", ...bearer(admin.access_token) },
    body: JSON.stringify({ role: "viewer" }),
  });
  assert.equal(missingUser.status, 404);
});

test("asset storage uploads and downloads an authenticated user's binary asset", async () => {
  const creator = await registerUser("asset-creator@example.com", "Asset Creator");
  const payload = Buffer.from("Canon OS stores image, video, and audio assets.");
  const upload = await fetch(`${baseUrl}/api/v1/assets`, {
    method: "POST",
    headers: {
      ...bearer(creator.access_token),
      "content-type": "application/octet-stream",
      "x-file-name": "campaign-brief.txt",
    },
    body: payload,
  });

  assert.equal(upload.status, 201);
  const asset = await upload.json();
  assert.match(asset.asset_id, /^[0-9a-f-]{36}$/);
  assert.equal(asset.size_bytes, payload.length);

  const download = await fetch(`${baseUrl}${asset.download_url}`, { headers: bearer(creator.access_token) });
  assert.equal(download.status, 200);
  assert.equal(download.headers.get("content-type"), "application/octet-stream");
  assert.match(download.headers.get("content-disposition"), /campaign-brief\.txt/);
  assert.deepEqual(Buffer.from(await download.arrayBuffer()), payload);

  const otherUser = await registerUser("asset-other@example.com", "Other User");
  const crossTenantDownload = await fetch(`${baseUrl}${asset.download_url}`, { headers: bearer(otherUser.access_token) });
  assert.equal(crossTenantDownload.status, 404, "asset keys are isolated by authenticated user");
});

test("asset storage rejects unauthenticated, malformed, and empty uploads", async () => {
  const unauthenticated = await fetch(`${baseUrl}/api/v1/assets`, {
    method: "POST",
    headers: { "content-type": "application/octet-stream", "x-file-name": "asset.bin" },
    body: Buffer.from("asset"),
  });
  assert.equal(unauthenticated.status, 401);

  const creator = await registerUser("invalid-asset@example.com", "Invalid Asset");
  const malformed = await fetch(`${baseUrl}/api/v1/assets`, {
    method: "POST",
    headers: { ...bearer(creator.access_token), "content-type": "application/octet-stream" },
    body: Buffer.from("asset"),
  });
  assert.equal(malformed.status, 400);

  const empty = await fetch(`${baseUrl}/api/v1/assets`, {
    method: "POST",
    headers: {
      ...bearer(creator.access_token),
      "content-type": "application/octet-stream",
      "x-file-name": "empty.bin",
    },
    body: Buffer.alloc(0),
  });
  assert.equal(empty.status, 400);
});
