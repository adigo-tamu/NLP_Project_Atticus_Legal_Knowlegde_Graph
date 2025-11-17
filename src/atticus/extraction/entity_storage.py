"""
Entity storage and retrieval using Neo4j.

This module handles storing extracted entities in the knowledge graph
and retrieving them for further processing.
"""

from typing import Dict, List, Optional

from atticus.core.logger import get_logger
from atticus.core.models import Entity
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class EntityStorage:
    """Storage manager for entities in Neo4j."""

    def __init__(self, neo4j_manager: Optional[Neo4jManager] = None):
        """
        Initialize entity storage.

        Args:
            neo4j_manager: Neo4j manager instance (creates new if None)
        """
        self.db = neo4j_manager or Neo4jManager()

    def store_entity(self, entity: Entity) -> bool:
        """
        Store a single entity in Neo4j.

        Args:
            entity: Entity to store

        Returns:
            True if successful
        """
        try:
            # Determine node label based on entity type
            node_label = self._get_node_label(entity.type.value)

            # Prepare properties
            properties = {
                "id": entity.id,
                "text": entity.text,
                "type": entity.type.value,
                "confidence": entity.confidence,
                "document_id": entity.document_id,
                "chunk_id": entity.chunk_id,
                "extraction_method": entity.extraction_method,
                "model": entity.model,
                "timestamp": entity.timestamp.isoformat(),
            }

            # Add optional properties
            if entity.context:
                properties["context"] = entity.context

            if entity.section:
                properties["section"] = entity.section

            if entity.position:
                properties["position_start"] = entity.position.start
                properties["position_end"] = entity.position.end

            # Add attributes as JSON
            if entity.attributes:
                # Store each attribute as a separate property with prefix
                for key, value in entity.attributes.items():
                    properties[f"attr_{key}"] = str(value)

            # Add aliases
            if entity.aliases:
                properties["aliases"] = ",".join(entity.aliases)

            # Create node
            self.db.create_node(node_label, properties)

            logger.debug(f"Stored entity {entity.id} as {node_label}")
            return True

        except Exception as e:
            logger.error(f"Failed to store entity {entity.id}: {e}")
            return False

    def store_batch(self, entities: List[Entity]) -> int:
        """
        Store multiple entities in batch.

        Args:
            entities: List of entities to store

        Returns:
            Number of successfully stored entities
        """
        success_count = 0

        for entity in entities:
            if self.store_entity(entity):
                success_count += 1

        logger.info(f"Stored {success_count}/{len(entities)} entities in Neo4j")
        return success_count

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve an entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Entity object or None
        """
        try:
            # Try to find entity with any label
            node = self.db.get_node(entity_id)

            if node:
                return self._node_to_entity(node)

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve entity {entity_id}: {e}")
            return None

    def get_entities_by_document(self, document_id: str) -> List[Entity]:
        """
        Get all entities for a document.

        Args:
            document_id: Document ID

        Returns:
            List of entities
        """
        try:
            query = """
            MATCH (e:Entity {document_id: $document_id})
            RETURN e
            """

            result = self.db.execute_query(query, {"document_id": document_id})

            entities = []
            for record in result:
                entity = self._node_to_entity(dict(record["e"]))
                if entity:
                    entities.append(entity)

            logger.info(f"Retrieved {len(entities)} entities for document {document_id}")
            return entities

        except Exception as e:
            logger.error(f"Failed to retrieve entities for document {document_id}: {e}")
            return []

    def get_entities_by_type(
        self,
        entity_type: str,
        document_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Entity]:
        """
        Get entities by type.

        Args:
            entity_type: Entity type
            document_id: Optional document filter
            limit: Maximum number of results

        Returns:
            List of entities
        """
        try:
            if document_id:
                query = """
                MATCH (e {type: $entity_type, document_id: $document_id})
                RETURN e
                LIMIT $limit
                """
                params = {
                    "entity_type": entity_type,
                    "document_id": document_id,
                    "limit": limit,
                }
            else:
                query = """
                MATCH (e {type: $entity_type})
                RETURN e
                LIMIT $limit
                """
                params = {"entity_type": entity_type, "limit": limit}

            result = self.db.execute_query(query, params)

            entities = []
            for record in result:
                entity = self._node_to_entity(dict(record["e"]))
                if entity:
                    entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Failed to retrieve entities by type {entity_type}: {e}")
            return []

    def search_entities(
        self,
        search_text: str,
        entity_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Entity]:
        """
        Search entities by text.

        Args:
            search_text: Text to search for
            entity_type: Optional entity type filter
            limit: Maximum results

        Returns:
            List of matching entities
        """
        try:
            if entity_type:
                query = """
                MATCH (e {type: $entity_type})
                WHERE e.text CONTAINS $search_text
                RETURN e
                LIMIT $limit
                """
                params = {
                    "entity_type": entity_type,
                    "search_text": search_text,
                    "limit": limit,
                }
            else:
                query = """
                MATCH (e)
                WHERE e.text CONTAINS $search_text
                RETURN e
                LIMIT $limit
                """
                params = {"search_text": search_text, "limit": limit}

            result = self.db.execute_query(query, params)

            entities = []
            for record in result:
                entity = self._node_to_entity(dict(record["e"]))
                if entity:
                    entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Failed to search entities for '{search_text}': {e}")
            return []

    def delete_entities_by_document(self, document_id: str) -> int:
        """
        Delete all entities for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted entities
        """
        try:
            query = """
            MATCH (e {document_id: $document_id})
            DELETE e
            RETURN count(e) as deleted
            """

            result = self.db.execute_write(query, {"document_id": document_id})

            deleted_count = result[0].get("deleted", 0) if result else 0
            logger.info(f"Deleted {deleted_count} entities for document {document_id}")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete entities for document {document_id}: {e}")
            return 0

    def _get_node_label(self, entity_type: str) -> str:
        """
        Map entity type to Neo4j node label.

        Args:
            entity_type: Entity type string

        Returns:
            Neo4j node label
        """
        label_mapping = {
            "Legal_Party": "LegalParty",
            "Legal_Concept": "LegalConcept",
            "Obligation": "Obligation",
            "Right": "Right",
            "Jurisdiction": "Jurisdiction",
            "Temporal_Entity": "TemporalEntity",
            "Financial_Term": "FinancialTerm",
            "Clause_Reference": "ClauseReference",
        }

        return label_mapping.get(entity_type, "Entity")

    def _node_to_entity(self, node: Dict) -> Optional[Entity]:
        """
        Convert Neo4j node to Entity object.

        Args:
            node: Node properties dictionary

        Returns:
            Entity object or None
        """
        try:
            from datetime import datetime

            from atticus.core.models import EntityType, Position

            # Extract attributes (properties starting with attr_)
            attributes = {}
            for key, value in node.items():
                if key.startswith("attr_"):
                    attr_name = key[5:]  # Remove 'attr_' prefix
                    attributes[attr_name] = value

            # Parse aliases
            aliases = []
            if "aliases" in node and node["aliases"]:
                aliases = node["aliases"].split(",")

            # Create Position if available
            position = None
            if "position_start" in node and "position_end" in node:
                position = Position(
                    start=node["position_start"],
                    end=node["position_end"],
                )

            # Map type string to EntityType enum
            entity_type_str = node.get("type", "Legal_Concept")
            entity_type = EntityType(entity_type_str)

            # Create Entity object
            entity = Entity(
                id=node["id"],
                text=node["text"],
                type=entity_type,
                confidence=float(node.get("confidence", 0.0)),
                context=node.get("context"),
                position=position,
                document_id=node["document_id"],
                chunk_id=node.get("chunk_id"),
                section=node.get("section"),
                attributes=attributes,
                aliases=aliases,
                extraction_method=node.get("extraction_method", "llm"),
                model=node.get("model"),
                timestamp=datetime.fromisoformat(node["timestamp"])
                if "timestamp" in node
                else datetime.utcnow(),
            )

            return entity

        except Exception as e:
            logger.error(f"Failed to convert node to entity: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        Get entity storage statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = {}

            # Total entities
            query = "MATCH (e:Entity) RETURN count(e) as count"
            result = self.db.execute_query(query)
            stats["total_entities"] = result[0]["count"] if result else 0

            # Entities by type
            query = """
            MATCH (e:Entity)
            RETURN e.type as type, count(e) as count
            ORDER BY count DESC
            """
            result = self.db.execute_query(query)
            stats["by_type"] = {record["type"]: record["count"] for record in result}

            # Average confidence
            query = "MATCH (e:Entity) RETURN avg(e.confidence) as avg_confidence"
            result = self.db.execute_query(query)
            stats["avg_confidence"] = round(result[0]["avg_confidence"], 3) if result else 0.0

            return stats

        except Exception as e:
            logger.error(f"Failed to get entity statistics: {e}")
            return {}
