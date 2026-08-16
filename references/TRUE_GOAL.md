# Canon OS — True Goal (End State)

This document describes the end state Canon OS is built toward. It is derived from
`references/overview.md` and `references/local-3d-model-pipeline.md`, governed by
`.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml`.

## 1. One sentence

A **portable, local-first AI creative & 3D studio** that discovers what a host can do and
adapts its entire capability surface to that host — producing images, video, audio, text, and
3D assets through a review-gated, blended creative↔3D pipeline.

## 2. What it is NOT

- Not a container product. Containers are one of three runtime options.
- Not bound to a specific OS, GPU vendor, or model. Models are registry entries.
- Not an agent-identity / harness artifact. The old ACK (`.agent/`) is retired.
- Not a fixed "compute brain." Capability is probed, not assumed.

## 3. The end-state experience

A user opens Canon OS on *any* machine — a laptop, a workstation, a server, a VM. Within
seconds the host probe classifies the machine. The studio then presents only the capabilities
the host can actually deliver well, and transparently routes the rest to configured remote
providers. The user runs a creative workflow (a 30-second commercial, a thumbnail, a
voiceover, a transcript) and, at any point, promotes assets into 3D — image-to-3D plus
mesh-correction — without leaving the same project, review gate, or storage model.

## 4. The invariant

```
CORE ──> CAPABILITY ──> PROVIDER ──> MODEL ──> RUNTIME ──> HARDWARE
```

Everything is resolved through this spine. Nothing hard-codes a model, a runtime, or a host
assumption.

## 5. Success criteria

- Boots and self-classifies on a bare host with zero external services.
- Runs the full creative pipeline locally when the host permits; degrades gracefully to
  remote only for capabilities it cannot meet.
- Produces valid 3D assets (watertight, textured) via local or remote 3D providers.
- Projects are portable folders; state survives restarts; secrets never committed.
- Conforms to the FOREVER doctrine (POL-001…007) — verifiable via `test_of_forever`.
