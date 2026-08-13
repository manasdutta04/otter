import Link from "next/link";
import { GITHUB_REPO } from "../../../lib/urls";

const RESULTS = `${GITHUB_REPO}/blob/main/benchmarks/results/qwen-v0.6-report.md`;
const SUITE = `${GITHUB_REPO}/blob/main/benchmarks/README.md`;

export default function BenchmarkDocsPage() {
  return (
    <>
      <h1>Benchmark</h1>
      <p className="lead">
        Frozen 20-task suite for Otter&apos;s local Qwen 7B coding path. Not a general model
        leaderboard. The headline number is end-to-end implement success — a valid patch that
        applies, stays on expected files, and passes or skips gold tests.
      </p>

      <p>
        Latest run is <strong>v0.6</strong> on <code>qwen2.5-coder:7b</code>. It is better than v0.5
        and it is not done. Retrieval and planning are heuristic Otter stages; only generation uses
        the LLM.
      </p>

      <h2>Headline (v0.6)</h2>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>v0.5</th>
            <th>v0.6</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>E2E implement success</td>
            <td>18.2%</td>
            <td>36.4%</td>
          </tr>
          <tr>
            <td>Patch generated / applied</td>
            <td>27.3%</td>
            <td>90.9%</td>
          </tr>
          <tr>
            <td>Unexpected modification rate</td>
            <td>0%</td>
            <td>0%</td>
          </tr>
          <tr>
            <td>Retrieval Recall@5</td>
            <td>93.2%</td>
            <td>93.2%</td>
          </tr>
          <tr>
            <td>Mean latency</td>
            <td>81.6s</td>
            <td>42.4s</td>
          </tr>
          <tr>
            <td>P95 latency</td>
            <td>273.4s</td>
            <td>100.8s</td>
          </tr>
        </tbody>
      </table>
      <p className="muted">
        20 tasks / 4 repositories (sample-app, bottle, click, starlette). 9 locate, 11 implement.
        Unexpected files stayed at 0% — quality gates were not weakened to raise E2E.
      </p>

      <h2>What this measures</h2>
      <ul>
        <li>Retrieval Recall@K / Precision@K against gold files</li>
        <li>Plan grounding (deterministic overlap, not a human judge)</li>
        <li>Structured patch JSON, apply, expected-file accuracy</li>
        <li>Syntax + targeted tests after apply</li>
        <li>Wall-clock latency</li>
      </ul>
      <p>
        It does not measure time-to-merge, cloud models, MCP/CLI UX, or human preference. Auto-approve
        exists only inside <code>benchmarks/workspaces/</code>.
      </p>

      <h2>v0.6 still fails</h2>
      <ul>
        <li>
          <strong>6 test failures</strong> — the patch applied, then gold tests (or expect-in-files)
          failed. Qwen 7B can emit valid JSON and still write the wrong test or API.
        </li>
        <li>
          <strong>1 incomplete_auth</strong> — the quality gate correctly rejected a login change with
          no login/register route.
        </li>
        <li>
          JSON malformed, destructive rewrites, missing edit targets, and syntax failures from v0.5
          are gone.
        </li>
      </ul>

      <h2>Reproduce</h2>
      <pre>
        <code>{`# Ollama must already have qwen2.5-coder:7b (the suite never pulls)
python -m venv benchmarks/.venv
benchmarks/.venv/bin/python -m pip install -r apps/api/requirements.txt -r benchmarks/requirements.txt
export PYTHONPATH="$PWD:$PWD/apps/api"
benchmarks/.venv/bin/python -m benchmarks.runners.run_benchmark --model qwen2.5-coder:7b`}</code>
      </pre>
      <p>
        Windows uses <code>benchmarks\.venv\Scripts\python.exe</code> and{" "}
        <code>set PYTHONPATH=%CD%;%CD%\apps\api</code>. Full notes:{" "}
        <a href={SUITE} target="_blank" rel="noreferrer">
          benchmarks/README.md
        </a>
        .
      </p>

      <h2>Reports</h2>
      <ul>
        <li>
          <a href={RESULTS} target="_blank" rel="noreferrer">
            qwen-v0.6-report.md
          </a>
        </li>
        <li>
          <Link href="/docs/models">Models</Link> — local Ollama setup used for this suite
        </li>
      </ul>
    </>
  );
}
