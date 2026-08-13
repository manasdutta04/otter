# Otter Benchmark v0.5 - Qwen2.5-Coder 7B

## Executive Summary

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 18.2%. The most common failure category was quality_gate (5 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.

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
- ping_latency_s: 7.399309000000358
- Repositories: bottle, click, sample-app, starlette
- Repository count: 4
- Task count: 20 (easy 5, medium 10, hard 5)
- Locate / implement: 9 / 11
- Otter commit SHA: 8dfe384156c4b58d4b8adb33f32c1787303b6ac7 (dirty working tree)
- Python: 3.13.4
- Node: v25.1.0

## v0.3 / v0.4 / v0.5 Results

| Metric | v0.3 | v0.4 | v0.5 | v0.4 -> v0.5 |
| --- | --- | --- | --- | --- |
| Recall@5 | 93.2% | 93.2% | 93.2% | +0.0 pp |
| Precision@5 | 43.0% | 43.0% | 43.0% | +0.0 pp |
| Precision@|gold| | 71.5% | 71.5% | 71.5% | +0.0 pp |
| Plan Grounding | 71.0% | 71.0% | 71.0% | +0.0 pp |
| Patch Success | 63.6% | 18.2% | 27.3% | +9.1 pp |
| End-to-End Success | 9.1% | 18.2% | 18.2% | +0.0 pp |
| Mean Latency | 44.319s | 72.187s | 81.624s | +9.437s |
| Median Latency | 15.597s | 14.564s | 17.389s | +2.825s |
| P95 Latency | 206.399s | 242.539s | 273.421s | +30.882s |
| Structured-output failures | 4 | 1 | 3 | 2 |
| Test failures | 2 | 0 | 0 | 0 |
| Wrong-file failures | 2 | 0 | 0 | 0 |

Deltas are v0.4 -> v0.5. Rates use percentage points, not relative percent change.
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
| Patch generated (structurally valid) | 27.3% |
| Patch applied | 27.3% |
| Raw structured-output success | 27.3% |
| Recovered structured-output rate | 0.0% |
| Tests ran (pass or fail) | 1 |
| Tests passed | 0 |
| Tests not verifiable | 0 |
| Test pass rate (of ran) | 0.0% |
| Unexpected modification rate | 0.0% |
| Expected file accuracy | 77.8% |

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
| Mean latency | 81.624s |
| Median latency | 17.389s |
| P95 latency | 273.421s |
| Mean generate latency | 146.778s |
| Mean first-attempt latency | 40.075s |
| Mean retry latency | N/A |
| Mean retrieval latency | 0.142s |
| Mean planning latency | 0.339s |

Token measurement: unavailable.

## Failure Analysis

| Failure Category | v0.3 | v0.4 | v0.5 | v0.4 -> v0.5 |
| --- | --- | --- | --- | --- |
| Test failure | 2 | 0 | 0 | 0 |
| Wrong file | 2 | 0 | 0 | 0 |
| JSON malformed | 0 | 1 | 3 | 2 |
| Wrong schema | 3 | 0 | 0 | 0 |
| Syntax failure | 1 | 0 | 1 | 1 |
| Not verifiable | 1 | 0 | 0 | 0 |
| Quality gate | 0 | 8 | 5 | -3 |
| Malformed model output | 1 | 0 | 0 | 0 |
| Other | 0 | 0 | 0 | N/A |

See `qwen-v0.5-failures.json` (9 rows).

## Quality-gate breakdown

| QUALITY_GATE category | Count |
| --- | --- |
| destructive_rewrite | 2 |
| edit_target_not_found | 2 |
| incomplete_auth | 1 |

## Root Cause Analysis

v0.4 quality-gate failures were mostly non-unique or missing edit snippets,
because edits were applied against truncated excerpts and short old_strings.
v0.5 applies edits to full files, allows empty old_string as append, uses
symbol-dense excerpts, compact retries, and structured QUALITY_GATE errors.

## Regression Testing

Existing Otter unit tests plus v0.5 generation/edit/harness regressions (57 passed).

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

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 18.2%. The most common failure category was quality_gate (5 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.
