"use strict";

const jwt = require("jsonwebtoken");

const ROLES = Object.freeze({
  ADMIN: "admin",
  MANAGER: "manager",
  VIEWER: "viewer",
});

const ROLE_VALUES = Object.freeze(Object.values(ROLES));

function unauthorized(message = "A valid access token is required.") {
  const error = new Error(message);
  error.status = 401;
  return error;
}

function forbidden(message = "You do not have permission to perform this action.") {
  const error = new Error(message);
  error.status = 403;
  return error;
}

function readBearerToken(header) {
  if (typeof header !== "string") {
    throw unauthorized();
  }
  const match = /^Bearer\s+(.+)$/i.exec(header.trim());
  if (!match || !match[1]) {
    throw unauthorized();
  }
  return match[1];
}

function createAuthorization({ userStore, accessTokenSecret }) {
  if (!userStore || !accessTokenSecret) {
    throw new Error("Authorization requires a user store and access-token secret.");
  }

  async function authenticate(request, response, next) {
    try {
      const token = readBearerToken(request.get("authorization"));
      const claims = jwt.verify(token, accessTokenSecret, { algorithms: ["HS256"] });
      if (claims.token_type !== "access" || typeof claims.sub !== "string") {
        throw unauthorized();
      }

      const user = await userStore.findById(claims.sub);
      if (!user || !user.isActive || !ROLE_VALUES.includes(user.role)) {
        throw unauthorized();
      }
      request.user = user;
      return next();
    } catch (error) {
      const authError = error.status ? error : unauthorized();
      return next(authError);
    }
  }

  function requireRole(...roles) {
    return (request, response, next) => {
      if (!request.user || !roles.includes(request.user.role)) {
        return next(forbidden());
      }
      return next();
    };
  }

  return { authenticate, requireRole };
}

module.exports = { ROLES, ROLE_VALUES, createAuthorization };
