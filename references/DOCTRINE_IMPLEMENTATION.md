# Canon OS — Doctrine Implementation

Maps `.governance/FOREVER_DOCTRINE_UNIVERSAL.yaml` onto the Canon OS codebase. The doctrine is
supreme; where code or docs conflict, the doctrine wins.

## 1. The constitution

`FOREVER_DOCTRINE_UNIVERSAL.yaml` defines:
- **7 policies** POL-001 … POL-007 (root, authority, layering, sovereignty, continuity,
  verification, transparency).
- **40 habits** (engineering practice: plain speech, root-cause over patch, multi-platform
  thinking, honest claims).
- **Layering protocol** — strict dependency direction; lower layers never import higher.
- **Worker covenant** — "write for the next worker": every artifact must be legible and
  continuable by the next actor (human or agent).

## 2. Policy → implementation map

| Policy | Canon OS implementation |
|--------|-------------------------|
| **POL-001 Deterministic Root** | `core/host/detection/` probe is the single bootstrap; everything else is discovered via the capability resolver. No hidden global state. |
| **POL-002 No Arbitrary Authority** | No provider/model/runtime referenced by name in core logic. All resolved through `models/registry/` + `core/capabilities/`. |
| **POL-003 Layering** | Enforced spine `CORE→CAPABILITY→PROVIDER→MODEL→RUNTIME→HARDWARE` (docs/ARCHITECTURE.md §4). `core/` never imports `providers/` implementations directly; it uses contracts. |
| **POL-004 Identity / Sovereignty** | Canon OS identity is project-level (`projects/`, `.studio/`). The external agent-identity harness (`.agent/` ACK) is retired and lives in `.trash/`. |
| **POL-005 Continuity** | `.studio/` + `projects/` persist across runs; migrations in `core/projects/migrations/` are forward-only. Docs and code honor "write for the next worker." |
| **POL-006 Verification** | `core/validation/` + `tests/` gate every pipeline stage; nothing ships unvalidated. `validate.py` enforces capability quality bars. |
| **POL-007 Transparency** | Each operation logs its capability class and the chosen provider/runtime to `.studio/logs/`. |

## 3. Layering protocol in practice

- `core/` depends on `core/capabilities/` contracts, not on `providers/*` code.
- `providers/*` depend on `models/` manifests and `runtimes/*` adapters.
- `runtimes/*` depend only on `host/` detection output and the OS.
- `interfaces/*` (web/api/cli/desktop) depend on `core/` orchestration, never on internals.

A lower layer importing a higher layer is a doctrine violation and must fail review.

## 4. The 40 habits (selected, applied)

- **Root-cause, not patch** — sanitization traced prior docs to their authoritative inputs
  rather than papering over them.
- **Multi-platform by default** — no OS/GPU assumption; capability probe decides.
- **Plain, honest speech** — docs state what is done vs. planned (see ARCHITECTURE §12).
- **Write for the next worker** — this file and the architecture spec are self-contained and
  cite their sources.

## 5. Verification

Run the doctrine's `test_of_forever` (7 gates) against this repository. Expected: each policy
above resolves to a concrete file/behavior. Gaps are tracked in `TASKS.md`.

### test_of_forever conformance (2026-08-15)

| # | Gate | Result | Evidence |
|---|------|--------|----------|
| 1 | One source of truth per concept (POL-001) | YES | `docs/ARCHITECTURE.md` + 3 vendored inputs; all prior docs in `.trash/` marked non-authoritative |
| 2 | Resolves own context, no fixed assumptions (POL-002) | YES | Capability probe + `models/registry/`; no model/runtime hard-coded in core |
| 3 | Updates add layers, never rewrite foundation (POL-003) | YES* | Sanitization was a one-time corrective rebuild (see `CHANGELOG.md`); ongoing changes layer via `TASKS.md` |
| 4 | Stops when unsure; changes leave traces (POL-004) | YES | Host-power depth flagged pending in `TASKS.md`; all moves logged in `CHANGELOG.md` |
| 5 | Context-agnostic; components real, not just documented (POL-005) | PARTIAL | `core/orchestration/chain.py`, `core/validation/validate.py`, `interfaces/{web,api}` real; providers/runtime-native scaffolds pending |
| 6 | Affirmatively reinforces identity (POL-006) | YES | Canon OS branding retained across docs; identity is project-level, ACK retired |
| 7 | Proves it works via signal, not claims (POL-007) | YES* | `validate.py` passes on all docs; structure sanity-checked; provider/runtime proofs tracked in `TASKS.md` |

*Items marked PARTIAL/YES* are honest: the probe/resolver and provider porting are the next
build steps, not yet signaled. No foundation claim is made that is not backed by an existing
artifact or a tracked task.
