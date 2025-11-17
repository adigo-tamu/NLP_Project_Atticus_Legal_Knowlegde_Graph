"""
Entity deduplication using embeddings and similarity matching.

This module implements entity deduplication to merge duplicate or
highly similar entities extracted from different parts of documents.
"""

from typing import Dict, List, Set, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Entity

logger = get_logger(__name__)


class EntityDeduplicator:
    """Deduplicates entities using embedding-based similarity."""

    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize entity deduplicator.

        Args:
            embedding_model: Sentence transformer model for embeddings
        """
        self.config = get_config()
        self.similarity_threshold = self.config.entity_extraction.merge_threshold

        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)
        logger.info("Embedding model loaded successfully")

    def deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities using embedding similarity.

        Args:
            entities: List of entities to deduplicate

        Returns:
            Deduplicated list of entities
        """
        if not entities:
            return []

        logger.info(f"Deduplicating {len(entities)} entities...")

        # Group entities by type (only merge within same type)
        entities_by_type = self._group_by_type(entities)

        deduplicated_entities = []

        for entity_type, type_entities in entities_by_type.items():
            logger.debug(f"Deduplicating {len(type_entities)} {entity_type} entities")

            # Deduplicate within type
            dedup_type_entities = self._deduplicate_by_type(type_entities)
            deduplicated_entities.extend(dedup_type_entities)

        logger.info(
            f"Deduplication complete: {len(entities)} → {len(deduplicated_entities)} entities "
            f"({len(entities) - len(deduplicated_entities)} duplicates removed)"
        )

        return deduplicated_entities

    def _group_by_type(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """Group entities by type."""
        groups = {}
        for entity in entities:
            type_key = entity.type.value
            if type_key not in groups:
                groups[type_key] = []
            groups[type_key].append(entity)
        return groups

    def _deduplicate_by_type(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities of the same type.

        Args:
            entities: List of entities of same type

        Returns:
            Deduplicated list
        """
        if len(entities) <= 1:
            return entities

        # Step 1: Exact text matching
        entities = self._deduplicate_exact_match(entities)

        if len(entities) <= 1:
            return entities

        # Step 2: Embedding-based similarity matching
        entities = self._deduplicate_embedding_match(entities)

        return entities

    def _deduplicate_exact_match(self, entities: List[Entity]) -> List[Entity]:
        """
        Remove exact duplicates by text (case-insensitive).

        Args:
            entities: List of entities

        Returns:
            Deduplicated list
        """
        seen_texts = {}
        deduplicated = []

        for entity in entities:
            # Normalize text for comparison
            normalized_text = entity.text.lower().strip()

            if normalized_text not in seen_texts:
                seen_texts[normalized_text] = entity
                deduplicated.append(entity)
            else:
                # Merge with existing entity (keep higher confidence)
                existing = seen_texts[normalized_text]
                if entity.confidence > existing.confidence:
                    # Replace with higher confidence version
                    deduplicated.remove(existing)
                    deduplicated.append(entity)
                    seen_texts[normalized_text] = entity
                else:
                    # Add aliases
                    if entity.text not in existing.aliases:
                        existing.aliases.append(entity.text)

        removed = len(entities) - len(deduplicated)
        if removed > 0:
            logger.debug(f"Exact match deduplication: removed {removed} duplicates")

        return deduplicated

    def _deduplicate_embedding_match(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate using embedding similarity.

        Args:
            entities: List of entities

        Returns:
            Deduplicated list
        """
        if len(entities) <= 1:
            return entities

        # Generate embeddings
        texts = [entity.text for entity in entities]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Compute pairwise similarities
        similarities = self._compute_similarity_matrix(embeddings)

        # Find duplicates
        to_remove: Set[int] = set()
        merged_indices: Dict[int, int] = {}  # Maps removed index to kept index

        for i in range(len(entities)):
            if i in to_remove:
                continue

            for j in range(i + 1, len(entities)):
                if j in to_remove:
                    continue

                # Check similarity
                if similarities[i, j] >= self.similarity_threshold:
                    # Merge j into i (keep higher confidence)
                    if entities[j].confidence > entities[i].confidence:
                        # Keep j, remove i
                        to_remove.add(i)
                        merged_indices[i] = j
                        # Add i's text as alias to j
                        if entities[i].text not in entities[j].aliases:
                            entities[j].aliases.append(entities[i].text)
                        break  # i is removed, no need to continue
                    else:
                        # Keep i, remove j
                        to_remove.add(j)
                        merged_indices[j] = i
                        # Add j's text as alias to i
                        if entities[j].text not in entities[i].aliases:
                            entities[i].aliases.append(entities[j].text)

        # Create deduplicated list
        deduplicated = [
            entity for idx, entity in enumerate(entities)
            if idx not in to_remove
        ]

        removed = len(to_remove)
        if removed > 0:
            logger.debug(f"Embedding-based deduplication: removed {removed} similar entities")

        return deduplicated

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity matrix for embeddings.

        Args:
            embeddings: Array of embeddings (n x dim)

        Returns:
            Similarity matrix (n x n)
        """
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms

        # Compute cosine similarity
        similarities = np.dot(normalized, normalized.T)

        return similarities

    def merge_entities(self, entity1: Entity, entity2: Entity) -> Entity:
        """
        Merge two similar entities.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            Merged entity
        """
        # Keep entity with higher confidence as base
        if entity1.confidence >= entity2.confidence:
            base_entity = entity1
            other_entity = entity2
        else:
            base_entity = entity2
            other_entity = entity1

        # Merge aliases
        if other_entity.text not in base_entity.aliases:
            base_entity.aliases.append(other_entity.text)

        # Merge attributes (keep non-conflicting)
        for key, value in other_entity.attributes.items():
            if key not in base_entity.attributes:
                base_entity.attributes[key] = value

        # Average confidence if similar
        base_entity.confidence = (entity1.confidence + entity2.confidence) / 2

        return base_entity

    def find_duplicates(
        self,
        entities: List[Entity],
        threshold: float = 0.9,
    ) -> List[Tuple[Entity, Entity, float]]:
        """
        Find potential duplicate entities without merging.

        Args:
            entities: List of entities
            threshold: Similarity threshold

        Returns:
            List of (entity1, entity2, similarity_score) tuples
        """
        duplicates = []

        # Generate embeddings
        texts = [entity.text for entity in entities]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Compute similarities
        similarities = self._compute_similarity_matrix(embeddings)

        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                if entities[i].type == entities[j].type:  # Same type only
                    similarity = similarities[i, j]
                    if similarity >= threshold:
                        duplicates.append((entities[i], entities[j], float(similarity)))

        return duplicates
