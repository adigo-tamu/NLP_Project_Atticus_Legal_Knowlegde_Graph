"""
Graph analytics and quality metrics.

This module provides analytics, statistics, and quality metrics for the knowledge graph.
"""

from typing import Dict, List, Optional

import networkx as nx

from atticus.core.logger import get_logger
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class GraphAnalytics:
    """Analytics and metrics for knowledge graph."""

    def __init__(self, neo4j_manager: Optional[Neo4jManager] = None):
        """
        Initialize graph analytics.

        Args:
            neo4j_manager: Neo4j manager instance
        """
        self.db = neo4j_manager or Neo4jManager()

    def get_graph_statistics(self, document_id: Optional[str] = None) -> Dict:
        """
        Get comprehensive graph statistics.

        Args:
            document_id: Optional document filter

        Returns:
            Dictionary with statistics
        """
        logger.info("Calculating graph statistics...")

        stats = {}

        # Basic counts
        stats["basic"] = self._get_basic_counts(document_id)

        # Node statistics
        stats["nodes"] = self._get_node_statistics(document_id)

        # Relationship statistics
        stats["relationships"] = self._get_relationship_statistics(document_id)

        # Connectivity statistics
        stats["connectivity"] = self._get_connectivity_statistics(document_id)

        # Density and other metrics
        stats["metrics"] = self._calculate_graph_metrics(document_id)

        logger.info(f"Graph statistics calculated: {stats['basic']}")

        return stats

    def _get_basic_counts(self, document_id: Optional[str] = None) -> Dict:
        """Get basic node and relationship counts."""
        if document_id:
            node_query = "MATCH (n {document_id: $document_id}) RETURN count(n) as count"
            rel_query = "MATCH ()-[r {document_id: $document_id}]->() RETURN count(r) as count"
            params = {"document_id": document_id}
        else:
            node_query = "MATCH (n) RETURN count(n) as count"
            rel_query = "MATCH ()-[r]->() RETURN count(r) as count"
            params = {}

        node_result = self.db.execute_query(node_query, params)
        rel_result = self.db.execute_query(rel_query, params)

        total_nodes = node_result[0]["count"] if node_result else 0
        total_relationships = rel_result[0]["count"] if rel_result else 0

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_relationships,
            "avg_degree": round(2 * total_relationships / total_nodes, 2) if total_nodes > 0 else 0,
        }

    def _get_node_statistics(self, document_id: Optional[str] = None) -> Dict:
        """Get node statistics by type."""
        if document_id:
            query = """
            MATCH (n {document_id: $document_id})
            RETURN labels(n)[0] as label, count(n) as count,
                   avg(n.confidence) as avg_confidence,
                   min(n.confidence) as min_confidence,
                   max(n.confidence) as max_confidence
            ORDER BY count DESC
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count,
                   avg(n.confidence) as avg_confidence,
                   min(n.confidence) as min_confidence,
                   max(n.confidence) as max_confidence
            ORDER BY count DESC
            """
            params = {}

        result = self.db.execute_query(query, params)

        by_type = {}
        for record in result:
            label = record["label"] or "Unknown"
            by_type[label] = {
                "count": record["count"],
                "avg_confidence": round(record["avg_confidence"], 3) if record["avg_confidence"] else None,
                "min_confidence": round(record["min_confidence"], 3) if record["min_confidence"] else None,
                "max_confidence": round(record["max_confidence"], 3) if record["max_confidence"] else None,
            }

        return by_type

    def _get_relationship_statistics(self, document_id: Optional[str] = None) -> Dict:
        """Get relationship statistics by type."""
        if document_id:
            query = """
            MATCH ()-[r {document_id: $document_id}]->()
            RETURN type(r) as type, count(r) as count,
                   avg(r.confidence) as avg_confidence,
                   min(r.confidence) as min_confidence,
                   max(r.confidence) as max_confidence
            ORDER BY count DESC
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count,
                   avg(r.confidence) as avg_confidence,
                   min(r.confidence) as min_confidence,
                   max(r.confidence) as max_confidence
            ORDER BY count DESC
            """
            params = {}

        result = self.db.execute_query(query, params)

        by_type = {}
        for record in result:
            rel_type = record["type"]
            by_type[rel_type] = {
                "count": record["count"],
                "avg_confidence": round(record["avg_confidence"], 3) if record["avg_confidence"] else None,
                "min_confidence": round(record["min_confidence"], 3) if record["min_confidence"] else None,
                "max_confidence": round(record["max_confidence"], 3) if record["max_confidence"] else None,
            }

        return by_type

    def _get_connectivity_statistics(self, document_id: Optional[str] = None) -> Dict:
        """Get graph connectivity statistics."""
        stats = {}

        # Degree distribution
        if document_id:
            query = """
            MATCH (n {document_id: $document_id})
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            RETURN min(degree) as min_degree, max(degree) as max_degree,
                   avg(degree) as avg_degree, percentileCont(degree, 0.5) as median_degree
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            RETURN min(degree) as min_degree, max(degree) as max_degree,
                   avg(degree) as avg_degree, percentileCont(degree, 0.5) as median_degree
            """
            params = {}

        result = self.db.execute_query(query, params)

        if result:
            stats["min_degree"] = result[0]["min_degree"]
            stats["max_degree"] = result[0]["max_degree"]
            stats["avg_degree"] = round(result[0]["avg_degree"], 2) if result[0]["avg_degree"] else 0
            stats["median_degree"] = round(result[0]["median_degree"], 2) if result[0]["median_degree"] else 0

        # Find hub nodes (nodes with highest degree)
        if document_id:
            hub_query = """
            MATCH (n {document_id: $document_id})
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            ORDER BY degree DESC
            LIMIT 5
            RETURN n.id as node_id, n.text as text, labels(n) as labels, degree
            """
        else:
            hub_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            ORDER BY degree DESC
            LIMIT 5
            RETURN n.id as node_id, n.text as text, labels(n) as labels, degree
            """

        hub_result = self.db.execute_query(hub_query, params)

        stats["hub_nodes"] = [
            {
                "id": record["node_id"],
                "text": record["text"][:50] if record.get("text") else "N/A",
                "labels": record["labels"],
                "degree": record["degree"],
            }
            for record in hub_result
        ]

        return stats

    def _calculate_graph_metrics(self, document_id: Optional[str] = None) -> Dict:
        """Calculate graph metrics like density, clustering coefficient, etc."""
        metrics = {}

        # Get basic counts
        basic = self._get_basic_counts(document_id)
        n_nodes = basic["total_nodes"]
        n_edges = basic["total_relationships"]

        if n_nodes < 2:
            return {"density": 0.0, "note": "Insufficient nodes for metrics"}

        # Graph density = actual edges / possible edges
        # For directed graph: possible edges = n * (n - 1)
        possible_edges = n_nodes * (n_nodes - 1)
        density = n_edges / possible_edges if possible_edges > 0 else 0

        metrics["density"] = round(density, 4)

        # Average path length (sample-based for large graphs)
        if document_id:
            path_query = """
            MATCH (n1 {document_id: $document_id}), (n2 {document_id: $document_id})
            WHERE id(n1) < id(n2)
            MATCH path = shortestPath((n1)-[*]-(n2))
            RETURN avg(length(path)) as avg_path_length
            LIMIT 1000
            """
            params = {"document_id": document_id}
        else:
            path_query = """
            MATCH (n1), (n2)
            WHERE id(n1) < id(n2)
            MATCH path = shortestPath((n1)-[*]-(n2))
            RETURN avg(length(path)) as avg_path_length
            LIMIT 1000
            """
            params = {}

        try:
            path_result = self.db.execute_query(path_query, params)
            if path_result and path_result[0]["avg_path_length"]:
                metrics["avg_path_length"] = round(path_result[0]["avg_path_length"], 2)
        except Exception as e:
            logger.debug(f"Could not calculate average path length: {e}")
            metrics["avg_path_length"] = None

        return metrics

    def find_central_entities(
        self,
        document_id: Optional[str] = None,
        top_k: int = 10,
        centrality_type: str = "degree",
    ) -> List[Dict]:
        """
        Find most central entities in the graph.

        Args:
            document_id: Optional document filter
            top_k: Number of top entities to return
            centrality_type: Type of centrality ('degree', 'betweenness', 'pagerank')

        Returns:
            List of central entities with scores
        """
        if centrality_type == "degree":
            # Degree centrality (simplest)
            if document_id:
                query = """
                MATCH (n {document_id: $document_id})
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) as degree
                ORDER BY degree DESC
                LIMIT $top_k
                RETURN n.id as entity_id, n.text as text, labels(n) as labels,
                       degree, n.type as entity_type
                """
                params = {"document_id": document_id, "top_k": top_k}
            else:
                query = """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) as degree
                ORDER BY degree DESC
                LIMIT $top_k
                RETURN n.id as entity_id, n.text as text, labels(n) as labels,
                       degree, n.type as entity_type
                """
                params = {"top_k": top_k}

            result = self.db.execute_query(query, params)

            return [
                {
                    "entity_id": record["entity_id"],
                    "text": record["text"][:50] if record.get("text") else "N/A",
                    "labels": record["labels"],
                    "type": record.get("entity_type", "Unknown"),
                    "centrality_score": record["degree"],
                    "centrality_type": "degree",
                }
                for record in result
            ]

        elif centrality_type == "pagerank":
            # PageRank centrality (requires Graph Data Science library)
            # This is a simplified version
            logger.warning("PageRank centrality requires Neo4j GDS library - using degree centrality instead")
            return self.find_central_entities(document_id, top_k, "degree")

        else:
            raise ValueError(f"Unknown centrality type: {centrality_type}")

    def analyze_document_graph(self, document_id: str) -> Dict:
        """
        Comprehensive analysis of a single document's knowledge graph.

        Args:
            document_id: Document ID

        Returns:
            Comprehensive analysis results
        """
        logger.info(f"Analyzing knowledge graph for document {document_id}...")

        analysis = {
            "document_id": document_id,
            "statistics": self.get_graph_statistics(document_id),
            "central_entities": self.find_central_entities(document_id, top_k=5),
        }

        # Entity coverage by type
        analysis["entity_coverage"] = self._analyze_entity_coverage(document_id)

        # Relationship patterns
        analysis["relationship_patterns"] = self._analyze_relationship_patterns(document_id)

        return analysis

    def _analyze_entity_coverage(self, document_id: str) -> Dict:
        """Analyze entity type coverage."""
        query = """
        MATCH (n {document_id: $document_id})
        RETURN n.type as entity_type, count(n) as count
        ORDER BY count DESC
        """

        result = self.db.execute_query(query, {"document_id": document_id})

        coverage = {record["entity_type"]: record["count"] for record in result}

        # Calculate percentage distribution
        total = sum(coverage.values())
        distribution = {
            entity_type: {
                "count": count,
                "percentage": round(100 * count / total, 1) if total > 0 else 0,
            }
            for entity_type, count in coverage.items()
        }

        return distribution

    def _analyze_relationship_patterns(self, document_id: str) -> Dict:
        """Analyze common relationship patterns."""
        # Find common relationship triples (entity_type -> relationship -> entity_type)
        query = """
        MATCH (source {document_id: $document_id})-[r]->(target {document_id: $document_id})
        RETURN source.type as source_type, type(r) as rel_type, target.type as target_type,
               count(*) as count
        ORDER BY count DESC
        LIMIT 20
        """

        result = self.db.execute_query(query, {"document_id": document_id})

        patterns = [
            {
                "pattern": f"{record['source_type']} --[{record['rel_type']}]--> {record['target_type']}",
                "count": record["count"],
            }
            for record in result
        ]

        return patterns

    def export_graph_summary(self, document_id: Optional[str] = None) -> str:
        """
        Export graph summary as formatted text.

        Args:
            document_id: Optional document filter

        Returns:
            Formatted summary text
        """
        stats = self.get_graph_statistics(document_id)

        summary = []
        summary.append("=" * 70)
        summary.append("KNOWLEDGE GRAPH SUMMARY")
        summary.append("=" * 70)

        # Basic stats
        summary.append("\nBASIC STATISTICS:")
        summary.append(f"  Total Nodes: {stats['basic']['total_nodes']}")
        summary.append(f"  Total Relationships: {stats['basic']['total_relationships']}")
        summary.append(f"  Average Degree: {stats['basic']['avg_degree']}")

        # Node types
        summary.append("\nNODE TYPES:")
        for node_type, node_stats in stats['nodes'].items():
            summary.append(f"  {node_type}: {node_stats['count']} nodes")
            if node_stats['avg_confidence']:
                summary.append(f"    Avg confidence: {node_stats['avg_confidence']}")

        # Relationship types
        summary.append("\nRELATIONSHIP TYPES:")
        for rel_type, rel_stats in stats['relationships'].items():
            summary.append(f"  {rel_type}: {rel_stats['count']} relationships")
            if rel_stats['avg_confidence']:
                summary.append(f"    Avg confidence: {rel_stats['avg_confidence']}")

        # Connectivity
        summary.append("\nCONNECTIVITY:")
        conn = stats['connectivity']
        summary.append(f"  Min Degree: {conn.get('min_degree', 0)}")
        summary.append(f"  Max Degree: {conn.get('max_degree', 0)}")
        summary.append(f"  Avg Degree: {conn.get('avg_degree', 0)}")
        summary.append(f"  Median Degree: {conn.get('median_degree', 0)}")

        # Hub nodes
        if conn.get('hub_nodes'):
            summary.append("\nHUB NODES (Highest Degree):")
            for hub in conn['hub_nodes'][:5]:
                summary.append(f"  - {hub['text']} (degree: {hub['degree']})")

        # Metrics
        summary.append("\nGRAPH METRICS:")
        summary.append(f"  Density: {stats['metrics']['density']}")
        if stats['metrics'].get('avg_path_length'):
            summary.append(f"  Avg Path Length: {stats['metrics']['avg_path_length']}")

        summary.append("=" * 70)

        return "\n".join(summary)
