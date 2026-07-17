# Independent Review — Phase 00, Step 07: object storage (MinIO/S3)

## Scope and requirement

Reviewed the active chain item `PHASE-0.7 object storage (MinIO/S3)` under
`FEAT_ASSET_STORAGE`; its validation gate is `upload/download`. The
Foundation table in `blueprint.md` labels this same deliverable `PHASE-0.6`,
but the authoritative active-chain/checklist label, supplied evidence, and
this review use Phase 0.7. The requirement is the same: an S3/MinIO asset
store for video, image, and audio assets. The blueprint additionally calls for
S3 versioning.

## Independent inspection

- `compose.yaml` defines a loopback-bound MinIO service with persistent
  `minio-data` storage and an `mc ready local` health check.
- `api/src/storage/asset-store.js` uses the AWS S3 client with the configured
  S3 endpoint and credentials, creates the bucket when needed, and enables
  bucket versioning before storing or reading objects.
- `api/src/app.js` exposes authenticated binary upload and download endpoints.
  It keys each object under the authenticated user's ID and a generated UUID,
  so a known asset ID cannot be read by another user.
- Upload retains content type and filename metadata; download restores both and
  returns the original binary body. The S3 client dependency is locked in
  `api/package-lock.json`.

## Reviewer-run verification

- `cd api && npm test` — passed: 10/10 Node HTTP integration tests. This
  includes authenticated binary upload/download, byte-for-byte payload
  verification, preserved content type/filename, cross-user 404 isolation,
  and malformed/empty upload rejection.
- `docker compose up -d minio` — passed. The actual `minio` container reached
  its declared `healthy` status at `127.0.0.1:9000`.
- Live S3 integration probe — passed against that MinIO instance, using the
  actual Express app configured with `S3_ENDPOINT`, `S3_ACCESS_KEY`, and
  `S3_SECRET_KEY`. An authenticated user uploaded an eight-byte binary payload
  and downloaded the exact bytes (HTTP 200); a second authenticated user
  received HTTP 404 for the same asset ID. A direct AWS S3 SDK probe confirmed
  the uploaded object in `canon-assets` and returned bucket versioning status
  `Enabled`.
- `python3 utilities/skills/enterprise-blueprint/scripts/validate_blueprint.py blueprint.md`
  — passed: 34/34 checks, 0 failed, 0 warned.
- `git diff --check -- compose.yaml api/package.json api/package-lock.json
  api/src/app.js api/src/storage/asset-store.js api/test/api.test.js
  api/README.md` — passed.

## Finding

The runnable API and real MinIO integration demonstrate the required
upload/download gate, including persistent S3-compatible storage behavior,
per-user access isolation, and enabled versioning. The external integration
was exercised locally against the actual MinIO service.

VERDICT: PASS
