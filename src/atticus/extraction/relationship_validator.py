"""
Relationship validation and quality control.

This module implements validation rules, confidence scoring adjustments,
and quality checks for extracted relationships.
"""

from typing import Dict, List, Optional, Tuple

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Relationship, RelationshipType

logger = get_logger(__name__)


class RelationshipValidator:
    """Validator for relationship extraction quality control."""

    def __init__(self):
        """Initialize relationship validator."""
        self.config = get_config()
        self.confidence_threshold = self.config.relationship_extraction.confidence_threshold

    def validate_relationship(self, relationship: Relationship) -> Tuple[bool, Optional[str]]:
        """
        Validate a single relationship.

        Args:
            relationship: Relationship to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not relationship.source_entity_id:
            return False, "Missing source entity ID"

        if not relationship.target_entity_id:
            return False, "Missing target entity ID"

        # Check for self-loops (usually not valid)
        if relationship.source_entity_id == relationship.target_entity_id:
            return False, "Self-loop relationship (source == target)"

        # Check confidence score
        if relationship.confidence < 0.0 or relationship.confidence > 1.0:
            return False, f"Invalid confidence score: {relationship.confidence}"

        # Type-specific validation
        if relationship.relationship_type == RelationshipType.FINANCIALLY_RELATES:
            if not self._validate_financial_relationship(relationship):
                return False, "Invalid financial relationship"

        elif relationship.relationship_type == RelationshipType.TEMPORALLY_PRECEDES:
            if not self._validate_temporal_relationship(relationship):
                return False, "Invalid temporal relationship"

        # All validations passed
        return True, None

    def _validate_financial_relationship(self, relationship: Relationship) -> bool:
        """Validate financial relationship has required properties."""
        # Should have financial information in properties
        if not relationship.properties:
            return True  # Optional properties

        # If properties exist, check for financial indicators
        financial_keys = ["amount", "currency", "payment_type", "frequency"]
        has_financial_info = any(key in relationship.properties for key in financial_keys)

        return has_financial_info or not relationship.properties

    def _validate_temporal_relationship(self, relationship: Relationship) -> bool:
        """Validate temporal relationship has temporal properties."""
        if not relationship.properties:
            return True  # Optional properties

        # If properties exist, check for temporal indicators
        temporal_keys = ["time_gap", "duration", "temporal_constraint", "deadline"]
        has_temporal_info = any(key in relationship.properties for key in temporal_keys)

        return has_temporal_info or not relationship.properties

    def adjust_confidence(self, relationship: Relationship) -> Relationship:
        """
        Adjust relationship confidence based on heuristics.

        Args:
            relationship: Relationship to adjust

        Returns:
            Relationship with adjusted confidence
        """
        original_confidence = relationship.confidence
        adjusted_confidence = original_confidence

        # Boost for explicit evidence
        if relationship.evidence:
            evidence_lower = relationship.evidence.lower()

            # Legal language indicators boost confidence
            legal_indicators = {
                "shall": 0.1,
                "must": 0.1,
                "hereby": 0.15,
                "pursuant to": 0.1,
                "subject to": 0.1,
                "grants": 0.15,
                "governed by": 0.15,
            }

            for indicator, boost in legal_indicators.items():
                if indicator in evidence_lower:
                    adjusted_confidence = min(1.0, adjusted_confidence + boost)
                    break  # Only apply one boost

        # Boost for reasoning (if chain-of-thought was used)
        if relationship.reasoning and len(relationship.reasoning) > 100:
            # Detailed reasoning suggests more careful analysis
            adjusted_confidence = min(1.0, adjusted_confidence + 0.05)

        # Type-specific boosts
        if relationship.relationship_type == RelationshipType.GRANTS_RIGHT:
            # Rights are usually explicit
            if relationship.evidence and "grant" in relationship.evidence.lower():
                adjusted_confidence = min(1.0, adjusted_confidence + 0.1)

        elif relationship.relationship_type == RelationshipType.OBLIGATES:
            # Obligations with "shall" or "must"
            if relationship.evidence:
                evidence_lower = relationship.evidence.lower()
                if "shall" in evidence_lower or "must" in evidence_lower:
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.1)

        # Reduce confidence for very long evidence (may be noisy)
        if relationship.evidence and len(relationship.evidence) > 500:
            adjusted_confidence = max(0.0, adjusted_confidence - 0.1)

        # Log significant adjustments
        if abs(adjusted_confidence - original_confidence) > 0.05:
            logger.debug(
                f"Confidence adjusted for {relationship.relationship_type.value}: "
                f"{original_confidence:.2f} → {adjusted_confidence:.2f}"
            )

        # Update relationship
        relationship.confidence = adjusted_confidence
        return relationship

    def filter_low_confidence(self, relationships: List[Relationship]) -> List[Relationship]:
        """
        Filter out relationships below confidence threshold.

        Args:
            relationships: List of relationships

        Returns:
            Filtered list of relationships
        """
        filtered = [
            rel for rel in relationships
            if rel.confidence >= self.confidence_threshold
        ]

        removed_count = len(relationships) - len(filtered)
        if removed_count > 0:
            logger.info(
                f"Filtered {removed_count} relationships below confidence threshold "
                f"({self.confidence_threshold})"
            )

        return filtered

    def validate_batch(self, relationships: List[Relationship]) -> List[Relationship]:
        """
        Validate a batch of relationships.

        Args:
            relationships: List of relationships to validate

        Returns:
            List of valid relationships
        """
        valid_relationships = []
        invalid_count = 0

        for relationship in relationships:
            # Adjust confidence
            relationship = self.adjust_confidence(relationship)

            # Validate
            is_valid, error_msg = self.validate_relationship(relationship)

            if is_valid:
                valid_relationships.append(relationship)
            else:
                invalid_count += 1
                logger.debug(
                    f"Invalid relationship {relationship.id}: {error_msg}"
                )

        if invalid_count > 0:
            logger.info(f"Validation removed {invalid_count} invalid relationships")

        # Filter by confidence
        valid_relationships = self.filter_low_confidence(valid_relationships)

        return valid_relationships

    def detect_contradictions(
        self,
        relationships: List[Relationship],
    ) -> List[Tuple[Relationship, Relationship]]:
        """
        Detect potential contradictory relationships.

        Args:
            relationships: List of relationships

        Returns:
            List of (rel1, rel2) tuples that may contradict
        """
        contradictions = []

        # Look for CONTRADICTS relationships
        contradiction_rels = [
            r for r in relationships
            if r.relationship_type == RelationshipType.CONTRADICTS
        ]

        for rel in contradiction_rels:
            # Find the entities involved
            # This is a simplified check - could be enhanced
            contradictions.append((rel, rel))  # Placeholder

        logger.info(f"Detected {len(contradictions)} potential contradictions")
        return contradictions

    def get_relationship_statistics(self, relationships: List[Relationship]) -> Dict:
        """
        Get statistics about extracted relationships.

        Args:
            relationships: List of relationships

        Returns:
            Dictionary with statistics
        """
        if not relationships:
            return {
                "total": 0,
                "by_type": {},
                "avg_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "with_evidence": 0,
                "with_reasoning": 0,
            }

        # Count by type
        by_type = {}
        for rel in relationships:
            type_name = rel.relationship_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # Confidence statistics
        confidences = [r.confidence for r in relationships]
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)

        # Evidence and reasoning
        with_evidence = sum(1 for r in relationships if r.evidence)
        with_reasoning = sum(1 for r in relationships if r.reasoning)

        return {
            "total": len(relationships),
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
            "min_confidence": round(min_confidence, 3),
            "max_confidence": round(max_confidence, 3),
            "with_evidence": with_evidence,
            "with_reasoning": with_reasoning,
        }

    def deduplicate_relationships(
        self,
        relationships: List[Relationship],
    ) -> List[Relationship]:
        """
        Remove duplicate relationships.

        Two relationships are considered duplicates if they have:
        - Same source entity
        - Same target entity
        - Same relationship type

        Args:
            relationships: List of relationships

        Returns:
            Deduplicated list
        """
        seen = set()
        unique_relationships = []

        for rel in relationships:
            # Create signature
            signature = (
                rel.source_entity_id,
                rel.target_entity_id,
                rel.relationship_type.value,
            )

            if signature not in seen:
                seen.add(signature)
                unique_relationships.append(rel)
            else:
                # Keep the one with higher confidence
                existing_idx = None
                for i, existing in enumerate(unique_relationships):
                    if (existing.source_entity_id == rel.source_entity_id and
                        existing.target_entity_id == rel.target_entity_id and
                        existing.relationship_type == rel.relationship_type):
                        existing_idx = i
                        break

                if existing_idx is not None:
                    if rel.confidence > unique_relationships[existing_idx].confidence:
                        unique_relationships[existing_idx] = rel

        removed = len(relationships) - len(unique_relationships)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate relationships")

        return unique_relationships
