"""
Entity validation and quality control.

This module implements validation rules, confidence scoring adjustments,
and quality checks for extracted entities.
"""

import re
from typing import Dict, List, Optional, Tuple

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Entity, EntityType

logger = get_logger(__name__)


class EntityValidator:
    """Validator for entity extraction quality control."""

    def __init__(self):
        """Initialize entity validator."""
        self.config = get_config()
        self.confidence_threshold = self.config.entity_extraction.confidence_threshold

    def validate_entity(self, entity: Entity) -> Tuple[bool, Optional[str]]:
        """
        Validate a single entity.

        Args:
            entity: Entity to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not entity.text or not entity.text.strip():
            return False, "Entity text is empty"

        if len(entity.text) > 1000:
            return False, "Entity text too long (>1000 chars)"

        # Check confidence score
        if entity.confidence < 0.0 or entity.confidence > 1.0:
            return False, f"Invalid confidence score: {entity.confidence}"

        # Type-specific validation
        if entity.type == EntityType.FINANCIAL_TERM:
            if not self._validate_financial_term(entity):
                return False, "Invalid financial term format"

        elif entity.type == EntityType.TEMPORAL_ENTITY:
            if not self._validate_temporal_entity(entity):
                return False, "Invalid temporal entity format"

        elif entity.type == EntityType.LEGAL_PARTY:
            if not self._validate_legal_party(entity):
                return False, "Invalid legal party format"

        # All validations passed
        return True, None

    def _validate_financial_term(self, entity: Entity) -> bool:
        """Validate financial term entity."""
        text = entity.text.strip()

        # Should contain numbers or currency symbols
        has_number = re.search(r'\d', text)
        has_currency = re.search(r'[\$€£¥]', text)

        # At least one should be present
        if not (has_number or has_currency):
            return False

        return True

    def _validate_temporal_entity(self, entity: Entity) -> bool:
        """Validate temporal entity."""
        text = entity.text.strip()

        # Common temporal patterns
        temporal_patterns = [
            r'\d+\s*(?:day|week|month|year|hour|minute)s?',  # "30 days", "2 years"
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)',  # Month names
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # Dates: 01/15/2024
            r'within|after|before|by|until|from|to',  # Temporal prepositions
        ]

        for pattern in temporal_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # If no pattern matched but confidence is high, still accept
        if entity.confidence > 0.8:
            return True

        return False

    def _validate_legal_party(self, entity: Entity) -> bool:
        """Validate legal party entity."""
        text = entity.text.strip()

        # Should not be just a pronoun
        pronouns = ['it', 'he', 'she', 'they', 'we', 'you', 'i']
        if text.lower() in pronouns:
            return False

        # Should have reasonable length (at least 2 characters)
        if len(text) < 2:
            return False

        return True

    def adjust_confidence(self, entity: Entity) -> Entity:
        """
        Adjust entity confidence based on heuristics.

        Args:
            entity: Entity to adjust

        Returns:
            Entity with adjusted confidence
        """
        original_confidence = entity.confidence
        adjusted_confidence = original_confidence

        # Boost confidence for well-structured entities
        if entity.type == EntityType.LEGAL_PARTY:
            # Boost if contains legal entity indicators
            legal_indicators = ['inc.', 'llc', 'corp.', 'ltd.', 'corporation', 'company']
            if any(indicator in entity.text.lower() for indicator in legal_indicators):
                adjusted_confidence = min(1.0, adjusted_confidence + 0.1)

        elif entity.type == EntityType.FINANCIAL_TERM:
            # Boost if has clear currency symbol and number
            if re.search(r'[\$€£¥]\s*\d+', entity.text):
                adjusted_confidence = min(1.0, adjusted_confidence + 0.15)

        elif entity.type == EntityType.CLAUSE_REFERENCE:
            # Boost if matches standard section format
            if re.search(r'(?:Section|Article|Clause)\s+\d+', entity.text, re.IGNORECASE):
                adjusted_confidence = min(1.0, adjusted_confidence + 0.2)

        elif entity.type == EntityType.TEMPORAL_ENTITY:
            # Boost for specific dates
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', entity.text):
                adjusted_confidence = min(1.0, adjusted_confidence + 0.1)

        # Reduce confidence for very short entities (likely incomplete)
        if len(entity.text.strip()) < 3:
            adjusted_confidence = max(0.0, adjusted_confidence - 0.2)

        # Reduce confidence for very long entities (likely over-extraction)
        if len(entity.text.strip()) > 200:
            adjusted_confidence = max(0.0, adjusted_confidence - 0.1)

        # Log significant adjustments
        if abs(adjusted_confidence - original_confidence) > 0.05:
            logger.debug(
                f"Confidence adjusted for '{entity.text[:50]}': "
                f"{original_confidence:.2f} → {adjusted_confidence:.2f}"
            )

        # Update entity
        entity.confidence = adjusted_confidence
        return entity

    def filter_low_confidence(self, entities: List[Entity]) -> List[Entity]:
        """
        Filter out entities below confidence threshold.

        Args:
            entities: List of entities

        Returns:
            Filtered list of entities
        """
        filtered = [
            entity for entity in entities
            if entity.confidence >= self.confidence_threshold
        ]

        removed_count = len(entities) - len(filtered)
        if removed_count > 0:
            logger.info(
                f"Filtered {removed_count} entities below confidence threshold "
                f"({self.confidence_threshold})"
            )

        return filtered

    def validate_batch(self, entities: List[Entity]) -> List[Entity]:
        """
        Validate a batch of entities.

        Args:
            entities: List of entities to validate

        Returns:
            List of valid entities
        """
        valid_entities = []
        invalid_count = 0

        for entity in entities:
            # Adjust confidence
            entity = self.adjust_confidence(entity)

            # Validate
            is_valid, error_msg = self.validate_entity(entity)

            if is_valid:
                valid_entities.append(entity)
            else:
                invalid_count += 1
                logger.debug(f"Invalid entity '{entity.text[:50]}': {error_msg}")

        if invalid_count > 0:
            logger.info(f"Validation removed {invalid_count} invalid entities")

        # Filter by confidence
        valid_entities = self.filter_low_confidence(valid_entities)

        return valid_entities

    def get_entity_statistics(self, entities: List[Entity]) -> Dict:
        """
        Get statistics about extracted entities.

        Args:
            entities: List of entities

        Returns:
            Dictionary with statistics
        """
        if not entities:
            return {
                "total": 0,
                "by_type": {},
                "avg_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
            }

        # Count by type
        by_type = {}
        for entity in entities:
            type_name = entity.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Confidence statistics
        confidences = [e.confidence for e in entities]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        return {
            "total": len(entities),
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
            "min_confidence": round(min_confidence, 3),
            "max_confidence": round(max_confidence, 3),
        }
