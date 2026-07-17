"use strict";

const express = require("express");
const { buildSchema, graphql } = require("graphql");

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

function createApp() {
  const app = express();
  app.disable("x-powered-by");
  app.use(express.json({ limit: "1mb" }));

  app.get("/health", (_request, response) => {
    response.status(200).json({ status: "ok", service: SERVICE_NAME });
  });

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
