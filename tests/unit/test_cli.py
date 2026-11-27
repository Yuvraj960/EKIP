"""tests.unit.test_cli — Unit tests for EKIP CLI dispatcher.

Verifies command line parsing, subcommands execution (start, api, ingest, test,
eval, mcp, status, reset, manual, help), and argument forwarding.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.cli import main


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    """Print help when requested via --help."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "EKIP" in captured.out
    assert "start" in captured.out
    assert "api" in captured.out
    assert "ingest" in captured.out
    assert "test" in captured.out


def test_cli_no_args(capsys: pytest.CaptureFixture[str]) -> None:
    """Print manual and return 0 when no subcommand is provided."""
    exit_code = main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "EKIP CLI MANUAL" in captured.out


def test_cli_manual_and_help_commands(capsys: pytest.CaptureFixture[str]) -> None:
    """Display CLI manual for both 'help' and 'manual' subcommands."""
    assert main(["manual"]) == 0
    captured1 = capsys.readouterr()
    assert "EKIP CLI MANUAL & USAGE GUIDE" in captured1.out

    assert main(["help"]) == 0
    captured2 = capsys.readouterr()
    assert "EKIP CLI MANUAL & USAGE GUIDE" in captured2.out


@patch("subprocess.run")
def test_cli_start(mock_run: MagicMock) -> None:
    """Dispatch start subcommand to streamlit run."""
    mock_run.return_value = MagicMock(returncode=0)
    exit_code = main(["start", "--port", "8505"])

    assert exit_code == 0
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert "streamlit" in called_args
    assert "run" in called_args
    assert "streamlit_app.py" in called_args
    assert "--server.port" in called_args
    assert "8505" in called_args


@patch("subprocess.run")
def test_cli_api(mock_run: MagicMock) -> None:
    """Dispatch api subcommand to uvicorn with host and port."""
    mock_run.return_value = MagicMock(returncode=0)
    exit_code = main(["api", "--host", "127.0.0.1", "--port", "9000", "--reload"])

    assert exit_code == 0
    mock_run.assert_called_once()
    called_args = mock_run.call_args[0][0]
    assert "uvicorn" in called_args
    assert "app.api.main:app" in called_args
    assert "--host" in called_args
    assert "127.0.0.1" in called_args
    assert "--port" in called_args
    assert "9000" in called_args
    assert "--reload" in called_args


@patch("app.cli.run_ingestion_pipeline")
def test_cli_ingest_dir(mock_pipeline: MagicMock, tmp_path: Path) -> None:
    """Dispatch ingest subcommand with directory path to run_ingestion_pipeline."""
    mock_pipeline.return_value = (5, 20)
    sample_dir = tmp_path / "docs"
    sample_dir.mkdir()

    exit_code = main(["ingest", str(sample_dir)])
    assert exit_code == 0
    mock_pipeline.assert_called_once_with(sample_dir)


@patch("app.cli.ingest_zip_archive")
def test_cli_ingest_zip(mock_ingest_zip: MagicMock, tmp_path: Path) -> None:
    """Dispatch ingest subcommand with zip file path to ingest_zip_archive."""
    mock_ingest_zip.return_value = (2, 8, "archive")
    sample_zip = tmp_path / "archive.zip"
    sample_zip.touch()

    exit_code = main(["ingest", str(sample_zip)])
    assert exit_code == 0
    mock_ingest_zip.assert_called_once_with(sample_zip, clear_previous=False)


def test_cli_ingest_nonexistent_path(tmp_path: Path) -> None:
    """Return error code 1 when target path does not exist."""
    missing_path = tmp_path / "does_not_exist"
    exit_code = main(["ingest", str(missing_path)])
    assert exit_code == 1


@patch("subprocess.run")
def test_cli_test_subcommands(mock_run: MagicMock) -> None:
    """Verify test subcommand variants: default pytest, --lint, --safe, and --eval."""
    mock_run.return_value = MagicMock(returncode=0)

    # 1. Default pytest
    assert main(["test"]) == 0
    assert "pytest" in mock_run.call_args_list[-1][0][0]

    # 2. Targeted test
    assert main(["test", "tests/unit/test_cli.py"]) == 0
    assert "tests/unit/test_cli.py" in mock_run.call_args_list[-1][0][0]

    # 3. Linter check
    assert main(["test", "--lint"]) == 0
    assert "ruff" in mock_run.call_args_list[-1][0][0]

    # 4. Type check
    assert main(["test", "--safe"]) == 0
    assert "mypy" in mock_run.call_args_list[-1][0][0]

    # 5. Eval suite check
    assert main(["test", "--eval"]) == 0
    assert "app.eval.run_eval" in mock_run.call_args_list[-1][0][0]


@patch("subprocess.run")
def test_cli_test_full(mock_run: MagicMock) -> None:
    """Verify that --full triggers pytest, ruff, and mypy in sequence."""
    mock_run.return_value = MagicMock(returncode=0)
    assert main(["test", "--full"]) == 0
    assert mock_run.call_count == 3


@patch("subprocess.run")
def test_cli_eval_shortcut(mock_run: MagicMock) -> None:
    """Verify ekip eval dispatches to the evaluation benchmark."""
    mock_run.return_value = MagicMock(returncode=0)
    assert main(["eval"]) == 0
    assert "app.eval.run_eval" in mock_run.call_args[0][0]


@patch("subprocess.run")
def test_cli_mcp_shortcut(mock_run: MagicMock) -> None:
    """Verify ekip mcp dispatches to standalone MCP server."""
    mock_run.return_value = MagicMock(returncode=0)
    assert main(["mcp"]) == 0
    assert "mcp_server.server" in mock_run.call_args[0][0]


@patch("app.cli.list_indexed_archives")
def test_cli_status(mock_list: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify status command inspects and formats active corpora."""
    mock_list.return_value = [
        {"archive_name": "auth.zip", "slug": "auth", "doc_count": 2, "chunk_count": 8}
    ]
    assert main(["status"]) == 0
    captured = capsys.readouterr()
    assert "EKIP PLATFORM STATUS" in captured.out
    assert "auth.zip" in captured.out
    assert "Chunks: 8" in captured.out


@patch("app.cli.clear_all_indexed_data")
def test_cli_reset(mock_clear: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    """Verify reset command with --force calls clear_all_indexed_data."""
    assert main(["reset", "--force"]) == 0
    mock_clear.assert_called_once()
    captured = capsys.readouterr()
    assert "All vector sub-databases" in captured.out
