# AGENTS.md — Canon OS (Bundle Cold-Start)

> Read this FIRST in any new session touching this bundle. It orients you across
> BOTH the studio and the blueprint. Deep detail lives in the per-component
> AGENTS/README files linked below.

---

## 1. WHAT THIS IS

Canon OS — an autonomous creative studio + marketing platform. One image plus an
optional sentence become a complete, per-platform campaign that self-distributes
and self-optimizes. Generation is local-first but API-adaptable (not strictly
local). This bundle holds two coupled halves:

| Component | Role | Entry doc |
|-----------|------|-----------|
| `ai-creative-studio/` | The running studio: identity stack + creative pipeline | `ai-creative-studio/AGENTS.md` |
| `enterprise-blueprint/` | The one-time source of truth + generated checklists | `enterprise-blueprint/blueprint.md` |

---

## 2. READ ORDER

1. `ai-creative-studio/CANON_OS.md` — project foundation (what/why/how/requirements).
2. `enterprise-blueprint/blueprint.md` — master specification (every module, screen, schema, phase, integrated with the adforge 7-agent / 7-phase chain).
3. `ai-creative-studio/AGENTS.md` — pipeline stages, agent→model map, commands.
4. `ai-creative-studio/creative-loop-ideology.md` — the doctrine behind the two-review mechanism.

---

## 3. THE GOVERNING RULE

The blueprint is the absolute, one-time source of truth. Once it exists you do
NOT keep editing it to drive work — you generate the checklist from it and build
against the checklist, which is loop-enforced and mapped 1:1 to the blueprint.

```bash
cd enterprise-blueprint
python3 enterprise-blueprint/scripts/validate_blueprint.py blueprint.md        # expect 34/34
python3 enterprise-blueprint/scripts/generate_checklist.py blueprint.md        # loop-enforced (the workflow)
```

If scope genuinely changes, amend the blueprint via a Change Log (CL-NNNN) entry
per Part V, then regenerate the checklist — never edit the checklist by hand.

---

## 4. ESTABLISHED MECHANISMS (adforge, integrated)

- **7 agents:** foundation-engineer, ai-engine, content-orchestrator,
  social-integrator, frontend-engineer, data-scientist, devops-engineer.
- **7-phase loop-enforced chain** (`.blueprint-chain/canon-os-blueprint.json`,
  phases 0–6). Locked until prior verified; never re-opened.
- **Two-review mechanism:**
  - *In-phase peer verification* — a dedicated reviewer agent (not the creator)
    checks the work is actually functional/correct. Loop enforcer gates + locks.
  - *Final holistic review* — Director pass: "would this be released?"

---

## 5. THE TWO-REVIEW MECHANISM (how "verification" works here)

- **In-phase peer verification** — runs every phase, right after the create
  agent finishes. A DEDICATED reviewer agent (never the creator) verifies the
  output is actually functional and correct, not merely present. The loop
  enforcer locks the phase on pass; a locked phase is never re-opened.
- **Final holistic review** — one Director pass over the whole repo: "would this
  be released?" — wholesome code intact, structure streamlined and organized.

Every build phase in the blueprint carries a peer-verify deliverable; Phase 6 is
the final holistic review.

---

## 6. HARD RULES

1. NEVER modify `ai-creative-studio/.agent/constitution.yaml` during a run.
2. NEVER skip chain verification — every artifact is verified before completing.
3. NEVER regenerate passing artifacts — only fix what fails review.
4. NEVER hard-delete source — move to `.trash/`.
5. ALWAYS git commit before structural changes. (Commit freely; pushing needs a go-ahead.)
6. Flash-first: cheap drafts for iteration, quality render only on approval.
7. Identity is immutable — defined once, inherited everywhere.
8. Local-first, API-adaptable — never strictly local (MOD-022 backend registry).

---

## 7. CURRENT STATE

- Blueprint validator: 34/34 passed, 0 failed, 0 warned.
- Checklist: 7 phases · 24 modules · 7 screens (loop mode).
- Reference checklist: `enterprise-blueprint/reference/` (plain/unlocked).
- Elevator pitch: `ai-creative-studio/PITCH.md`.
