"""app — Engineering Knowledge Intelligence Platform main package.

This package contains all application modules:
- api/        FastAPI routes and Pydantic schemas
- core/       Settings, logging, error handling, permissions
- ingestion/  Document loaders, chunking, ChromaDB indexing
- retrieval/  Chunk retriever and context formatter
- chains/     LCEL pipelines for classification and answering
- agents/     Bounded agent and tool implementations
- mcp/        MCP protocol client
- services/   Application orchestration layer
"""
