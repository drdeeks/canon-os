# Canon OS — Hackathon Blueprint
## Derived from the Canon OS Master Blueprint
## Version: 1.0-hackathon | Document Class: HACKATHON EXECUTION SPECIFICATION
### Date: 2026-07-16 | Submission target: OpenAI Build Week

> **READ FIRST — Document Authority.** This is a derived, hackathon-specific copy of the
> master specification at `../../blueprint.md`. It narrows delivery scope for
> the July 21, 2026 OpenAI Build Week submission; it does not amend, replace,
> or modify the master blueprint. When the two documents conflict, the master
> remains the product authority and this document governs the hackathon demo.

# PART I: Vision & Hackathon Outcome

> **Rollback Tag:** `[SYS-OVERVIEW-v1]`

## 1.1 Problem and audience

Small businesses and lean marketing teams need a credible, brand-consistent
campaign without an agency workflow, specialist tools, or a manual format pass
for every platform. Canon OS turns a brand image and optional campaign sentence
into a reviewable short-form campaign draft.

## 1.2 Submission outcome

The demonstrated vertical slice must complete this honest, repeatable flow:

1. Upload one brand image and optional campaign sentence.
2. Extract and display an immutable brand profile.
3. Produce a commercial script and storyboard.
4. Generate one draft creative asset through the backend registry.
5. Produce labeled platform variants and captions.
6. Show a campaign calendar and clearly labeled sample analytics insight.

The selected Devpost category is **Work & Productivity**. The demo is a
working product slice, not a claim that all production social integrations,
billing, or autonomous optimization are complete.

## 1.3 Explicit non-goals for the submission

- Live OAuth publishing to social platforms.
- Billing, subscriptions, production RBAC, and multi-tenant provisioning.
- A claim of real engagement learning when only sample analytics are used.
- A requirement to download local models during judging.

## 1.4 Demo success criteria

- The happy path succeeds on a clean checkout using documented setup.
- Every generated or simulated result is labeled truthfully.
- A judge can inspect output, backend choice, and the Codex/GPT-5.6 build log.
- The demo video can reproduce the entire workflow in under three minutes.

## 1.5 Technical approach

Use the existing Flask dashboard and backend registry. Default to a configured
provider where available; otherwise use deterministic demo fixtures so the
workflow remains runnable and never implies a generation that did not occur.
Identity is created once per campaign and inherited by subsequent artifacts.

# PART II: Hackathon Module Registry

> **Rollback Tag:** `[MODULE-REGISTRY-v1]`

| Module ID | Module | Hackathon responsibility | Feature Flag |
|---|---|---|---|
| MOD-001 | Brand Identity Manager | Create and show immutable brand DNA from upload | FEAT_BRAND_IDENTITY |
| MOD-002 | Script Generator | Produce campaign script from brand and brief | FEAT_SCRIPT_GEN |
| MOD-003 | Storyboard Engine | Render a scene-by-scene preview | FEAT_STORYBOARD |
| MOD-004 | Video Renderer | Produce one short creative draft or fixture-backed draft | FEAT_VIDEO_RENDER |
| MOD-008 | Content Calendar | Display scheduled platform-ready campaign items | FEAT_CONTENT_CALENDAR |
| MOD-009 | Platform Adapter | Produce labeled platform formats and captions | FEAT_PLATFORM_ADAPT |
| MOD-011 | Analytics Tracker | Display imported/sample metrics with provenance | FEAT_ANALYTICS |
| MOD-013 | Dashboard UI | Deliver the three-screen judge flow | FEAT_DASHBOARD |
| MOD-018 | Quality Checker | Confirm brand identity fields travel through the flow | FEAT_QUALITY_CHECK |
| MOD-021 | Image & Photo Studio | Support image upload and draft image generation/editing | FEAT_IMAGE_STUDIO |
| MOD-022 | Backend Registry | Show per-modality local/API backend selection | FEAT_BACKEND_REGISTRY |

## 2.1 Dependency order

`MOD-001 → MOD-002/MOD-003 → MOD-004/MOD-021 → MOD-009/MOD-008 → MOD-011`.
The dashboard and backend registry are cross-cutting and must expose this order
without requiring a judge to configure unavailable services.

## 2.2 Feature flags

All displayed hackathon features use the existing `FEAT_*` names. Unavailable
external providers must fail visibly and offer the documented demo fixture path;
they must never silently substitute an unmarked result.

# PART III: Functional Specification

> **Rollback Tag:** `[SPECS-v1]`

## 3.1 Brand Setup screen

Inputs: brand image, brand name, optional campaign sentence, and target
platforms. Outputs: colors, tone, target audience, and a locked brand profile
used throughout the current campaign. A user can start a new profile but cannot
silently mutate an in-progress campaign identity.

## 3.2 Campaign Studio screen

Show the script, storyboard, generation status, source/backend provenance,
draft creative, platform variants, and captions. A failed provider request
must show a recoverable error and retain the inputs. Demo fixtures must carry a
`Demo data` label in the UI and in any exported artifact metadata.

## 3.3 Results screen

Show a campaign calendar plus engagement metrics. Metrics are either imported
from a supported source or identified as sample data. The recommendation must
state the evidence source and must not imply autonomous posting or optimization.

## 3.4 Public interfaces

Existing dashboard endpoints remain the integration surface. The hackathon flow
requires a documented request/response example for generation, a status result
that includes backend provenance, and stable output URLs for the demo.

## 3.5 Accessibility and reliability

The three screens require keyboard-operable controls, visible status/error
messages, image alt text, sufficient contrast, and responsive behavior. The
happy path must be reproducible with sample inputs and without secrets.

# PART IV: Data, Evidence, and Security

> **Rollback Tag:** `[DATA-ARCH-v1]`

## 4.1 Campaign record

Each demo campaign records: input asset reference, immutable brand profile,
brief, selected backend, generated outputs, platform variants, timestamps, and
whether each result is generated, imported, or fixture-backed.

## 4.2 Evidence record

`docs/hackathon/CODEX_BUILD_LOG.md` records dated decisions, relevant commit
hashes, and how Codex and GPT-5.6 contributed. This supports the Devpost
description, demo narration, and required `/feedback` Session ID.

## 4.3 Secrets and privacy

No API key is committed. Provider keys are read from environment/configuration
references only. Sample inputs contain no customer data. Uploaded assets are
kept local to the documented development environment unless the user selects a
provider and accepts that provider's terms.

## 4.4 Resource budget

The submission must remain judge-runnable: avoid model downloads and large
binary dependencies in the default path. Provider and local-generation paths
are optional enhancements, never setup prerequisites.

## 4.5 Minimal contract and migration convention

`POST /api/v1/generate` accepts campaign input and returns a job/status record
with backend provenance. `GET /api/v1/status` returns backend availability. Any
persistent schema change uses a reversible `V{NNN}__description.sql` migration.

```sql
CREATE TABLE hackathon_campaign_evidence (
    campaign_id TEXT PRIMARY KEY,
    provenance TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
```

# PART V: Change Control

> **Rollback Tag:** `[CHANGE-CONTROL-v1]`

## 5.1 Rules

1. Do not change `../../blueprint.md` for hackathon scope.
2. Record each change to this derived blueprint in its change log.
3. Never edit generated checklist or chain state by hand.
4. Regenerate only artifacts that fail validation or no longer match this file.
5. Commit structural changes before the next structural change.
6. Keep every claim in UI, README, demo, and Devpost submission verifiable.

## 5.2 Change log

## CL-0001
Date        : 2026-07-16
Type        : docs
Modules     : MOD-001, MOD-002, MOD-003, MOD-004, MOD-008, MOD-009, MOD-011, MOD-013, MOD-018, MOD-021, MOD-022
Description : Create the derived hackathon scope and evidence requirements.
Impact      : Medium
Testing     : Blueprint validation and generated loop checklist.
Rollback    : Remove the docs/hackathon workspace; master blueprint is unchanged.

## PART VI: Phase Checklist

> **Enforcement.** Generate the checklist and phase validators from this file
> in loop mode. A creator completes a task; an independent reviewer verifies
> its deliverable; only then may the enforcer mark it complete and unlock the
> next phase. Validators test real artifacts and behavior, not file presence.

### PHASE-0: Submission Foundation
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| Repository access | FEAT_DASHBOARD | documented local launch and sample input | clean-start happy path | RB-H0 |
| Repository access | FEAT_QUALITY_CHECK | hackathon standards and Codex build log | docs present and internally consistent | RB-H0 |
| Repository access | FEAT_BACKEND_REGISTRY | provider-free demo configuration | no secret or model download required | RB-H0 |
| Peer verify | FEAT_QUALITY_CHECK | phase-0 review record | independent reviewer confirms runnable foundation | RB-H0 |
> **Rollback Tag:** `[PHASE-0-v1]`

### PHASE-1: Campaign Core
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| PHASE-0 complete | FEAT_BRAND_IDENTITY | immutable brand profile from image and brief | identity displayed and carried forward | RB-H1 |
| PHASE-1.1 | FEAT_SCRIPT_GEN | commercial script | script reflects brief and profile | RB-H1 |
| PHASE-1.2 | FEAT_STORYBOARD | storyboard preview | scenes map to the script | RB-H1 |
| Peer verify | FEAT_QUALITY_CHECK | phase-1 review record | reviewer tests image-to-storyboard flow | RB-H1 |
> **Rollback Tag:** `[PHASE-1-v1]`

### PHASE-2: Creative and Platform Outputs
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| PHASE-1 complete | FEAT_IMAGE_STUDIO | draft creative asset | output/provenance is visible | RB-H2 |
| PHASE-2.1 | FEAT_VIDEO_RENDER | short commercial draft or labeled fixture | output loads and label is truthful | RB-H2 |
| PHASE-2.2 | FEAT_PLATFORM_ADAPT | platform variants and captions | formats are labeled and derived from campaign | RB-H2 |
| Peer verify | FEAT_QUALITY_CHECK | phase-2 review record | reviewer checks assets and failure path | RB-H2 |
> **Rollback Tag:** `[PHASE-2-v1]`

### PHASE-3: Campaign Results and Provenance
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| PHASE-2 complete | FEAT_CONTENT_CALENDAR | campaign calendar | items show platform and schedule | RB-H3 |
| PHASE-3.1 | FEAT_ANALYTICS | metrics and recommendation | imported/sample provenance is explicit | RB-H3 |
| PHASE-3.2 | FEAT_BACKEND_REGISTRY | backend selection/status | selected backend is shown per modality | RB-H3 |
| Peer verify | FEAT_QUALITY_CHECK | phase-3 review record | reviewer confirms no overclaiming | RB-H3 |
> **Rollback Tag:** `[PHASE-3-v1]`

### PHASE-4: Product Quality and Evidence
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| PHASE-3 complete | FEAT_DASHBOARD | responsive accessible three-screen flow | keyboard and narrow viewport smoke test | RB-H4 |
| PHASE-4.1 | FEAT_QUALITY_CHECK | automated and manual test evidence | happy path and failure path pass | RB-H4 |
| PHASE-4.2 | FEAT_QUALITY_CHECK | Codex/GPT-5.6 evidence log | README and log agree | RB-H4 |
| Peer verify | FEAT_QUALITY_CHECK | phase-4 review record | independent reviewer signs off | RB-H4 |
> **Rollback Tag:** `[PHASE-4-v1]`

### PHASE-5: Submission and Director Review
| Prerequisite | Feature Flag | Deliverables | Validation Gate | Rollback |
|---|---|---|---|---|
| PHASE-4 complete | FEAT_DASHBOARD | public three-minute demo video | shows working flow and required narration | RB-H5 |
| PHASE-5.1 | FEAT_QUALITY_CHECK | complete Devpost draft | all required fields and links present | RB-H5 |
| PHASE-5.2 | FEAT_QUALITY_CHECK | release README and runbook | judge can run/test without guessing | RB-H5 |
| Final holistic review | FEAT_QUALITY_CHECK | director review record | release answer is yes | RB-H5 |
> **Rollback Tag:** `[PHASE-5-v1]`

## PART VII: Quality Standards

> **Rollback Tag:** `[QUALITY-v1]`

## 7.1 Required verification

- Unit or route-level checks cover the campaign happy path and provider failure.
- A reviewer distinct from the implementer executes each phase gate.
- The final run starts from documented setup and uses the supplied sample input.
- The interface is reviewed with Impeccable after core behavior is working.

## 7.2 Performance and usability

The demo must provide progress feedback, preserve input on error, load the
dashboard with a p95 page response under two seconds on a standard laptop, and
avoid blocking on optional model downloads. A fallback may be used only when
labeled and documented. New core-flow tests maintain at least 80% coverage for
the touched route/service module and exercise one retry or circuit breaker path
for an unavailable provider.

## 7.3 Release decision

Release only when the product behavior, README, Devpost description, video,
and evidence log make the same truthful claims. A broken or hidden integration
is not a completed capability.
