"""
Graph consistency validation and quality checks.

This module implements validation rules and quality checks for the knowledge graph
to ensure consistency, completeness, and correctness.
"""

from typing import Dict, List, Optional, Set, Tuple

from atticus.core.logger import get_logger
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class GraphValidator:
    """Validates knowledge graph consistency and quality."""

    def __init__(self, neo4j_manager: Optional[Neo4jManager] = None):
        """
        Initialize graph validator.

        Args:
            neo4j_manager: Neo4j manager instance
        """
        self.db = neo4j_manager or Neo4jManager()
        self.validation_results = {}

    def validate_graph(self, document_id: Optional[str] = None) -> Dict:
        """
        Run all validation checks on the graph.

        Args:
            document_id: Optional document ID to validate (None for entire graph)

        Returns:
            Dictionary with validation results
        """
        logger.info(f"Running graph validation{f' for document {document_id}' if document_id else ''}...")

        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "checks": {},
        }

        # Run all validation checks
        checks = [
            ("orphan_nodes", self.check_orphan_nodes),
            ("dangling_relationships", self.check_dangling_relationships),
            ("self_loops", self.check_self_loops),
            ("duplicate_relationships", self.check_duplicate_relationships),
            ("missing_properties", self.check_missing_properties),
            ("invalid_confidence", self.check_invalid_confidence),
            ("circular_dependencies", self.check_circular_dependencies),
            ("consistency", self.check_semantic_consistency),
        ]

        for check_name, check_func in checks:
            try:
                check_result = check_func(document_id)
                results["checks"][check_name] = check_result

                if check_result.get("errors"):
                    results["errors"].extend(check_result["errors"])
                    results["valid"] = False

                if check_result.get("warnings"):
                    results["warnings"].extend(check_result["warnings"])

            except Exception as e:
                logger.error(f"Validation check '{check_name}' failed: {e}")
                results["errors"].append(f"Check '{check_name}' failed: {str(e)}")
                results["valid"] = False

        # Summary
        results["summary"] = {
            "total_errors": len(results["errors"]),
            "total_warnings": len(results["warnings"]),
            "checks_passed": sum(1 for c in results["checks"].values() if c.get("passed", False)),
            "checks_total": len(checks),
        }

        logger.info(
            f"Validation complete: {results['summary']['checks_passed']}/{results['summary']['checks_total']} "
            f"checks passed, {results['summary']['total_errors']} errors, "
            f"{results['summary']['total_warnings']} warnings"
        )

        return results

    def check_orphan_nodes(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for orphan nodes (nodes with no relationships).

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        if document_id:
            query = """
            MATCH (n {document_id: $document_id})
            WHERE NOT (n)--()
            RETURN n.id as node_id, labels(n) as labels, n.text as text
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (n)
            WHERE NOT (n)--()
            RETURN n.id as node_id, labels(n) as labels, n.text as text
            LIMIT 100
            """
            params = {}

        result = self.db.execute_query(query, params)

        orphans = [
            {
                "id": record["node_id"],
                "labels": record["labels"],
                "text": record["text"][:50] if record.get("text") else "N/A",
            }
            for record in result
        ]

        passed = len(orphans) == 0

        return {
            "passed": passed,
            "orphan_count": len(orphans),
            "orphans": orphans[:10],  # Return first 10
            "warnings": [f"Found {len(orphans)} orphan nodes"] if orphans else [],
        }

    def check_dangling_relationships(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for relationships pointing to non-existent nodes.

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        # This shouldn't happen in Neo4j (referential integrity)
        # but we check anyway

        if document_id:
            query = """
            MATCH ()-[r {document_id: $document_id}]->()
            WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
            RETURN r.id as rel_id, type(r) as rel_type
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH ()-[r]->()
            WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
            RETURN r.id as rel_id, type(r) as rel_type
            LIMIT 100
            """
            params = {}

        result = self.db.execute_query(query, params)

        dangling = [{"id": record["rel_id"], "type": record["rel_type"]} for record in result]

        passed = len(dangling) == 0

        return {
            "passed": passed,
            "dangling_count": len(dangling),
            "errors": [f"Found {len(dangling)} dangling relationships"] if dangling else [],
        }

    def check_self_loops(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for self-loop relationships (node pointing to itself).

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        if document_id:
            query = """
            MATCH (n {document_id: $document_id})-[r]->(n)
            RETURN n.id as node_id, type(r) as rel_type, r.id as rel_id
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (n)-[r]->(n)
            RETURN n.id as node_id, type(r) as rel_type, r.id as rel_id
            LIMIT 100
            """
            params = {}

        result = self.db.execute_query(query, params)

        self_loops = [
            {
                "node_id": record["node_id"],
                "relationship_type": record["rel_type"],
                "relationship_id": record["rel_id"],
            }
            for record in result
        ]

        # Self-loops are usually errors
        passed = len(self_loops) == 0

        return {
            "passed": passed,
            "self_loop_count": len(self_loops),
            "self_loops": self_loops[:10],
            "errors": [f"Found {len(self_loops)} self-loop relationships"] if self_loops else [],
        }

    def check_duplicate_relationships(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for duplicate relationships (same source, target, type).

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        if document_id:
            query = """
            MATCH (a {document_id: $document_id})-[r]->(b)
            WITH a, b, type(r) as rel_type, collect(r) as rels
            WHERE size(rels) > 1
            RETURN a.id as source_id, b.id as target_id, rel_type, size(rels) as count
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (a)-[r]->(b)
            WITH a, b, type(r) as rel_type, collect(r) as rels
            WHERE size(rels) > 1
            RETURN a.id as source_id, b.id as target_id, rel_type, size(rels) as count
            LIMIT 100
            """
            params = {}

        result = self.db.execute_query(query, params)

        duplicates = [
            {
                "source": record["source_id"],
                "target": record["target_id"],
                "type": record["rel_type"],
                "count": record["count"],
            }
            for record in result
        ]

        passed = len(duplicates) == 0

        return {
            "passed": passed,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates[:10],
            "warnings": [f"Found {len(duplicates)} duplicate relationships"] if duplicates else [],
        }

    def check_missing_properties(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for nodes/relationships missing required properties.

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        issues = []

        # Check for entities missing required properties
        required_entity_props = ["id", "text", "type", "confidence"]

        if document_id:
            query = f"""
            MATCH (n {{document_id: $document_id}})
            WHERE any(prop in {required_entity_props} WHERE NOT exists(n[prop]))
            RETURN n.id as node_id, labels(n) as labels,
                   [prop in {required_entity_props} WHERE NOT exists(n[prop])] as missing_props
            LIMIT 50
            """
            params = {"document_id": document_id}
        else:
            query = f"""
            MATCH (n)
            WHERE any(prop in {required_entity_props} WHERE NOT exists(n[prop]))
            RETURN n.id as node_id, labels(n) as labels,
                   [prop in {required_entity_props} WHERE NOT exists(n[prop])] as missing_props
            LIMIT 50
            """
            params = {}

        result = self.db.execute_query(query, params)

        for record in result:
            issues.append(
                {
                    "type": "node",
                    "id": record["node_id"],
                    "labels": record["labels"],
                    "missing_properties": record["missing_props"],
                }
            )

        passed = len(issues) == 0

        return {
            "passed": passed,
            "missing_property_count": len(issues),
            "issues": issues[:10],
            "warnings": [f"Found {len(issues)} nodes with missing properties"] if issues else [],
        }

    def check_invalid_confidence(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for confidence scores outside valid range [0, 1].

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        issues = []

        # Check nodes
        if document_id:
            node_query = """
            MATCH (n {document_id: $document_id})
            WHERE exists(n.confidence) AND (n.confidence < 0 OR n.confidence > 1)
            RETURN n.id as id, n.confidence as confidence, 'node' as type
            """
            params = {"document_id": document_id}
        else:
            node_query = """
            MATCH (n)
            WHERE exists(n.confidence) AND (n.confidence < 0 OR n.confidence > 1)
            RETURN n.id as id, n.confidence as confidence, 'node' as type
            LIMIT 50
            """
            params = {}

        result = self.db.execute_query(node_query, params)
        issues.extend([dict(record) for record in result])

        # Check relationships
        if document_id:
            rel_query = """
            MATCH ()-[r {document_id: $document_id}]->()
            WHERE exists(r.confidence) AND (r.confidence < 0 OR r.confidence > 1)
            RETURN r.id as id, r.confidence as confidence, type(r) as type
            """
        else:
            rel_query = """
            MATCH ()-[r]->()
            WHERE exists(r.confidence) AND (r.confidence < 0 OR r.confidence > 1)
            RETURN r.id as id, r.confidence as confidence, type(r) as type
            LIMIT 50
            """

        result = self.db.execute_query(rel_query, params)
        issues.extend([dict(record) for record in result])

        passed = len(issues) == 0

        return {
            "passed": passed,
            "invalid_confidence_count": len(issues),
            "issues": issues[:10],
            "errors": [f"Found {len(issues)} items with invalid confidence scores"] if issues else [],
        }

    def check_circular_dependencies(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for circular DEPENDS_ON relationships.

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        if document_id:
            query = """
            MATCH path = (n {document_id: $document_id})-[:DEPENDS_ON*]->(n)
            RETURN [node in nodes(path) | node.id] as cycle
            LIMIT 20
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH path = (n)-[:DEPENDS_ON*]->(n)
            RETURN [node in nodes(path) | node.id] as cycle
            LIMIT 20
            """
            params = {}

        result = self.db.execute_query(query, params)

        cycles = [record["cycle"] for record in result]

        passed = len(cycles) == 0

        return {
            "passed": passed,
            "cycle_count": len(cycles),
            "cycles": cycles[:5],
            "warnings": [f"Found {len(cycles)} circular dependencies"] if cycles else [],
        }

    def check_semantic_consistency(self, document_id: Optional[str] = None) -> Dict:
        """
        Check for semantic consistency issues.

        Examples:
        - OBLIGATES relationship where source is not a Legal_Party
        - GRANTS_RIGHT where target is not a Right
        - Etc.

        Args:
            document_id: Optional document filter

        Returns:
            Check result dictionary
        """
        issues = []

        # Check OBLIGATES relationships
        # Source should be a Legal_Party or Clause
        if document_id:
            query = """
            MATCH (source {document_id: $document_id})-[r:OBLIGATES]->(target)
            WHERE NOT 'LegalParty' IN labels(source) AND NOT 'Clause' IN labels(source)
            RETURN source.id as source_id, labels(source) as source_labels, r.id as rel_id
            LIMIT 20
            """
            params = {"document_id": document_id}
        else:
            query = """
            MATCH (source)-[r:OBLIGATES]->(target)
            WHERE NOT 'LegalParty' IN labels(source) AND NOT 'Clause' IN labels(source)
            RETURN source.id as source_id, labels(source) as source_labels, r.id as rel_id
            LIMIT 20
            """
            params = {}

        result = self.db.execute_query(query, params)
        for record in result:
            issues.append(
                {
                    "type": "semantic_mismatch",
                    "relationship": "OBLIGATES",
                    "issue": f"Source {record['source_id']} has unexpected labels: {record['source_labels']}",
                }
            )

        passed = len(issues) == 0

        return {
            "passed": passed,
            "consistency_issue_count": len(issues),
            "issues": issues[:10],
            "warnings": [f"Found {len(issues)} semantic consistency issues"] if issues else [],
        }

    def get_graph_quality_score(self, document_id: Optional[str] = None) -> float:
        """
        Calculate overall graph quality score (0-1).

        Args:
            document_id: Optional document filter

        Returns:
            Quality score between 0 and 1
        """
        validation_results = self.validate_graph(document_id)

        # Calculate score based on checks passed
        checks_passed = validation_results["summary"]["checks_passed"]
        checks_total = validation_results["summary"]["checks_total"]

        base_score = checks_passed / checks_total if checks_total > 0 else 0

        # Penalize for errors (more severe than warnings)
        error_count = validation_results["summary"]["total_errors"]
        warning_count = validation_results["summary"]["total_warnings"]

        # Penalty: -0.1 per error, -0.05 per warning (capped)
        penalty = min(0.5, (error_count * 0.1) + (warning_count * 0.05))

        quality_score = max(0.0, base_score - penalty)

        logger.info(f"Graph quality score: {quality_score:.2f}")

        return quality_score
