"""app.ingestion.zip_handler — Secure zip archive extraction and ingestion.

Provides utilities to safely unpack uploaded zip archives containing engineering
documentation into partitioned subfolders and trigger automatic ingestion into
per-archive ChromaDB sub-databases.

Usage:
    from app.ingestion.zip_handler import ingest_zip_archive
    doc_count, chunk_count, slug = ingest_zip_archive(uploaded_file)
"""

import io
import shutil
import zipfile
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.ingestion.archive_manager import (
    clear_all_indexed_data,
    record_archive,
    sanitize_archive_slug,
)
from app.ingestion.run_ingest import run_ingestion_pipeline

ZipSource = str | Path | BinaryIO | bytes
DEFAULT_ARCHIVE_NAME: str = "archive.zip"


def _resolve_archive_name(zip_source: ZipSource, explicit_name: str | None) -> str:
    """Resolve user-facing archive name from parameter or source object.

    Args:
        zip_source: File path, open binary stream, or raw byte buffer.
        explicit_name: Optional explicit archive name string.

    Returns:
        String filename for the archive.
    """
    if explicit_name:
        return explicit_name
    if isinstance(zip_source, (str, Path)):
        return Path(zip_source).name
    name_attr = getattr(zip_source, "name", None)
    if name_attr:
        return str(name_attr)
    return DEFAULT_ARCHIVE_NAME


def _prepare_target_directory(target_dir: Path, clear_target: bool) -> None:
    """Ensure target directory exists and optionally remove prior contents.

    Args:
        target_dir: Target directory path.
        clear_target: Whether to remove existing files before extraction.
    """
    if clear_target and target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)


def _open_zip_file(zip_source: ZipSource) -> zipfile.ZipFile:
    """Return an open ZipFile instance from path, file-like object, or bytes.

    Args:
        zip_source: File path, open binary stream, or raw byte buffer.

    Returns:
        Open ZipFile instance.
    """
    if isinstance(zip_source, bytes):
        return zipfile.ZipFile(io.BytesIO(zip_source))
    return zipfile.ZipFile(zip_source)


def _extract_member_safely(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    target_dir: Path,
) -> Path | None:
    """Safely extract a single zip member preventing directory traversal (Zip Slip).

    Args:
        archive: Open ZipFile instance.
        member: Archive member to extract.
        target_dir: Target root directory for extraction.

    Returns:
        Extracted destination Path, or None if member is a directory.

    Raises:
        ValueError: If Zip Slip path traversal attempt is detected.
    """
    dest_path = (target_dir / member.filename).resolve()
    resolved_root = target_dir.resolve()

    if not dest_path.is_relative_to(resolved_root):
        raise ValueError(
            f"Zip Slip security vulnerability detected in archive member: {member.filename}"
        )

    if member.is_dir():
        return None

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member) as src, dest_path.open("wb") as dst:
        shutil.copyfileobj(src, dst)

    return dest_path


def extract_zip_archive(
    zip_source: ZipSource,
    target_dir: Path | None = None,
    clear_target: bool = True,
) -> list[Path]:
    """Safely extract all files from a zip archive into a destination directory.

    Args:
        zip_source: File path, open binary stream, or raw byte buffer.
        target_dir: Target directory for files. Defaults to settings.uploaded_docs_dir.
        clear_target: Whether to clean target_dir before extraction.

    Returns:
        List of Path objects for all safely extracted files.
    """
    dest_dir = target_dir or Path(settings.uploaded_docs_dir)
    _prepare_target_directory(dest_dir, clear_target)

    extracted_files: list[Path] = []
    with _open_zip_file(zip_source) as archive:
        for member in archive.infolist():
            extracted = _extract_member_safely(archive, member, dest_dir)
            if extracted is not None:
                extracted_files.append(extracted)

    return extracted_files


def ingest_zip_archive(
    zip_source: ZipSource,
    archive_name: str | None = None,
    target_docs_dir: Path | None = None,
    target_chroma_dir: Path | None = None,
    clear_previous: bool = False,
) -> tuple[int, int, str]:
    """Extract a zip archive into a partitioned sub-database and run ingestion.

    Args:
        zip_source: File path, open binary stream, or raw byte buffer.
        archive_name: Optional user-facing archive filename.
        target_docs_dir: Optional document extraction directory override.
        target_chroma_dir: Optional Chroma persistence directory override.
        clear_previous: Whether to wipe all previously indexed data first.

    Returns:
        Tuple of (loaded_documents_count, indexed_chunks_count, archive_slug).
    """
    if clear_previous:
        clear_all_indexed_data()

    resolved_name = _resolve_archive_name(zip_source, archive_name)
    slug = sanitize_archive_slug(resolved_name)

    dest_docs = target_docs_dir or (Path(settings.uploaded_docs_dir) / slug)
    dest_chroma = target_chroma_dir or (Path(settings.chroma_persist_dir) / slug)

    extracted = extract_zip_archive(zip_source, target_dir=dest_docs, clear_target=True)
    if not extracted:
        return 0, 0, slug

    doc_count, chunk_count = run_ingestion_pipeline(
        folder_path=dest_docs,
        persist_dir=str(dest_chroma),
        collection_name=slug,
        archive_name=resolved_name,
    )

    base_chroma = target_chroma_dir.parent if target_chroma_dir else None
    record_archive(
        archive_name=resolved_name,
        slug=slug,
        doc_count=doc_count,
        chunk_count=chunk_count,
        base_chroma_dir=base_chroma,
    )

    return doc_count, chunk_count, slug
