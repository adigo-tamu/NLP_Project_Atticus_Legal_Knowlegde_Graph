"""Entity and relationship extraction modules."""

# Entity extraction
from atticus.extraction.entity_deduplicator import EntityDeduplicator
from atticus.extraction.entity_extractor import EntityExtractor
from atticus.extraction.entity_storage import EntityStorage
from atticus.extraction.entity_validator import EntityValidator

# Relationship extraction
from atticus.extraction.relationship_extractor import RelationshipExtractor
from atticus.extraction.relationship_validator import RelationshipValidator
from atticus.extraction.relationship_storage import RelationshipStorage
from atticus.extraction.coreference_resolver import CoreferenceResolver

# Pipelines
from atticus.extraction.pipeline import EntityExtractionPipeline
from atticus.extraction.complete_pipeline import CompleteExtractionPipeline

__all__ = [
    # Entity extraction
    "EntityExtractor",
    "EntityValidator",
    "EntityDeduplicator",
    "EntityStorage",
    # Relationship extraction
    "RelationshipExtractor",
    "RelationshipValidator",
    "RelationshipStorage",
    "CoreferenceResolver",
    # Pipelines
    "EntityExtractionPipeline",
    "CompleteExtractionPipeline",
]
