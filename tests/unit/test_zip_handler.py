"""tests.unit.test_zip_handler — Unit tests for zip extraction and ingestion.

Verifies safe archive extraction, directory traversal (Zip Slip) rejection,
and automated ingestion pipeline integration.
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.zip_handler import (
    extract_zip_archive,
    ingest_zip_archive,
)


def _create_sample_zip_bytes(files: dict[str, str]) -> bytes:
    """Helper to create an in-memory zip archive from filename -> content mapping."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return buf.getvalue()


def test_extract_zip_archive_valid(tmp_path: Path) -> None:
    """Extract valid zip archive containing nested files into target directory."""
    zip_bytes = _create_sample_zip_bytes(
        {
            "guide.md": "# Engineering Guide\nContent here.",
            "specs/api.json": '{"service": "auth"}',
        }
    )

    target_dir = tmp_path / "extracted"
    extracted = extract_zip_archive(zip_bytes, target_dir=target_dir)

    assert len(extracted) == 2
    assert (target_dir / "guide.md").exists()
    assert (target_dir / "specs" / "api.json").exists()
    assert (target_dir / "guide.md").read_text(encoding="utf-8") == (
        "# Engineering Guide\nContent here."
    )


def test_extract_zip_archive_zip_slip_rejected(tmp_path: Path) -> None:
    """Raise ValueError when archive contains Zip Slip path traversal member."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "malicious payload")
    zip_bytes = buf.getvalue()

    target_dir = tmp_path / "sandbox"
    with pytest.raises(ValueError, match="Zip Slip"):
        extract_zip_archive(zip_bytes, target_dir=target_dir)


def test_extract_zip_archive_clears_prior_content(tmp_path: Path) -> None:
    """Ensure existing files in target directory are removed if clear_target is True."""
    target_dir = tmp_path / "cleanup"
    target_dir.mkdir(parents=True)
    old_file = target_dir / "old_doc.txt"
    old_file.write_text("prior content", encoding="utf-8")

    zip_bytes = _create_sample_zip_bytes({"new_doc.md": "# New Doc"})
    extracted = extract_zip_archive(zip_bytes, target_dir=target_dir, clear_target=True)

    assert not old_file.exists()
    assert len(extracted) == 1
    assert (target_dir / "new_doc.md").exists()


def test_extract_zip_archive_from_file_path(tmp_path: Path) -> None:
    """Extract zip from a Path on disk."""
    zip_path = tmp_path / "archive.zip"
    zip_bytes = _create_sample_zip_bytes({"test.txt": "hello world"})
    zip_path.write_bytes(zip_bytes)

    dest_dir = tmp_path / "out"
    extracted = extract_zip_archive(zip_path, target_dir=dest_dir)

    assert len(extracted) == 1
    assert (dest_dir / "test.txt").read_text(encoding="utf-8") == "hello world"


@patch("app.ingestion.zip_handler.run_ingestion_pipeline")
def test_ingest_zip_archive_success(mock_pipeline: MagicMock, tmp_path: Path) -> None:
    """Trigger ingestion pipeline on extracted documents and return counts and slug."""
    mock_pipeline.return_value = (3, 12)
    zip_bytes = _create_sample_zip_bytes({"runbook.md": "# Runbook"})

    target_docs = tmp_path / "docs" / "runbook_archive"
    target_chroma = tmp_path / "chroma" / "runbook_archive"
    docs_count, chunks_count, slug = ingest_zip_archive(
        zip_bytes,
        archive_name="runbook_archive.zip",
        target_docs_dir=target_docs,
        target_chroma_dir=target_chroma,
    )

    assert docs_count == 3
    assert chunks_count == 12
    assert slug == "runbook_archive"
    mock_pipeline.assert_called_once_with(
        folder_path=target_docs,
        persist_dir=str(target_chroma),
        collection_name=slug,
        archive_name="runbook_archive.zip",
    )


def test_ingest_zip_archive_empty(tmp_path: Path) -> None:
    """Return (0, 0, slug) when zip archive has no extractable document files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("empty_dir/", "")
    zip_bytes = buf.getvalue()

    target_docs = tmp_path / "empty_docs"
    docs_count, chunks_count, slug = ingest_zip_archive(
        zip_bytes,
        archive_name="empty.zip",
        target_docs_dir=target_docs,
        target_chroma_dir=tmp_path / "empty_chroma",
    )

    assert docs_count == 0
    assert chunks_count == 0
    assert slug == "empty"
