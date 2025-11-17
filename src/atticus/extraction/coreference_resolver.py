"""
Coreference resolution for legal entities.

This module handles resolving entity references (pronouns, aliases, defined terms)
to their canonical entities.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from atticus.core.logger import get_logger
from atticus.core.models import Entity, EntityType

logger = get_logger(__name__)


class CoreferenceResolver:
    """Resolves entity coreferences in legal documents."""

    def __init__(self):
        """Initialize coreference resolver."""
        self.entity_aliases: Dict[str, Set[str]] = {}  # canonical_id -> aliases
        self.alias_to_canonical: Dict[str, str] = {}  # alias -> canonical_id

    def build_coreference_map(self, entities: List[Entity]) -> None:
        """
        Build coreference map from entities.

        Args:
            entities: List of entities from document
        """
        logger.info(f"Building coreference map from {len(entities)} entities")

        # Reset maps
        self.entity_aliases = {}
        self.alias_to_canonical = {}

        # Step 1: Find defined terms and party definitions
        party_definitions = self._extract_party_definitions(entities)

        # Step 2: Build alias maps
        for canonical_id, aliases in party_definitions.items():
            self.entity_aliases[canonical_id] = set(aliases)
            for alias in aliases:
                normalized_alias = self._normalize_text(alias)
                self.alias_to_canonical[normalized_alias] = canonical_id

        # Step 3: Add entity aliases from extraction
        for entity in entities:
            if entity.type == EntityType.LEGAL_PARTY and entity.aliases:
                if entity.id not in self.entity_aliases:
                    self.entity_aliases[entity.id] = set()

                for alias in entity.aliases:
                    normalized_alias = self._normalize_text(alias)
                    self.entity_aliases[entity.id].add(alias)
                    self.alias_to_canonical[normalized_alias] = entity.id

        logger.info(f"Built coreference map with {len(self.entity_aliases)} canonical entities")

    def resolve_entity(self, entity_text: str, entities: List[Entity]) -> Optional[str]:
        """
        Resolve entity text to canonical entity ID.

        Args:
            entity_text: Text to resolve
            entities: Available entities

        Returns:
            Canonical entity ID or None
        """
        normalized_text = self._normalize_text(entity_text)

        # Direct lookup in alias map
        if normalized_text in self.alias_to_canonical:
            return self.alias_to_canonical[normalized_text]

        # Pronoun resolution
        if self._is_pronoun(entity_text):
            # Would need context and recent entities for proper resolution
            # This is a simplified version
            logger.debug(f"Cannot resolve pronoun '{entity_text}' without context")
            return None

        # Try exact match with existing entities
        for entity in entities:
            if self._normalize_text(entity.text) == normalized_text:
                return entity.id

        # Try partial match (for abbreviations, etc.)
        for entity in entities:
            if entity.type == EntityType.LEGAL_PARTY:
                if self._is_partial_match(normalized_text, entity.text):
                    return entity.id

        return None

    def resolve_coreferences_in_relationships(
        self,
        relationships_data: List[Dict],
        entities: List[Entity],
    ) -> List[Dict]:
        """
        Resolve coreferences in extracted relationship data.

        Args:
            relationships_data: Raw relationship data from LLM
            entities: Available entities

        Returns:
            Relationship data with resolved entity IDs
        """
        resolved = []

        for rel_data in relationships_data:
            # Resolve source entity
            source_text = rel_data.get("source_entity_text", "")
            source_id = rel_data.get("source_entity_id")

            if source_text and not source_id:
                source_id = self.resolve_entity(source_text, entities)
                if source_id:
                    rel_data["source_entity_id"] = source_id

            # Resolve target entity
            target_text = rel_data.get("target_entity_text", "")
            target_id = rel_data.get("target_entity_id")

            if target_text and not target_id:
                target_id = self.resolve_entity(target_text, entities)
                if target_id:
                    rel_data["target_entity_id"] = target_id

            # Only include if both IDs resolved
            if source_id and target_id:
                resolved.append(rel_data)
            else:
                logger.debug(
                    f"Could not resolve relationship: {source_text} -> {target_text}"
                )

        logger.info(
            f"Resolved {len(resolved)}/{len(relationships_data)} relationships"
        )

        return resolved

    def _extract_party_definitions(self, entities: List[Entity]) -> Dict[str, List[str]]:
        """
        Extract party definitions from entities.

        Looks for patterns like "ABC Corp ('Seller')" in entity text or context.

        Args:
            entities: List of entities

        Returns:
            Dictionary mapping canonical entity ID to list of aliases
        """
        definitions = {}

        # Patterns for party definitions
        patterns = [
            r"([^,\(]+)\s*\((?:the\s+)?['\"]([^'\"]+)['\"]\)",  # ABC Corp ("Seller")
            r"([^,\(]+)\s*\(hereinafter\s+['\"]([^'\"]+)['\"]\)",  # hereinafter "Seller"
            r"([^,\(]+)\s*,\s*(?:a|an)\s+[^,]+\s+\(['\"]([^'\"]+)['\"]\)",  # ABC Corp, a Delaware corporation ("Seller")
        ]

        for entity in entities:
            if entity.type != EntityType.LEGAL_PARTY:
                continue

            # Check entity text
            text_to_check = entity.text
            if entity.context:
                text_to_check = entity.context

            for pattern in patterns:
                matches = re.finditer(pattern, text_to_check)
                for match in matches:
                    legal_name = match.group(1).strip()
                    role_name = match.group(2).strip()

                    # Use entity ID as canonical if it matches
                    if self._normalize_text(legal_name) in self._normalize_text(entity.text):
                        if entity.id not in definitions:
                            definitions[entity.id] = []

                        # Add both the legal name and role as aliases
                        definitions[entity.id].append(legal_name)
                        definitions[entity.id].append(role_name)
                        definitions[entity.id].append(f"the {role_name}")

        return definitions

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        # Remove extra whitespace, lowercase
        normalized = " ".join(text.split()).lower()
        # Remove punctuation at end
        normalized = normalized.rstrip(".,;:")
        return normalized

    def _is_pronoun(self, text: str) -> bool:
        """Check if text is a pronoun."""
        pronouns = {
            "it", "its", "itself",
            "he", "his", "him", "himself",
            "she", "her", "hers", "herself",
            "they", "their", "theirs", "them", "themselves",
            "we", "our", "ours", "us", "ourselves",
            "you", "your", "yours", "yourself", "yourselves",
        }
        return self._normalize_text(text) in pronouns

    def _is_partial_match(self, query: str, entity_text: str) -> bool:
        """
        Check if query is a partial match of entity text.

        Useful for abbreviations or shortened forms.

        Args:
            query: Query text
            entity_text: Full entity text

        Returns:
            True if partial match
        """
        query_norm = self._normalize_text(query)
        entity_norm = self._normalize_text(entity_text)

        # Check if query is substring of entity
        if query_norm in entity_norm:
            return True

        # Check if query matches company name without suffix
        # e.g., "TechCorp" matches "TechCorp Inc."
        entity_words = entity_norm.split()
        if len(entity_words) > 1:
            # Remove common suffixes
            suffixes = ["inc", "llc", "corp", "corporation", "ltd", "limited", "company", "co"]
            if entity_words[-1] in suffixes:
                entity_without_suffix = " ".join(entity_words[:-1])
                if query_norm == entity_without_suffix:
                    return True

        return False

    def get_canonical_entity(self, entity_id: str) -> Optional[str]:
        """
        Get canonical entity ID for a given entity ID.

        Args:
            entity_id: Entity ID (may be an alias)

        Returns:
            Canonical entity ID
        """
        # Check if it's already canonical
        if entity_id in self.entity_aliases:
            return entity_id

        # Check if it's an alias
        for canonical_id, aliases in self.entity_aliases.items():
            if entity_id in [a.lower() for a in aliases]:
                return canonical_id

        # Not found, return original
        return entity_id

    def merge_entities_by_coreference(self, entities: List[Entity]) -> List[Entity]:
        """
        Merge entities that are coreferences of each other.

        Args:
            entities: List of entities

        Returns:
            Merged list of entities
        """
        # Build coreference map first
        self.build_coreference_map(entities)

        # Group entities by canonical ID
        canonical_groups: Dict[str, List[Entity]] = {}

        for entity in entities:
            canonical_id = self.get_canonical_entity(entity.id)
            if canonical_id not in canonical_groups:
                canonical_groups[canonical_id] = []
            canonical_groups[canonical_id].append(entity)

        # Merge each group
        merged_entities = []
        for canonical_id, group in canonical_groups.items():
            if len(group) == 1:
                merged_entities.append(group[0])
            else:
                # Merge multiple entities
                merged = self._merge_entity_group(group)
                merged_entities.append(merged)

        logger.info(
            f"Merged {len(entities)} entities into {len(merged_entities)} "
            f"canonical entities"
        )

        return merged_entities

    def _merge_entity_group(self, entities: List[Entity]) -> Entity:
        """
        Merge a group of coreferent entities.

        Args:
            entities: List of entities to merge

        Returns:
            Merged entity
        """
        # Use entity with highest confidence as base
        base_entity = max(entities, key=lambda e: e.confidence)

        # Collect all aliases
        all_aliases = set()
        for entity in entities:
            all_aliases.add(entity.text)
            all_aliases.update(entity.aliases)

        # Remove the base text from aliases
        all_aliases.discard(base_entity.text)

        # Update base entity
        base_entity.aliases = list(all_aliases)

        # Average confidence
        base_entity.confidence = sum(e.confidence for e in entities) / len(entities)

        return base_entity
