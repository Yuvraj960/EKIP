"""app.core.errors — Custom exception classes for EKIP.

Using custom exceptions (instead of generic Exception) makes error handling
cleaner and lets the API return meaningful error messages.

Usage:
    from app.core.errors import DocumentNotFoundError, PermissionDeniedError
    raise DocumentNotFoundError(f"No document with id: {doc_id}")
"""


class EKIPError(Exception):
    """Base exception for all EKIP application errors."""


class DocumentNotFoundError(EKIPError):
    """Raised when a requested document is not in the index."""


class InsufficientEvidenceError(EKIPError):
    """Raised when retrieved chunks don't meet the minimum threshold."""


class PermissionDeniedError(PermissionError, EKIPError):
    """Raised when an agent tries to call a tool not in the allowlist."""


class IngestionError(EKIPError):
    """Raised when document ingestion fails."""


class ValidationError(EKIPError):
    """Raised when LLM output fails Pydantic validation."""
