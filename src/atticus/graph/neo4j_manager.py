"""
Neo4j database manager for knowledge graph operations.

This module provides a high-level interface for interacting with Neo4j,
including connection management, CRUD operations, and query execution.
"""

from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError

from atticus.core.config import get_config
from atticus.core.exceptions import DatabaseError
from atticus.core.logger import get_logger
from atticus.graph.schema import GraphSchema

logger = get_logger(__name__)


class Neo4jManager:
    """Manager for Neo4j database operations."""

    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Neo4j manager.

        Args:
            uri: Neo4j connection URI (default from config)
            user: Neo4j username (default from config)
            password: Neo4j password (default from config)
        """
        config = get_config()

        self.uri = uri or config.neo4j.uri
        self.user = user or config.neo4j.user
        self.password = password or config.neo4j.password
        self.database = config.neo4j.database

        self.driver = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=get_config().neo4j.max_connection_lifetime,
                max_connection_pool_size=get_config().neo4j.max_connection_pool_size,
                connection_acquisition_timeout=get_config().neo4j.connection_acquisition_timeout,
            )
            # Verify connectivity
            self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            error_msg = f"Failed to connect to Neo4j: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, database="neo4j", operation="connect")

    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        if not self.driver:
            raise DatabaseError("Not connected to Neo4j", database="neo4j", operation="execute_query")

        parameters = parameters or {}

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                return [dict(record) for record in result]
        except Neo4jError as e:
            error_msg = f"Neo4j query failed: {str(e)}"
            logger.error(f"{error_msg}\nQuery: {query}\nParameters: {parameters}")
            raise DatabaseError(error_msg, database="neo4j", operation="execute_query")

    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a write transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            Query result
        """
        if not self.driver:
            raise DatabaseError("Not connected to Neo4j", database="neo4j", operation="execute_write")

        parameters = parameters or {}

        def _execute(tx):
            return tx.run(query, parameters).data()

        try:
            with self.driver.session(database=self.database) as session:
                return session.execute_write(_execute)
        except Neo4jError as e:
            error_msg = f"Neo4j write transaction failed: {str(e)}"
            logger.error(f"{error_msg}\nQuery: {query}\nParameters: {parameters}")
            raise DatabaseError(error_msg, database="neo4j", operation="execute_write")

    def initialize_schema(self) -> None:
        """Initialize database schema with constraints and indexes."""
        logger.info("Initializing Neo4j schema...")

        try:
            # Create constraints
            constraint_queries = GraphSchema.get_constraint_queries()
            for query in constraint_queries:
                try:
                    self.execute_query(query)
                    logger.debug(f"Created constraint: {query[:100]}...")
                except Exception as e:
                    logger.warning(f"Failed to create constraint: {str(e)}")

            # Create indexes
            index_queries = GraphSchema.get_index_queries()
            for query in index_queries:
                try:
                    self.execute_query(query)
                    logger.debug(f"Created index: {query[:100]}...")
                except Exception as e:
                    logger.warning(f"Failed to create index: {str(e)}")

            # Create full-text indexes
            fulltext_queries = GraphSchema.get_fulltext_index_queries()
            for query in fulltext_queries:
                try:
                    self.execute_query(query)
                    logger.debug(f"Created fulltext index: {query[:100]}...")
                except Exception as e:
                    logger.warning(f"Failed to create fulltext index: {str(e)}")

            logger.info("Schema initialization completed")
        except Exception as e:
            error_msg = f"Failed to initialize schema: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg, database="neo4j", operation="initialize_schema")

    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a node in the graph.

        Args:
            label: Node label
            properties: Node properties

        Returns:
            Created node properties
        """
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """

        result = self.execute_write(query, {"properties": properties})
        if result and len(result) > 0:
            return dict(result[0]["n"])
        return {}

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        source_label: str = "Entity",
        target_label: str = "Entity",
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a relationship between two nodes.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Relationship type
            source_label: Source node label
            target_label: Target node label
            properties: Relationship properties

        Returns:
            Created relationship properties
        """
        properties = properties or {}

        query = f"""
        MATCH (source:{source_label} {{id: $source_id}})
        MATCH (target:{target_label} {{id: $target_id}})
        CREATE (source)-[r:{relationship_type} $properties]->(target)
        RETURN r
        """

        result = self.execute_write(
            query,
            {"source_id": source_id, "target_id": target_id, "properties": properties},
        )

        if result and len(result) > 0:
            return dict(result[0]["r"])
        return {}

    def get_node(self, node_id: str, label: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.

        Args:
            node_id: Node ID
            label: Optional node label for faster lookup

        Returns:
            Node properties or None if not found
        """
        if label:
            query = f"MATCH (n:{label} {{id: $node_id}}) RETURN n"
        else:
            query = "MATCH (n {id: $node_id}) RETURN n"

        result = self.execute_query(query, {"node_id": node_id})

        if result and len(result) > 0:
            return dict(result[0]["n"])
        return None

    def update_node(self, node_id: str, properties: Dict[str, Any], label: Optional[str] = None) -> Dict[str, Any]:
        """
        Update node properties.

        Args:
            node_id: Node ID
            properties: Properties to update
            label: Optional node label

        Returns:
            Updated node properties
        """
        if label:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            SET n += $properties
            RETURN n
            """
        else:
            query = """
            MATCH (n {id: $node_id})
            SET n += $properties
            RETURN n
            """

        result = self.execute_write(query, {"node_id": node_id, "properties": properties})

        if result and len(result) > 0:
            return dict(result[0]["n"])
        return {}

    def delete_node(self, node_id: str, label: Optional[str] = None) -> bool:
        """
        Delete a node and its relationships.

        Args:
            node_id: Node ID
            label: Optional node label

        Returns:
            True if deleted, False otherwise
        """
        if label:
            query = f"""
            MATCH (n:{label} {{id: $node_id}})
            DETACH DELETE n
            RETURN count(n) as deleted
            """
        else:
            query = """
            MATCH (n {id: $node_id})
            DETACH DELETE n
            RETURN count(n) as deleted
            """

        result = self.execute_write(query, {"node_id": node_id})
        return result and len(result) > 0 and result[0].get("deleted", 0) > 0

    def find_nodes(self, label: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Find nodes matching criteria.

        Args:
            label: Node label to filter by
            filters: Property filters
            limit: Maximum number of results

        Returns:
            List of matching nodes
        """
        filters = filters or {}

        if label:
            query = f"MATCH (n:{label})"
        else:
            query = "MATCH (n)"

        # Add WHERE clauses for filters
        if filters:
            where_clauses = [f"n.{key} = ${key}" for key in filters.keys()]
            query += " WHERE " + " AND ".join(where_clauses)

        query += f" RETURN n LIMIT {limit}"

        result = self.execute_query(query, filters)
        return [dict(record["n"]) for record in result]

    def get_relationships(
        self,
        node_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a node.

        Args:
            node_id: Node ID
            relationship_type: Optional relationship type filter
            direction: Relationship direction ('outgoing', 'incoming', 'both')
            limit: Maximum number of results

        Returns:
            List of relationships with connected nodes
        """
        if relationship_type:
            rel_pattern = f"[r:{relationship_type}]"
        else:
            rel_pattern = "[r]"

        if direction == "outgoing":
            pattern = f"(n {{id: $node_id}})-{rel_pattern}->(related)"
        elif direction == "incoming":
            pattern = f"(n {{id: $node_id}})<-{rel_pattern}-(related)"
        else:  # both
            pattern = f"(n {{id: $node_id}})-{rel_pattern}-(related)"

        query = f"""
        MATCH {pattern}
        RETURN n, r, related
        LIMIT {limit}
        """

        result = self.execute_query(query, {"node_id": node_id})
        return [
            {
                "source": dict(record["n"]),
                "relationship": dict(record["r"]),
                "target": dict(record["related"]),
            }
            for record in result
        ]

    def execute_graph_query(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom Cypher query.

        Args:
            cypher_query: Cypher query
            parameters: Query parameters

        Returns:
            Query results
        """
        return self.execute_query(cypher_query, parameters)

    def clear_database(self) -> None:
        """Clear all nodes and relationships (USE WITH CAUTION)."""
        logger.warning("Clearing entire database...")
        query = "MATCH (n) DETACH DELETE n"
        self.execute_write(query)
        logger.info("Database cleared")

    def get_statistics(self) -> Dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dictionary with node and relationship counts
        """
        stats = {}

        # Total nodes
        result = self.execute_query("MATCH (n) RETURN count(n) as count")
        stats["total_nodes"] = result[0]["count"] if result else 0

        # Total relationships
        result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
        stats["total_relationships"] = result[0]["count"] if result else 0

        # Nodes by label
        result = self.execute_query("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """)
        stats["nodes_by_label"] = {record["label"]: record["count"] for record in result if record["label"]}

        # Relationships by type
        result = self.execute_query("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """)
        stats["relationships_by_type"] = {record["type"]: record["count"] for record in result}

        return stats
