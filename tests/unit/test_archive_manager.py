"""tests.unit.test_archive_manager — Unit tests for multi-archive partitioning.

Verifies slug sanitization, manifest tracking, sub-database listing, and database wipe.
"""

from pathlib import Path

from app.ingestion.archive_manager import (
    CHROMA_SQLITE_FILE,
    clear_all_indexed_data,
    delete_archive_data,
    list_indexed_archives,
    load_manifest,
    record_archive,
    sanitize_archive_slug,
)


def test_sanitize_archive_slug() -> None:
    """Normalize filenames with extensions and symbols to clean alphanumeric slugs."""
    assert sanitize_archive_slug("Auth Guide (v1.2).zip") == "auth_guide_v1_2"
    assert sanitize_archive_slug("Deploy-Runbook_2026.ZIP") == "deploy_runbook_2026"
    assert sanitize_archive_slug("SimpleDocs.zip") == "simpledocs"
    assert sanitize_archive_slug("!@#$%^&*().zip") == "archive"


def test_record_and_load_manifest(tmp_path: Path) -> None:
    """Record archive entry in manifest and verify retrieval."""
    entry = record_archive(
        archive_name="auth_docs.zip",
        slug="auth_docs",
        doc_count=4,
        chunk_count=16,
        base_chroma_dir=tmp_path,
    )

    assert entry["archive_name"] == "auth_docs.zip"
    assert entry["slug"] == "auth_docs"
    assert entry["doc_count"] == 4
    assert entry["chunk_count"] == 16

    manifest = load_manifest(tmp_path)
    assert "auth_docs" in manifest.get("archives", {})
    assert manifest["archives"]["auth_docs"]["chunk_count"] == 16


def test_list_indexed_archives_active_and_unregistered(tmp_path: Path) -> None:
    """List both manifest-registered and unregistered sub-databases on disk."""
    record_archive(
        archive_name="auth_docs.zip",
        slug="auth_docs",
        doc_count=4,
        chunk_count=16,
        base_chroma_dir=tmp_path,
    )
    (tmp_path / "auth_docs").mkdir()
    (tmp_path / "auth_docs" / CHROMA_SQLITE_FILE).touch()

    # Create unrecorded sub-database
    (tmp_path / "legacy_runbooks").mkdir()
    (tmp_path / "legacy_runbooks" / CHROMA_SQLITE_FILE).touch()

    archives = list_indexed_archives(tmp_path)
    slugs = {a["slug"] for a in archives}
    assert "auth_docs" in slugs
    assert "legacy_runbooks" in slugs


def test_clear_all_indexed_data(tmp_path: Path) -> None:
    """Wipe all sub-databases and uploaded files on reset."""
    chroma_dir = tmp_path / "chroma"
    docs_dir = tmp_path / "docs"

    (chroma_dir / "sub_db").mkdir(parents=True)
    (chroma_dir / "sub_db" / "file.txt").write_text("db data")
    (docs_dir / "sub_db").mkdir(parents=True)
    (docs_dir / "sub_db" / "doc.md").write_text("raw doc")

    clear_all_indexed_data(base_chroma_dir=chroma_dir, base_docs_dir=docs_dir)

    assert chroma_dir.exists()
    assert docs_dir.exists()
    assert len(list(chroma_dir.iterdir())) == 0
    assert len(list(docs_dir.iterdir())) == 0


def test_delete_archive_data(tmp_path: Path) -> None:
    """Delete a specific sub-database folder and clean manifest."""
    chroma_dir = tmp_path / "chroma"
    docs_dir = tmp_path / "docs"

    record_archive(
        archive_name="target.zip",
        slug="target",
        doc_count=2,
        chunk_count=8,
        base_chroma_dir=chroma_dir,
    )
    (chroma_dir / "target").mkdir(parents=True)
    (docs_dir / "target").mkdir(parents=True)

    deleted = delete_archive_data("target", base_chroma_dir=chroma_dir, base_docs_dir=docs_dir)
    assert deleted is True
    assert not (chroma_dir / "target").exists()
    assert not (docs_dir / "target").exists()

    manifest = load_manifest(chroma_dir)
    assert "target" not in manifest.get("archives", {})
