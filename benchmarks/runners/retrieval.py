"""Run Otter's real lexical retriever (model-independent)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from packages.retrieval import RepositorySemanticIndex

from benchmarks.runners.metrics import retrieval_metrics, unique_ranked_files


def run_retrieval(root: Path, prompt: str, gold_files: list[str]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        index = RepositorySemanticIndex(Path(root))
        hits = index.search(prompt, top_k=24)
        ranked = unique_ranked_files(hits)
        latency_s = time.perf_counter() - started
        metrics = retrieval_metrics(ranked, gold_files)
        return {
            "ok": True,
            "ranked_files": ranked[:10],
            "hit_count": len(hits),
            "latency_s": latency_s,
            "metrics": metrics,
            "error": None,
        }
    except Exception as error:  # noqa: BLE001
        return {
            "ok": False,
            "ranked_files": [],
            "hit_count": 0,
            "latency_s": time.perf_counter() - started,
            "metrics": retrieval_metrics([], gold_files),
            "error": str(error),
        }
