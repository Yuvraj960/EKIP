"""app.ingestion.loaders — Document file loaders.

Loads engineering documents (.md, .pdf, .docx, .csv, .tsv, .html, .txt, .json, .yaml)
into LangChain Document objects with standardized metadata.

Usage:
    from pathlib import Path
    from app.ingestion.loaders import load_documents
    docs = load_documents(Path("data/sample_docs/"))
"""

from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
)
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langsmith import traceable

from app.core.tracing import (
    META_MODULE,
    RUN_TYPE_CHAIN,
    TAG_EKIP,
    TAG_INGESTION,
    add_trace_metadata,
    add_trace_tags,
)

TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".md", ".markdown", ".txt", ".rst", ".json", ".yaml", ".yml"}
)
HTML_EXTENSIONS: frozenset[str] = frozenset({".html", ".htm"})
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        *TEXT_EXTENSIONS,
        *HTML_EXTENSIONS,
        ".pdf",
        ".docx",
        ".csv",
        ".tsv",
    }
)
DEFAULT_ENCODING: str = "utf-8"


def get_loader_for_file(file_path: Path) -> BaseLoader:
    """Instantiate and return the appropriate LangChain loader for a file.

    Args:
        file_path: Path to the target document.

    Returns:
        Configured BaseLoader instance for the document format.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = file_path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return TextLoader(str(file_path), encoding=DEFAULT_ENCODING)
    if ext == ".csv":
        return CSVLoader(str(file_path), encoding=DEFAULT_ENCODING)
    if ext == ".tsv":
        return CSVLoader(
            str(file_path),
            encoding=DEFAULT_ENCODING,
            csv_args={"delimiter": "\t"},
        )
    if ext == ".pdf":
        return PyPDFLoader(str(file_path))
    if ext in HTML_EXTENSIONS:
        return UnstructuredHTMLLoader(str(file_path))
    if ext == ".docx":
        return Docx2txtLoader(str(file_path))

    raise ValueError(f"Unsupported file format: {ext}")


@traceable(
    name="ingestion.load_file",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "file"],
    metadata={META_MODULE: "app.ingestion.loaders"},
)
def load_file(file_path: Path) -> list[Document]:
    """Load a single file and return a list of Document objects with clean metadata.

    Args:
        file_path: Path to the document file.

    Returns:
        List of Document instances with normalized source metadata.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file extension is not supported.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    loader = get_loader_for_file(file_path)
    loaded_docs = loader.load()

    normalized_docs: list[Document] = []
    for doc in loaded_docs:
        updated_metadata = dict(doc.metadata)
        updated_metadata["source"] = file_path.name
        updated_metadata["extension"] = file_path.suffix.lower().lstrip(".")
        normalized_docs.append(
            Document(
                page_content=doc.page_content,
                metadata=updated_metadata,
            )
        )

    return normalized_docs


@traceable(
    name="ingestion.load_documents",
    run_type=RUN_TYPE_CHAIN,
    tags=[TAG_EKIP, TAG_INGESTION, "loaders"],
    metadata={META_MODULE: "app.ingestion.loaders"},
)
def load_documents(folder: Path) -> list[Document]:
    """Load all supported documents from a directory recursively.

    Args:
        folder: Path to folder containing documents.

    Returns:
        List of loaded Document objects sorted by filename.

    Raises:
        NotADirectoryError: If the provided path is not an existing directory.
    """
    if not folder.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder}")

    all_docs: list[Document] = []
    matched_files = sorted(
        f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    for file_path in matched_files:
        all_docs.extend(load_file(file_path))

    add_trace_tags([f"files_loaded:{len(matched_files)}"])
    add_trace_metadata({"files_count": len(matched_files), "docs_count": len(all_docs)})
    return all_docs
