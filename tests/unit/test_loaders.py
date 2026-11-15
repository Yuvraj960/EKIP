"""tests.unit.test_loaders — Unit tests for app.ingestion.loaders."""

from pathlib import Path

import pytest
from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredHTMLLoader,
)

from app.ingestion.loaders import get_loader_for_file, load_documents, load_file


def test_load_single_markdown_file(tmp_path: Path) -> None:
    """Verify that a markdown file is loaded with normalized source metadata."""
    doc_path = tmp_path / "sample_guide.md"
    doc_path.write_text("# Guide\n\nThis is sample content.", encoding="utf-8")

    docs = load_file(doc_path)
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "sample_guide.md"
    assert docs[0].metadata["extension"] == "md"
    assert "This is sample content." in docs[0].page_content


def test_load_csv_file(tmp_path: Path) -> None:
    """Verify that a CSV file is loaded and parsed row-by-row into documents."""
    csv_path = tmp_path / "services.csv"
    csv_content = "service,status,port\nauth,active,8080\napi,active,8000\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    docs = load_file(csv_path)
    assert len(docs) == 2
    assert docs[0].metadata["source"] == "services.csv"
    assert docs[0].metadata["extension"] == "csv"
    assert "service: auth" in docs[0].page_content


def test_load_tsv_file(tmp_path: Path) -> None:
    """Verify that a TSV file is parsed with tab delimiter into documents."""
    tsv_path = tmp_path / "metrics.tsv"
    tsv_path.write_text("metric\tthreshold\tseverity\nerror_rate\t5%\tSEV-1\n", encoding="utf-8")

    docs = load_file(tsv_path)
    assert len(docs) == 1
    assert docs[0].metadata["source"] == "metrics.tsv"
    assert docs[0].metadata["extension"] == "tsv"
    assert "metric: error_rate" in docs[0].page_content


def test_load_structured_text_files(tmp_path: Path) -> None:
    """Verify loading json, yaml, and rst files via TextLoader."""
    json_path = tmp_path / "schema.json"
    json_path.write_text('{"endpoint": "/ask", "version": "1.0"}', encoding="utf-8")

    yaml_path = tmp_path / "deploy.yaml"
    yaml_path.write_text("replicas: 3\nimage: app:latest", encoding="utf-8")

    rst_path = tmp_path / "docs.rst"
    rst_path.write_text("API Overview\n============\nDetails here.", encoding="utf-8")

    docs_json = load_file(json_path)
    docs_yaml = load_file(yaml_path)
    docs_rst = load_file(rst_path)

    assert len(docs_json) == 1 and docs_json[0].metadata["extension"] == "json"
    assert len(docs_yaml) == 1 and docs_yaml[0].metadata["extension"] == "yaml"
    assert len(docs_rst) == 1 and docs_rst[0].metadata["extension"] == "rst"


def test_get_loader_for_all_supported_types(tmp_path: Path) -> None:
    """Verify get_loader_for_file returns correct loader instances for existing files."""
    files = {
        "a.md": TextLoader,
        "b.txt": TextLoader,
        "c.rst": TextLoader,
        "d.json": TextLoader,
        "e.yaml": TextLoader,
        "f.csv": CSVLoader,
        "g.tsv": CSVLoader,
        "h.pdf": PyPDFLoader,
        "i.html": UnstructuredHTMLLoader,
        "j.docx": Docx2txtLoader,
    }
    for name, expected_cls in files.items():
        file_path = tmp_path / name
        file_path.write_bytes(b"%PDF-1.4" if name.endswith(".pdf") else b"content")
        loader = get_loader_for_file(file_path)
        assert isinstance(loader, expected_cls)


def test_load_file_not_found(tmp_path: Path) -> None:
    """Verify FileNotFoundError is raised when file does not exist."""
    missing = tmp_path / "nonexistent.md"
    with pytest.raises(FileNotFoundError):
        load_file(missing)


def test_unsupported_file_extension(tmp_path: Path) -> None:
    """Verify ValueError is raised for unsupported file types."""
    unsupported = tmp_path / "file.exe"
    unsupported.write_bytes(b"MZ\x90")
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_loader_for_file(unsupported)


def test_load_documents_from_directory(tmp_path: Path) -> None:
    """Verify that all supported documents in a directory are loaded and unhandled ones ignored."""
    (tmp_path / "doc1.md").write_text("# Doc 1\nContent 1", encoding="utf-8")
    (tmp_path / "doc2.txt").write_text("Text content 2", encoding="utf-8")
    (tmp_path / "doc3.csv").write_text("col1,col2\nval1,val2", encoding="utf-8")
    (tmp_path / "doc4.json").write_text('{"key": "val"}', encoding="utf-8")
    (tmp_path / "ignore.bin").write_bytes(b"\x00\x01\x02")

    loaded = load_documents(tmp_path)
    sources = [doc.metadata["source"] for doc in loaded]
    assert "doc1.md" in sources
    assert "doc2.txt" in sources
    assert "doc3.csv" in sources
    assert "doc4.json" in sources
    assert "ignore.bin" not in sources


def test_load_documents_invalid_directory(tmp_path: Path) -> None:
    """Verify NotADirectoryError is raised for non-directory paths."""
    fake_dir = tmp_path / "does_not_exist"
    with pytest.raises(NotADirectoryError):
        load_documents(fake_dir)
