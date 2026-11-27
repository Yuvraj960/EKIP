"""app.cli — Unified command-line interface for EKIP.

Provides custom CLI commands to start the Streamlit web application, run the
FastAPI backend, ingest documents, run quality checks, execute evaluation suites,
and inspect active sub-database corpora.

Usage:
    ekip start [--port 8501]
    ekip api [--port 8000] [--reload]
    ekip ingest [folder_or_zip] [--clear]
    ekip test [--lint] [--safe] [--eval] [--full]
    ekip eval
    ekip status
    ekip reset [--force]
    ekip help / ekip manual
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from app.ingestion.archive_manager import clear_all_indexed_data, list_indexed_archives
from app.ingestion.run_ingest import run_ingestion_pipeline
from app.ingestion.zip_handler import ingest_zip_archive

STREAMLIT_APP_SCRIPT: str = "streamlit_app.py"


def _ensure_environment() -> None:
    """Auto-bootstrap configuration and essential storage directories."""
    env_file = Path(".env")
    example_file = Path(".env.example")
    if not env_file.exists() and example_file.exists():
        shutil.copyfile(example_file, env_file)
        print("[EKIP] Initialized .env from template.", file=sys.stderr)

    Path(settings.uploaded_docs_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)


def _run_streamlit(port: int | None = None) -> int:
    """Launch the Streamlit web UI with environment auto-bootstrapping.

    Args:
        port: Optional port number override.

    Returns:
        Process exit code.
    """
    _ensure_environment()
    cmd = [sys.executable, "-m", "streamlit", "run", STREAMLIT_APP_SCRIPT]
    if port is not None:
        cmd.extend(["--server.port", str(port)])

    result = subprocess.run(cmd)
    return result.returncode


def _run_api(host: str | None = None, port: int | None = None, reload: bool = False) -> int:
    """Launch the FastAPI server via Uvicorn.

    Args:
        host: Host interface address. Defaults to settings.api_host.
        port: Port number. Defaults to settings.api_port.
        reload: Whether to enable auto-reload on code changes.

    Returns:
        Process exit code.
    """
    _ensure_environment()
    target_host = host or settings.api_host
    target_port = port or settings.api_port
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.api.main:app",
        "--host",
        target_host,
        "--port",
        str(target_port),
    ]
    if reload:
        cmd.append("--reload")

    result = subprocess.run(cmd)
    return result.returncode


def _run_ingest(source: str, clear: bool = False) -> int:
    """Run document ingestion from a directory or zip archive.

    Args:
        source: Directory path or zip archive path.
        clear: Whether to clear all existing data before indexing.

    Returns:
        Process exit code (0 for success, 1 for failure).
    """
    _ensure_environment()
    target_path = Path(source)
    if not target_path.exists():
        print(f"Error: Target path does not exist: {source}", file=sys.stderr)
        return 1

    if target_path.suffix.lower() == ".zip":
        doc_count, chunk_count, _ = ingest_zip_archive(target_path, clear_previous=clear)
    elif target_path.is_dir():
        doc_count, chunk_count = run_ingestion_pipeline(target_path)
    else:
        print(f"Error: Target must be a directory or .zip file: {source}", file=sys.stderr)
        return 1

    print(f"Successfully indexed {chunk_count} chunks from {doc_count} documents.")
    return 0


def _run_test_checks(
    lint: bool = False,
    safe: bool = False,
    eval_suite: bool = False,
    full: bool = False,
    target: str | None = None,
) -> int:
    """Execute unit tests, code linter, type checker, or evaluation benchmark.

    Args:
        lint: Whether to run Ruff linter.
        safe: Whether to run Mypy static type checker.
        eval_suite: Whether to run the evaluation benchmark suite.
        full: Whether to run tests, linter, and type checker in sequence.
        target: Optional specific test path.

    Returns:
        Integer process exit code.
    """
    if full:
        r1 = subprocess.run([sys.executable, "-m", "pytest", "tests/unit", "-q"]).returncode
        r2 = subprocess.run([sys.executable, "-m", "ruff", "check", "."]).returncode
        r3 = subprocess.run([sys.executable, "-m", "mypy", "app", "mcp_server"]).returncode
        return r1 or r2 or r3
    if lint:
        return subprocess.run([sys.executable, "-m", "ruff", "check", "."]).returncode
    if safe:
        return subprocess.run([sys.executable, "-m", "mypy", "app", "mcp_server"]).returncode
    if eval_suite:
        return subprocess.run([sys.executable, "-m", "app.eval.run_eval"]).returncode

    pytest_target = target or "tests/unit"
    return subprocess.run([sys.executable, "-m", "pytest", pytest_target, "-q"]).returncode


def _show_status() -> int:
    """Display active model configurations and partitioned sub-database corpora."""
    print("=" * 60)
    print("           EKIP PLATFORM STATUS & ACTIVE CORPUS")
    print("=" * 60)
    print(f"Inference Model : {settings.inference_model} ({settings.inference_engine.value})")
    print(f"Embedding Model : {settings.embedding_model} ({settings.embedding_engine.value})")
    print(f"Chroma DB Path  : {settings.chroma_persist_dir}")
    print(f"Uploads Path    : {settings.uploaded_docs_dir}")
    print("-" * 60)

    archives = list_indexed_archives()
    if not archives:
        print("Active Archives : None (Database is empty)")
    else:
        print(f"Active Archives : {len(archives)} Partitioned Sub-Database(s)")
        for arc in archives:
            name = arc.get("archive_name") or arc.get("slug")
            chunks = arc.get("chunk_count", 0)
            docs = arc.get("doc_count", 0)
            print(f"  • {name:<30} | Chunks: {chunks:<4} | Docs: {docs}")
    print("=" * 60)
    return 0


def _run_reset(force: bool = False) -> int:
    """Wipe all partitioned Chroma sub-databases and uploaded raw documents.

    Args:
        force: Whether to skip confirmation prompt.

    Returns:
        Exit code (0 for success).
    """
    if not force:
        confirm = input("Are you sure you want to wipe all databases? (y/N): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Reset cancelled.")
            return 0

    clear_all_indexed_data()
    print("[EKIP] All vector sub-databases, uploaded files, and manifest references wiped.")
    return 0


def _show_manual() -> int:
    """Print comprehensive CLI user manual and on-the-go usage instructions."""
    manual = """
================================================================================
                      EKIP CLI MANUAL & USAGE GUIDE
================================================================================

1. CORE APPLICATION COMMANDS:
   ekip start [--port PORT]
     Launch the Streamlit interactive chat web assistant.
     Automatically verifies environment and bootstraps dependencies.
     Example: ekip start
     Example: ekip start --port 8505

   ekip api [--host HOST] [--port PORT] [--reload]
     Launch the high-performance FastAPI REST backend service with Swagger UI.
     Example: ekip api
     Example: ekip api --port 8000 --reload

2. DOCUMENT & STORAGE COMMANDS:
   ekip ingest [path_or_zip] [--clear]
     Ingest a documentation directory or .zip archive into ChromaDB.
     Supports .md, .pdf, .docx, .csv, .tsv, .html, .txt, .json, .yaml, .rst.
     Example: ekip ingest my_runbooks.zip
     Example: ekip ingest data/sample_docs --clear

   ekip status
     Display active inference/embedding engines and list all active sub-databases.
     Example: ekip status

   ekip reset [--force]
     Wipe all Chroma vector sub-databases, uploaded archives, and manifest entries.
     Example: ekip reset --force

3. TESTING & QUALITY ASSURANCE COMMANDS:
   ekip test [target]
     Execute isolated unit tests using pytest.
     Example: ekip test
     Example: ekip test tests/unit/test_retriever.py

   ekip test --lint
     Run the Ruff static code linter and formatting validation.
     Example: ekip test --lint

   ekip test --safe
     Run the Mypy strict type safety checker.
     Example: ekip test --safe

   ekip test --eval
     Run the 24-case offline ground-truth evaluation benchmark suite.
     Example: ekip test --eval

   ekip test --full
     Run complete quality checks (unit tests + linter + type checker).
     Example: ekip test --full

   ekip eval
     Direct shortcut to run the 24-case evaluation benchmark.
     Example: ekip eval

   ekip mcp
     Launch the standalone Model Context Protocol (MCP) server over stdio.
     Example: ekip mcp

4. HELP & DOCUMENTATION:
   ekip help
   ekip manual
     Display this command reference manual on-the-go.
================================================================================
"""
    print(manual.strip())
    return 0


def _add_core_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Register core application subparsers for start, api, and ingest.

    Args:
        subparsers: Root ArgumentParser subparsers action.
    """
    start_p = subparsers.add_parser("start", help="Launch Streamlit chat interface")
    start_p.add_argument("--port", type=int, default=None, help="Server port (default: 8501)")

    api_p = subparsers.add_parser("api", help="Launch FastAPI REST backend")
    api_p.add_argument("--host", type=str, default=None, help="Host address")
    api_p.add_argument("--port", type=int, default=None, help="Port number")
    api_p.add_argument("--reload", action="store_true", help="Enable auto-reload")

    ingest_p = subparsers.add_parser("ingest", help="Ingest documents or zip archive")
    ingest_p.add_argument(
        "source",
        nargs="?",
        default="data/sample_docs",
        help="Folder or .zip archive to ingest",
    )
    ingest_p.add_argument(
        "--clear",
        action="store_true",
        help="Clear previous databases and references before indexing",
    )


def _add_test_and_ops_subparsers(subparsers: argparse._SubParsersAction) -> None:
    """Register testing, status, reset, and manual subparsers.

    Args:
        subparsers: Root ArgumentParser subparsers action.
    """
    test_p = subparsers.add_parser("test", help="Run tests, linter, type checks, or eval")
    test_p.add_argument("target", nargs="?", default=None, help="Optional test file path")
    test_p.add_argument("--lint", action="store_true", help="Run Ruff linter")
    test_p.add_argument("--safe", action="store_true", help="Run Mypy type checker")
    test_p.add_argument("--eval", action="store_true", help="Run evaluation benchmark")
    test_p.add_argument("--full", action="store_true", help="Run tests, linter, and type checks")

    subparsers.add_parser("eval", help="Run 24-case evaluation benchmark")
    subparsers.add_parser("mcp", help="Run standalone MCP server")
    subparsers.add_parser("status", help="Inspect active models and indexed sub-databases")

    reset_p = subparsers.add_parser("reset", help="Wipe all sub-databases and files")
    reset_p.add_argument("--force", action="store_true", help="Skip confirmation prompt")

    subparsers.add_parser("help", help="Display full on-the-go user manual")
    subparsers.add_parser("manual", help="Display full on-the-go user manual")


def _build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for the EKIP CLI tool.

    Returns:
        Configured ArgumentParser with all registered subparsers.
    """
    parser = argparse.ArgumentParser(
        prog="ekip",
        description="EKIP — Engineering Knowledge Intelligence Platform CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")
    _add_core_subparsers(subparsers)
    _add_test_and_ops_subparsers(subparsers)
    return parser


def main(args: list[str] | None = None) -> int:
    """CLI dispatcher executing requested subcommand.

    Args:
        args: Optional list of CLI arguments (defaults to sys.argv[1:]).

    Returns:
        Integer exit code.
    """
    parser = _build_parser()
    parsed = parser.parse_args(args)

    if parsed.subcommand == "start":
        return _run_streamlit(port=parsed.port)
    if parsed.subcommand == "api":
        return _run_api(host=parsed.host, port=parsed.port, reload=parsed.reload)
    if parsed.subcommand == "ingest":
        return _run_ingest(source=parsed.source, clear=parsed.clear)
    if parsed.subcommand == "test":
        return _run_test_checks(
            lint=parsed.lint,
            safe=parsed.safe,
            eval_suite=parsed.eval,
            full=parsed.full,
            target=parsed.target,
        )
    if parsed.subcommand == "eval":
        return subprocess.run([sys.executable, "-m", "app.eval.run_eval"]).returncode
    if parsed.subcommand == "mcp":
        return subprocess.run([sys.executable, "-m", "mcp_server.server"]).returncode
    if parsed.subcommand == "status":
        return _show_status()
    if parsed.subcommand == "reset":
        return _run_reset(force=parsed.force)
    if parsed.subcommand in ("help", "manual"):
        return _show_manual()

    return _show_manual()


if __name__ == "__main__":
    sys.exit(main())
