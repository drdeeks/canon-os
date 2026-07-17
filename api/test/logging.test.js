"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const test = require("node:test");
const { createApp } = require("../src/app");
const { createLogger, resolveLogLevel } = require("../src/observability/logger");
const { getRequestId } = require("../src/observability/http-logging");

test("structured logger writes parseable JSON records and honors its level", () => {
  const records = [];
  const logger = createLogger({
    service: "test-api",
    level: "info",
    now: () => new Date("2026-07-17T13:10:00.000Z"),
    sink: { log: (record) => records.push(record) },
  });

  logger.debug("ignored", { request_id: "request-1" });
  logger.info("http_request_completed", { request_id: "request-1", http_status: 200 });

  assert.equal(records.length, 1);
  assert.deepEqual(JSON.parse(records[0]), {
    timestamp: "2026-07-17T13:10:00.000Z",
    level: "info",
    service: "test-api",
    event: "http_request_completed",
    request_id: "request-1",
    http_status: 200,
  });
  assert.equal(resolveLogLevel("WARN"), "warn");
  assert.throws(() => resolveLogLevel("verbose"), /LOG_LEVEL/);
});

test("HTTP middleware emits a structured completion record and preserves safe request IDs", async () => {
  const records = [];
  const logger = createLogger({
    sink: { log: (record) => records.push(JSON.parse(record)) },
    now: () => new Date("2026-07-17T13:10:00.000Z"),
  });
  const clockValues = [10_000_000n, 35_500_000n];
  const server = http.createServer(createApp({
    logger,
    requestIdFactory: () => "generated-request-id",
    loggingNow: () => clockValues.shift(),
  }));
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));

  try {
    const response = await fetch(`http://127.0.0.1:${server.address().port}/health`, {
      headers: { "x-request-id": "campaign-42.request_7" },
    });
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("x-request-id"), "campaign-42.request_7");
    assert.deepEqual(await response.json(), { status: "ok", service: "canon-os-api" });

    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(records.length, 1);
    assert.deepEqual(records[0], {
      timestamp: "2026-07-17T13:10:00.000Z",
      level: "info",
      service: "canon-os-api",
      event: "http_request_completed",
      request_id: "campaign-42.request_7",
      http_method: "GET",
      http_path: "/health",
      http_status: 200,
      duration_ms: 25.5,
    });
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
});

test("request IDs reject unsafe values and use the generated correlation ID", () => {
  const request = { get: () => "unsafe id with spaces" };
  assert.equal(getRequestId(request, () => "generated-request-id"), "generated-request-id");
});
