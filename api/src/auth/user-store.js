"use strict";

const { randomUUID } = require("node:crypto");

function normalizeEmail(email) {
  return email.trim().toLowerCase();
}

function publicUser(user) {
  return {
    id: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    isActive: user.isActive,
    lastLoginAt: user.lastLoginAt,
  };
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

    async findById(userId) {
      for (const user of usersByEmail.values()) {
        if (user.id === userId) {
          return { ...user };
        }
      }
      return null;
    },

    async listUsers() {
      return [...usersByEmail.values()].map((user) => publicUser(user));
    },

    async updateRole(userId, role) {
      for (const user of usersByEmail.values()) {
        if (user.id === userId) {
          user.role = role;
          return publicUser(user);
        }
      }
      return null;
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

    async findById(userId) {
      const result = await pool.query(
        `SELECT id, email, name, password_hash, role, is_active, last_login_at
         FROM users WHERE id = $1`,
        [userId],
      );
      return toUser(result.rows[0]);
    },

    async listUsers() {
      const result = await pool.query(
        `SELECT id, email, name, role, is_active, last_login_at
         FROM users ORDER BY email`,
      );
      return result.rows.map((row) => publicUser(toUser(row)));
    },

    async updateRole(userId, role) {
      const result = await pool.query(
        `UPDATE users SET role = $1, updated_at = NOW()
         WHERE id = $2
         RETURNING id, email, name, role, is_active, last_login_at`,
        [role, userId],
      );
      return result.rows[0] ? publicUser(toUser(result.rows[0])) : null;
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
