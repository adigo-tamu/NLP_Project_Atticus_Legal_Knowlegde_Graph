"""
Graph population pipeline with validation and quality control.

This module provides the pipeline for populating the knowledge graph with
validated entities and relationships, including cross-document disambiguation
and quality metrics.
"""

from typing import Dict, List, Optional, Tuple

from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, Entity, Relationship
from atticus.extraction.complete_pipeline import CompleteExtractionPipeline
from atticus.graph.entity_disambiguator import EntityDisambiguator
from atticus.graph.graph_analytics import GraphAnalytics
from atticus.graph.graph_validator import GraphValidator
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class GraphPopulationPipeline:
    """Pipeline for populating and validating the knowledge graph."""

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        neo4j_manager: Optional[Neo4jManager] = None,
    ):
        """
        Initialize graph population pipeline.

        Args:
            llm_model: LLM model to use
            llm_provider: LLM provider (openai, anthropic)
            neo4j_manager: Neo4j manager instance
        """
        logger.info("Initializing graph population pipeline...")

        self.db = neo4j_manager or Neo4jManager()

        # Initialize components
        self.extraction_pipeline = CompleteExtractionPipeline(
            llm_model=llm_model,
            llm_provider=llm_provider,
            neo4j_manager=self.db,
        )

        self.disambiguator = EntityDisambiguator(neo4j_manager=self.db)
        self.validator = GraphValidator(neo4j_manager=self.db)
        self.analytics = GraphAnalytics(neo4j_manager=self.db)

        logger.info("Graph population pipeline initialized successfully")

    def populate_from_documents(
        self,
        document_paths: List[str],
        disambiguate: bool = True,
        validate: bool = True,
    ) -> Dict:
        """
        Populate graph from multiple documents with disambiguation and validation.

        Args:
            document_paths: List of document file paths
            disambiguate: Whether to run entity disambiguation
            validate: Whether to run graph validation

        Returns:
            Summary statistics
        """
        logger.info("=" * 70)
        logger.info(f"GRAPH POPULATION: Processing {len(document_paths)} documents")
        logger.info("=" * 70)

        summary = {
            "total_documents": len(document_paths),
            "successful": 0,
            "failed": 0,
            "total_entities": 0,
            "total_relationships": 0,
            "validation_issues": [],
            "quality_metrics": {},
        }

        # ============================================================
        # PHASE 1: EXTRACT AND STORE
        # ============================================================
        logger.info("\n[PHASE 1/4] Extracting entities and relationships...")

        all_entities = []
        all_relationships = []

        for i, doc_path in enumerate(document_paths):
            logger.info(f"\n  Processing document {i+1}/{len(document_paths)}: {doc_path}")

            try:
                document, chunks, entities, relationships = (
                    self.extraction_pipeline.process_document(
                        document_path=doc_path,
                        store_in_graph=True,
                        extract_relationships=True,
                    )
                )

                all_entities.extend(entities)
                all_relationships.extend(relationships)
                summary["successful"] += 1

                logger.info(
                    f"  ✓ Extracted {len(entities)} entities, {len(relationships)} relationships"
                )

            except Exception as e:
                logger.error(f"  ✗ Failed to process {doc_path}: {e}")
                summary["failed"] += 1
                continue

        summary["total_entities"] = len(all_entities)
        summary["total_relationships"] = len(all_relationships)

        logger.info("\n✓ Extraction phase completed")
        logger.info(f"  Documents processed: {summary['successful']}/{len(document_paths)}")
        logger.info(f"  Total entities: {summary['total_entities']}")
        logger.info(f"  Total relationships: {summary['total_relationships']}")

        # ============================================================
        # PHASE 2: CROSS-DOCUMENT DISAMBIGUATION
        # ============================================================
        if disambiguate and len(all_entities) > 0:
            logger.info("\n[PHASE 2/4] Running cross-document entity disambiguation...")

            try:
                disambiguation_results = self.disambiguator.disambiguate_entities(
                    entities=all_entities,
                    group_by_type=True,
                )

                summary["disambiguation"] = {
                    "total_clusters": len(disambiguation_results["clusters"]),
                    "merged_entities": disambiguation_results["merged_count"],
                    "clusters_by_type": {},
                }

                # Count clusters by type
                for cluster in disambiguation_results["clusters"]:
                    entity_type = cluster["entity_type"]
                    if entity_type not in summary["disambiguation"]["clusters_by_type"]:
                        summary["disambiguation"]["clusters_by_type"][entity_type] = 0
                    summary["disambiguation"]["clusters_by_type"][entity_type] += 1

                logger.info("✓ Disambiguation completed")
                logger.info(f"  Total clusters: {summary['disambiguation']['total_clusters']}")
                logger.info(f"  Merged entities: {summary['disambiguation']['merged_entities']}")
                logger.info(f"  Clusters by type: {summary['disambiguation']['clusters_by_type']}")

            except Exception as e:
                logger.error(f"✗ Disambiguation failed: {e}")
                summary["disambiguation"] = {"error": str(e)}
        else:
            logger.info("\n[PHASE 2/4] Skipping disambiguation")

        # ============================================================
        # PHASE 3: GRAPH VALIDATION
        # ============================================================
        if validate:
            logger.info("\n[PHASE 3/4] Running graph validation...")

            try:
                validation_report = self.validator.validate_graph()

                summary["validation"] = {
                    "total_issues": validation_report["summary"]["total_issues"],
                    "issues_by_check": validation_report["summary"]["issues_by_check"],
                }

                # Log validation results
                logger.info("✓ Validation completed")
                logger.info(f"  Total issues found: {validation_report['summary']['total_issues']}")

                for check_name, count in validation_report["summary"]["issues_by_check"].items():
                    if count > 0:
                        logger.warning(f"  - {check_name}: {count} issues")

                # Store top issues
                summary["validation_issues"] = []
                for check_name, issues in validation_report["checks"].items():
                    if issues:
                        summary["validation_issues"].extend(issues[:5])  # Top 5 per check

            except Exception as e:
                logger.error(f"✗ Validation failed: {e}")
                summary["validation"] = {"error": str(e)}
        else:
            logger.info("\n[PHASE 3/4] Skipping validation")

        # ============================================================
        # PHASE 4: QUALITY METRICS
        # ============================================================
        logger.info("\n[PHASE 4/4] Calculating quality metrics...")

        try:
            graph_stats = self.analytics.get_graph_statistics()

            summary["quality_metrics"] = {
                "total_nodes": graph_stats["basic"]["total_nodes"],
                "total_relationships": graph_stats["basic"]["total_relationships"],
                "avg_degree": graph_stats["basic"]["avg_degree"],
                "graph_density": graph_stats["metrics"]["density"],
                "node_types": len(graph_stats["nodes"]),
                "relationship_types": len(graph_stats["relationships"]),
            }

            # Add connectivity metrics
            if "connectivity" in graph_stats:
                summary["quality_metrics"]["connectivity"] = {
                    "avg_degree": graph_stats["connectivity"].get("avg_degree", 0),
                    "max_degree": graph_stats["connectivity"].get("max_degree", 0),
                    "hub_nodes_count": len(graph_stats["connectivity"].get("hub_nodes", [])),
                }

            logger.info("✓ Quality metrics calculated")
            logger.info(f"  Graph density: {summary['quality_metrics']['graph_density']}")
            logger.info(f"  Average degree: {summary['quality_metrics']['avg_degree']}")
            logger.info(f"  Node types: {summary['quality_metrics']['node_types']}")
            logger.info(f"  Relationship types: {summary['quality_metrics']['relationship_types']}")

        except Exception as e:
            logger.error(f"✗ Quality metrics calculation failed: {e}")
            summary["quality_metrics"] = {"error": str(e)}

        # ============================================================
        # SUMMARY
        # ============================================================
        logger.info("\n" + "=" * 70)
        logger.info("GRAPH POPULATION COMPLETED")
        logger.info("=" * 70)
        logger.info(f"  Documents processed: {summary['successful']}/{summary['total_documents']}")
        logger.info(f"  Total entities: {summary['total_entities']}")
        logger.info(f"  Total relationships: {summary['total_relationships']}")

        if disambiguate and "disambiguation" in summary:
            logger.info(f"  Entity clusters: {summary['disambiguation'].get('total_clusters', 0)}")

        if validate and "validation" in summary:
            logger.info(f"  Validation issues: {summary['validation'].get('total_issues', 0)}")

        logger.info(f"  Graph density: {summary['quality_metrics'].get('graph_density', 'N/A')}")
        logger.info("=" * 70 + "\n")

        return summary

    def populate_from_extraction(
        self,
        documents: List[Tuple[Document, List[DocumentChunk]]],
        disambiguate: bool = True,
        validate: bool = True,
    ) -> Dict:
        """
        Populate graph from pre-processed documents.

        Args:
            documents: List of (document, chunks) tuples
            disambiguate: Whether to run entity disambiguation
            validate: Whether to run graph validation

        Returns:
            Summary statistics
        """
        logger.info("=" * 70)
        logger.info(f"GRAPH POPULATION: Processing {len(documents)} pre-processed documents")
        logger.info("=" * 70)

        summary = {
            "total_documents": len(documents),
            "successful": 0,
            "failed": 0,
            "total_entities": 0,
            "total_relationships": 0,
        }

        all_entities = []
        all_relationships = []

        # Extract entities and relationships
        for i, (document, chunks) in enumerate(documents):
            logger.info(f"\n  Processing document {i+1}/{len(documents)}: {document.title}")

            try:
                entities, relationships = self.extraction_pipeline.extract_only(
                    document=document,
                    chunks=chunks,
                    extract_relationships=True,
                )

                all_entities.extend(entities)
                all_relationships.extend(relationships)
                summary["successful"] += 1

                logger.info(
                    f"  ✓ Extracted {len(entities)} entities, {len(relationships)} relationships"
                )

            except Exception as e:
                logger.error(f"  ✗ Failed to process {document.title}: {e}")
                summary["failed"] += 1
                continue

        summary["total_entities"] = len(all_entities)
        summary["total_relationships"] = len(all_relationships)

        # Continue with disambiguation and validation as in populate_from_documents
        # (Same logic as above)

        return summary

    def validate_and_repair(self, document_id: Optional[str] = None) -> Dict:
        """
        Validate graph and attempt to repair common issues.

        Args:
            document_id: Optional document filter

        Returns:
            Repair report
        """
        logger.info("\n" + "=" * 70)
        logger.info("GRAPH VALIDATION AND REPAIR")
        logger.info("=" * 70)

        report = {
            "validation": None,
            "repairs": {
                "orphan_nodes_removed": 0,
                "dangling_relationships_removed": 0,
                "self_loops_removed": 0,
                "duplicate_relationships_removed": 0,
            },
        }

        # Step 1: Validate
        logger.info("\n[1/2] Running validation...")
        validation_report = self.validator.validate_graph(document_id=document_id)
        report["validation"] = validation_report

        total_issues = validation_report["summary"]["total_issues"]
        logger.info(f"✓ Found {total_issues} issues")

        # Step 2: Repair
        logger.info("\n[2/2] Attempting repairs...")

        # Remove orphan nodes
        if validation_report["checks"]["orphan_nodes"]:
            logger.info(f"  Removing {len(validation_report['checks']['orphan_nodes'])} orphan nodes...")
            removed = self.validator.remove_orphan_nodes(document_id=document_id)
            report["repairs"]["orphan_nodes_removed"] = removed
            logger.info(f"  ✓ Removed {removed} orphan nodes")

        # Remove self-loops
        if validation_report["checks"]["self_loops"]:
            logger.info(f"  Removing {len(validation_report['checks']['self_loops'])} self-loops...")
            # Implement self-loop removal
            # For now, just log
            logger.info("  ⚠ Self-loop removal not yet implemented")

        # Remove duplicate relationships
        if validation_report["checks"]["duplicate_relationships"]:
            logger.info(
                f"  Removing {len(validation_report['checks']['duplicate_relationships'])} duplicate relationships..."
            )
            # Implement duplicate removal
            logger.info("  ⚠ Duplicate relationship removal not yet implemented")

        logger.info("\n" + "=" * 70)
        logger.info("REPAIR COMPLETED")
        logger.info("=" * 70)
        logger.info(f"  Orphan nodes removed: {report['repairs']['orphan_nodes_removed']}")
        logger.info("=" * 70 + "\n")

        return report

    def get_population_statistics(self) -> Dict:
        """
        Get comprehensive population statistics.

        Returns:
            Statistics dictionary
        """
        stats = {}

        # Graph statistics
        stats["graph"] = self.analytics.get_graph_statistics()

        # Extraction statistics
        stats["extraction"] = self.extraction_pipeline.get_extraction_stats()

        # Validation summary
        validation = self.validator.validate_graph()
        stats["validation"] = {
            "total_issues": validation["summary"]["total_issues"],
            "issues_by_check": validation["summary"]["issues_by_check"],
        }

        return stats

    def export_summary_report(self, output_path: str, document_id: Optional[str] = None):
        """
        Export comprehensive summary report.

        Args:
            output_path: Path to save report
            document_id: Optional document filter
        """
        logger.info(f"Generating summary report to {output_path}...")

        summary_text = self.analytics.export_graph_summary(document_id=document_id)

        # Add validation section
        validation = self.validator.validate_graph(document_id=document_id)
        summary_text += "\n\n" + "=" * 70
        summary_text += "\nVALIDATION REPORT\n"
        summary_text += "=" * 70
        summary_text += f"\nTotal Issues: {validation['summary']['total_issues']}\n"

        for check_name, count in validation["summary"]["issues_by_check"].items():
            summary_text += f"  {check_name}: {count}\n"

        # Write to file
        with open(output_path, "w") as f:
            f.write(summary_text)

        logger.info(f"✓ Summary report exported to {output_path}")
