"use strict";

const express = require("express");
const { buildSchema, graphql } = require("graphql");
const { createAuthService } = require("./auth/service");
const { createInMemoryUserStore, createPostgresUserStore } = require("./auth/user-store");
const { ROLES, ROLE_VALUES, createAuthorization } = require("./auth/authorization");

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
