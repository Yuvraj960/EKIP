"""tests.unit.test_routes — Unit tests for app.api.routes."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes import app
from app.api.schemas import AnswerResponse, Citation, EvidenceStatus

client = TestClient(app)


def test_health_endpoint() -> None:
    """Verify that GET /health returns 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_ask_endpoint_valid_request() -> None:
    """Verify that POST /ask returns AnswerResponse JSON on valid query."""
    mock_answer = AnswerResponse(
        answer="The rollback command is ekip-deploy rollback.",
        citations=[
            Citation(
                source="deployment_runbook.md",
                section="Rollback Procedure",
                passage_excerpt="Execute ekip-deploy rollback --target previous",
            )
        ],
        evidence_status=EvidenceStatus.SUFFICIENT,
    )

    with patch("app.api.routes.handle_query", return_value=mock_answer):
        response = client.post(
            "/ask",
            json={"question": "What is the rollback command?", "top_k": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["evidence_status"] == "SUFFICIENT"
        assert "ekip-deploy rollback" in data["answer"]
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source"] == "deployment_runbook.md"


def test_ask_endpoint_invalid_empty_question() -> None:
    """Verify that POST /ask rejects empty questions with 422 Unprocessable Entity."""
    response = client.post("/ask", json={"question": "", "top_k": 3})
    assert response.status_code == 422


def test_ingest_endpoint_success(tmp_path: Path) -> None:
    """Verify that POST /ingest triggers ingestion and returns counts."""
    with patch("app.api.routes.run_ingestion_pipeline", return_value=(3, 12)):
        response = client.post("/ingest", json={"folder_path": str(tmp_path)})
        assert response.status_code == 200
        data = response.json()
        assert data["documents_loaded"] == 3
        assert data["chunks_indexed"] == 12
        assert data["status"] == "SUCCESS"


def test_ingest_endpoint_folder_not_found(tmp_path: Path) -> None:
    """Verify that POST /ingest returns 404 when folder does not exist."""
    fake_folder = tmp_path / "nonexistent_dir"
    response = client.post("/ingest", json={"folder_path": str(fake_folder)})
    assert response.status_code == 404
    assert "Directory not found" in response.json()["detail"]
