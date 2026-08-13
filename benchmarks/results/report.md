# Otter Benchmark v0.3 - Qwen2.5-Coder 7B

## Executive Summary

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 9.1%. The most common failure category was wrong_schema (3 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.

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
- ping_latency_s: 7.8275356000012835
- Repositories: bottle, click, sample-app, starlette
- Repository count: 4
- Task count: 20 (easy 5, medium 10, hard 5)
- Locate / implement: 9 / 11
- Otter commit SHA: cbde1a4dec2295f43ddda7d198a54dca365480fb (dirty working tree)
- Python: 3.13.4
- Node: v25.1.0

## v0.2 -> v0.3 Results

| Metric | v0.2 | v0.3 | Delta |
| --- | --- | --- | --- |
| Recall@5 | 85.0% | 93.2% | +8.2 pp |
| Precision@5 | 37.0% | 43.0% | +6.0 pp |
| Precision@|gold| | 61.7% | 71.5% | +9.8 pp |
| Plan Grounding | 64.0% | 71.0% | +7.0 pp |
| Patch Success | 81.8% | 63.6% | -18.2 pp |
| End-to-End Success | 27.3% | 9.1% | -18.2 pp |
| Mean Latency | 36.849s | 44.319s | +7.470s |
| Median Latency | 25.845s | 15.597s | -10.248s |
| P95 Latency | 93.252s | 206.399s | +113.147s |
| Structured-output failures | 2 | 4 | 2 |
| Test failures | 4 | 2 | -2 |
| Wrong-file failures | 2 | 2 | 0 |

Deltas for rates are percentage points, not relative percent change.

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
| Patch generated (structurally valid) | 63.6% |
| Patch applied | 63.6% |
| Raw structured-output success | 45.5% |
| Recovered structured-output rate | 18.2% |
| Tests ran (pass or fail) | 3 |
| Tests passed | 0 |
| Tests not verifiable | 1 |
| Test pass rate (of ran) | 0.0% |
| Unexpected modification rate | 28.6% |
| Expected file accuracy | 63.1% |

## End-to-End Success

A task is E2E-successful only when a valid patch is generated, applied, syntax-ok,
expect_in_files passes, at least one gold file is modified, no unexpected files are
modified, and tests are `pass` or `skipped`. `not_verifiable` does not count as success.

| Metric | Qwen 7B |
| --- | --- |
| Task success rate (implement) | 9.1% |

## Performance

| Metric | Qwen 7B |
| --- | --- |
| Mean latency | 44.319s |
| Median latency | 15.597s |
| P95 latency | 206.399s |
| Mean generate latency | 78.553s |
| Mean retrieval latency | 0.170s |
| Mean planning latency | 0.384s |

Token measurement: unavailable.

## Failure Analysis

| Failure Category | v0.2 | v0.3 | Delta |
| --- | --- | --- | --- |
| Test failure | 4 | 2 | -2 |
| Wrong file | 2 | 2 | 0 |
| JSON malformed | 0 | 0 | 0 |
| Wrong schema | 2 | 3 | 1 |
| Syntax failure | 0 | 1 | 1 |
| Not verifiable | 0 | 1 | 1 |
| Other | 0 | 1 | N/A |

See `qwen-v0.3-failures.json` (10 rows).

## Root Cause Analysis

v0.2 mislabeled several failures as test/JSON issues. Generation context was planner
rglob junk (LICENSE/Makefile/manifests/.po), so Qwen rewrote library files as stubs.
v0.3 feeds TF-IDF ranked source files into generate_patch, stops synthesizing
package.json on Python-only patches, and isolates pytest from the host site-packages.

## Regression Testing

Existing Otter unit tests plus new context/planner/harness regressions:
45 passed (test_llm_patch, test_e2e_flow, test_agent_core, test_patch_safety,
test_schemas, test_planner, test_metrics).

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

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 9.1%. The most common failure category was wrong_schema (3 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.
