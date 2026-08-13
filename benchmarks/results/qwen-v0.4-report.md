# Otter Benchmark v0.4 - Qwen2.5-Coder 7B

## Executive Summary

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 18.2%. The most common failure category was quality_gate (8 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.

This is an engineering baseline on a fixed 20-task suite. It is not a statistically
representative evaluation of general model capability.

## Benchmark Setup

- OS: Windows 11 (10.0.26200)
- CPU: AMD64 Family 23 Model 96 Stepping 1, AuthenticAMD
- RAM: 15.4 GiB
- GPU: NVIDIA GeForce RTX 3050 Ti Laptop GPU, 4096 MiB
- Ollama version: ollama version is 0.20.2
- Model: qwen2.5-coder:7b
- status: available
- ping_ok: True
- ping_latency_s: 7.306246200001624
- Repositories: bottle, click, sample-app, starlette
- Repository count: 4
- Task count: 20 (easy 5, medium 10, hard 5)
- Locate / implement: 9 / 11
- Otter commit SHA: 8dfe384156c4b58d4b8adb33f32c1787303b6ac7 (dirty working tree)
- Python: 3.13.4
- Node: v25.1.0

## v0.2 / v0.3 / v0.4 Results

| Metric | v0.2 | v0.3 | v0.4 | v0.3 -> v0.4 |
| --- | --- | --- | --- | --- |
| Recall@5 | 85.0% | 93.2% | 93.2% | +0.0 pp |
| Precision@5 | 37.0% | 43.0% | 43.0% | +0.0 pp |
| Precision@|gold| | 61.7% | 71.5% | 71.5% | +0.0 pp |
| Plan Grounding | 64.0% | 71.0% | 71.0% | +0.0 pp |
| Patch Success | 81.8% | 63.6% | 18.2% | -45.5 pp |
| End-to-End Success | 27.3% | 9.1% | 18.2% | +9.1 pp |
| Mean Latency | 36.849s | 44.319s | 72.187s | +27.868s |
| Median Latency | 25.845s | 15.597s | 14.564s | -1.033s |
| P95 Latency | 93.252s | 206.399s | 242.539s | +36.140s |
| Structured-output failures | 2 | 4 | 1 | -3 |
| Test failures | 4 | 2 | 0 | -2 |
| Wrong-file failures | 2 | 2 | 0 | -2 |

Deltas are v0.3 -> v0.4. Rates use percentage points, not relative percent change.
Targets in the spec are goals, not claims. If E2E stays low, that is the result.

## Retrieval

| Metric | Qwen 7B |
| --- | --- |
| Recall@3 | 77.2% |
| Recall@5 | 93.2% |
| Recall@10 | 94.2% |
| Precision@3 | 60.0% |
| Precision@5 | 43.0% |
| Precision@10 | 22.0% |
| Precision@|gold| | 71.5% |

Precision@5 is bounded by gold-set size. Precision@|gold| is the fairer ranking metric.

## Planning

| Metric | Qwen 7B |
| --- | --- |
| Plan Grounding Score | 71.0% |
| Plan success rate (>=8/10 overlap) | 55.0% |

Plan Grounding Score is deterministic string/path overlap with gold specs,
not human-judged planning accuracy.

## Patch Generation

| Metric | Qwen 7B |
| --- | --- |
| Patch generated (structurally valid) | 18.2% |
| Patch applied | 18.2% |
| Raw structured-output success | 18.2% |
| Recovered structured-output rate | 0.0% |
| Tests ran (pass or fail) | 0 |
| Tests passed | 0 |
| Tests not verifiable | 0 |
| Test pass rate (of ran) | N/A |
| Unexpected modification rate | 0.0% |
| Expected file accuracy | 66.7% |

## End-to-End Success

A task is E2E-successful only when a valid patch is generated, applied, syntax-ok,
expect_in_files passes, at least one gold file is modified, no unexpected files are
modified, and tests are `pass` or `skipped`. `not_verifiable` does not count as success.

| Metric | Qwen 7B |
| --- | --- |
| Task success rate (implement) | 18.2% |

## Performance

| Metric | Qwen 7B |
| --- | --- |
| Mean latency | 72.187s |
| Median latency | 14.564s |
| P95 latency | 242.539s |
| Mean generate latency | 129.713s |
| Mean first-attempt latency | 14.486s |
| Mean retry latency | N/A |
| Mean retrieval latency | 0.142s |
| Mean planning latency | 0.343s |

Token measurement: unavailable.

## Failure Analysis

| Failure Category | v0.2 | v0.3 | v0.4 | v0.3 -> v0.4 |
| --- | --- | --- | --- | --- |
| Test failure | 4 | 2 | 0 | -2 |
| Wrong file | 2 | 2 | 0 | -2 |
| JSON malformed | 0 | 0 | 1 | 1 |
| Wrong schema | 2 | 3 | 0 | -3 |
| Syntax failure | 0 | 1 | 0 | -1 |
| Not verifiable | 0 | 1 | 0 | -1 |
| Quality gate | 0 | 0 | 8 | 8 |
| Malformed model output | 0 | 1 | 0 | -1 |
| Other | 0 | 0 | 0 | N/A |

See `qwen-v0.4-failures.json` (9 rows).

## Root Cause Analysis

v0.3 improved TF-IDF retrieval and planning, but generate dumped too much source
into OLLAMA_NUM_CTX=4096. That produced refuse-JSON, truncated full-file rewrites,
and unsolicited package.json. v0.4 keeps TF-IDF ranking, shrinks generate context,
requires edits for existing files, rejects stub rewrites, and retries once on
validation errors.

## Regression Testing

Existing Otter unit tests plus v0.4 edits/context/harness regressions (52 passed).

## Limitations

- Tasks are constructed engineering prompts over 4 repositories, not a production workload.
- Benchmark size is 20 tasks.
- Planner and retriever are heuristic; they do not use the candidate LLM.
- Plan rubric is deterministic overlap, not a human review.
- Targeted pytest only; full upstream suites are not run.
- TypeScript sample-app has no real compiler/test harness; those tasks can skip tests.
- Hardware is a single machine; results do not generalize.
- Auto-approve is benchmark-only.

## Conclusion

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 18.2%. The most common failure category was quality_gate (8 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.
