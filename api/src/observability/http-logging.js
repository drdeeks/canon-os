"use strict";

const { randomUUID } = require("node:crypto");

const MAX_REQUEST_ID_LENGTH = 128;

function getRequestId(request, requestIdFactory) {
  const supplied = request.get("x-request-id");
  if (typeof supplied === "string" && /^[A-Za-z0-9._-]{1,128}$/.test(supplied)) {
    return supplied;
  }
  return requestIdFactory();
}

function createHttpLoggingMiddleware({ logger, enabled = true, requestIdFactory = randomUUID, now = () => process.hrtime.bigint() } = {}) {
  if (!logger || typeof logger.info !== "function") {
    throw new Error("HTTP logging requires a logger with an info method.");
  }
  if (typeof requestIdFactory !== "function") {
    throw new Error("HTTP logging requires a requestIdFactory function.");
  }

  return (request, response, next) => {
    const requestId = getRequestId(request, requestIdFactory);
    request.requestId = requestId;
    response.set("x-request-id", requestId);
    if (!enabled) {
      return next();
    }

    const startedAt = now();
    response.once("finish", () => {
      const elapsedNanoseconds = now() - startedAt;
      const fields = {
        request_id: requestId,
        http_method: request.method,
        http_path: request.path,
        http_status: response.statusCode,
        duration_ms: Number(elapsedNanoseconds) / 1_000_000,
      };
      if (request.user?.id) {
        fields.user_id = request.user.id;
      }
      logger.info("http_request_completed", fields);
    });
    return next();
  };
}

module.exports = { MAX_REQUEST_ID_LENGTH, createHttpLoggingMiddleware, getRequestId };
