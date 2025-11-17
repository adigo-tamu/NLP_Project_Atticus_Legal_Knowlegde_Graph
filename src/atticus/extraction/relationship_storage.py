"""
Relationship storage and retrieval using Neo4j.

This module handles storing extracted relationships in the knowledge graph
and creating edges between entity nodes.
"""

from typing import Dict, List, Optional

from atticus.core.logger import get_logger
from atticus.core.models import Relationship
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class RelationshipStorage:
    """Storage manager for relationships in Neo4j."""

    def __init__(self, neo4j_manager: Optional[Neo4jManager] = None):
        """
        Initialize relationship storage.

        Args:
            neo4j_manager: Neo4j manager instance (creates new if None)
        """
        self.db = neo4j_manager or Neo4jManager()

    def store_relationship(self, relationship: Relationship) -> bool:
        """
        Store a single relationship in Neo4j.

        Creates an edge between two entity nodes.

        Args:
            relationship: Relationship to store

        Returns:
            True if successful
        """
        try:
            # Prepare relationship properties
            properties = {
                "id": relationship.id,
                "confidence": relationship.confidence,
                "document_id": relationship.document_id,
                "chunk_id": relationship.chunk_id,
                "extraction_method": relationship.extraction_method,
                "model": relationship.model,
                "timestamp": relationship.timestamp.isoformat(),
            }

            # Add optional properties
            if relationship.evidence:
                properties["evidence"] = relationship.evidence

            if relationship.reasoning:
                properties["reasoning"] = relationship.reasoning

            if relationship.position:
                properties["position_start"] = relationship.position.start
                properties["position_end"] = relationship.position.end

            # Add custom properties
            if relationship.properties:
                for key, value in relationship.properties.items():
                    properties[f"prop_{key}"] = str(value)

            # Add temporal info if present
            if relationship.temporal_info:
                for key, value in relationship.temporal_info.items():
                    properties[f"temporal_{key}"] = str(value)

            # Create relationship in Neo4j
            self.db.create_relationship(
                source_id=relationship.source_entity_id,
                target_id=relationship.target_entity_id,
                relationship_type=relationship.relationship_type.value,
                source_label="Entity",  # Generic label, could be more specific
                target_label="Entity",
                properties=properties,
            )

            logger.debug(
                f"Stored relationship {relationship.id}: "
                f"{relationship.relationship_type.value}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store relationship {relationship.id}: {e}")
            return False

    def store_batch(self, relationships: List[Relationship]) -> int:
        """
        Store multiple relationships in batch.

        Args:
            relationships: List of relationships to store

        Returns:
            Number of successfully stored relationships
        """
        success_count = 0

        for relationship in relationships:
            if self.store_relationship(relationship):
                success_count += 1

        logger.info(f"Stored {success_count}/{len(relationships)} relationships in Neo4j")
        return success_count

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Retrieve a relationship by ID.

        Args:
            relationship_id: Relationship ID

        Returns:
            Relationship object or None
        """
        try:
            query = """
            MATCH ()-[r {id: $relationship_id}]->()
            RETURN r
            """

            result = self.db.execute_query(query, {"relationship_id": relationship_id})

            if result and len(result) > 0:
                return self._edge_to_relationship(dict(result[0]["r"]))

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve relationship {relationship_id}: {e}")
            return None

    def get_relationships_by_document(self, document_id: str) -> List[Relationship]:
        """
        Get all relationships for a document.

        Args:
            document_id: Document ID

        Returns:
            List of relationships
        """
        try:
            query = """
            MATCH ()-[r {document_id: $document_id}]->()
            RETURN r
            """

            result = self.db.execute_query(query, {"document_id": document_id})

            relationships = []
            for record in result:
                rel = self._edge_to_relationship(dict(record["r"]))
                if rel:
                    relationships.append(rel)

            logger.info(f"Retrieved {len(relationships)} relationships for document {document_id}")
            return relationships

        except Exception as e:
            logger.error(f"Failed to retrieve relationships for document {document_id}: {e}")
            return []

    def get_relationships_by_entity(
        self,
        entity_id: str,
        direction: str = "both",
    ) -> List[Relationship]:
        """
        Get relationships for an entity.

        Args:
            entity_id: Entity ID
            direction: 'outgoing', 'incoming', or 'both'

        Returns:
            List of relationships
        """
        try:
            if direction == "outgoing":
                pattern = f"(e {{id: $entity_id}})-[r]->()"
            elif direction == "incoming":
                pattern = f"()-[r]->(e {{id: $entity_id}})"
            else:  # both
                pattern = f"(e {{id: $entity_id}})-[r]-()"

            query = f"""
            MATCH {pattern}
            RETURN r
            """

            result = self.db.execute_query(query, {"entity_id": entity_id})

            relationships = []
            for record in result:
                rel = self._edge_to_relationship(dict(record["r"]))
                if rel:
                    relationships.append(rel)

            return relationships

        except Exception as e:
            logger.error(f"Failed to retrieve relationships for entity {entity_id}: {e}")
            return []

    def get_relationships_by_type(
        self,
        relationship_type: str,
        document_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Relationship]:
        """
        Get relationships by type.

        Args:
            relationship_type: Relationship type
            document_id: Optional document filter
            limit: Maximum results

        Returns:
            List of relationships
        """
        try:
            if document_id:
                query = f"""
                MATCH ()-[r:{relationship_type} {{document_id: $document_id}}]->()
                RETURN r
                LIMIT $limit
                """
                params = {"document_id": document_id, "limit": limit}
            else:
                query = f"""
                MATCH ()-[r:{relationship_type}]->()
                RETURN r
                LIMIT $limit
                """
                params = {"limit": limit}

            result = self.db.execute_query(query, params)

            relationships = []
            for record in result:
                rel = self._edge_to_relationship(dict(record["r"]))
                if rel:
                    relationships.append(rel)

            return relationships

        except Exception as e:
            logger.error(f"Failed to retrieve relationships by type {relationship_type}: {e}")
            return []

    def delete_relationships_by_document(self, document_id: str) -> int:
        """
        Delete all relationships for a document.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted relationships
        """
        try:
            query = """
            MATCH ()-[r {document_id: $document_id}]->()
            DELETE r
            RETURN count(r) as deleted
            """

            result = self.db.execute_write(query, {"document_id": document_id})

            deleted_count = result[0].get("deleted", 0) if result else 0
            logger.info(f"Deleted {deleted_count} relationships for document {document_id}")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete relationships for document {document_id}: {e}")
            return 0

    def find_paths(
        self,
        start_entity_id: str,
        end_entity_id: str,
        max_depth: int = 3,
    ) -> List[List[Dict]]:
        """
        Find paths between two entities.

        Args:
            start_entity_id: Starting entity ID
            end_entity_id: Ending entity ID
            max_depth: Maximum path length

        Returns:
            List of paths (each path is a list of relationship dicts)
        """
        try:
            query = f"""
            MATCH path = (start {{id: $start_id}})-[*1..{max_depth}]-(end {{id: $end_id}})
            RETURN [r in relationships(path) | r] as rels
            LIMIT 10
            """

            result = self.db.execute_query(
                query,
                {"start_id": start_entity_id, "end_id": end_entity_id},
            )

            paths = []
            for record in result:
                path_rels = [dict(r) for r in record["rels"]]
                paths.append(path_rels)

            logger.info(f"Found {len(paths)} paths between entities")
            return paths

        except Exception as e:
            logger.error(f"Failed to find paths: {e}")
            return []

    def _edge_to_relationship(self, edge: Dict) -> Optional[Relationship]:
        """
        Convert Neo4j edge to Relationship object.

        Args:
            edge: Edge properties dictionary

        Returns:
            Relationship object or None
        """
        try:
            from datetime import datetime

            from atticus.core.models import RelationshipType, Position

            # Extract custom properties
            properties = {}
            temporal_info = {}

            for key, value in edge.items():
                if key.startswith("prop_"):
                    prop_name = key[5:]  # Remove 'prop_' prefix
                    properties[prop_name] = value
                elif key.startswith("temporal_"):
                    temporal_name = key[9:]  # Remove 'temporal_' prefix
                    temporal_info[temporal_name] = value

            # Create Position if available
            position = None
            if "position_start" in edge and "position_end" in edge:
                position = Position(
                    start=edge["position_start"],
                    end=edge["position_end"],
                )

            # Map type to RelationshipType enum
            # The type comes from the edge label
            rel_type_str = edge.get("type", "REFERENCES")
            rel_type = RelationshipType(rel_type_str)

            # Create Relationship object
            relationship = Relationship(
                id=edge["id"],
                source_entity_id=edge.get("source_entity_id", ""),
                target_entity_id=edge.get("target_entity_id", ""),
                relationship_type=rel_type,
                confidence=float(edge.get("confidence", 0.0)),
                evidence=edge.get("evidence"),
                reasoning=edge.get("reasoning"),
                document_id=edge["document_id"],
                chunk_id=edge.get("chunk_id"),
                position=position,
                properties=properties,
                temporal_info=temporal_info if temporal_info else None,
                extraction_method=edge.get("extraction_method", "llm"),
                model=edge.get("model"),
                timestamp=datetime.fromisoformat(edge["timestamp"])
                if "timestamp" in edge
                else datetime.utcnow(),
            )

            return relationship

        except Exception as e:
            logger.error(f"Failed to convert edge to relationship: {e}")
            return None

    def get_statistics(self) -> Dict:
        """
        Get relationship storage statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = {}

            # Total relationships
            query = "MATCH ()-[r]->() RETURN count(r) as count"
            result = self.db.execute_query(query)
            stats["total_relationships"] = result[0]["count"] if result else 0

            # Relationships by type
            query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            result = self.db.execute_query(query)
            stats["by_type"] = {record["type"]: record["count"] for record in result}

            # Average confidence
            query = "MATCH ()-[r]->() RETURN avg(r.confidence) as avg_confidence"
            result = self.db.execute_query(query)
            stats["avg_confidence"] = round(result[0]["avg_confidence"], 3) if result else 0.0

            return stats

        except Exception as e:
            logger.error(f"Failed to get relationship statistics: {e}")
            return {}
