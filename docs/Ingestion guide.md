# Document Ingestion & Multi-Archive Storage Guide

## 1. Supported Document Formats

Engineering documentation comes in many shapes. EKIP natively parses **10 industry-standard formats**:

| Format | Extension | Underlying Parser | Extracted Metadata |
|---|---|---|---|
| **Markdown** | `.md` | Custom regex + heading parser | Source file, Section heading, Character offset |
| **PDF Documents** | `.pdf` | `pypdf` | Source file, Page number |
| **Word Documents** | `.docx` | `docx2txt` | Source file, Text blocks |
| **Tabular Data** | `.csv`, `.tsv` | Python `csv` | Source file, Row-structured records |
| **Web & Wiki Pages** | `.html` | `unstructured` | Source file, Structured DOM text |
| **Plain Text** | `.txt` | Native UTF-8 loader | Source file, Paragraphs |
| **Structured Specs** | `.json` | Native JSON parser | Source file, Formatted key-value hierarchy |
| **Configuration** | `.yaml`, `.yml` | Native YAML parser | Source file, Clean YAML blocks |
| **reStructuredText** | `.rst` | Native text parser | Source file, Section blocks |

All loaders are unified under `app/ingestion/loaders.py`.

---

## 2. Heading-Aware Chunking Pipeline

Splitting technical documents arbitrarily breaks code snippets, runbook steps, and API parameters.
EKIP implements **heading-aware chunking** ([`app/ingestion/chunker.py`](../app/ingestion/chunker.py)):

1. **Hierarchy Extraction**: Tracks `# H1`, `## H2`, and `### H3` headings across the document.
2. **Chunk Size & Overlap**: Default chunk size of `1000` characters with `200` characters of sliding overlap to preserve sentence boundaries.
3. **Deterministic Chunk IDs**: Every chunk receives a unique, reproducible identifier:
   `{document_name}_{chunk_index:03d}` (e.g. `auth_guide_002`).
4. **Metadata Preservation**: Every chunk is injected with:
   - `source`: Original document filename.
   - `heading`: Section title where the chunk belongs.
   - `chunk_id`: Deterministic ID.
   - `archive_name`: User-facing `.zip` archive name (for multi-corpus provenance).

---

## 3. Sub-Database Partitioning & Manifest Tracking

Instead of dumping every uploaded archive into a single flat collection, EKIP organizes indexes into **named sub-databases**:

```
data/
├── uploaded_docs/                      # Extracted source documents
│   ├── auth_service/                   # Subfolder for auth_service.zip
│   │   ├── oauth2_flow.md
│   │   └── jwt_spec.json
│   └── kubernetes_runbooks/            # Subfolder for kubernetes_runbooks.zip
│       └── rollback_canary.pdf
│
└── chroma_db/                          # Partitioned vector sub-databases
    ├── manifest.json                   # Archive catalog & chunk statistics
    ├── auth_service/                   # Chroma sub-database for auth_service
    │   └── chroma.sqlite3
    └── kubernetes_runbooks/            # Chroma sub-database for kubernetes
        └── chroma.sqlite3
```

### The Manifest (`manifest.json`)
The manifest catalog stores vital corpus metrics:
```json
{
  "archives": {
    "auth_service": {
      "archive_name": "auth_service.zip",
      "slug": "auth_service",
      "doc_count": 4,
      "chunk_count": 16,
      "indexed_at": "2026-11-08T00:15:00+00:00"
    }
  }
}
```

### Why Partitioning Matters:
- **No Accidental Stacking**: Ingesting a new archive will never pollute previous collections unless you want it to.
- **Incremental Addition**: You can add context over time (e.g., adding `billing_specs.zip` to existing `auth_service.zip`).
- **Complete Transparency**: The UI inspects `manifest.json` and active folders to show you exact archive names, document counts, and chunk statistics.

---

## 4. Ingestion Workflows

### Method A: Web UI Zip Upload (Recommended)
1. Start the platform: `ekip start`.
2. The initial landing screen prompts you to upload an engineering `.zip` archive.
3. Optional: Check `"Clear previous databases before indexing this archive"` if you want a fresh reference set.
4. Click **`🚀 Ingest into Sub-Database`**. The system unzips safely, chunks, embeds, and opens the chat assistant automatically.

### Method B: Unified CLI (`ekip ingest`)
You can ingest folders or `.zip` archives directly from your terminal:

```bash
# Ingest an archive into a new partitioned sub-database
ekip ingest path/to/runbooks.zip

# Ingest and clear all previous data first (fresh start)
ekip ingest path/to/runbooks.zip --clear

# Ingest a raw folder
ekip ingest data/sample_docs/
```

### Method C: Python SDK
```python
from app.ingestion.zip_handler import ingest_zip_archive

doc_count, chunk_count, slug = ingest_zip_archive(
    zip_source="path/to/my_docs.zip",
    clear_previous=False,
)
print(f"Indexed {chunk_count} chunks into sub-database '{slug}'.")
```

---

## 5. One-Click Database Reset

If you need to start fresh with zero stale documents:
- **In Streamlit**: Click **`🗑️ Clear Previous Data (Wipe All Sub-Databases)`** on the upload screen or in the sidebar.
- **Via CLI**: Run `ekip ingest <new_archive.zip> --clear`.
- **Programmatically**:
  ```python
  from app.ingestion.archive_manager import clear_all_indexed_data
  clear_all_indexed_data()
  ```
All sub-databases, uploaded raw files, and manifest references are removed in one operation.
