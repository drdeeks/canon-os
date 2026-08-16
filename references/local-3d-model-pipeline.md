CLIENT FACING REQUIREMENT

Before I begin development, I need access to the computer that will serve as the primary compute environment for this project.

This does not mean I need to turn your computer into my development workstation or permanently install the entire development environment onto it. The development environment, source code, models, configurations, project data and working artifacts will be maintained through a persistent external environment.

I need access to your computer because the system is specifically being engineered to take advantage of its actual hardware capabilities. I need to characterize the machine, establish the required host-level compute bridge, install the minimum native dependencies required for hardware access, benchmark the available workloads, integrate the appropriate models, and continuously validate the system against the real environment.

The goal is not simply to make something that technically runs. The goal is to determine what this hardware can actually accomplish and build the orchestration system around those capabilities, while keeping the architecture adaptable enough to use other machines or compute workers when they provide capabilities the primary system does not.

Because this is a multi-model 3D production system involving generation, vision, geometry processing, materials, Blender automation, quality control, export validation, persistent artifacts, routing and iterative refinement, the amount of engineering involved is substantial. The computer therefore needs to be available throughout development for testing, benchmarking, troubleshooting and optimization.

I am not charging you for this development. However, if I am going to undertake it seriously, I need the ability to actually develop and validate against the hardware the system is intended to use. Without that access, I would be designing against assumptions rather than engineering against reality.

If you’re serious about having the most capable and optimized system this hardware can provide, access to the compute environment needs to be established before development begins.


==========


LOCAL 3D STUDIO

Definitive Operational Specification for a Local-First, Multi-Model 3D Generation System

Version: 1.0
Date: 2026-08-15
Primary host: Apple Silicon MacBook Pro, M4 Max
Design principle: Creative Orchestration Doctrine applied to 3D asset production

────────

0. Executive Definition

This specification defines a local-first 3D generation studio that accepts natural-language requests, images, sketches, existing meshes, and structured asset briefs, then produces validated 3D assets in a user-selected format and quality tier.

The system is deliberately not a single-model text-to-3D application. It is a software organization composed of:

• a persistent project identity layer;
• multiple local LLM specialists running primarily through llama.cpp;
• specialized 3D generation models;
• image and vision models;
• geometry and topology processors;
• material and texture generation;
• Blender-based deterministic production;
• automated QA and visual critique;
• an artifact and revision store;
• a silent iterative loop;
• a scheduler that can use the M4 Max locally and optionally dispatch Linux/CUDA-only stages to another machine.

The M4 Max is the control plane and a capable local production node. It is not treated as a magic substitute for an NVIDIA CUDA workstation. Models whose published requirements are Linux + NVIDIA CUDA are explicitly classified as remote-worker candidates rather than falsely labeled as native Mac components.

────────

1. Design Doctrine

The architecture directly inherits the Creative Orchestration Doctrine:

1. Identity is immutable.
2. Responsibility is singular. One agent, one production question.
3. Every important decision produces an artifact.
4. Generation is iterative. Generate → evaluate → critique → revise → repeat.
5. Every creation stage has a reviewer.
6. Context is retrieved, not stuffed into every prompt.
7. Regenerate only the failed component.
8. Decision authority is hierarchical.
9. The machine keeps operational complexity out of the user’s face.
10. The final artifact is a verified production result, not merely a generated file.

The original doctrine explicitly separates identity, specialization, artifacts, evaluation, retrieval, and selective regeneration. This 3D system implements those same concepts for geometry, materials, topology, and export. fileciteturn0file0L34-L40 fileciteturn0file0L70-L110 fileciteturn0file0L114-L144 fileciteturn0file0L148-L190 fileciteturn0file0L194-L234

────────

2. Platform Reality: M4 Max

2.1 What the M4 Max is good at

Apple’s M4 Max MacBook Pro can be configured with up to 128 GB unified memory. citeturn530305search10

The Apple Silicon memory architecture is especially valuable for a local studio because CPU-side orchestration, GPU-side inference, image processing, Blender, and large artifact caches can share the same unified memory pool.

llama.cpp has native Metal support on macOS, and its current backend explicitly recognizes M4 and M4 Max devices. citeturn186714search0turn186714search8

Apple also provides an MPS backend for PyTorch on Apple Silicon, so selected neural workloads can use the GPU rather than falling back entirely to CPU. citeturn186714search6

2.2 What the M4 Max is not

The M4 Max is not an NVIDIA CUDA GPU.

That matters because some high-end 3D projects are still published as Linux/CUDA stacks. For example, Microsoft TRELLIS.2 currently documents Linux + NVIDIA GPU requirements with at least 24 GB VRAM and CUDA 12.4 in its primary tested configuration. citeturn333016search0

Hunyuan3D-2.1 publishes macOS support, but its tested environment is CUDA-based and some components include GPU-specific dependencies. The project reports roughly 10 GB VRAM for shape generation, 21 GB for texture generation, and 29 GB combined, while its requirements include cupy-cuda12x. citeturn333016search10turn333016search1

Therefore the architecture uses three capability classes:

A. Native Mac

Runs directly on macOS/MPS/Metal and is considered production-capable on the M4 Max after local validation.

B. Mac Experimental

The project claims macOS support or can technically run on Apple Silicon, but important kernels, rasterizers, or performance characteristics may not be fully validated for MPS/Metal.

C. Linux/NVIDIA Worker

Requires CUDA, Linux-specific libraries, or NVIDIA kernels. The M4 Max orchestrates the job but a separate worker performs the actual inference.

This classification is mandatory. No component may advertise itself as “local on Mac” unless it passes the platform capability probe.

────────

3. Ventoy + External Storage Architecture

3.1 Correct use of Ventoy on Apple Silicon

Ventoy is useful here as a portable system and persistence carrier, but it should not be treated as a way to boot a completely independent Linux installation directly from USB on an Apple Silicon Mac.

Asahi Linux documents that Apple Silicon cannot boot an OS purely from USB storage. The boot chain uses the internal NVMe storage and boot policy; external storage can be used after the system’s boot process has been established, but it is not a simple PC-style “boot Linux ISO from USB” path. citeturn333016search6turn333016search8

Ventoy’s persistence plugin is still useful. Ventoy can keep persistence data alongside ISO files, allowing changes to survive reboots for supported Linux distributions. citeturn333016search4

3.2 Recommended storage model

Use a high-speed external USB4/Thunderbolt NVMe enclosure, not a cheap USB flash drive.

Recommended physical layout:

```text
External NVMe SSD
│
├── VENTOY
│   ├── ubuntu.iso
│   ├── fedora.iso
│   ├── rescue.iso
│   └── ventoy.json
│
├── DATA  (exFAT or APFS, Mac-accessible)
│   ├── projects/
│   ├── imports/
│   ├── exports/
│   ├── references/
│   ├── renders/
│   └── manifests/
│
└── LINUX-DATA / WORKER STORAGE
    ├── model_cache/
    ├── hf_cache/
    ├── pip_cache/
    ├── docker/
    └── worker_projects/
```

Important filesystem rule

Do not rely on a shared exchange filesystem for every Linux-native package environment. Model repositories often use symlinks, file permissions, sockets, or Linux-specific semantics.

Use:

• Mac-accessible DATA: exFAT/APFS where needed for exchange.
• Linux-native WORKER storage: ext4 or the worker’s native filesystem.
• Versioned artifacts: replicated/synchronized between the two through the orchestrator.

This prevents the classic “it exists on the USB but Python cannot execute it” failure.

────────

4. Overall System Architecture

```text
                               USER
                                 │
                   text / image / sketch / mesh
                                 │
                                 ▼
                     ┌─────────────────────┐
                     │  CHAT / CONTROL UI  │
                     └──────────┬──────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │    PROJECT IDENTITY     │
                    │ immutable creative spec │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │      ORCHESTRATOR      │
                    │ policy + DAG + queue   │
                    └────────────┬───────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       LOCAL LLM POOL      VISION / IMAGE      CAPABILITY
       llama.cpp/Metal       MPS/Metal          ROUTER
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 ▼
                       ASSET SPECIFICATION
                                 │
                                 ▼
                     GENERATION PLAN / DAG
                                 │
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
       Native Mac 3D       Experimental Mac      Remote CUDA
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 ▼
                          CANDIDATE POOL
                                 │
                                 ▼
                          GEOMETRY QA
                                 │
                                 ▼
                        MATERIAL / TEXTURE
                                 │
                                 ▼
                         TOPOLOGY / UV QA
                                 │
                                 ▼
                           LOD / EXPORT
                                 │
                                 ▼
                        FINAL REVIEW / HASH
                                 │
                                 ▼
                         VERIFIED ARTIFACT
```

────────

5. Responsibilities

Every specialist has exactly one production responsibility.

|Specialist        |Question                                             |Typical output              |
|------------------|-----------------------------------------------------|----------------------------|
|Executive Director|What are we making?                                  |`creative_brief.json`       |
|Asset Architect   |What must the asset contain?                         |`asset_spec.json`           |
|Visual Analyst    |What is visible in the references?                   |`reference_analysis.json`   |
|Prompt Composer   |How should this intent be expressed to the generator?|`generation_prompt.json`    |
|Model Router      |Which generator should run?                          |`generation_plan.json`      |
|Geometry Generator|Can this form be generated?                          |candidate mesh              |
|Geometry Critic   |Is the geometry structurally acceptable?             |`geometry_eval.json`        |
|Material Director |What material language should be applied?            |`material_spec.json`        |
|Texture Generator |Can the surface appearance be produced?              |PBR texture set             |
|Topology Engineer |Is the mesh usable?                                  |repaired/remeshed mesh      |
|Blender Operator  |How is the production asset assembled?               |`.blend` + rendered artifact|
|Export Engineer   |Can the chosen format faithfully represent it?       |final export                |
|Quality Director  |Is it good enough?                                   |`final_review.json`         |
|Pipeline Guardian |Did the workflow remain healthy?                     |run telemetry               |

The generator has no creative authority. It executes a specification. This mirrors the source doctrine’s distinction between planning, prompting, generation, and evaluation. fileciteturn0file0L238-L282 fileciteturn0file0L338-L365

────────

6. LLM Stack

6.1 Primary orchestration model

Recommended baseline: Qwen3 32B GGUF

Qwen publishes official GGUF variants and documents direct use through llama.cpp and llama-server. citeturn378443search3turn378443search0

Use this model for:

• project interpretation;
• asset architecture;
• prompt compilation;
• policy evaluation;
• critique;
• workflow decisions;
• structured JSON generation.

On an M4 Max with 64–128 GB unified memory, a quantized Qwen3-class model is a practical local orchestration model. Do not run every specialist concurrently at maximum context size; the scheduler should load only the model needed for the current stage.

6.2 Coding / Blender automation model

Qwen3-Coder-Next GGUF

Qwen publishes GGUF builds usable with llama.cpp on macOS and Linux. citeturn378443search2turn378443search7

Use only for:

• Blender Python;
• repair scripts;
• conversion adapters;
• pipeline code;
• unit tests;
• debugging tool errors.

Do not let the coding model rewrite project identity or creative policy.

6.3 Vision model

A llama.cpp multimodal model can be used for local image inspection. llama.cpp currently exposes multimodal image input through libmtmd, including its server API. citeturn378443search4

A practical baseline is Gemma 3 12B or 27B with a multimodal projector, both documented by llama.cpp. This stage should remain replaceable because vision capability is a fast-moving target. citeturn378443search1

Vision responsibilities

• reference decomposition;
• silhouette comparison;
• color/material comparison;
• defect detection;
• visual QA;
• before/after review.

The vision model is a reviewer, not the final source of truth.

────────

7. 3D Model Stack

7.1 Tier 1: native / practical on M4 Max

Stable Fast 3D

Stable Fast 3D is a single-image mesh reconstruction system and its official project explicitly supports CUDA or MPS availability. It produces textured meshes, UVs, predicted material parameters, and remeshing options. citeturn333016search7

Use for:

• rapid image-to-3D drafts;
• low-cost candidate generation;
• interactive iteration;
• baseline assets;
• fallback when heavier models are unavailable.

7.2 Tier 2: experimental Mac

Hunyuan3D-2.1

Hunyuan3D-2.1 provides a separate 3D shape model and PBR texture model. The project lists macOS support but its tested dependency stack is CUDA-oriented. citeturn333016search10turn333016search1

Use the M4 Max implementation only after a platform-specific probe validates:

• model load;
• attention kernels;
• custom rasterizer;
• memory use;
• texture generation;
• final export.

If any stage fails, automatically route the same generation contract to a Linux/NVIDIA worker.

7.3 Tier 3: high-end Linux/NVIDIA

TRELLIS.2

TRELLIS.2 is a high-fidelity 3D generator. Its published prerequisites currently call for Linux and an NVIDIA GPU with at least 24 GB VRAM, with CUDA 12.4 used in its documented setup. citeturn333016search0

Therefore:

• control plane: M4 Max;
• generation worker: Linux + NVIDIA;
• artifacts: shared project store;
• user experience: still one chat interface.

The user must not care which worker executed the job unless they ask.

────────

8. Model Selection Matrix

|Stage              |Primary                   |Alternate                |M4 Max         |NVIDIA worker|
|-------------------|--------------------------|-------------------------|---------------|-------------|
|Orchestration      |Qwen3 32B GGUF            |Qwen3 30B-A3B            |Yes            |Yes          |
|Coding             |Qwen3-Coder-Next          |another code GGUF        |Yes            |Yes          |
|Vision             |Gemma 3 12B/27B           |another supported VLM    |Yes            |Yes          |
|Fast image→3D      |Stable Fast 3D            |TripoSR-derived tools    |Yes / MPS      |Yes          |
|Main image→3D      |Hunyuan3D-2.1             |TRELLIS family           |Experimental   |Yes          |
|High-end image→3D  |TRELLIS.2                 |future 3D models         |No             |Yes          |
|Concept images     |local diffusion stack     |alternate diffusion model|MPS-dependent  |Yes          |
|Texture enhancement|local upscaler / PBR tools|worker-side image model  |Yes / selective|Yes          |
|Mesh cleanup       |MeshLab / Open3D / Blender|custom Python            |Yes            |Yes          |
|Final assembly     |Blender                   |Blender headless         |Yes            |Yes          |

The router selects by capability, quality target, current machine availability, and historical success rate.

────────

9. Quality Ladder

The user chooses one of these profiles, or overrides individual dimensions.

PROFILE: DRAFT

Purpose: speed.

• simple geometry;
• modest polygon count;
• 512–1K textures;
• minimal refinement;
• one generation pass before returning for human review.

PROFILE: LOW_POLY

Purpose: optimized games/mobile/web.

Suggested defaults:

• 5K–50K triangles;
• 1K–2K textures;
• reduced material count;
• baked normals;
• LOD 0–2;
• collision mesh available.

PROFILE: GAME_READY

Purpose: Unity/Unreal/Godot.

Suggested defaults:

• 50K–300K triangles;
• 2K–4K textures;
• clean UVs;
• PBR maps;
• optional rig;
• LOD chain;
• collision proxy.

PROFILE: HIGH

Purpose: general production.

Suggested defaults:

• 300K–2M+ triangles;
• 4K textures;
• higher surface detail;
• more rigorous QA.

PROFILE: CINEMATIC

Purpose: close-up rendering.

Suggested defaults:

• 2M–10M+ triangles;
• 4K–8K texture sets;
• displacement/normal detail;
• UDIM-ready UVs where practical;
• stronger geometric review;
• multiple material groups.

PROFILE: ULTIMATE

Purpose: maximum local/worker capability.

• generator chosen dynamically;
• highest feasible geometry;
• 8K texture sets or UDIMs;
• microdetail where useful;
• displacement;
• separate material maps;
• aggressive iterative critique;
• multiple candidates before selection;
• final archive includes all production artifacts.

Important

“8K” is a texture-resolution target, not a synonym for geometric quality.

The system therefore exposes these independently:

```text
geometry_detail       0–100
texture_resolution    512 / 1K / 2K / 4K / 8K
material_complexity   0–100
surface_microdetail   0–100
topology_quality      0–100
poly_budget           explicit
rig_complexity        none / basic / advanced
lod_count             integer
```

────────

10. User-Facing Chat Contract

The user should be able to say:

> Create a lifelike female cyberpunk bounty hunter from this image. Ultimate quality. 8K textures. Keep the face extremely accurate. Make the clothing extremely detailed. Give me FBX and GLB.

The system turns that into:

```json
{
  "asset_type": "character",
  "reference_mode": "image",
  "quality_profile": "ultimate",
  "geometry_detail": 95,
  "texture_resolution": 8192,
  "material_complexity": 90,
  "surface_microdetail": 95,
  "identity_fidelity": 100,
  "topology_quality": 95,
  "outputs": ["fbx", "glb"],
  "rig": "basic"
}
```

The user can then say:

> Make the body 20% simpler, but don’t touch the face or clothes.

The orchestrator changes only:

```json
{
  "geometry.body.detail": "-20%",
  "preserve": ["face", "clothing"]
}
```

No project-wide regeneration occurs.

────────

11. Customization Controls

The chat interface should expose optional controls as sliders or presets.

Geometry

• polygon budget;
• silhouette fidelity;
• anatomical precision;
• topology cleanliness;
• subdivision amount;
• symmetry;
• sharpness;
• deformation readiness.

Materials

• realism;
• roughness complexity;
• metallic behavior;
• subsurface scattering;
• translucency;
• weathering;
• dirt;
• wear;
• micro-surface detail.

Textures

• resolution;
• UV density;
• texture count;
• UDIM mode;
• normal detail;
• displacement;
• baked AO;
• emission.

Performance

• target triangle count;
• texture budget;
• number of LODs;
• mobile optimization;
• draw-call target;
• material count.

Fidelity

• reference identity;
• silhouette fidelity;
• face fidelity;
• clothing fidelity;
• prop fidelity;
• pose fidelity;
• color fidelity.

────────

12. Project Specification Artifact

Every generation begins by producing an immutable request contract.

Example:

```json
{
  "project_id": "proj_20260815_001",
  "asset_id": "asset_bounty_hunter_001",
  "identity_version": "1.0.0",
  "input": {
    "type": "image",
    "source": "imports/reference_001.png"
  },
  "quality": {
    "profile": "cinematic",
    "geometry_detail": 90,
    "texture_resolution": 8192,
    "material_complexity": 85,
    "microdetail": 95
  },
  "geometry": {
    "target_triangles": 5000000,
    "topology": "production",
    "lods": [1, 0.5, 0.15]
  },
  "outputs": ["glb", "fbx", "blend"],
  "preserve": [
    "face_identity",
    "silhouette",
    "clothing_design"
  ]
}
```

This artifact becomes the authoritative contract for the run.

────────

13. Generation DAG

Generation is a directed acyclic graph rather than a rigid linear script.

```text
INPUT
  │
  ├── reference analysis
  ├── style analysis
  └── asset classification
          │
          ▼
     ASSET SPEC
          │
          ▼
    MODEL ROUTER
       ┌──┼──┐
       │  │  │
       ▼  ▼  ▼
     SF3D HY21 TRELLIS
       │  │  │
       └──┼──┘
          ▼
    CANDIDATE POOL
          │
          ▼
    GEOMETRY CRITIC
       ┌──┴──┐
       │     │
     FAIL   PASS
       │     │
       ▼     ▼
    REVISE   MATERIAL
                │
                ▼
             UV/QA
                │
                ▼
             REMESH
                │
                ▼
            LOD BUILD
                │
                ▼
            EXPORT QA
                │
                ▼
             PUBLISH
```

A failed texture does not trigger mesh regeneration. A failed topology check does not trigger image-generation again. Each failure maps to a component owner.

────────

14. Silent Creative Loop

The user’s visible state should stay simple:

```text
Analyzing reference…
Generating geometry…
Refining materials…
Validating asset…
Preparing exports…
Done.
```

The internal state is substantially richer:

```text
ANALYZE
  ↓
SPECIFY
  ↓
PLAN
  ↓
GENERATE CANDIDATES
  ↓
MEASURE
  ↓
VISUAL CRITIQUE
  ↓
CLASSIFY FAILURE
  ↓
TARGETED REVISION
  ↓
REMEASURE
  ↓
ASSEMBLE
  ↓
FINAL QA
  ↓
EXPORT
  ↓
HASH
  ↓
ARCHIVE
```

The system is allowed to iterate without narrating every internal thought.

This directly implements the doctrine’s requirement that generation is iterative and that only the failing component should be regenerated. fileciteturn0file0L148-L164 fileciteturn0file0L224-L234

────────

15. Evaluation System

15.1 Deterministic checks

The following should be measured programmatically:

• vertex count;
• triangle count;
• connected components;
• non-manifold edges;
• degenerate faces;
• inverted normals;
• UV overlap;
• UV coverage;
• texture dimensions;
• missing material references;
• invalid file references;
• object scale;
• bounding box;
• transform state;
• export loadability.

15.2 Vision checks

A local vision model compares render snapshots against the reference:

• silhouette;
• proportions;
• face structure;
• clothing;
• color palette;
• major markings;
• visible artifacts;
• lighting response.

15.3 LLM review

The critic outputs structured data:

```json
{
  "status": "FAIL",
  "scores": {
    "identity": 0.97,
    "geometry": 0.91,
    "materials": 0.88,
    "topology": 0.62,
    "presentation": 0.94
  },
  "failure": "topology",
  "action": "remesh_only"
}
```

This is a critical architecture rule:

> The LLM recommends the correction. Deterministic tools perform the correction whenever a deterministic tool exists.

────────

16. Blender Production Layer

Blender is the assembly engine and deterministic export authority.

The coding model writes a script rather than manually manipulating a GUI.

Example production script responsibilities:

```python
load_candidate()
repair_mesh()
apply_scale()
recalculate_normals()
unwrap_uvs()
create_materials()
assign_pbr_textures()
bake_required_maps()
create_lods()
create_collision_mesh()
set_origin_and_units()
validate_scene()
export_requested_formats()
```

The script itself becomes an artifact:

```text
artifacts/
  blender/
    build_asset.py
    validate_asset.py
    export_asset.py
```

This makes every build reproducible.

────────

17. Export System

The system should support at minimum:

• GLB;
• GLTF;
• FBX;
• OBJ + MTL;
• STL;
• USDZ;
• 3MF;
• BLEND.

Meshy’s current export documentation confirms the same broad family of practical targets and identifies GLB for web/real-time, FBX for game engines, USDZ for Apple AR, STL/3MF for printing, and BLEND for continued Blender editing. citeturn530305search1turn530305search0

Output selection rule

The user may select one, several, or AUTO.

Example:

```text
Output: AUTO
Destination: game engine
```

The system selects:

```text
FBX + GLB
```

Example:

```text
Output: 3D print
```

The system selects:

```text
STL
```

or

```text
3MF
```

when color/material information is relevant.

Example:

```text
Output: Apple AR
```

The system selects:

```text
USDZ + GLB
```

────────

18. Format Preservation Rules

Never perform a casual conversion as the final operation.

The export path is:

```text
MASTER ASSET
   ↓
FORMAT ADAPTER
   ↓
EXPORT
   ↓
RELOAD EXPORTED FILE
   ↓
VALIDATE
   ↓
HASH
   ↓
DELIVER
```

For every final format the system should create:

```text
exports/
  model.glb
  model.glb.sha256
  model.fbx
  model.fbx.sha256
  model.obj
  model.mtl
  textures/
  model.obj.sha256
```

This is what keeps a format conversion from quietly destroying the artifact.

────────

19. Full Project Tree

```text
local-3d-studio/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── package.json
├── Makefile
├── .env.example
│
├── apps/
│   ├── chat-ui/
│   ├── asset-viewer/
│   └── admin-console/
│
├── orchestrator/
│   ├── main.py
│   ├── scheduler.py
│   ├── dag.py
│   ├── router.py
│   ├── policy.py
│   ├── capability_probe.py
│   ├── queue.py
│   ├── retries.py
│   ├── artifact_registry.py
│   └── worker_client.py
│
├── agents/
│   ├── executive_director/
│   ├── asset_architect/
│   ├── visual_analyst/
│   ├── prompt_composer/
│   ├── geometry_critic/
│   ├── material_director/
│   ├── topology_engineer/
│   ├── export_engineer/
│   ├── quality_director/
│   ├── blender_operator/
│   └── pipeline_guardian/
│
├── models/
│   ├── registry.yaml
│   ├── llm/
│   ├── vision/
│   ├── image/
│   ├── mesh/
│   ├── texture/
│   └── upscalers/
│
├── adapters/
│   ├── llama_cpp/
│   ├── stable_fast_3d/
│   ├── hunyuan3d/
│   ├── trellis2/
│   ├── blender/
│   ├── meshlab/
│   └── open3d/
│
├── policies/
│   ├── quality_profiles.yaml
│   ├── routing_policy.yaml
│   ├── failure_policy.yaml
│   ├── export_policy.yaml
│   └── safety_policy.yaml
│
├── memory/
│   ├── immutable/
│   │   ├── identity.json
│   │   ├── style.json
│   │   ├── visual_language.json
│   │   └── quality_philosophy.json
│   ├── project/
│   │   ├── assets/
│   │   ├── references/
│   │   ├── prompts/
│   │   ├── evaluations/
│   │   └── revisions/
│   └── working/
│
├── projects/
│   └── <project-id>/
│       ├── identity/
│       ├── briefs/
│       ├── assets/
│       ├── candidates/
│       ├── evaluations/
│       ├── revisions/
│       ├── renders/
│       ├── exports/
│       └── manifests/
│
├── workers/
│   ├── local-mac/
│   └── linux-cuda/
│       ├── docker/
│       ├── launch.sh
│       └── worker_api.py
│
├── scripts/
│   ├── bootstrap_mac.sh
│   ├── bootstrap_linux.sh
│   ├── install_models.py
│   ├── probe_capabilities.py
│   ├── validate_project.py
│   └── recover_run.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── model-contracts/
│   └── export-validation/
│
└── runtime/
    ├── cache/
    ├── logs/
    ├── jobs/
    ├── locks/
    └── telemetry/
```

────────

20. Model Registry

The registry must be declarative.

Example:

```yaml
models:
  qwen3_32b:
    role: orchestration
    backend: llama_cpp
    platform: [mac, linux]
    modality: text

  qwen3_coder_next:
    role: coding
    backend: llama_cpp
    platform: [mac, linux]
    modality: text

  gemma3_27b_vision:
    role: vision
    backend: llama_cpp
    platform: [mac, linux]
    modality: image_text

  stable_fast_3d:
    role: image_to_3d
    platform: [mac, linux]
    accelerator: [mps, cuda]

  hunyuan3d_21:
    role: image_to_3d
    platform: [mac, linux]
    accelerator: [cuda]
    mac_status: experimental

  trellis2:
    role: high_end_image_to_3d
    platform: [linux]
    accelerator: [cuda]
    min_vram_gb: 24
```

The registry is how the system knows what can and cannot run on the current machine.

────────

21. Hardware Profiles

Profile A: M4 Max 36–48 GB

Target:

• orchestration;
• local LLMs;
• vision;
• Stable Fast 3D drafts;
• Blender;
• low/medium quality exports;
• remote high-end worker when necessary.

Avoid:

• keeping multiple large models resident simultaneously;
• 8K multi-UDIM jobs entirely on-device;
• CUDA-only models pretending to be native.

Profile B: M4 Max 64 GB

Recommended baseline.

Good for:

• larger local LLMs;
• vision models;
• stable 3D reconstruction;
• substantial Blender scenes;
• 4K assets;
• selected experimental Hunyuan workflows;
• remote high-end generation.

Profile C: M4 Max 128 GB

Ideal local control/studio configuration.

Good for:

• large quantized LLMs;
• multiple specialist models loaded sequentially;
• large Blender scenes;
• high-resolution texture processing;
• aggressive local iteration;
• multiple candidate assets held simultaneously.

Still not a CUDA machine.

Its advantage is memory capacity and unified orchestration, not pretending to be an NVIDIA workstation.

Profile D: M4 Max + Linux NVIDIA worker

This is the recommended high-end configuration.

```text
MacBook Pro M4 Max
    │
    ├── chat UI
    ├── project state
    ├── LLM orchestration
    ├── local vision
    ├── Blender
    └── job scheduler
             │
             │ LAN / secure API
             ▼
Linux NVIDIA Worker
    ├── TRELLIS.2
    ├── CUDA builds
    ├── high-VRAM texture generation
    └── other CUDA-only models
```

The Mac remains the studio console. The Linux workstation becomes a compute organ.

────────

22. End-to-End Example: Photorealistic Character

User request

```text
Create a photorealistic character from this reference.
Keep the face extremely accurate.
Maximum clothing detail.
Cinematic quality.
8K textures.
Export FBX and GLB.
```

Internal stages

```text
1. Vision analyst
2. Asset architect
3. Prompt composer
4. Router chooses Hunyuan/remote high-end path
5. Generate geometry candidates
6. Geometry critic
7. Reject candidate 2 for topology
8. Keep candidate 1
9. Generate PBR materials
10. Vision compare
11. Increase face fidelity only
12. Remesh
13. Generate LODs
14. Blender assembly
15. Export FBX
16. Export GLB
17. Reload both
18. Validate both
19. SHA-256 hash
20. Publish
```

The user sees only the progression and the finished files.

────────

23. End-to-End Example: Low Poly Game Character

```text
Create a stylized low-poly character for Godot.
25,000 triangles maximum.
2K textures.
Three LODs.
GLB only.
```

The planner transforms the request into:

```json
{
  "profile": "low_poly",
  "target_triangles": 25000,
  "texture_resolution": 2048,
  "lods": 3,
  "output": "glb",
  "material_count": "low"
}
```

The system should not waste a high-end cinematic model call on this.

────────

24. End-to-End Example: 3D Printing

```text
Turn this reference into a detailed figurine.
It must be printable.
No hollow unsupported geometry.
3MF and STL.
```

The pipeline adds:

```text
wall thickness check
manifold check
normal check
support-risk inspection
watertightness check
scale validation
STL export
3MF export
re-import validation
```

The user receives both files plus a printable validation report.

────────

25. Remote Worker Protocol

The remote worker should receive a self-contained job manifest rather than a huge prompt.

Example:

```json
{
  "job_id": "job_01HXYZ",
  "project_id": "proj_001",
  "asset_id": "asset_001",
  "stage": "high_end_image_to_3d",
  "model": "trellis2",
  "input_artifacts": [
    "references/reference_001.png",
    "manifests/generation_plan.json"
  ],
  "quality": {
    "geometry": 95,
    "texture": 95,
    "resolution": 8192
  },
  "return": [
    "mesh",
    "textures",
    "metadata",
    "telemetry"
  ]
}
```

The worker returns:

```json
{
  "job_id": "job_01HXYZ",
  "status": "succeeded",
  "artifacts": [
    "candidate.glb",
    "textures.zip",
    "generation.json"
  ],
  "checks": {
    "exit_code": 0,
    "model_loaded": true,
    "output_valid": true
  }
}
```

────────

26. Failure Handling

Every stage must classify failure.

```text
FAILURE
│
├── model unavailable
├── out of memory
├── invalid input
├── geometry defect
├── texture defect
├── UV defect
├── export defect
├── visual identity defect
└── system fault
```

Examples:

Out of memory

```text
reduce batch size
↓
reduce resolution
↓
offload stage
↓
remote worker
```

Topology failure

```text
preserve geometry candidate
↓
remesh only
↓
re-run topology QA
```

Texture failure

```text
preserve mesh
↓
regenerate material stage
↓
re-bake
```

Export failure

```text
preserve master
↓
change exporter
↓
re-import
↓
validate
```

The doctrine’s “regenerate only failure” principle is enforced by the job graph, not by hoping the model remembers what it did. fileciteturn0file0L224-L234

────────

27. Queue and Persistence

The system must tolerate:

• worker disappearing;
• Mac going to sleep;
• model crash;
• USB drive disconnection;
• network interruption;
• export failure.

Jobs therefore use durable states:

```text
QUEUED
CLAIMED
RUNNING
CHECKPOINTED
SUCCEEDED
FAILED_RETRYABLE
FAILED_FINAL
CANCELLED
```

Every job is idempotent.

A job may be safely resumed from the last completed artifact.

Example:

```text
Geometry generated ✓
Geometry QA ✓
Texture generation ✗ power failure

Resume:
Geometry generated ✓
Geometry QA ✓
Texture generation → resume
```

The geometry is not regenerated.

────────

28. Cache Strategy

Use content-addressed storage.

```text
sha256(input + model + parameters) → cache key
```

Example:

```text
cache/
  sha256_abc123/
    request.json
    output.glb
    metrics.json
```

If the same input, model, seed, and parameters are requested again, the system can return the cached artifact rather than recompute it.

This is especially valuable for large 3D models.

────────

29. Reproducibility

Every asset must store:

```text
model name
model hash/version
prompt
seed
parameters
source references
software versions
GPU/CPU profile
quality profile
routing decision
revision history
export settings
artifact hashes
```

The final package should contain a manifest:

```json
{
  "asset_id": "asset_001",
  "source_revision": "rev_07",
  "generator": "hunyuan3d-2.1",
  "review_status": "passed",
  "exports": {
    "glb": "sha256:...",
    "fbx": "sha256:..."
  }
}
```

────────

30. What the User Must Install

On the M4 Max

Required:

• current macOS;
• Xcode Command Line Tools;
• Homebrew;
• Python 3.11/3.12 environment;
• llama.cpp;
• Blender;
• Git;
• external NVMe storage;
• project runtime;
• selected model weights.

PyTorch’s current Apple Silicon guidance supports the MPS backend on Apple silicon and requires macOS 14+ and current Python/Xcode tooling. citeturn186714search6

Optional local models

• Qwen3 GGUF;
• Qwen3-Coder-Next GGUF;
• Gemma 3 multimodal GGUF;
• Stable Fast 3D;
• image generation model;
• local image upscaling stack.

Optional NVIDIA worker

• Linux;
• NVIDIA driver;
• CUDA;
• Docker or Conda;
• TRELLIS.2;
• Hunyuan CUDA stack;
• other high-end CUDA-only models.

────────

31. What Is Custom-Made

The following should be developed specifically for this system rather than delegated to a single third-party application:

1. orchestrator
2. model_registry
3. capability_probe
4. quality_profiles
5. artifact_registry
6. evaluation schema
7. revision engine
8. queue
9. worker protocol
10. chat interface
11. export validator
12. silent loop controller
13. project memory
14. routing policy
15. failure taxonomy

This is where the actual value of the system lives.

The underlying models are replaceable.

The organization is yours.

────────

32. Model Replacement Rule

Never hard-code a model name into the creative logic.

Bad:

```python
model = "hunyuan3d-2.1"
```

Good:

```python
model = router.select(
    task="image_to_3d",
    quality="cinematic",
    constraints=capabilities
)
```

The router might return:

```text
stable-fast-3d
```

or

```text
hunyuan3d-2.1
```

or

```text
trellis2@remote-worker-01
```

without changing the rest of the pipeline.

────────

33. Capability Probe

At startup:

```text
probe()
│
├── CPU
├── unified memory
├── GPU
├── Metal
├── MPS
├── Python
├── Blender
├── llama.cpp
├── model weights
├── external storage
└── worker connectivity
```

Example output:

```json
{
  "host": "macbook-pro-m4-max",
  "memory_gb": 64,
  "metal": true,
  "mps": true,
  "cuda": false,
  "llama_cpp": true,
  "stable_fast_3d": "available",
  "hunyuan3d_21": "experimental",
  "trellis2": "remote_only",
  "worker": {
    "linux-cuda-01": "online"
  }
}
```

This object drives the router.

────────

34. Recommended First Build

Do not start by installing every model in existence.

Build the architecture around this initial stack:

```text
LLM:
  Qwen3 32B GGUF

Coding:
  Qwen3-Coder-Next GGUF

Vision:
  Gemma 3 12B or 27B multimodal GGUF

3D:
  Stable Fast 3D

Experimental 3D:
  Hunyuan3D-2.1

Scene / assembly:
  Blender

Mesh processing:
  Open3D + trimesh + PyMeshLab

Inference gateway:
  llama.cpp / llama-server

Storage:
  external NVMe

Optional high-end worker:
  Linux + NVIDIA
```

Then add TRELLIS.2 only when a Linux/CUDA worker is available, because its published prerequisites are not an M4 Max-native stack. citeturn333016search0

────────

35. Acceptance Criteria

The system is considered operational only when it can demonstrate all of the following:

Input

• text prompt;
• image reference;
• existing mesh;
• output format selection;
• quality selection.

Planning

• immutable asset specification;
• model routing;
• quality policy;
• artifact creation.

Generation

• at least one local 3D path;
• multiple model adapters;
• deterministic Blender post-processing.

Evaluation

• geometry metrics;
• visual review;
• failure classification;
• targeted revision.

Output

• GLB;
• FBX;
• OBJ/MTL;
• STL;
• USDZ;
• 3MF;
• BLEND.

Reliability

• persistent queue;
• retryable jobs;
• resumable jobs;
• cache;
• artifact hashes;
• worker fallback.

User experience

• natural language control;
• visible progress;
• customizable quality;
• no requirement to understand which model executed each stage;
• explicit warning only when the requested quality cannot be achieved on the available hardware.

────────

36. Final Architecture

The definitive target is:

```text
                     ┌────────────────────┐
                     │       USER         │
                     │ natural language   │
                     │ image / reference  │
                     └─────────┬──────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │      CHAT UI       │
                     └─────────┬──────────┘
                               │
                               ▼
                     ┌────────────────────┐
                     │ CREATIVE IDENTITY  │
                     │    immutable       │
                     └─────────┬──────────┘
                               │
                               ▼
                  ┌──────────────────────────┐
                  │      ORCHESTRATOR        │
                  │ DAG + queue + policy     │
                  └────────────┬─────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   llama.cpp LLMs         Vision models         Router
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
                       ASSET SPECIFICATION
                               │
                               ▼
                         MODEL SELECTION
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
        Native Mac        Experimental        Linux/CUDA
             │                 │                 │
             ▼                 ▼                 ▼
          SF3D            Hunyuan3D          TRELLIS.2
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                         CANDIDATE POOL
                               │
                               ▼
                           EVALUATION
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                  FAIL                   PASS
                    │                     │
                    ▼                     ▼
               TARGETED FIX          MATERIALS
                                          │
                                          ▼
                                     UV / TOPOLOGY
                                          │
                                          ▼
                                        BLENDER
                                          │
                                          ▼
                                        LODS
                                          │
                                          ▼
                                    FINAL QA
                                          │
                                          ▼
                                      EXPORT
                                          │
                                          ▼
                                      HASH
                                          │
                                          ▼
                                     ARCHIVE
```

The system is therefore not “an AI that makes 3D models.”

It is a local-first 3D production organization in which:

• the M4 Max provides the intelligent control plane;
• llama.cpp provides the local LLM nervous system;
• specialist models perform specialized generation;
• Blender performs deterministic assembly;
• evaluators police quality;
• a persistent artifact system preserves successful work;
• Ventoy/external storage provides portable system/data infrastructure where appropriate;
• Linux/NVIDIA workers provide the CUDA-only high end;
• the user controls the creative target through one chat interface;
• the system silently performs the engineering required to reach that target.

That is the correct foundation for a localized Meshy-class system without pretending that one machine or one model can perform every job equally well.

────────

37. Authoritative Technical References

• Apple M4 Max MacBook Pro technical specifications.
• Apple Metal and PyTorch MPS documentation.
• Asahi Linux M4 feature and boot documentation.
• llama.cpp Metal, multimodal, and server documentation.
• Qwen3 llama.cpp / GGUF documentation.
• Qwen3-Coder-Next GGUF distribution.
• Stability AI Stable Fast 3D repository.
• Tencent Hunyuan3D-2.1 repository and requirements.
• Microsoft TRELLIS.2 repository and requirements.
• Ventoy persistence documentation.
• Meshy export/API documentation used as the reference point for practical output-format coverage.

The architecture must be revalidated against model repositories before installing or pinning any model, because model support, kernels, checkpoints, and hardware requirements evolve.