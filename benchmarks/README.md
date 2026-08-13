# Otter engineering benchmark

Reproducible technical baseline for Otter’s repository intelligence and coding pipeline.

Primary model: **qwen2.5-coder:7b**. v0.3+ is Qwen-only. Gemma4 E2B remains in archived v0.1/v0.2 reports only. This suite never pulls models and never calls cloud LLM APIs.

## Versions

- **v0.1 — Baseline:** archived under `benchmarks/results/v0.1/`. Honest first run; do not overwrite.
- **v0.2:** same 20 tasks after structured-output and retrieval-ranking fixes. Frozen at `benchmarks/results/v0.2/` and `v0.2-baseline.json`.
- **v0.3:** Qwen-only reliability run after generation-context and harness fixes. `benchmarks/results/qwen-v0.3-report.md`.
- **v0.4 / v0.5:** edit-first generation, full-file apply, quality gates. `qwen-v0.5-report.md`.
- **v0.6 (current):** structured JSON salvage, symbol/quote anchors, keep-good-edits. Public summary: `/docs/benchmark`. Full report: `benchmarks/results/qwen-v0.6-report.md`.

## Goals

Answer: how well does Otter’s local Qwen 7B coding pipeline work as an engineering-intelligence / coding system, and did a fixed 20-task suite improve after a targeted pipeline change?

Measured:

- Retrieval Recall@K / Precision@K (K = 3, 5, 10) against gold files
- Planning quality (deterministic rubric, max 10)
- Patch generation success, expected-file accuracy, unexpected-file rate
- Targeted test / syntax results after apply
- End-to-end task success
- Wall-clock latency (mean / median / p95)
- Context size in characters (and tokens only if Ollama returns `usage`)

Not measured:

- Developer productivity or time-to-merge
- Cloud models, embeddings, or Qdrant
- VS Code / MCP product surfaces
- Human preference or LLM-as-judge scores

## Fidelity notes

Otter’s **retriever is lexical** (TF-IDF + keyword). Otter’s **planner is keyword heuristics**. Those stages do not call the LLM, so both models receive the same retrieval and plan scores unless a stage is BLOCKED.

The **coding path is the LLM step**. Context budgets still differ by model name (`packages.agent.model_adapt.budget_for_model`) if a smaller model is passed explicitly.

The runner **does not change production Otter**. Ollama free-failover is disabled only via monkeypatch inside `benchmarks/runners/model_runner.py` so a Qwen failure cannot silently become Gemma.

Approval is simulated with the real state machine (`ready_for_approval` → generate → `patch_ready` → auto-approve → apply). Auto-approve is allowed **only** on copies under `benchmarks/workspaces/`. The Otter repo and `REPOSITORY_DATA_DIR` are never written.

## Dataset

About 20 gold tasks (5 easy / 10 medium / 5 hard) over:

| ID | Origin |
|----|--------|
| `sample-app` | `apps/mcp/fixtures/sample_repo` (in-tree) |
| `bottle` | GitHub `bottlepy/bottle` @ tag in `fixtures/repos.lock.yaml` |
| `click` | GitHub `pallets/click` @ pinned tag |
| `starlette` | GitHub `encode/starlette` @ pinned tag |

Gold answers were written by inspecting those trees. Models do not generate ground truth.

## Reproduce

From the repository root, with Ollama running and `qwen2.5-coder:7b` present (`ollama list`):

```bash
python -m venv benchmarks/.venv
benchmarks\.venv\Scripts\python.exe -m pip install -r apps/api/requirements.txt -r benchmarks/requirements.txt
set PYTHONPATH=%CD%;%CD%\apps\api
benchmarks\.venv\Scripts\python.exe -m benchmarks.runners.run_benchmark
```

Unix:

```bash
python -m venv benchmarks/.venv
benchmarks/.venv/bin/python -m pip install -r apps/api/requirements.txt -r benchmarks/requirements.txt
export PYTHONPATH="$PWD:$PWD/apps/api"
benchmarks/.venv/bin/python -m benchmarks.runners.run_benchmark
```

Optional:

```bash
python -m benchmarks.runners.run_benchmark --model qwen2.5-coder:7b
python -m pytest benchmarks/tests/test_metrics.py -q
```

Clones land in `benchmarks/cache/` (gitignored). Per-task apply copies land in `benchmarks/workspaces/` (gitignored). Results are written to `benchmarks/results/`.

## Methodology

1. Probe Ollama. Missing model → BLOCKED (no pull).
2. Ensure locked repos (clone if needed; clone failure → BLOCKED).
3. For every task × model: retrieve, inspect+plan, score plan, and (implement tasks) generate → approve → apply → syntax/tests.
4. Aggregate only from executed rows. FAILED/BLOCKED rows are not filled with estimates.

Temperature is `0`. Local generate timeout is 300s, matching `app.llm.generate_patch`.
