-- Roll back V001__init_schema.sql. Drop dependents before their referenced tables.

DROP TABLE IF EXISTS policy_rules;
DROP TABLE IF EXISTS backups;
DROP TABLE IF EXISTS audit_trail;
DROP TABLE IF EXISTS agent_logs;
DROP TABLE IF EXISTS job_queue;
DROP TABLE IF EXISTS provider_keys;
DROP TABLE IF EXISTS social_auth;
DROP TABLE IF EXISTS analytics_metrics;
DROP TABLE IF EXISTS scheduled_posts;
DROP TABLE IF EXISTS content_assets;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS brands;
DROP TABLE IF EXISTS users;

DROP EXTENSION IF EXISTS pgcrypto;
