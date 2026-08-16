"use strict";

const LOG_LEVELS = Object.freeze({
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
});

function resolveLogLevel(level = process.env.LOG_LEVEL || "info") {
  const normalized = String(level).toLowerCase();
  if (!Object.hasOwn(LOG_LEVELS, normalized)) {
    throw new Error("LOG_LEVEL must be one of: debug, info, warn, error.");
  }
  return normalized;
}

function createLogger({ service = "canon-os-api", level, sink = console, now = () => new Date() } = {}) {
  const minimumLevel = resolveLogLevel(level);

  function emit(logLevel, event, fields = {}) {
    if (!Object.hasOwn(LOG_LEVELS, logLevel)) {
      throw new Error("logLevel must be one of: debug, info, warn, error.");
    }
    if (typeof event !== "string" || event.trim() === "") {
      throw new Error("A non-empty log event is required.");
    }
    if (fields === null || Array.isArray(fields) || typeof fields !== "object") {
      throw new Error("Log fields must be an object.");
    }
    if (LOG_LEVELS[logLevel] < LOG_LEVELS[minimumLevel]) {
      return;
    }

    const record = {
      timestamp: now().toISOString(),
      level: logLevel,
      service,
      event,
      ...fields,
    };
    const serialized = JSON.stringify(record);
    const writer = logLevel === "error" && typeof sink.error === "function" ? sink.error : sink.log;
    writer.call(sink, serialized);
  }

  return Object.freeze({
    debug: (event, fields) => emit("debug", event, fields),
    info: (event, fields) => emit("info", event, fields),
    warn: (event, fields) => emit("warn", event, fields),
    error: (event, fields) => emit("error", event, fields),
  });
}

module.exports = { LOG_LEVELS, createLogger, resolveLogLevel };
