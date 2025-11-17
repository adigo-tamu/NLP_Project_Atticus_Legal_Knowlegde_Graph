"""
Custom exceptions for Project Atticus.

This module defines the exception hierarchy for handling various error conditions
throughout the application.
"""

from typing import Any, Dict, Optional


class AtticusException(Exception):
    """Base exception for all Atticus-related errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Atticus exception.

        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Optional additional error details
        """
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation of the exception."""
        base_msg = self.message
        if self.error_code:
            base_msg = f"[{self.error_code}] {base_msg}"
        if self.details:
            base_msg += f" | Details: {self.details}"
        return base_msg


class ConfigurationError(AtticusException):
    """Raised when there is a configuration error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)


class DocumentProcessingError(AtticusException):
    """Raised when document processing fails."""

    def __init__(self, message: str, document_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if document_id:
            details["document_id"] = document_id
        kwargs["details"] = details
        super().__init__(message, error_code="DOC_PROCESSING_ERROR", **kwargs)


class EntityExtractionError(AtticusException):
    """Raised when entity extraction fails."""

    def __init__(self, message: str, chunk_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if chunk_id:
            details["chunk_id"] = chunk_id
        kwargs["details"] = details
        super().__init__(message, error_code="ENTITY_EXTRACTION_ERROR", **kwargs)


class RelationshipExtractionError(AtticusException):
    """Raised when relationship extraction fails."""

    def __init__(self, message: str, chunk_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if chunk_id:
            details["chunk_id"] = chunk_id
        kwargs["details"] = details
        super().__init__(message, error_code="RELATIONSHIP_EXTRACTION_ERROR", **kwargs)


class GraphConstructionError(AtticusException):
    """Raised when knowledge graph construction fails."""

    def __init__(self, message: str, graph_operation: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if graph_operation:
            details["operation"] = graph_operation
        kwargs["details"] = details
        super().__init__(message, error_code="GRAPH_CONSTRUCTION_ERROR", **kwargs)


class LLMAPIError(AtticusException):
    """Raised when LLM API calls fail."""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if model:
            details["model"] = model
        if status_code:
            details["status_code"] = status_code
        kwargs["details"] = details
        super().__init__(message, error_code="LLM_API_ERROR", **kwargs)


class DatabaseError(AtticusException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str,
        database: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if database:
            details["database"] = database
        if operation:
            details["operation"] = operation
        kwargs["details"] = details
        super().__init__(message, error_code="DATABASE_ERROR", **kwargs)


class ValidationError(AtticusException):
    """Raised when data validation fails."""

    def __init__(self, message: str, validation_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if validation_type:
            details["validation_type"] = validation_type
        kwargs["details"] = details
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class RAGError(AtticusException):
    """Raised when RAG operations fail."""

    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if query:
            details["query"] = query
        kwargs["details"] = details
        super().__init__(message, error_code="RAG_ERROR", **kwargs)


class EvaluationError(AtticusException):
    """Raised when evaluation operations fail."""

    def __init__(self, message: str, metric: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if metric:
            details["metric"] = metric
        kwargs["details"] = details
        super().__init__(message, error_code="EVALUATION_ERROR", **kwargs)
