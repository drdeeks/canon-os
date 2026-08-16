"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");
const { createApp } = require("../src/app");
const { createHttpError, normalizeError } = require("../src/errors/error-middleware");

async function startServer(app) {
  const server = http.createServer(app);
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  return {
    server,
    baseUrl: `http://127.0.0.1:${server.address().port}`,
  };
}

async function stopServer(server) {
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}

test("error normalization preserves safe client failures and hides internal details", () => {
  assert.deepEqual(normalizeError(createHttpError(422, "Campaign brief is invalid.", "INVALID_BRIEF")), {
    status: 422,
    message: "Campaign brief is invalid.",
    code: "INVALID_BRIEF",
  });
  assert.deepEqual(normalizeError(new Error("database password leaked")), {
    status: 500,
    message: "Internal server error.",
    code: "INTERNAL_ERROR",
  });
  assert.throws(() => createHttpError(200, "not an error"), /400 and 599/);
});

test("central error middleware handles malformed JSON and unknown routes with correlation IDs", async () => {
  const { server, baseUrl } = await startServer(createApp({
    requestIdFactory: () => "generated-error-request-id",
  }));

  try {
    const malformedJson = await fetch(`${baseUrl}/graphql`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-request-id": "malformed-json-42" },
      body: "{",
    });
    assert.equal(malformedJson.status, 400);
    assert.equal(malformedJson.headers.get("x-request-id"), "malformed-json-42");
    assert.deepEqual(await malformedJson.json(), { error: "Malformed JSON request body." });

    const unknownRoute = await fetch(`${baseUrl}/not-a-route`);
    assert.equal(unknownRoute.status, 404);
    assert.equal(unknownRoute.headers.get("x-request-id"), "generated-error-request-id");
    assert.deepEqual(await unknownRoute.json(), { error: "Route not found." });
  } finally {
    await stopServer(server);
  }
});

test("central error middleware logs unexpected failures without exposing their details", async () => {
  const errors = [];
  const logger = {
    info() {},
    error(event, fields) {
      errors.push({ event, fields });
    },
  };
  const assetStore = {
    async upload() {
      throw new Error("S3 credential should never reach a client");
    },
  };
  const { server, baseUrl } = await startServer(createApp({
    logger,
    assetStore,
    accessTokenSecret: "error-test-access-secret",
    refreshTokenSecret: "error-test-refresh-secret",
  }));

  try {
    const registration = await fetch(`${baseUrl}/api/v1/auth/register`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        email: "error-handler@example.com",
        password: "a-long-test-password",
        name: "Error Handler",
      }),
    });
    const { access_token: accessToken } = await registration.json();

    const response = await fetch(`${baseUrl}/api/v1/assets`, {
      method: "POST",
      headers: {
        authorization: `Bearer ${accessToken}`,
        "content-type": "application/octet-stream",
        "x-file-name": "brief.png",
        "x-request-id": "internal-failure-7",
      },
      body: Buffer.from("asset"),
    });
    assert.equal(response.status, 500);
    assert.deepEqual(await response.json(), { error: "Internal server error." });

    assert.deepEqual(errors, [{
      event: "http_request_failed",
      fields: {
        request_id: "internal-failure-7",
        http_method: "POST",
        http_path: "/api/v1/assets",
        http_status: 500,
        error_code: "INTERNAL_ERROR",
        error_type: "Error",
      },
    }]);
  } finally {
    await stopServer(server);
  }
});
