# API Reference & Endpoints

## Overview
The EKIP REST API provides programmatic access to document indexing, knowledge querying, and system status checks. All endpoints return JSON responses and adhere to standard HTTP status codes. Base URL: `https://api.ekip.internal/v1`.

## Authentication
Pass bearer token or service API key in request headers:
- `Authorization: Bearer <access_token>`
- `X-API-Key: <service_key>`

## Endpoints

### POST /ask
Submits a query to the knowledge engine. The query is classified and routed either to RAG answer generation or to bounded agent execution.

**Request Body**:
```json
{
  "query": "What is the rollback command for backend?",
  "top_k": 5,
  "stream": false
}
```

**Response (200 OK)**:
```json
{
  "answer": "The rollback command is `ekip-deploy rollback --service ekip-backend --target previous`.",
  "status": "SUFFICIENT",
  "citations": [
    {
      "source": "deployment_runbook.md",
      "title": "Production Deployment & Rollback Runbook",
      "section": "Rollback Procedure",
      "quote": "Initiate Automated Rollback: Execute ekip-deploy rollback..."
    }
  ]
}
```

### POST /ingest
Triggers ingestion and vector indexing for specified document paths or collections.

**Request Body**:
```json
{
  "folder_path": "data/sample_docs",
  "force_reindex": false
}
```

**Response (200 OK)**:
```json
{
  "documents_loaded": 4,
  "chunks_indexed": 28,
  "status": "SUCCESS"
}
```

### GET /health
Returns current service health, version, and dependencies status.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "chroma": "connected",
  "gemini_api": "connected"
}
```

## Error Codes & Responses
- `400 Bad Request`: Invalid request payload or missing required fields.
- `401 Unauthorized`: Missing or expired authentication token.
- `403 Forbidden`: Insufficient RBAC permissions for requested operation.
- `404 Not Found`: Requested document or resource does not exist.
- `429 Too Many Requests`: Rate limit exceeded (standard quota: 100 requests per minute per IP).
- `500 Internal Server Error`: Unhandled application error; check request `trace_id`.
