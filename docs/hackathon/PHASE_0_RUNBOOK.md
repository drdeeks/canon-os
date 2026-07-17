# Phase 0 Runbook — Submission Foundation

This is the clean-start path for the OpenAI Build Week judge/demo foundation.
It is intentionally provider-free by default: no API keys, paid providers, or
model downloads are required.

## Prerequisites

- Python 3.11+.
- A shell from the repository root.
- Python packages from `app/dashboard/requirements.txt`.

## Provider-free local launch

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r app/dashboard/requirements.txt

export CREATOR_HOME="$PWD/.tmp/hackathon-creator"
export STUDIO_MOUNT="$PWD/.tmp/hackathon-studio"
export STUDIO_CONFIG="$PWD/docs/hackathon/provider-free-backends.json"

python app/dashboard/app.py
```

Open <http://localhost:5000>. The dashboard should load without credentials.

## Smoke checks

Run these in another shell with the same environment if desired:

```bash
curl -fsS http://localhost:5000/api/status
curl -fsS http://localhost:5000/api/models
curl -fsS -X POST http://localhost:5000/api/text/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Launch a small bakery campaign","max_tokens":80}'
```

Expected result:

- `/api/status` reports the selected `demo-*` backends as healthy.
- `/api/models` lists deterministic fixture models.
- Text generation returns a response labeled as a demo fixture.

## Sample input

Use the repository sample brand image:

- Image: `docs/Canon-Brand.PNG`
- Brand name: `Canon OS Coffee`
- Campaign sentence: `Launch a cozy morning subscription for local remote workers.`
- Target platforms: `Instagram Reels`, `TikTok`, `LinkedIn`

No customer data or private asset is required. If a later phase uses generated
or simulated creative output, it must display `Demo fixture`, `sample output`,
or equivalent provenance in the UI and documentation.

## Provider configuration rule

The default judge path is `docs/hackathon/provider-free-backends.json`. It
selects only local deterministic demo adapters. Optional real providers may be
configured later through environment variables or a separate local config file,
but those are not submission prerequisites and must never be committed with
secrets.
