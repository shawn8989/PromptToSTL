# AGENTS.md — PromptToSTL

Read this first. Shawn works with **two** AI agents (Claude Code and Codex) across three related repos; the rules below exist so you don't collide or contradict each other.

## Shared knowledge base (read before changing anything)

An Obsidian vault outside this repo is the source of truth for architecture, decisions, and work in progress:

```
/Users/shawn/Documents/Obsidian Vaults/PocketMaker/PocketMaker
```

Start with `Start-Here.md`, `Agents/Handoff-Protocol.md`, and `Projects/PromptToSTL/PromptToSTL.md`. It will **not** appear in a repo listing — open it by absolute path. If you cannot read outside the repo, say so rather than guessing.

## What this is

Python/Streamlit app for parametric 3D generation, and — as of the tap handle job — the **geometry layer for the whole system**.

- Parametric generation by shelling out to **OpenSCAD** via `subprocess` (`src/core/runner.py`)
- **LLM intent routing** (`src/intent/`)
- **STL validation** with `trimesh` (`src/core/validate.py`)
- **`src/tapgraft/`** — CLI that merges a scanned object onto a threaded base and verifies the result

Sibling repos: `~/Documents/Workspace/iOS/PocketMaker` (iOS capture) and `~/Documents/Workspace/iOS/PocketMakerStudio` (macOS cockpit). Studio invokes `tapgraft` by subprocess — it does **not** reimplement geometry in Swift. Reasoning: `Specs/ADR-005-mesh-booleans-in-python.md` in the vault.

## Non-negotiables

1. **Everything is millimetres.** STL carries no unit information. Never rescale silently; OBJ and USDZ from the Swift side are metres.
2. **The verification gate is the product.** `tapgraft` writes nothing until every check passes. On failure: write `<out>.FAILED.stl`, name the failed check and likely cause, exit nonzero, never write the success path.
3. **`manifold3d` is the primary boolean engine**, `trimesh` is the fallback — and a fallback must print a loud diagnostic. A silent fallback hides the real problem.
4. **Tests use generated primitives only.** A drilled cylinder for the base, a lumpy sphere-on-a-stick for the scan. No real scans, no client assets, no binary fixtures in the repo.
5. **Client photos and scans never get committed.**

## Build and test

```bash
pytest                      # pytest.ini sets pythonpath=. and testpaths=tests
pytest tests/test_tapgraft_cli.py -v
ruff check --no-cache
```

`pip install .` exposes the `tapgraft` console entry point. Editable installs have been unreliable on this machine's Python — prefer a normal install when verifying the CLI.

## Workflow rules

- Claim work in the vault's `Working/Backlog.md` (`Owner`, `Status`) before starting.
- Append a session entry to `Working/Session-Log.md` when you finish — it is the only handoff channel between agents.
- Record real decisions as ADRs in the vault's `Specs/` or `Decisions/`, not in chat.
- If you find uncommitted changes you did not make, **stop and report**. Never `reset`, `stash`, or `checkout` over another agent's work, and never `git add -A` when someone else has work in flight.

## Related specs

- `Specs/tapgraft-cli.md` — pipeline, verification gate, JSON report schema, required tests
- `Specs/studio-graft-bridge.md` — how Studio calls this tool
- `Handoffs/codex-tapgraft-handoff.md` — the current job brief
- `Projects/PocketMaker/beer-thug-tap-handle.md` — live job log
