# Phase 0.8 — Job Queue (RabbitMQ)

## Requirement

Implement `PHASE-0.8` / `FEAT_JOB_QUEUE`: a RabbitMQ job queue with the
validation gate **"job enqueues"**. This is the active checklist item following
the completed MinIO/S3 storage item. The blueprint identifies MOD-016 as
RabbitMQ orchestration for asynchronous tasks and defines job metadata including
job type, payload, status, priority, and retry fields.

## Files changed

- `api/package.json` and `api/package-lock.json` — add the AMQP client.
- `api/src/queue/job-queue.js` — durable RabbitMQ publisher using publisher
  confirms.
- `api/src/app.js` — authenticated `POST /api/v1/jobs` enqueue endpoint with
  input validation and unavailable-broker handling.
- `api/test/api.test.js` — endpoint contract and validation tests.
- `api/test/job-queue.test.js` — RabbitMQ declaration, persistent delivery,
  and publisher-confirm unit tests.
- `compose.yaml` — local RabbitMQ 4.1 management service and health check.
- `api/README.md` — local configuration and API contract.

## Commands run with results

- `cd api && npm install amqplib@^0.10.9` — passed; dependency installed with
  zero reported vulnerabilities.
- `cd api && npm test` — passed: 14 tests, 0 failures.
- `docker compose up -d rabbitmq` — passed; broker started.
- RabbitMQ health poll using `docker inspect` — passed; container reported
  `healthy`.
- API-to-broker gate script using `RABBITMQ_URL=amqp://canon:canon-development-secret@127.0.0.1:5672`
  — passed. It registered a user, called `POST /api/v1/jobs`, received `202`,
  consumed the same JSON envelope from durable `canon.jobs`, and verified
  persistent delivery mode.
- `git diff --check` — passed; no whitespace errors.

## Known limitations

- This foundation item publishes and confirms jobs. Job workers, retry handling,
  and workflow-specific consumers are deliberately deferred to later pipeline
  work.
- The existing `job_queue` database schema remains the metadata contract; this
  scoped enqueue endpoint does not introduce a second persistence workflow.

builder_status: ready_for_independent_review
