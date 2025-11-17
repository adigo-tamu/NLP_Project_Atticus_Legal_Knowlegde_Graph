#!/usr/bin/env python
"""
Test script for graph population pipeline.

This script demonstrates the complete graph population workflow including:
- Entity and relationship extraction from multiple documents
- Cross-document entity disambiguation
- Graph validation and quality metrics
- Export to various formats (GraphML, RDF, JSON)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.graph.graph_exporter import GraphExporter
from atticus.graph.graph_population import GraphPopulationPipeline

logger = get_logger(__name__)


def test_graph_population():
    """Test complete graph population pipeline."""

    logger.info("=" * 70)
    logger.info("GRAPH POPULATION PIPELINE TEST")
    logger.info("=" * 70)

    try:
        # Check API keys
        config = get_config()
        if not config.validate_api_keys():
            logger.error("API keys not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")
            logger.info("Copy .env.example to .env and add your API keys")
            return

        # Initialize pipeline
        logger.info("\nInitializing graph population pipeline...")
        pipeline = GraphPopulationPipeline()

        # For this demo, we'll use sample documents
        # In production, you would provide actual document paths
        sample_docs = []

        # Check if sample documents exist
        data_dir = Path(__file__).parent.parent / "data" / "sample"
        if data_dir.exists():
            sample_docs = list(data_dir.glob("*.pdf"))[:3]  # Process up to 3 documents

        if not sample_docs:
            logger.warning("No sample documents found in data/sample/")
            logger.info("The pipeline is initialized and ready to process documents.")
            logger.info("Usage:")
            logger.info("  pipeline.populate_from_documents(document_paths=['path/to/doc1.pdf', ...])")
            logger.info("\nDemonstrating graph statistics and export instead...")

            # Demonstrate statistics
            logger.info("\n" + "=" * 70)
            logger.info("GRAPH STATISTICS")
            logger.info("=" * 70)

            stats = pipeline.get_population_statistics()

            if stats.get("graph"):
                logger.info(f"\nBasic Statistics:")
                logger.info(f"  Total Nodes: {stats['graph']['basic']['total_nodes']}")
                logger.info(f"  Total Relationships: {stats['graph']['basic']['total_relationships']}")
                logger.info(f"  Average Degree: {stats['graph']['basic']['avg_degree']}")

                logger.info(f"\nGraph Metrics:")
                logger.info(f"  Density: {stats['graph']['metrics']['density']}")

                logger.info(f"\nNode Types:")
                for node_type, node_stats in stats['graph']['nodes'].items():
                    logger.info(f"  {node_type}: {node_stats['count']} nodes")

                logger.info(f"\nRelationship Types:")
                for rel_type, rel_stats in stats['graph']['relationships'].items():
                    logger.info(f"  {rel_type}: {rel_stats['count']} relationships")

            if stats.get("validation"):
                logger.info(f"\nValidation:")
                logger.info(f"  Total Issues: {stats['validation']['total_issues']}")

            # Demonstrate export
            logger.info("\n" + "=" * 70)
            logger.info("GRAPH EXPORT DEMO")
            logger.info("=" * 70)

            output_dir = Path(__file__).parent.parent / "output"
            output_dir.mkdir(exist_ok=True)

            exporter = GraphExporter()

            # Export to GraphML
            graphml_path = output_dir / "knowledge_graph.graphml"
            logger.info(f"\nExporting to GraphML: {graphml_path}")
            if exporter.export_to_graphml(str(graphml_path)):
                logger.info("✓ GraphML export successful")

            # Export to RDF (Turtle)
            rdf_path = output_dir / "knowledge_graph.ttl"
            logger.info(f"\nExporting to RDF (Turtle): {rdf_path}")
            if exporter.export_to_rdf(str(rdf_path), format="turtle"):
                logger.info("✓ RDF export successful")

            # Export to JSON
            json_path = output_dir / "knowledge_graph.json"
            logger.info(f"\nExporting to JSON: {json_path}")
            if exporter.export_to_json(str(json_path)):
                logger.info("✓ JSON export successful")

            # Export summary report
            report_path = output_dir / "graph_summary.txt"
            logger.info(f"\nExporting summary report: {report_path}")
            pipeline.export_summary_report(str(report_path))
            logger.info("✓ Summary report exported")

            logger.info("\n" + "=" * 70)
            logger.info("EXPORT COMPLETED")
            logger.info("=" * 70)
            logger.info(f"  Output directory: {output_dir}")
            logger.info(f"  Files generated:")
            logger.info(f"    - {graphml_path.name} (GraphML format)")
            logger.info(f"    - {rdf_path.name} (RDF Turtle format)")
            logger.info(f"    - {json_path.name} (JSON format)")
            logger.info(f"    - {report_path.name} (Summary report)")
            logger.info("=" * 70)

        else:
            # Process sample documents
            logger.info(f"\nFound {len(sample_docs)} sample documents:")
            for doc in sample_docs:
                logger.info(f"  - {doc.name}")

            logger.info("\nProcessing documents...")
            summary = pipeline.populate_from_documents(
                document_paths=[str(d) for d in sample_docs],
                disambiguate=True,
                validate=True,
            )

            # Display summary
            logger.info("\n" + "=" * 70)
            logger.info("POPULATION SUMMARY")
            logger.info("=" * 70)
            logger.info(f"  Documents processed: {summary['successful']}/{summary['total_documents']}")
            logger.info(f"  Total entities: {summary['total_entities']}")
            logger.info(f"  Total relationships: {summary['total_relationships']}")

            if "disambiguation" in summary:
                logger.info(f"  Entity clusters: {summary['disambiguation']['total_clusters']}")
                logger.info(f"  Merged entities: {summary['disambiguation']['merged_entities']}")

            if "validation" in summary:
                logger.info(f"  Validation issues: {summary['validation']['total_issues']}")

            if "quality_metrics" in summary:
                logger.info(f"  Graph density: {summary['quality_metrics']['graph_density']}")

            # Export results
            logger.info("\n" + "=" * 70)
            logger.info("EXPORTING RESULTS")
            logger.info("=" * 70)

            output_dir = Path(__file__).parent.parent / "output"
            output_dir.mkdir(exist_ok=True)

            exporter = GraphExporter()

            # Export to all formats
            exporter.export_to_graphml(str(output_dir / "knowledge_graph.graphml"))
            exporter.export_to_rdf(str(output_dir / "knowledge_graph.ttl"), format="turtle")
            exporter.export_to_json(str(output_dir / "knowledge_graph.json"))
            pipeline.export_summary_report(str(output_dir / "graph_summary.txt"))

            logger.info("✓ All exports completed")

        logger.info("\n" + "=" * 70)
        logger.info("✓ TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


def test_validation_and_repair():
    """Test graph validation and repair."""

    logger.info("\n" + "=" * 70)
    logger.info("VALIDATION AND REPAIR TEST")
    logger.info("=" * 70)

    try:
        pipeline = GraphPopulationPipeline()

        # Run validation and repair
        logger.info("\nRunning validation and repair...")
        report = pipeline.validate_and_repair()

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 70)

        if report["validation"]:
            total_issues = report["validation"]["summary"]["total_issues"]
            logger.info(f"  Total issues found: {total_issues}")

            for check_name, count in report["validation"]["summary"]["issues_by_check"].items():
                if count > 0:
                    logger.warning(f"    {check_name}: {count} issues")

        logger.info("\n" + "=" * 70)
        logger.info("REPAIR RESULTS")
        logger.info("=" * 70)
        logger.info(f"  Orphan nodes removed: {report['repairs']['orphan_nodes_removed']}")
        logger.info(f"  Self-loops removed: {report['repairs']['self_loops_removed']}")
        logger.info(f"  Duplicate relationships removed: {report['repairs']['duplicate_relationships_removed']}")

        logger.info("\n✓ Validation and repair completed")

    except Exception as e:
        logger.error(f"\n✗ Validation test failed: {e}", exc_info=True)


def main():
    """Run all tests."""

    # Test 1: Graph population
    test_graph_population()

    # Test 2: Validation and repair
    test_validation_and_repair()


if __name__ == "__main__":
    main()
