# Demo Vertical Slice

Current hackathon priority: ship a usable commercial-generation product before
expanding the rest of the blueprint.

## Must work now

- User opens `/` and sees the commercial builder, not a generic dashboard.
- User uploads one brand/product image.
- User can select local/API backend routing for text, image, video, and TTS.
- User can generate a draft package:
  - brand palette/product analysis;
  - 10-scene, 30-second script;
  - storyboard;
  - quality gate;
  - social platform package.
- User can request final MP4 rendering and download the assembled commercial.
- Social output is connector-ready: captions, hashtags, aspect ratios, asset
  handoff state, and next step for connected publishing.

## Scaffold now, full implementation later

- Auth/RBAC, projects, queue, analytics, social OAuth, billing, and provider
  management must stay visible as product infrastructure, but they do not need
  full polished screens for the demo.
- Social publishing must not claim external posting until real accounts are
  connected. Use `ready_to_connect` / `draft_ready` states.

## Validation

- `.venv/bin/python -m unittest discover --start-directory tests --pattern 'test_*.py' --verbose`
- `.venv/bin/python scripts/validate_phase_1_gate.py`
- `node .agents/skills/impeccable/scripts/detect.mjs --json app/dashboard/templates/workspace.html`

