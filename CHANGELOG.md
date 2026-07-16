# Canon OS — CHANGELOG

> This file is the append-only change log. No entry may be modified or deleted.
> All entries must follow the format defined in blueprint.md Part V.

---

## CL-0001 — Establish Canon OS Blueprint & Scope

```yaml
Date        : 2026-07-16
Author      : Canon OS Foundation <foundation@canon-os.local>
Type        : feature
Modules     : MOD-001, MOD-004, MOD-021, MOD-022
Description : Establish Canon OS blueprint from foundation. Add full creative-studio
              scope (image generation, inpainting/photo editing, video, audio, STT,
              music), local-first-but-API-adaptable backend registry, and unify with
              the adforge 7-agent / 7-phase loop-enforced chain and two-review mechanism.
Impact      : High
Testing     : Validator 34/34, checklist generated (loop mode), 7 phases / 24 modules / 7 screens
Rollback    : Revert blueprint.md to prior commit; regenerate checklist from prior blueprint
```

## CL-0002 — Image Studio, Backend Registry & Model Management

```yaml
Date        : 2026-07-16
Author      : Canon OS Foundation <foundation@canon-os.local>
Type        : feature
Modules     : MOD-021, MOD-022, MOD-024
Description : Add Image & Photo Studio (MOD-021), Backend Registry (MOD-022), and
              Model Management (MOD-024) so generation is not strictly local and
              covers paint/photo in addition to the creative campaign pipeline.
Impact      : Medium
Testing     : Validator pass; SPEC-006 / SPEC-007 added; Screen 6.1 / Screen 7.1 added
Rollback    : Disable FEAT_IMAGE_STUDIO / FEAT_BACKEND_REGISTRY flags; revert specs
```

## CL-0003 — Remove Stale Scaffold Artifacts

```yaml
Date        : 2026-07-16
Author      : Canon OS Foundation <foundation@canon-os.local>
Type        : chore
Modules     : N/A
Description : Removed stale hackathon-submission duplicate directory (ai-creative-studio/b/),
              stale tarball, and reset project.json + CHANGELOG.md to Canon OS.
              Re-point project name from the prior hackathon-submission label to "Canon OS".
Impact      : Low
Testing     : validate_blueprint.py 34/34; no leftover hackathon-submission strings remain
Rollback    : Restore from .trash/ if needed
```
