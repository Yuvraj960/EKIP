"""app.ingestion — Document processing pipeline.

Modules:
- loaders.py     Load .md, .pdf, .html files into LangChain Document objects
- chunker.py     Split documents into sized chunks with rich metadata
- indexer.py     Embed chunks with Gemini and store in ChromaDB
- run_ingest.py  CLI entry point: python -m app.ingestion.run_ingest <folder>
"""
