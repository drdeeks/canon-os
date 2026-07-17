"use strict";

const express = require("express");
const { buildSchema, graphql } = require("graphql");
const { createAuthService } = require("./auth/service");
const { createInMemoryUserStore, createPostgresUserStore } = require("./auth/user-store");
const { ROLES, ROLE_VALUES, createAuthorization } = require("./auth/authorization");
const { createS3AssetStore } = require("./storage/asset-store");
const { createRabbitMqJobQueue } = require("./queue/job-queue");
const { randomUUID } = require("node:crypto");

const SERVICE_NAME = "canon-os-api";
const schema = buildSchema(`
  type Health {
    status: String!
    service: String!
  }

  type Query {
    health: Health!
  }
`);

const rootValue = {
  health: () => ({ status: "ok", service: SERVICE_NAME }),
};

function createApp(options = {}) {
  const app = express();
  const userStore = options.userStore || (process.env.DATABASE_URL
    ? createPostgresUserStore({ databaseUrl: process.env.DATABASE_URL })
    : createInMemoryUserStore());
  const isProduction = process.env.NODE_ENV === "production";
  const accessTokenSecret = options.accessTokenSecret || process.env.JWT_ACCESS_SECRET ||
    (isProduction ? null : "development-access-secret-not-for-production");
  const refreshTokenSecret = options.refreshTokenSecret || process.env.JWT_REFRESH_SECRET ||
    (isProduction ? null : "development-refresh-secret-not-for-production");
  const auth = createAuthService({ userStore, accessTokenSecret, refreshTokenSecret });
  const authorization = createAuthorization({ userStore, accessTokenSecret });
  const assetStore = options.assetStore || (process.env.S3_ENDPOINT
    ? createS3AssetStore()
    : null);
  const jobQueue = options.jobQueue || (process.env.RABBITMQ_URL
    ? createRabbitMqJobQueue()
    : null);

  app.disable("x-powered-by");
  app.use(express.json({ limit: "1mb" }));

  app.get("/health", (_request, response) => {
    response.status(200).json({ status: "ok", service: SERVICE_NAME });
  });

  app.post("/api/v1/auth/register", async (request, response) => {
    try {
      response.status(201).json(await auth.register(request.body || {}));
    } catch (error) {
      response.status(error.code === "EMAIL_TAKEN" ? 409 : error.status || 500).json({
        error: (error.status || error.code === "EMAIL_TAKEN")
          ? error.message
          : "Unable to register account.",
      });
    }
  });

  app.post("/api/v1/auth/login", async (request, response) => {
    try {
      response.status(200).json(await auth.login(request.body || {}));
    } catch (error) {
      response.status(error.status || 500).json({
        error: error.status ? error.message : "Unable to log in.",
      });
    }
  });

  app.get("/api/v1/users/me", authorization.authenticate, (request, response) => {
    response.status(200).json({
      id: request.user.id,
      email: request.user.email,
      name: request.user.name,
      role: request.user.role,
    });
  });

  app.get(
    "/api/v1/users",
    authorization.authenticate,
    authorization.requireRole(ROLES.ADMIN, ROLES.MANAGER),
    async (_request, response, next) => {
      try {
        response.status(200).json({ users: await userStore.listUsers() });
      } catch (error) {
        next(error);
      }
    },
  );

  function requireJobQueue(_request, response, next) {
    if (!jobQueue) {
      return response.status(503).json({ error: "Job queue is not configured." });
    }
    return next();
  }

  app.post(
    "/api/v1/jobs",
    authorization.authenticate,
    requireJobQueue,
    async (request, response, next) => {
      const { job_type: jobType, payload, priority = 0 } = request.body || {};
      if (typeof jobType !== "string" || jobType.trim() === "" || jobType.length > 100) {
        return response.status(400).json({ error: "job_type must be a non-empty string up to 100 characters." });
      }
      if (payload === null || Array.isArray(payload) || typeof payload !== "object") {
        return response.status(400).json({ error: "payload must be a JSON object." });
      }
      if (!Number.isInteger(priority) || priority < 0 || priority > 10) {
        return response.status(400).json({ error: "priority must be an integer between 0 and 10." });
      }

      const job = {
        id: randomUUID(),
        job_type: jobType.trim(),
        payload,
        priority,
        user_id: request.user.id,
        status: "pending",
        attempts: 0,
        max_attempts: 3,
        enqueued_at: new Date().toISOString(),
      };
      try {
        await jobQueue.enqueue(job);
        return response.status(202).json({ job });
      } catch (error) {
        return response.status(503).json({ error: "Unable to enqueue job." });
      }
    },
  );

  app.patch(
    "/api/v1/users/:userId/role",
    authorization.authenticate,
    authorization.requireRole(ROLES.ADMIN),
    async (request, response, next) => {
      try {
        const { role } = request.body || {};
        if (typeof role !== "string" || !ROLE_VALUES.includes(role)) {
          return response.status(400).json({ error: "Role must be one of: admin, manager, viewer." });
        }
        const user = await userStore.updateRole(request.params.userId, role);
        if (!user) {
          return response.status(404).json({ error: "User not found." });
        }
        return response.status(200).json({ user });
      } catch (error) {
        return next(error);
      }
    },
  );

  function requireAssetStore(_request, response, next) {
    if (!assetStore) {
      return response.status(503).json({ error: "Asset storage is not configured." });
    }
    return next();
  }

  app.post(
    "/api/v1/assets",
    authorization.authenticate,
    requireAssetStore,
    express.raw({ type: "application/octet-stream", limit: "100mb" }),
    async (request, response, next) => {
      try {
        const filename = request.get("x-file-name");
        if (typeof filename !== "string" || filename.trim() === "" || filename.length > 255) {
          return response.status(400).json({ error: "x-file-name must contain a filename up to 255 characters." });
        }
        if (!Buffer.isBuffer(request.body) || request.body.length === 0) {
          return response.status(400).json({ error: "Asset upload body must be non-empty binary data." });
        }
        const assetId = randomUUID();
        await assetStore.upload({
          key: `${request.user.id}/${assetId}`,
          body: request.body,
          contentType: request.get("content-type"),
          filename: filename.trim(),
        });
        return response.status(201).json({
          asset_id: assetId,
          download_url: `/api/v1/assets/${assetId}`,
          content_type: request.get("content-type") || "application/octet-stream",
          size_bytes: request.body.length,
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  app.get(
    "/api/v1/assets/:assetId",
    authorization.authenticate,
    requireAssetStore,
    async (request, response, next) => {
      if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(request.params.assetId)) {
        return response.status(400).json({ error: "assetId must be a UUID." });
      }
      try {
        const asset = await assetStore.download({ key: `${request.user.id}/${request.params.assetId}` });
        response.type(asset.contentType);
        response.set("Content-Disposition", `attachment; filename="${asset.filename.replace(/[\\"\r\n]/g, "_")}"`);
        return response.status(200).send(asset.body);
      } catch (error) {
        if (error.code === "ASSET_NOT_FOUND" || error.name === "NoSuchKey" || error.$metadata?.httpStatusCode === 404) {
          return response.status(404).json({ error: "Asset not found." });
        }
        return next(error);
      }
    },
  );

  app.post("/graphql", async (request, response) => {
    const { query, variables, operationName } = request.body || {};
    if (typeof query !== "string" || query.trim() === "") {
      return response.status(400).json({
        errors: [{ message: "GraphQL request body must include a non-empty query." }],
      });
    }

    const result = await graphql({
      schema,
      source: query,
      rootValue,
      variableValues: variables,
      operationName,
    });
    return response.status(result.errors ? 400 : 200).json(result);
  });

  return app;
}

module.exports = { SERVICE_NAME, createApp };
