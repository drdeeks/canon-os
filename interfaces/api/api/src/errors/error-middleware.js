"use strict";

const CLIENT_ERROR_MIN = 400;
const CLIENT_ERROR_MAX = 499;
const SERVER_ERROR_MIN = 500;
const SERVER_ERROR_MAX = 599;

function createHttpError(status, message, code) {
  if (!Number.isInteger(status) || status < CLIENT_ERROR_MIN || status > SERVER_ERROR_MAX) {
    throw new Error("HTTP error status must be an integer between 400 and 599.");
  }
  const error = new Error(message);
  error.status = status;
  if (code) {
    error.code = code;
  }
  return error;
}

function normalizeError(error) {
  if (error?.type === "entity.parse.failed") {
    return { status: 400, message: "Malformed JSON request body.", code: "INVALID_JSON" };
  }
  if (error?.code === "EMAIL_TAKEN") {
    return { status: 409, message: "An account with this email already exists.", code: "EMAIL_TAKEN" };
  }

  const status = Number.isInteger(error?.status) ? error.status : error?.statusCode;
  if (Number.isInteger(status) && status >= CLIENT_ERROR_MIN && status <= CLIENT_ERROR_MAX) {
    return { status, message: error.message || "Request failed.", code: error.code || "REQUEST_ERROR" };
  }
  if (Number.isInteger(status) && status >= SERVER_ERROR_MIN && status <= SERVER_ERROR_MAX) {
    return { status, message: "Internal server error.", code: error?.code || "INTERNAL_ERROR" };
  }
  return { status: 500, message: "Internal server error.", code: error?.code || "INTERNAL_ERROR" };
}

function createNotFoundMiddleware() {
  return (request, _response, next) => next(createHttpError(404, "Route not found.", "ROUTE_NOT_FOUND"));
}

function createErrorMiddleware({ logger } = {}) {
  return (error, request, response, next) => {
    if (response.headersSent) {
      return next(error);
    }

    const normalized = normalizeError(error);
    if (typeof logger?.error === "function") {
      logger.error("http_request_failed", {
        request_id: request.requestId,
        http_method: request.method,
        http_path: request.path,
        http_status: normalized.status,
        error_code: normalized.code,
        error_type: error?.name || "Error",
      });
    }
    return response.status(normalized.status).json({ error: normalized.message });
  };
}

module.exports = { createErrorMiddleware, createHttpError, createNotFoundMiddleware, normalizeError };
