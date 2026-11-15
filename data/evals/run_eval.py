"""data.evals.run_eval — Comprehensive evaluation harness for EKIP.

Evaluates system performance against data/evals/eval_set.json across
retrieval relevance, citation accuracy, uncertainty handling, and latency.

Usage:
    python data/evals/run_eval.py
"""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langsmith import traceable

from app.api.schemas import AnswerResponse, EvidenceStatus
from app.core.tracing import (
    META_LATENCY_SEC,
    META_MODULE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_EVAL,
    add_trace_metadata,
    add_trace_tags,
)
from app.services.orchestrator import handle_query

EVAL_SET_PATH: Path = Path("data/evals/eval_set.json")
RESULTS_DIR: Path = Path("data/evals")


@traceable(
    name="eval.evaluate_single_item",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_EVAL, "benchmark"],
    metadata={META_MODULE: "data.evals.run_eval"},
)
def evaluate_single_item(eval_item: dict[str, Any]) -> dict[str, Any]:
    """Execute evaluation for a single benchmark item and measure metrics.

    Args:
        eval_item: Evaluation test case specification dictionary.

    Returns:
        Dictionary containing execution result, score comparisons, and timing.
    """
    question = eval_item["question"]
    expected_status = eval_item["expected_evidence_status"]
    expected_sources = set(eval_item.get("expected_sources", []))
    q_type = eval_item.get("question_type", "answerable")

    start_time = time.perf_counter()
    response: AnswerResponse = handle_query(question)
    latency_sec = round(time.perf_counter() - start_time, 3)

    actual_status = response.evidence_status.value
    cited_sources = {c.source for c in response.citations}

    # Evaluate status match (for ambiguous queries, PARTIAL or INSUFFICIENT is accepted)
    if q_type == "ambiguous":
        status_match = actual_status in {
            EvidenceStatus.PARTIAL.value,
            EvidenceStatus.INSUFFICIENT.value,
        }
    else:
        status_match = actual_status == expected_status

    # Evaluate citation source match
    if q_type == "unanswerable":
        source_match = len(cited_sources) == 0
    elif q_type == "action":
        # Action queries draft responses; verify text cites relevant runbooks or docs
        source_match = any(src in response.answer for src in expected_sources) or bool(
            cited_sources & expected_sources
        )
    else:
        source_match = bool(cited_sources & expected_sources)

    is_passed = status_match and source_match

    add_trace_tags([f"eval_id:{eval_item['id']}", f"passed:{is_passed}"])
    add_trace_metadata(
        {
            "eval_id": eval_item["id"],
            "question_type": q_type,
            "passed": is_passed,
            "status_match": status_match,
            "source_match": source_match,
            META_LATENCY_SEC: latency_sec,
        }
    )

    return {
        "id": eval_item["id"],
        "question": question,
        "question_type": q_type,
        "expected_status": expected_status,
        "actual_status": actual_status,
        "status_match": status_match,
        "expected_sources": list(expected_sources),
        "cited_sources": list(cited_sources),
        "source_match": source_match,
        "latency_sec": latency_sec,
        "passed": is_passed,
        "answer_snippet": response.answer[:120].replace("\n", " "),
    }


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate benchmark metrics across all evaluation results.

    Args:
        results: List of evaluation item results.

    Returns:
        Summary metrics dictionary.
    """
    total = len(results)
    if total == 0:
        return {}

    passed_count = sum(1 for r in results if r["passed"])
    answerable = [r for r in results if r["question_type"] == "answerable"]
    unanswerable = [r for r in results if r["question_type"] == "unanswerable"]

    ans_status_match = (
        sum(1 for r in answerable if r["status_match"]) / len(answerable)
        if answerable
        else 0.0
    )
    unans_status_match = (
        sum(1 for r in unanswerable if r["status_match"]) / len(unanswerable)
        if unanswerable
        else 0.0
    )
    source_match_rate = sum(1 for r in results if r["source_match"]) / total
    avg_latency = sum(r["latency_sec"] for r in results) / total

    return {
        "total_queries": total,
        "passed_queries": passed_count,
        "overall_pass_rate": round(passed_count / total * 100, 1),
        "answerable_accuracy": round(ans_status_match * 100, 1),
        "unanswerable_safety": round(unans_status_match * 100, 1),
        "source_match_rate": round(source_match_rate * 100, 1),
        "average_latency_sec": round(avg_latency, 2),
    }


def print_metrics_summary(metrics: dict[str, Any], results: list[dict[str, Any]]) -> None:
    """Print formatted evaluation summary table to the console.

    Args:
        metrics: Summary metrics dictionary.
        results: List of per-item evaluation records.
    """
    print("\n" + "=" * 70)
    print("           EKIP PHASE 7 EVALUATION SUMMARY REPORT")
    print("=" * 70)
    for r in results:
        status_sym = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"[{r['id']}] {status_sym} | {r['question_type'].upper():<12} | "
              f"{r['latency_sec']}s | {r['actual_status']}")
        if not r["passed"]:
            print(f"       Expected Status: {r['expected_status']}, Got: {r['actual_status']}")
            print(f"       Expected Sources: {r['expected_sources']}, Cited: {r['cited_sources']}")

    print("-" * 70)
    print(f"Total Evaluations:       {metrics['total_queries']}")
    print(f"Passed Evaluations:      {metrics['passed_queries']} / {metrics['total_queries']} "
          f"({metrics['overall_pass_rate']}%)")
    print(f"Answerable Accuracy:     {metrics['answerable_accuracy']}% (Target: >=80%)")
    print(f"Unanswerable Safety:     {metrics['unanswerable_safety']}% (Target: >=90%)")
    print(f"Source Match Rate:       {metrics['source_match_rate']}% (Target: >=70%)")
    print(f"Average Latency:         {metrics['average_latency_sec']}s (Target: <5.0s)")
    print("=" * 70 + "\n")


@traceable(
    name="eval.run_evaluations",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_EVAL, "suite"],
    metadata={META_MODULE: "data.evals.run_eval"},
)
def run_evaluations(
    eval_file: Path = EVAL_SET_PATH,
    output_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    """Load benchmark dataset, run all evaluations, save results and report metrics.

    Args:
        eval_file: Path to evaluation JSON dataset.
        output_dir: Directory where timestamped result artifacts are saved.

    Returns:
        Summary metrics dictionary.
    """
    with open(eval_file, encoding="utf-8") as f:
        eval_items: list[dict[str, Any]] = json.load(f)

    print(f"Running evaluation benchmark on {len(eval_items)} test cases...")
    results: list[dict[str, Any]] = []

    for item in eval_items:
        res = evaluate_single_item(item)
        results.append(res)

    metrics = compute_metrics(results)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"results_{timestamp}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"metrics": metrics, "results": results}, f, indent=2)

    print(f"Saved evaluation run artifact to: {out_file}")
    print_metrics_summary(metrics, results)
    return metrics


if __name__ == "__main__":
    run_evaluations()
