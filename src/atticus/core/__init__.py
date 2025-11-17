"""Core utilities and base classes for Project Atticus."""

from atticus.core.config import Config, get_config
from atticus.core.logger import get_logger
from atticus.core.exceptions import (
    AtticusException,
    ConfigurationError,
    DocumentProcessingError,
    EntityExtractionError,
    RelationshipExtractionError,
    GraphConstructionError,
    LLMAPIError,
    DatabaseError,
)

__all__ = [
    "Config",
    "get_config",
    "get_logger",
    "AtticusException",
    "ConfigurationError",
    "DocumentProcessingError",
    "EntityExtractionError",
    "RelationshipExtractionError",
    "GraphConstructionError",
    "LLMAPIError",
    "DatabaseError",
]
