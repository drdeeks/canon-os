"use strict";

const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");

const PASSWORD_MIN_LENGTH = 12;

function validationError(message) {
  const error = new Error(message);
  error.status = 400;
  return error;
}

function validateRegistration({ email, password, name }) {
  if (typeof email !== "string" || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    throw validationError("A valid email is required.");
  }
  if (typeof name !== "string" || name.trim().length === 0 || name.trim().length > 255) {
    throw validationError("A name between 1 and 255 characters is required.");
  }
  if (typeof password !== "string" || password.length < PASSWORD_MIN_LENGTH) {
    throw validationError(`Password must be at least ${PASSWORD_MIN_LENGTH} characters.`);
  }
}

function validateLogin({ email, password }) {
  if (typeof email !== "string" || typeof password !== "string" || !email.trim() || !password) {
    throw validationError("Email and password are required.");
  }
}

function createAuthService({ userStore, accessTokenSecret, refreshTokenSecret }) {
  if (!userStore || !accessTokenSecret || !refreshTokenSecret) {
    throw new Error("Auth service requires a user store and JWT secrets.");
  }

  function issueTokens(user) {
    const claims = { sub: user.id, email: user.email, role: user.role };
    return {
      access_token: jwt.sign({ ...claims, token_type: "access" }, accessTokenSecret, {
        algorithm: "HS256",
        expiresIn: "15m",
      }),
      refresh_token: jwt.sign({ ...claims, token_type: "refresh" }, refreshTokenSecret, {
        algorithm: "HS256",
        expiresIn: "7d",
      }),
    };
  }

  return {
    async register(input) {
      validateRegistration(input);
      const user = await userStore.createUser({
        email: input.email,
        name: input.name.trim(),
        passwordHash: await bcrypt.hash(input.password, 12),
      });
      return { user_id: user.id, ...issueTokens(user) };
    },

    async login(input) {
      validateLogin(input);
      const user = await userStore.findByEmail(input.email);
      const passwordMatches = user && user.isActive && await bcrypt.compare(input.password, user.passwordHash);
      if (!passwordMatches) {
        const error = new Error("Invalid email or password.");
        error.status = 401;
        throw error;
      }
      await userStore.recordLogin(user.id);
      return issueTokens(user);
    },
  };
}

module.exports = { PASSWORD_MIN_LENGTH, createAuthService };
