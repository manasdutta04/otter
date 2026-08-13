# Otter Benchmark v0.6 - Qwen2.5-Coder 7B

## Executive Summary

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 36.4%. The most common failure category was test failure (6 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.

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
- ping_latency_s: 1.413720900000044
- Repositories: bottle, click, sample-app, starlette
- Repository count: 4
- Task count: 20 (easy 5, medium 10, hard 5)
- Locate / implement: 9 / 11
- Otter commit SHA: ad0307c720d6f56ab3ae68b9cdf4566adde162d0 (dirty working tree)
- Python: 3.13.4
- Node: v25.1.0

## v0.4 / v0.5 / v0.6 Results

| Metric | v0.4 | v0.5 | v0.6 | v0.5 -> v0.6 |
| --- | --- | --- | --- | --- |
| Recall@5 | 93.2% | 93.2% | 93.2% | +0.0 pp |
| Precision@5 | 43.0% | 43.0% | 43.0% | +0.0 pp |
| Precision@|gold| | 71.5% | 71.5% | 71.5% | +0.0 pp |
| Plan Grounding | 71.0% | 71.0% | 71.0% | +0.0 pp |
| Patch Success | 18.2% | 27.3% | 90.9% | +63.6 pp |
| End-to-End Success | 18.2% | 18.2% | 36.4% | +18.2 pp |
| Mean Latency | 72.187s | 81.624s | 42.402s | -39.222s |
| Median Latency | 14.564s | 17.389s | 37.622s | +20.233s |
| P95 Latency | 242.539s | 273.421s | 100.815s | -172.606s |
| Structured-output failures | 1 | 3 | 0 | -3 |
| Test failures | 0 | 0 | 6 | 6 |
| Wrong-file failures | 0 | 0 | 0 | 0 |

Deltas are v0.5 -> v0.6. Rates use percentage points, not relative percent change.
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
| Patch generated (structurally valid) | 90.9% |
| Patch applied | 90.9% |
| Raw structured-output success | 63.6% |
| Recovered structured-output rate | 27.3% |
| Structured-output recovery failure | 0.0% |
| Tests ran (pass or fail) | 7 |
| Tests passed | 1 |
| Tests not verifiable | 0 |
| Test pass rate (of ran) | 14.3% |
| Unexpected modification rate | 0.0% |
| Expected file accuracy | 77.7% |

## End-to-End Success

A task is E2E-successful only when a valid patch is generated, applied, syntax-ok,
expect_in_files passes, at least one gold file is modified, no unexpected files are
modified, and tests are `pass` or `skipped`. `not_verifiable` does not count as success.

| Metric | Qwen 7B |
| --- | --- |
| Task success rate (implement) | 36.4% |

## Performance

| Metric | Qwen 7B |
| --- | --- |
| Mean latency | 42.402s |
| Median latency | 37.622s |
| P95 latency | 100.815s |
| Mean generate latency | 74.224s |
| Mean first-attempt latency | 69.476s |
| Mean retry latency | 51.974s |
| Mean retrieval latency | 0.194s |
| Mean planning latency | 0.537s |

Token measurement: unavailable.

## Failure Analysis

| Failure Category | v0.4 | v0.5 | v0.6 | v0.5 -> v0.6 |
| --- | --- | --- | --- | --- |
| Test failure | 0 | 0 | 6 | 6 |
| Wrong file | 0 | 0 | 0 | 0 |
| JSON malformed | 1 | 3 | 0 | -3 |
| Wrong schema | 0 | 0 | 0 | 0 |
| Syntax failure | 0 | 1 | 0 | -1 |
| Not verifiable | 0 | 0 | 0 | 0 |
| Quality gate | 8 | 5 | 1 | -4 |
| Malformed model output | 0 | 0 | 0 | 0 |
| Other | 0 | 0 | 0 | N/A |

See `qwen-v0.6-failures.json` (7 rows).

## Quality-gate breakdown

| QUALITY_GATE category | Count |
| --- | --- |
| incomplete_auth | 1 |

## Root Cause Analysis

v0.5 still lost valid edits when a stub files[] rewrite tripped destructive_rewrite,
failed JSON on Python triple-quotes, and required exact old_string including quotes.
v0.6 salvages edits[], keeps good edits when files[] is destructive, scopes edits
by symbol / quote-safe unique literals, compact-repairs JSON without resending the repo,
and syntax-checks new Python files before apply.

## Regression Testing

79 Otter unit tests passed (v0.5 had 57), including v0.6 JSON/anchor/syntax/auth regressions.

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

Qwen2.5-Coder 7B end-to-end implement success on this 20-task suite is 36.4%. The most common failure category was test failure (6 occurrences). Plan Grounding Score is deterministic string/path overlap, not human-judged planning accuracy.
