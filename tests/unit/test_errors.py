"""tests.unit.test_errors — Unit tests for EKIP custom exception hierarchy."""

import pytest

from app.core.errors import (
    DocumentNotFoundError,
    EKIPError,
    IngestionError,
    InsufficientEvidenceError,
    PermissionDeniedError,
    ValidationError,
)


def test_ekip_error_hierarchy() -> None:
    """Verify that all EKIP custom exceptions inherit from EKIPError."""
    assert issubclass(DocumentNotFoundError, EKIPError)
    assert issubclass(InsufficientEvidenceError, EKIPError)
    assert issubclass(PermissionDeniedError, EKIPError)
    assert issubclass(PermissionDeniedError, PermissionError)
    assert issubclass(IngestionError, EKIPError)
    assert issubclass(ValidationError, EKIPError)


def test_raising_ekip_exceptions() -> None:
    """Verify raising and catching custom exceptions with messages."""
    with pytest.raises(DocumentNotFoundError) as exc_info:
        raise DocumentNotFoundError("Missing doc: doc-1")
    assert "Missing doc: doc-1" in str(exc_info.value)

    with pytest.raises(PermissionDeniedError) as perm_info:
        raise PermissionDeniedError("Tool blocked")
    assert "Tool blocked" in str(perm_info.value)
