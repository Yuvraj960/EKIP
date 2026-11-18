"""app.ingestion.archive_manager — Multi-archive partitioning and manifest tracking.

Manages sub-databases in ChromaDB per uploaded zip archive, maintains manifest
metadata of all active documentation corpora, and provides complete database reset.

Usage:
    from app.ingestion.archive_manager import list_indexed_archives, clear_all_indexed_data
    archives = list_indexed_archives()
    clear_all_indexed_data()
"""

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

MANIFEST_FILENAME: str = "manifest.json"
CHROMA_SQLITE_FILE: str = "chroma.sqlite3"
DEFAULT_ARCHIVE_SLUG: str = "archive"


def sanitize_archive_slug(name: str) -> str:
    """Normalize archive filename to a filesystem- and ChromaDB-safe slug.

    Args:
        name: Original zip archive filename.

    Returns:
        Clean alphanumeric slug with underscores.
    """
    clean_name = name.removesuffix(".zip").removesuffix(".ZIP")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", clean_name).strip("_").lower()
    return slug or DEFAULT_ARCHIVE_SLUG


def get_manifest_path(base_chroma_dir: Path | None = None) -> Path:
    """Return Path to the manifest.json file in the Chroma root directory.

    Args:
        base_chroma_dir: Optional Chroma persistence directory.

    Returns:
        Path object pointing to manifest.json.
    """
    root = base_chroma_dir or Path(settings.chroma_persist_dir)
    return root / MANIFEST_FILENAME


def load_manifest(base_chroma_dir: Path | None = None) -> dict[str, Any]:
    """Read archive metadata manifest from disk.

    Args:
        base_chroma_dir: Optional Chroma persistence directory.

    Returns:
        Manifest dictionary containing archives mapping.
    """
    manifest_path = get_manifest_path(base_chroma_dir)
    if not manifest_path.exists():
        return {"archives": {}}

    try:
        content = manifest_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if isinstance(data, dict) and "archives" in data:
            return data
    except (json.JSONDecodeError, OSError):
        pass

    return {"archives": {}}


def save_manifest(data: dict[str, Any], base_chroma_dir: Path | None = None) -> None:
    """Write archive metadata manifest to disk.

    Args:
        data: Manifest dictionary to persist.
        base_chroma_dir: Optional Chroma persistence directory.
    """
    manifest_path = get_manifest_path(base_chroma_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_archive(
    archive_name: str,
    slug: str,
    doc_count: int,
    chunk_count: int,
    base_chroma_dir: Path | None = None,
) -> dict[str, Any]:
    """Register or update an archive entry in the persistent manifest.

    Args:
        archive_name: User-facing archive filename.
        slug: Normalized subfolder identifier.
        doc_count: Number of extracted source documents.
        chunk_count: Number of indexed chunks in ChromaDB.
        base_chroma_dir: Optional Chroma persistence directory.

    Returns:
        Persisted archive metadata dictionary.
    """
    manifest = load_manifest(base_chroma_dir)
    entry = {
        "archive_name": archive_name,
        "slug": slug,
        "doc_count": doc_count,
        "chunk_count": chunk_count,
        "indexed_at": datetime.now(UTC).isoformat(),
    }
    manifest.setdefault("archives", {})[slug] = entry
    save_manifest(manifest, base_chroma_dir)
    return entry


def _discover_unregistered_subdirs(
    root: Path,
    known_slugs: set[str],
) -> list[dict[str, Any]]:
    """Find Chroma subdirectories on disk not currently in the manifest.

    Args:
        root: Chroma root persistence directory.
        known_slugs: Set of slugs already registered in manifest.

    Returns:
        List of synthesized archive metadata records.
    """
    unregistered: list[dict[str, Any]] = []
    if not root.exists():
        return unregistered

    for child in root.iterdir():
        if child.is_dir() and child.name not in known_slugs:
            if (child / CHROMA_SQLITE_FILE).exists():
                unregistered.append(
                    {
                        "archive_name": f"{child.name}.zip",
                        "slug": child.name,
                        "doc_count": 0,
                        "chunk_count": 0,
                        "indexed_at": datetime.now(UTC).isoformat(),
                    }
                )
    return unregistered


def list_indexed_archives(base_chroma_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return all active partitioned archives available in the vector store.

    Args:
        base_chroma_dir: Optional Chroma persistence directory.

    Returns:
        List of archive metadata dictionaries sorted by indexed_at.
    """
    root = base_chroma_dir or Path(settings.chroma_persist_dir)
    manifest = load_manifest(root)
    active: list[dict[str, Any]] = []

    for slug, entry in manifest.get("archives", {}).items():
        sub_db = root / slug
        if sub_db.exists() and (sub_db / CHROMA_SQLITE_FILE).exists():
            active.append(entry)

    known = {e["slug"] for e in active}
    active.extend(_discover_unregistered_subdirs(root, known))
    return sorted(active, key=lambda x: str(x.get("indexed_at", "")))


def clear_all_indexed_data(
    base_chroma_dir: Path | None = None,
    base_docs_dir: Path | None = None,
) -> None:
    """Completely wipe all Chroma sub-databases, uploaded files, and manifest.

    Args:
        base_chroma_dir: Optional Chroma persistence directory.
        base_docs_dir: Optional uploaded docs persistence directory.
    """
    chroma_root = base_chroma_dir or Path(settings.chroma_persist_dir)
    docs_root = base_docs_dir or Path(settings.uploaded_docs_dir)

    if chroma_root.exists():
        shutil.rmtree(chroma_root, ignore_errors=True)
    chroma_root.mkdir(parents=True, exist_ok=True)

    if docs_root.exists():
        shutil.rmtree(docs_root, ignore_errors=True)
    docs_root.mkdir(parents=True, exist_ok=True)


def delete_archive_data(
    slug: str,
    base_chroma_dir: Path | None = None,
    base_docs_dir: Path | None = None,
) -> bool:
    """Delete a single archive sub-database and its uploaded source files.

    Args:
        slug: Normalized archive identifier to delete.
        base_chroma_dir: Optional Chroma persistence directory.
        base_docs_dir: Optional uploaded docs persistence directory.

    Returns:
        True if archive existed and was deleted, False otherwise.
    """
    chroma_root = base_chroma_dir or Path(settings.chroma_persist_dir)
    docs_root = base_docs_dir or Path(settings.uploaded_docs_dir)

    sub_db = chroma_root / slug
    sub_docs = docs_root / slug
    deleted = False

    if sub_db.exists():
        shutil.rmtree(sub_db, ignore_errors=True)
        deleted = True
    if sub_docs.exists():
        shutil.rmtree(sub_docs, ignore_errors=True)
        deleted = True

    manifest = load_manifest(chroma_root)
    if slug in manifest.get("archives", {}):
        del manifest["archives"][slug]
        save_manifest(manifest, chroma_root)
        deleted = True

    return deleted
