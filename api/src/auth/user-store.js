"use strict";

const { randomUUID } = require("node:crypto");

function normalizeEmail(email) {
  return email.trim().toLowerCase();
}

function createInMemoryUserStore() {
  const usersByEmail = new Map();

  return {
    async createUser({ email, name, passwordHash }) {
      const normalizedEmail = normalizeEmail(email);
      if (usersByEmail.has(normalizedEmail)) {
        const error = new Error("An account with this email already exists.");
        error.code = "EMAIL_TAKEN";
        throw error;
      }

      const user = {
        id: randomUUID(),
        email: normalizedEmail,
        name,
        passwordHash,
        role: "viewer",
        isActive: true,
        lastLoginAt: null,
      };
      usersByEmail.set(normalizedEmail, user);
      return { ...user };
    },

    async findByEmail(email) {
      const user = usersByEmail.get(normalizeEmail(email));
      return user ? { ...user } : null;
    },

    async recordLogin(userId) {
      for (const user of usersByEmail.values()) {
        if (user.id === userId) {
          user.lastLoginAt = new Date();
          return;
        }
      }
    },
  };
}

function createPostgresUserStore({ databaseUrl }) {
  if (!databaseUrl) {
    throw new Error("databaseUrl is required for the PostgreSQL user store.");
  }

  const { Pool } = require("pg");
  const pool = new Pool({ connectionString: databaseUrl });

  function toUser(row) {
    return row && {
      id: row.id,
      email: row.email,
      name: row.name,
      passwordHash: row.password_hash,
      role: row.role,
      isActive: row.is_active,
      lastLoginAt: row.last_login_at,
    };
  }

  return {
    async createUser({ email, name, passwordHash }) {
      try {
        const result = await pool.query(
          `INSERT INTO users (email, name, password_hash)
           VALUES ($1, $2, $3)
           RETURNING id, email, name, password_hash, role, is_active, last_login_at`,
          [normalizeEmail(email), name, passwordHash],
        );
        return toUser(result.rows[0]);
      } catch (error) {
        if (error.code === "23505") {
          error.code = "EMAIL_TAKEN";
        }
        throw error;
      }
    },

    async findByEmail(email) {
      const result = await pool.query(
        `SELECT id, email, name, password_hash, role, is_active, last_login_at
         FROM users WHERE email = $1`,
        [normalizeEmail(email)],
      );
      return toUser(result.rows[0]);
    },

    async recordLogin(userId) {
      await pool.query("UPDATE users SET last_login_at = NOW() WHERE id = $1", [userId]);
    },

    async close() {
      await pool.end();
    },
  };
}

module.exports = { createInMemoryUserStore, createPostgresUserStore };
