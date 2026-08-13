# Otter Benchmark Report

**Otter Benchmark v0.1 — Baseline.** Do not overwrite these numbers; later runs compare against this archive.

Technical baseline only. Numbers below come from executed runner rows. Missing values are N/A or BLOCKED.

## Interpretation

This benchmark is an engineering baseline rather than a statistically
representative evaluation. Results are based on 20 tasks across 4 repositories
and should be interpreted as directional evidence for model selection and
pipeline debugging rather than general model capability.

Plan Score here is **Plan–Ground Truth Overlap** (deterministic string/path
overlap), not human-judged planning accuracy.

Precision@5 of 36% is close to the mathematical ceiling for ~2 gold files
per task (max P@5 ≈ 40%). The more useful retrieval signal is Recall@5 = 84%
with noisy extra context.

The 11 “malformed model output” rows mixed two different failures:

- JSON parse / invalid patch shape (especially Gemma)
- Otter quality-gate false positives (`register` in “register the route”,
  `authentication` in HTTP Basic copy) plus a second `validate_patch_quality`
  pass in the runner

Those are pipeline bugs, not evidence that the model cannot code. v0.2
addresses them on this same 20-task suite.

## Environment

- OS: Windows 11 (10.0.26200)
- CPU: AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD
- RAM: 15.4 GiB
- GPU: NVIDIA GeForce RTX 3050 Ti Laptop GPU, 4096 MiB
- Ollama version: ollama version is 0.20.2
- Otter commit SHA: cbde1a4dec2295f43ddda7d198a54dca365480fb
- Python version: 3.13.4
- Node version: v25.1.0

## Models

### Qwen2.5-Coder 7B

- status: available
- version: qwen2.5-coder:7b
- availability: True
- ping_ok: True
- ping_latency_s: 8.637786600000254
- error: None

### Gemma4 E2B

- status: available
- version: gemma4:e2b
- availability: True
- ping_ok: True
- ping_latency_s: 12.262308699999267
- error: None

## Dataset

- Repositories: bottle, click, sample-app, starlette
- Number of repositories: 4
- Number of tasks: 20
- Easy: 5
- Medium: 10
- Hard: 5
- Locate: 9
- Implement: 11

## Results

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Retrieval Recall@5 | 84.0% | 84.0% |
| Retrieval Precision@5 | 36.0% | 36.0% |
| Plan Grounding Score (overlap) | 64.0% | 64.0% |
| Plan Success Rate | 20.0% | 20.0% |
| Patch Success Rate | 54.5% | 45.5% |
| Test Pass Rate | 0.0% | 0.0% |
| End-to-End Success | 9.1% | 0.0% |
| Mean Latency | 35.053s | 54.575s |
| Median Latency | 23.334s | 49.242s |
| P95 Latency | 98.578s | 104.736s |
| Avg Context Size | 3174 chars | 2151 chars |

Retrieval and plan columns are Otter-heuristic metrics (identical across models when both complete the same tasks).

## Retrieval

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Recall@3 | 63.4% | 63.4% |
| Recall@5 | 84.0% | 84.0% |
| Recall@10 | 88.7% | 88.7% |
| Precision@3 | 46.7% | 46.7% |
| Precision@5 | 36.0% | 36.0% |
| Precision@10 | 20.0% | 20.0% |

## Planning

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Mean plan score | 64.0% | 64.0% |
| Plan success rate | 20.0% | 20.0% |

## Code Generation

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Patch success rate | 54.5% | 45.5% |
| Test pass rate | 0.0% | 0.0% |
| Unexpected modification rate | 33.3% | 40.0% |
| Expected file accuracy | 82.2% | 33.3% |

## End-to-End

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Task success rate (implement) | 9.1% | 0.0% |

## Performance

| Metric | Qwen 7B | Gemma 2B |
| --- | --- | --- |
| Mean latency | 35.053s | 54.575s |
| Median latency | 23.334s | 49.242s |
| P95 latency | 98.578s | 104.736s |
| Mean generate latency | 51.269s | 88.746s |
| Mean retrieval latency | 0.149s | 0.181s |

Token measurement: unavailable. If unavailable, context size is reported in characters assembled before `generate_patch`.

## Failure Analysis

Top failure modes:

- malformed model output: 11
- test failure: 5
- incorrect file selection: 4
- syntax failure: 1

See `failures.json` (21 rows).

## Model Comparison

Qwen2.5-Coder 7B is the primary model (Otter's default local coder). Gemma4 E2B is the constrained comparison.

Qwen2.5-Coder 7B achieved a higher end-to-end implement success rate (9.1%) than Gemma4 E2B (0.0%) on this benchmark.
Qwen2.5-Coder 7B had lower mean total task latency (Qwen 35.05s, Gemma 54.58s).
The most common failure category was malformed model output (11 occurrences).
Retrieval and planning scores are expected to match across models because those Otter stages are heuristic, not LLM-backed.

Where Qwen is better or worse is taken only from the rates above (e2e, patch success, latency). Retrieval/plan equality is not a model win.

## Limitations

- Tasks are constructed engineering prompts over real public/in-tree repos, not a production team workload.
- Benchmark size is 20 tasks across 4 repositories.
- Planner and retriever are heuristic; they do not use the candidate LLM.
- Plan rubric is deterministic string/path overlap, not a human review.
- Targeted pytest only; full upstream suites are not run.
- Local 7B/E2B models with 300s generate timeout and small context budgets.
- TypeScript sample-app has no real compiler/test harness (`npm test` is a stub); implement success there leans on expect-in-files checks.
- Hardware is a single machine; results do not generalize to other GPUs/RAM.
- Auto-approve is benchmark-only and does not change Otter's product approval UX.

## Conclusion

Qwen2.5-Coder 7B achieved a higher end-to-end implement success rate (9.1%) than Gemma4 E2B (0.0%) on this benchmark. Qwen2.5-Coder 7B had lower mean total task latency (Qwen 35.05s, Gemma 54.58s). The most common failure category was malformed model output (11 occurrences). Retrieval and planning scores are expected to match across models because those Otter stages are heuristic, not LLM-backed.
