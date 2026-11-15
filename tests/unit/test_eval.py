"""tests.unit.test_eval — Unit tests for evaluation harness."""

from unittest.mock import patch

from app.api.schemas import AnswerResponse, Citation, EvidenceStatus
from data.evals.run_eval import compute_metrics, evaluate_single_item


def test_compute_metrics_summary() -> None:
    """Verify calculation of aggregate metrics."""
    mock_results = [
        {
            "id": "eval-001",
            "question_type": "answerable",
            "status_match": True,
            "source_match": True,
            "latency_sec": 1.2,
            "passed": True,
        },
        {
            "id": "eval-002",
            "question_type": "unanswerable",
            "status_match": True,
            "source_match": True,
            "latency_sec": 0.4,
            "passed": True,
        },
        {
            "id": "eval-003",
            "question_type": "answerable",
            "status_match": False,
            "source_match": False,
            "latency_sec": 1.5,
            "passed": False,
        },
    ]

    metrics = compute_metrics(mock_results)
    assert metrics["total_queries"] == 3
    assert metrics["passed_queries"] == 2
    assert metrics["overall_pass_rate"] == 66.7
    assert metrics["answerable_accuracy"] == 50.0
    assert metrics["unanswerable_safety"] == 100.0
    assert metrics["source_match_rate"] == 66.7
    assert metrics["average_latency_sec"] == 1.03


def test_evaluate_single_item_answerable_pass() -> None:
    """Verify evaluate_single_item records pass when status and source match."""
    eval_item = {
        "id": "eval-001",
        "question": "What is the OAuth flow?",
        "expected_sources": ["auth_guide.md"],
        "expected_evidence_status": "SUFFICIENT",
        "question_type": "answerable",
    }

    dummy_response = AnswerResponse(
        answer="The OAuth flow...",
        citations=[Citation(source="auth_guide.md", section="OAuth", passage_excerpt="flow")],
        evidence_status=EvidenceStatus.SUFFICIENT,
    )

    with patch("data.evals.run_eval.handle_query", return_value=dummy_response):
        res = evaluate_single_item(eval_item)
        assert res["passed"] is True
        assert res["status_match"] is True
        assert res["source_match"] is True
