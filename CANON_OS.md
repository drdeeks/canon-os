# Canon OS — Project Foundation

> **This document is the identity of the Creative Studio.**
> The studio *is* Canon OS. This file is the single source of truth for what
> the project is, why it exists, how it functions, and what it requires.
> Infrastructure already established in this directory (chain engine,
> orchestrator, ACK identity system, model-tiering strategy) is retained and
> reused. Anything describing *specific* agents, model bindings, or
> agent→chain assignments is a PLACEHOLDER / EXAMPLE to be wired — see
> `.agent/canon-os-agent-chain-map.example.yaml`.

---

## PART I — Vision

Canon OS is an autonomous content-generation platform that transforms minimal
user input (an image + an optional sentence) into complete, production-ready
campaigns. It handles end-to-end content creation, multi-format adaptation,
and analytics-driven optimization — with zero manual intervention after
initial brand setup.

**Core Capabilities**
- Instant generation: upload image + tagline → finished short-form commercial
- Autonomous pipeline: define brand identity → self-triggering content engine
- Multi-format distribution: vertical / horizontal / square per destination
- Adaptive learning: content evolves from engagement metrics
- Unified control: one surface for all campaigns, assets, and analytics

**Target Users**
- Small businesses without a marketing team
- E-commerce brands needing a consistent content presence
- Agencies managing multiple client campaigns
- Creators scaling video production

**Differentiators**
- Zero manual intervention after brand setup
- Optimization driven by real engagement data
- Cross-format adaptation from a single source asset
- Brand-consistency enforcement across every generated artifact
- Cost-effective vs. traditional agency workflows

---

## PART II — How It Functions

Minimal input flows through a staged generation pipeline. Each stage is a
role, each role produces one artifact, and each artifact is gated before the
next stage unlocks (chain enforcement, already established in this directory).

```
USER INPUT (image + optional sentence)
        │
        ▼
BRAND ANALYSIS        extract colors, style, mood, product type
        │
        ▼
SCRIPT / COPY         generate narration + taglines
        │
        ▼
STORYBOARD            scene breakdown + shot descriptions
        │
        ▼
GENERATION (iterate)  flash-first previews (image / video / audio)
        │
        ▼
IN-PHASE PEER REVIEW  dedicated reviewer verifies the work is functional
        │             (real content/code check — not the creator)
        ▼
GENERATION (final)    quality-tier render of passed shots
        │
        ▼
ASSEMBLY              compose final deliverable
        │
        ▼
OPTIMIZATION          adapt from engagement metrics
        │
        ▼
FINAL HOLISTIC REVIEW wholesome code intact, repo streamlined + organized,
                      "Would this be released?"
```

### Layered Architecture (retained infrastructure)

```
USER LAYER            control surface
   │
API GATEWAY           auth · rate limiting · routing · versioning
   │
SERVICE LAYER         Brand Identity · Content Engine · Orchestration · Analytics
   │
AI / ML LAYER         Video · Image · Audio · Text generation
   │
STORAGE & QUEUE       metadata · cache · asset store · job queue
   │
DISTRIBUTION          format-adapted output targets
```

### Enforcement (established, reused)
- **Chain enforcement (loop-enforced)** — sequential phase dependency; a phase
  is locked until its in-phase review passes, and once locked the chain never
  returns to it. Verification accumulates forward.
- **Two-review mechanism** (Creative Orchestration Doctrine — critique is owned
  by a reviewer, never the creator):
  1. **In-phase peer verification** — runs every phase, immediately after the
     create agent finishes. A *dedicated reviewer agent in the same phase*
     checks that the work is actually implemented, actually functional, and
     correct — not merely present. The loop enforcer gates the phase on this.
  2. **Final holistic review** — runs once at the end. A single reviewer
     (Director) judges the whole repository: wholesome code intact, all
     deliverables proper, structure streamlined and organized. One question:
     "Would this be released?" If not, revise only the weakest component.
- **ACK identity-first** — identity gates every action at t=0
- **Habits / conscience** — "can I do better?" quality questions before any
  task is marked complete
- **Policy boundaries** — mission, constraints, and budgets

---

## PART III — What Is Required

### Technology
- Qwen model family (text / vision) + generative media models (video / image / audio)
- Python, YAML, shell tooling
- Containerized deployment

### Quality Standards
- 80%+ unit-test coverage on core modules
- Zero lint errors
- Validation gates: every declared deliverable must exist and be non-empty
- No destructive operations (`.trash/` instead of delete)
- Secrets management + audit logging

### Cost Optimization (strategy retained)
- Flash-first iteration — cheap previews, quality render only on pass
- Minimal context loading — load only identity + inputs
- Short-clip validation before full render
- Batch processing for similar operations
- Context caching for repeated inputs

### Deliverables
- Working project + source
- Documentation (this foundation, checklist, agent identities, policy)
- Demo video
- Chain-enforced, validated pipeline

---

## PART IV — Agents, Models & Chain (PLACEHOLDERS / EXAMPLES)

> The roles below are Canon OS's *target* functional decomposition, brought in
> as an EXAMPLE. Specific agent definitions, model bindings, and the
> agent→chain assignment still NEED TO BE DONE against this studio's
> established `.agent/` system and chain engine. Do not treat these as final.
> The wiring lives in `.agent/canon-os-agent-chain-map.example.yaml`.

| # | Role (example) | Responsibility (example) |
|---|----------------|--------------------------|
| 1 | Foundation     | project structure, data layer, API |
| 2 | AI Engine      | brand extraction, script + media generation |
| 3 | Content Orchestrator | campaign assembly, scheduling, batch runs |
| 4 | Distribution Integrator | format adaptation + destination delivery |
| 5 | Frontend       | control surface, real-time updates |
| 6 | Data Scientist | analytics, adaptive learning, A/B testing |
| 7 | DevOps         | deployment, monitoring, security |

Model bindings (reasoning / vision / media tiers) and per-role create/revise
assignments are examples only — reconcile against the studio's established
`.agent/model-map.yaml` before wiring.
