"""
Cross-document entity disambiguation using embeddings.

This module handles disambiguating entities across multiple documents,
identifying when entities in different documents refer to the same real-world entity.
"""

from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Entity, EntityType

logger = get_logger(__name__)


class EntityDisambiguator:
    """Disambiguates entities across multiple documents."""

    def __init__(self, embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize entity disambiguator.

        Args:
            embedding_model: Sentence transformer model for embeddings
        """
        self.config = get_config()
        self.similarity_threshold = 0.90  # Higher threshold for cross-document matching

        # Load embedding model
        logger.info(f"Loading embedding model for disambiguation: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # Entity clusters - groups of entities referring to same real-world entity
        self.entity_clusters: Dict[str, Set[str]] = {}  # canonical_id -> set of entity_ids
        self.entity_to_cluster: Dict[str, str] = {}  # entity_id -> canonical_id

    def disambiguate_entities(
        self,
        entities: List[Entity],
        group_by_type: bool = True,
    ) -> Dict[str, List[Entity]]:
        """
        Disambiguate entities and group by canonical entity.

        Args:
            entities: List of entities from multiple documents
            group_by_type: Only match entities of same type

        Returns:
            Dictionary mapping canonical entity ID to list of equivalent entities
        """
        logger.info(f"Disambiguating {len(entities)} entities across documents...")

        if group_by_type:
            # Group by entity type first
            entities_by_type = self._group_by_type(entities)

            all_clusters = {}
            for entity_type, type_entities in entities_by_type.items():
                logger.debug(f"Disambiguating {len(type_entities)} {entity_type} entities")
                type_clusters = self._disambiguate_by_similarity(type_entities)
                all_clusters.update(type_clusters)

            return all_clusters
        else:
            return self._disambiguate_by_similarity(entities)

    def _group_by_type(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """Group entities by type."""
        groups = {}
        for entity in entities:
            type_key = entity.type.value
            if type_key not in groups:
                groups[type_key] = []
            groups[type_key].append(entity)
        return groups

    def _disambiguate_by_similarity(
        self,
        entities: List[Entity],
    ) -> Dict[str, List[Entity]]:
        """
        Disambiguate entities using similarity matching.

        Args:
            entities: List of entities to disambiguate

        Returns:
            Dictionary of canonical_id -> equivalent entities
        """
        if len(entities) <= 1:
            # Single entity or empty list
            if entities:
                return {entities[0].id: entities}
            return {}

        # Step 1: Exact text matching
        exact_match_clusters = self._cluster_by_exact_match(entities)

        # Step 2: Embedding-based matching for remaining entities
        unclustered_entities = []
        for entity in entities:
            if entity.id not in self.entity_to_cluster:
                unclustered_entities.append(entity)

        if unclustered_entities:
            embedding_clusters = self._cluster_by_embeddings(unclustered_entities)

            # Merge with exact match clusters
            for canonical_id, cluster_entities in embedding_clusters.items():
                if canonical_id in exact_match_clusters:
                    exact_match_clusters[canonical_id].extend(cluster_entities)
                else:
                    exact_match_clusters[canonical_id] = cluster_entities

        logger.info(
            f"Disambiguated {len(entities)} entities into {len(exact_match_clusters)} "
            f"canonical entities"
        )

        return exact_match_clusters

    def _cluster_by_exact_match(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """
        Cluster entities by exact text match (case-insensitive).

        Args:
            entities: List of entities

        Returns:
            Dictionary of canonical_id -> equivalent entities
        """
        text_to_entities: Dict[str, List[Entity]] = {}

        for entity in entities:
            normalized_text = self._normalize_text(entity.text)

            if normalized_text not in text_to_entities:
                text_to_entities[normalized_text] = []
            text_to_entities[normalized_text].append(entity)

        # Convert to canonical clusters
        clusters = {}
        for normalized_text, cluster_entities in text_to_entities.items():
            if len(cluster_entities) > 1:
                # Multiple entities with same text - use highest confidence as canonical
                canonical = max(cluster_entities, key=lambda e: e.confidence)
                canonical_id = canonical.id

                clusters[canonical_id] = cluster_entities

                # Track cluster membership
                for entity in cluster_entities:
                    self.entity_to_cluster[entity.id] = canonical_id

                if canonical_id not in self.entity_clusters:
                    self.entity_clusters[canonical_id] = set()
                self.entity_clusters[canonical_id].update(e.id for e in cluster_entities)

        return clusters

    def _cluster_by_embeddings(
        self,
        entities: List[Entity],
    ) -> Dict[str, List[Entity]]:
        """
        Cluster entities using embedding similarity.

        Args:
            entities: List of entities to cluster

        Returns:
            Dictionary of canonical_id -> equivalent entities
        """
        if len(entities) <= 1:
            return {entities[0].id: entities} if entities else {}

        # Generate embeddings
        texts = [self._get_entity_text_for_embedding(e) for e in entities]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Compute similarity matrix
        similarities = self._compute_similarity_matrix(embeddings)

        # Cluster using similarity threshold
        clusters = {}
        clustered_indices: Set[int] = set()

        for i in range(len(entities)):
            if i in clustered_indices:
                continue

            # Start new cluster with entity i
            cluster_entities = [entities[i]]
            clustered_indices.add(i)

            # Find similar entities
            for j in range(i + 1, len(entities)):
                if j in clustered_indices:
                    continue

                if similarities[i, j] >= self.similarity_threshold:
                    cluster_entities.append(entities[j])
                    clustered_indices.add(j)

            # Store cluster if it has multiple entities
            if len(cluster_entities) > 1:
                canonical = max(cluster_entities, key=lambda e: e.confidence)
                canonical_id = canonical.id

                clusters[canonical_id] = cluster_entities

                # Track cluster membership
                for entity in cluster_entities:
                    self.entity_to_cluster[entity.id] = canonical_id

                if canonical_id not in self.entity_clusters:
                    self.entity_clusters[canonical_id] = set()
                self.entity_clusters[canonical_id].update(e.id for e in cluster_entities)

        return clusters

    def _get_entity_text_for_embedding(self, entity: Entity) -> str:
        """
        Get text for embedding generation.

        Includes entity text and context for better matching.

        Args:
            entity: Entity object

        Returns:
            Text for embedding
        """
        parts = [entity.text]

        # Add context if available
        if entity.context:
            parts.append(entity.context)

        # Add type information
        parts.append(f"Type: {entity.type.value}")

        # Add key attributes for legal parties
        if entity.type == EntityType.LEGAL_PARTY and entity.attributes:
            if "role" in entity.attributes:
                parts.append(f"Role: {entity.attributes['role']}")
            if "entity_subtype" in entity.attributes:
                parts.append(f"Subtype: {entity.attributes['entity_subtype']}")

        return " | ".join(parts)

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity matrix.

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

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        return " ".join(text.split()).lower().strip()

    def get_canonical_entity_id(self, entity_id: str) -> str:
        """
        Get canonical entity ID for a given entity.

        Args:
            entity_id: Entity ID

        Returns:
            Canonical entity ID
        """
        return self.entity_to_cluster.get(entity_id, entity_id)

    def find_equivalent_entities(
        self,
        entity: Entity,
        all_entities: List[Entity],
        top_k: int = 5,
    ) -> List[Tuple[Entity, float]]:
        """
        Find entities equivalent to the given entity.

        Args:
            entity: Query entity
            all_entities: All available entities
            top_k: Number of top matches to return

        Returns:
            List of (entity, similarity_score) tuples
        """
        # Generate embedding for query entity
        query_text = self._get_entity_text_for_embedding(entity)
        query_embedding = self.embedding_model.encode([query_text], convert_to_numpy=True)

        # Generate embeddings for all entities
        all_texts = [self._get_entity_text_for_embedding(e) for e in all_entities]
        all_embeddings = self.embedding_model.encode(all_texts, convert_to_numpy=True)

        # Compute similarities
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        all_norms = all_embeddings / np.linalg.norm(all_embeddings, axis=1, keepdims=True)
        similarities = np.dot(all_norms, query_norm.T).flatten()

        # Get top k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = [
            (all_entities[idx], float(similarities[idx]))
            for idx in top_indices
            if similarities[idx] >= self.similarity_threshold
        ]

        return results

    def merge_clusters(
        self,
        cluster1_id: str,
        cluster2_id: str,
    ) -> str:
        """
        Merge two entity clusters.

        Args:
            cluster1_id: First cluster canonical ID
            cluster2_id: Second cluster canonical ID

        Returns:
            New canonical ID (the one with more entities)
        """
        if cluster1_id not in self.entity_clusters or cluster2_id not in self.entity_clusters:
            logger.warning(f"Cannot merge clusters: one or both not found")
            return cluster1_id

        # Use cluster with more entities as canonical
        cluster1_size = len(self.entity_clusters[cluster1_id])
        cluster2_size = len(self.entity_clusters[cluster2_id])

        if cluster1_size >= cluster2_size:
            canonical_id = cluster1_id
            merge_id = cluster2_id
        else:
            canonical_id = cluster2_id
            merge_id = cluster1_id

        # Merge entities
        self.entity_clusters[canonical_id].update(self.entity_clusters[merge_id])

        # Update entity-to-cluster mapping
        for entity_id in self.entity_clusters[merge_id]:
            self.entity_to_cluster[entity_id] = canonical_id

        # Remove merged cluster
        del self.entity_clusters[merge_id]

        logger.info(f"Merged clusters {cluster1_id} and {cluster2_id} into {canonical_id}")

        return canonical_id

    def get_disambiguation_statistics(self) -> Dict:
        """
        Get statistics about entity disambiguation.

        Returns:
            Dictionary with statistics
        """
        total_entities = sum(len(cluster) for cluster in self.entity_clusters.values())

        cluster_sizes = [len(cluster) for cluster in self.entity_clusters.values()]
        avg_cluster_size = np.mean(cluster_sizes) if cluster_sizes else 0
        max_cluster_size = max(cluster_sizes) if cluster_sizes else 0

        return {
            "total_canonical_entities": len(self.entity_clusters),
            "total_entity_mentions": total_entities,
            "avg_cluster_size": round(avg_cluster_size, 2),
            "max_cluster_size": max_cluster_size,
            "disambiguation_ratio": round(total_entities / len(self.entity_clusters), 2)
            if self.entity_clusters else 0,
        }
