# AGENTS.md — Canon OS (Creative Studio) Orchestration System
# Read this FIRST in any session working on the creative pipeline
#
# PROJECT IDENTITY: This studio IS Canon OS. See CANON_OS.md for the project
# foundation (purpose, function, requirements, architecture). Agent/model/chain
# specifics that still need wiring are placeholders in
# .agent/canon-os-agent-chain-map.example.yaml.

## System Overview

Canon OS is an autonomous content-generation platform (this Creative Studio),
built on three pillars:

1. **Agent Character Kit (ACK)** — tamper-proof character enforcement, knowledge indexing, memory
2. **Loop Enforcer** — sequential dependency chain enforcement with verification gates
3. **Model Map** — token-optimized Qwen model assignment per agent per phase

## Pipeline Stages (Strict Order)

```
 1. Executive Director  → creative-brief.yaml       (identity — IMMUTABLE)
 2. Narrative Architect → beat-sheet.yaml            (structure)
 3. Screenwriter        → screenplay.yaml            (dialogue + scenes)
 4. Storyboard Artist   → storyboard.yaml            (visual composition)
 5. Cinematographer     → shot-list.yaml             (camera + lighting)
 6. Prompt Composer     → prompt-graph.yaml          (machine prompts)
 7. Generation Engine   → renders/iteration/         (flash model previews)
 8. Quality Reviewer    → evaluation-report.yaml     (scores + pass/fail)
 9. Generation Engine   → renders/final/             (quality model final)
10. Assembly Engine     → assembled/final-video.mp4  (video editing)
11. Director            → director-review.yaml       (holistic review)
12. Director            → published/                 (release)
```

Each stage is LOCKED until the prior stage is VERIFIED and COMPLETE.

## Agent → Model Assignment

| Agent               | Create Model       | Revise Model       | Why                                      |
|---------------------|--------------------|--------------------|------------------------------------------|
| Executive Director  | qwen3-max          | qwen3.5-plus       | Vision synthesis needs max reasoning      |
| Narrative Architect | qwen3.5-plus       | qwen3.5-flash      | Structure planning, fast revisions        |
| Screenwriter        | qwen3.5-plus       | qwen3.5-flash      | Creative writing, fast revisions          |
| Storyboard Artist   | qwen3-vl-flash     | qwen3-vl-flash     | Visual planning with vision model         |
| Cinematographer     | qwen3-vl-flash     | qwen3-vl-flash     | Technical specs, vision understanding     |
| Prompt Composer     | qwen3-max          | qwen3.5-flash      | Precise prompt optimization               |
| Generation Engine   | wan2.6-i2v-flash   | wan2.7-i2v         | Flash for iteration, quality for final    |
| Quality Reviewer    | qwen3-vl-plus      | qwen3-vl-flash     | Visual evaluation needs vision            |
| Director            | qwen3-max          | qwen3.5-flash      | Holistic review needs max reasoning       |
| Assembly Engine     | qwen3.5-flash      | qwen3.5-flash      | Technical assembly, no creativity needed  |

## Video Generation Models (Wan / HappyHorse)

| Use Case           | Iteration Model      | Final Model       | Strategy                                |
|--------------------|----------------------|-------------------|-----------------------------------------|
| Motion preview     | wan2.6-i2v-flash     | —                 | 2-3 sec, 720p, validate motion          |
| Final video shot   | —                    | wan2.7-i2v        | 5-10 sec, 1080p, after preview passes   |
| Establishing shots | wan2.6-t2v           | wan2.7-t2v        | No ref image needed                     |
| Transitions        | wan2.2-kf2v-flash    | —                 | First+last frame interpolation           |
| With audio         | —                    | wan2.7-t2v        | Auto-dubbing for hero shots             |

## Token Reduction Strategies

1. **Flash-first iteration** — 40-60% savings on generation tokens
2. **Retrieve don't remember** — 50-70% savings on input tokens via ACK semantic search
3. **Working memory isolation** — each agent loads only its own inputs
4. **Regenerate only failure** — 70-90% savings on revision tokens
5. **Thinking mode off** — 30-50% savings on output tokens
6. **Short clips first** — 50-70% savings on video generation
7. **Context caching** — 20-30% savings on repeated inputs (Creative Brief)
8. **Batch API** — 50% off for non-realtime bulk generation

## Key Commands

```bash
# Pipeline status
python3 creative-pipeline-chain.py status
python3 orchestrator.py status

# Dispatch an agent
python3 orchestrator.py dispatch <agent-id> [phase]

# Chain enforcement
python3 chain.py check . creative-pipeline <file>
python3 chain.py verify . creative-pipeline <file>
python3 chain.py complete . creative-pipeline <file>

# ACK operations (Agent Character Kit — @drdeeks/character-kit)
aik memory log "message" -t "tag1,tag2"
aik semantic search "query"
aik knowledge add "Name" --type person --facts '{}'

# Enforcer validation (per-tool-call gate)
echo '{"tool_name":"write_file","tool_input":{"path":"artifacts/test.yaml"}}' | \
  aik hook --framework hermes
```

## File Structure

```
ai-creative-studio/
├── .agent/                          # ACK identity system
│   ├── constitution.yaml            # Core identity + hard constraints
│   ├── enforcer.yaml                # Tool allow/deny policies per agent
│   ├── model-map.yaml               # Qwen model assignments + token strategy
│   ├── SOUL.md                      # Agent soul / personality
│   ├── agents/                      # Per-agent identity files
│   │   ├── executive-director.yaml
│   │   ├── narrative-architect.yaml
│   │   ├── screenwriter.yaml
│   │   ├── storyboard-artist.yaml
│   │   ├── cinematographer.yaml
│   │   ├── prompt-composer.yaml
│   │   ├── generation-engine.yaml
│   │   ├── quality-reviewer.yaml
│   │   ├── director.yaml
│   │   └── assembly-engine.yaml
│   ├── habits/                      # ACK enforcement habits
│   │   └── habits.yaml
│   └── logs/                        # Enforcer audit trail
├── artifacts/                       # Pipeline output artifacts (created during execution)
├── corpus/                          # User-supplied reference docs
├── knowledge/                       # ACK knowledge graph
├── memory/                          # ACK three-layer memory
│   ├── daily/
│   └── weekly/
├── creative-pipeline-chain.py       # Chain enforcement entry point
├── orchestrator.py                  # Pipeline orchestration
├── chain.py                         # Loop-enforcer core engine
├── chain_report.py                  # Chain status reporter
├── validate.py                      # Artifact validator
└── creative-loop-ideology.md        # Philosophy document (corpus)
```

## Validation Criteria (Hackathon Track)

The system must demonstrate:
- [x] Autonomous end-to-end short drama creation pipeline
- [x] Scriptwriting and storyboarding agents
- [x] Video generation via Wan / HappyHorse models
- [x] Narrative ability (coherent story with character development)
- [x] Multimodal orchestration (text → visual → video → audio → assembly)
- [x] Token budget optimization (model tiering, flash-first iteration)
- [x] Identity enforcement (ACK constitution gates every action)
- [x] Chain enforcement (loop-enforcer prevents out-of-order execution)
- [x] Quality gating (evaluation loops with revision-only-failure)

## Important Rules

1. NEVER modify constitution.yaml during pipeline execution
2. NEVER skip chain verification — every artifact must be verified before completing
3. NEVER load full project context — use ACK semantic search
4. NEVER use quality models for iteration — flash first, quality final
5. NEVER regenerate passing artifacts — only fix what fails evaluation
6. ALWAYS log to ACK memory after completing a stage
7. ALWAYS check chain state before starting work on a stage
