# Phase 0.7 — Object storage (MinIO/S3)

## Requirement

The active chain item is `PHASE-0.7`: deliver **object storage (MinIO/S3)**
under `FEAT_ASSET_STORAGE`. Its validation gate is **upload/download**. The
blueprint also identifies S3/MinIO as the store for video, image, and audio
assets, requires S3 versioning in the backup strategy, and defines S3/MinIO
presigned URLs as downstream media outputs.

## Files changed

- `compose.yaml` — local, loopback-bound MinIO service with a persistent volume
  and health check.
- `api/package.json` and `api/package-lock.json` — AWS SDK S3 client.
- `api/src/storage/asset-store.js` — S3-compatible MinIO/AWS adapter, bucket
  creation, bucket versioning, and an in-memory test double.
- `api/src/app.js` — authenticated binary upload and download routes with
  tenant-prefixed object keys.
- `api/test/api.test.js` — upload/download, isolation, and invalid-upload
  coverage.
- `api/README.md` — local configuration and endpoint contract.

## Commands run with results

- `cd api && npm install @aws-sdk/client-s3@^3.0.0` — passed.
- `cd api && npm test` — passed: 10 tests, including asset upload/download and
  cross-user isolation.
- `docker compose up -d minio` — passed; MinIO healthy at loopback port 9000.
- Authenticated Express API + real MinIO binary upload/download script — passed.
- `python3 utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: 34/34 checks, 0 failed, 0 warned.
- `git diff --check` — passed.

## Known limitations

- The local compose credentials are development defaults and must be overridden
  outside local development.
- S3 configuration is intentionally opt-in (`S3_ENDPOINT`, `S3_ACCESS_KEY`,
  `S3_SECRET_KEY`); without it the API reports asset storage as unavailable
  instead of persisting locally.
- Presigned URL generation and durable asset metadata belong to their consuming
  media modules; this active item provides the required authenticated
  upload/download storage boundary.

builder_status: ready_for_independent_review
