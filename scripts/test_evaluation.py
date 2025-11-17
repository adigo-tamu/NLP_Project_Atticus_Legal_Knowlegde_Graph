#!/usr/bin/env python
"""
Test script for evaluation framework.

This script demonstrates how to use the evaluation framework to measure
entity extraction, relationship extraction, and graph construction performance.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.logger import get_logger
from atticus.core.models import Entity, EntityType, Position, Relationship, RelationshipType
from atticus.evaluation import (
    EntityEvaluator,
    GraphEvaluator,
    RelationshipEvaluator,
)

logger = get_logger(__name__)


def create_sample_data():
    """Create sample predicted and ground truth data for testing."""

    # Sample predicted entities
    predicted_entities = [
        Entity(
            id="pred_1",
            text="TechCorp Inc.",
            type=EntityType.LEGAL_PARTY,
            confidence=0.95,
            document_id="doc_1",
            position=Position(start=10, end=23, page=1),
        ),
        Entity(
            id="pred_2",
            text="Payment of $10,000",
            type=EntityType.FINANCIAL_TERM,
            confidence=0.88,
            document_id="doc_1",
            position=Position(start=50, end=68, page=1),
        ),
        Entity(
            id="pred_3",
            text="Confidentiality",
            type=EntityType.OBLIGATION,
            confidence=0.92,
            document_id="doc_1",
            position=Position(start=100, end=115, page=1),
        ),
        Entity(
            id="pred_4",
            text="California",
            type=EntityType.JURISDICTION,
            confidence=0.97,
            document_id="doc_1",
            position=Position(start=200, end=210, page=2),
        ),
        # Extra predicted entity (false positive)
        Entity(
            id="pred_5",
            text="Nonexistent Party",
            type=EntityType.LEGAL_PARTY,
            confidence=0.70,
            document_id="doc_1",
            position=Position(start=300, end=317, page=2),
        ),
    ]

    # Sample ground truth entities
    ground_truth_entities = [
        Entity(
            id="gt_1",
            text="TechCorp Inc.",
            type=EntityType.LEGAL_PARTY,
            confidence=1.0,
            document_id="doc_1",
            position=Position(start=10, end=23, page=1),
        ),
        Entity(
            id="gt_2",
            text="Payment of $10,000",
            type=EntityType.FINANCIAL_TERM,
            confidence=1.0,
            document_id="doc_1",
            position=Position(start=50, end=68, page=1),
        ),
        Entity(
            id="gt_3",
            text="Confidentiality",
            type=EntityType.OBLIGATION,
            confidence=1.0,
            document_id="doc_1",
            position=Position(start=100, end=115, page=1),
        ),
        Entity(
            id="gt_4",
            text="California",
            type=EntityType.JURISDICTION,
            confidence=1.0,
            document_id="doc_1",
            position=Position(start=200, end=210, page=2),
        ),
        # Missed entity (false negative)
        Entity(
            id="gt_5",
            text="30 days",
            type=EntityType.TEMPORAL_ENTITY,
            confidence=1.0,
            document_id="doc_1",
            position=Position(start=250, end=257, page=2),
        ),
    ]

    # Sample predicted relationships
    predicted_relationships = [
        Relationship(
            id="pred_rel_1",
            source_id="pred_1",
            target_id="pred_2",
            type=RelationshipType.OBLIGATES,
            confidence=0.89,
            evidence="TechCorp Inc. shall pay $10,000...",
            document_id="doc_1",
        ),
        Relationship(
            id="pred_rel_2",
            source_id="pred_1",
            target_id="pred_3",
            type=RelationshipType.OBLIGATES,
            confidence=0.85,
            evidence="TechCorp Inc. must maintain confidentiality...",
            document_id="doc_1",
        ),
        Relationship(
            id="pred_rel_3",
            source_id="pred_4",
            target_id="pred_1",
            type=RelationshipType.GOVERNS,
            confidence=0.91,
            evidence="This agreement shall be governed by California law...",
            document_id="doc_1",
        ),
        # Extra relationship (false positive)
        Relationship(
            id="pred_rel_4",
            source_id="pred_5",
            target_id="pred_2",
            type=RelationshipType.REFERENCES,
            confidence=0.72,
            evidence="...",
            document_id="doc_1",
        ),
    ]

    # Sample ground truth relationships
    ground_truth_relationships = [
        Relationship(
            id="gt_rel_1",
            source_id="gt_1",
            target_id="gt_2",
            type=RelationshipType.OBLIGATES,
            confidence=1.0,
            evidence="TechCorp Inc. shall pay $10,000...",
            document_id="doc_1",
        ),
        Relationship(
            id="gt_rel_2",
            source_id="gt_1",
            target_id="gt_3",
            type=RelationshipType.OBLIGATES,
            confidence=1.0,
            evidence="TechCorp Inc. must maintain confidentiality...",
            document_id="doc_1",
        ),
        Relationship(
            id="gt_rel_3",
            source_id="gt_4",
            target_id="gt_1",
            type=RelationshipType.GOVERNS,
            confidence=1.0,
            evidence="This agreement shall be governed by California law...",
            document_id="doc_1",
        ),
        # Missed relationship (false negative)
        Relationship(
            id="gt_rel_4",
            source_id="gt_2",
            target_id="gt_5",
            type=RelationshipType.TEMPORALLY_PRECEDES,
            confidence=1.0,
            evidence="Payment within 30 days...",
            document_id="doc_1",
        ),
    ]

    return (
        predicted_entities,
        ground_truth_entities,
        predicted_relationships,
        ground_truth_relationships,
    )


def test_entity_evaluation():
    """Test entity extraction evaluation."""
    logger.info("=" * 70)
    logger.info("TEST 1: Entity Extraction Evaluation")
    logger.info("=" * 70)

    # Get sample data
    (
        predicted_entities,
        ground_truth_entities,
        _,
        _,
    ) = create_sample_data()

    # Initialize evaluator
    evaluator = EntityEvaluator(matching_strategy="exact")

    # Run evaluation
    results = evaluator.evaluate(
        predicted_entities=predicted_entities,
        ground_truth_entities=ground_truth_entities,
        by_type=True,
    )

    # Print results
    evaluator.print_results(results)

    # Export results
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    evaluator.export_results(results, str(output_dir / "entity_evaluation.json"))

    # Check if target met
    target_f1 = 0.85
    actual_f1 = results["overall"].f1

    if actual_f1 >= target_f1:
        logger.info(f"✓ Entity F1 target met: {actual_f1:.4f} >= {target_f1}")
    else:
        logger.warning(f"⚠ Entity F1 below target: {actual_f1:.4f} < {target_f1}")

    return results


def test_relationship_evaluation():
    """Test relationship extraction evaluation."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Relationship Extraction Evaluation")
    logger.info("=" * 70)

    # Get sample data
    (
        _,
        _,
        predicted_relationships,
        ground_truth_relationships,
    ) = create_sample_data()

    # Initialize evaluator
    evaluator = RelationshipEvaluator(matching_strategy="exact")

    # Run evaluation
    results = evaluator.evaluate(
        predicted_relationships=predicted_relationships,
        ground_truth_relationships=ground_truth_relationships,
        by_type=True,
    )

    # Print results
    evaluator.print_results(results)

    # Export results
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    evaluator.export_results(
        results, str(output_dir / "relationship_evaluation.json")
    )

    # Check if target met
    target_f1 = 0.70
    actual_f1 = results["overall"].f1

    if actual_f1 >= target_f1:
        logger.info(f"✓ Relationship F1 target met: {actual_f1:.4f} >= {target_f1}")
    else:
        logger.warning(
            f"⚠ Relationship F1 below target: {actual_f1:.4f} < {target_f1}"
        )

    return results


def test_graph_evaluation():
    """Test graph construction evaluation (full triples)."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Graph Evaluation (Full Triples)")
    logger.info("=" * 70)

    # Get sample data
    (
        predicted_entities,
        ground_truth_entities,
        predicted_relationships,
        ground_truth_relationships,
    ) = create_sample_data()

    # Initialize evaluator
    evaluator = GraphEvaluator(matching_strategy="exact")

    # Run evaluation
    results = evaluator.evaluate(
        predicted_entities=predicted_entities,
        predicted_relationships=predicted_relationships,
        ground_truth_entities=ground_truth_entities,
        ground_truth_relationships=ground_truth_relationships,
        by_relationship_type=True,
    )

    # Print results
    evaluator.print_results(results)

    # Export results
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    evaluator.export_results(results, str(output_dir / "graph_evaluation.json"))

    # Check if target met
    target_f1 = 0.40
    actual_f1 = results["overall"].f1

    if actual_f1 >= target_f1:
        logger.info(f"✓ Graph F1 target met: {actual_f1:.4f} >= {target_f1}")
    else:
        logger.warning(f"⚠ Graph F1 below target: {actual_f1:.4f} < {target_f1}")

    return results


def generate_summary_report(
    entity_results: dict,
    relationship_results: dict,
    graph_results: dict,
):
    """Generate comprehensive evaluation summary report."""
    logger.info("\n" + "=" * 70)
    logger.info("COMPREHENSIVE EVALUATION SUMMARY")
    logger.info("=" * 70)

    # Performance targets
    logger.info("\nPerformance Targets:")
    logger.info("  Entity F1:        ≥ 0.85")
    logger.info("  Relationship F1:  ≥ 0.70")
    logger.info("  Graph F1:         ≥ 0.40")

    # Actual results
    logger.info("\nActual Results:")
    entity_f1 = entity_results["overall"].f1
    rel_f1 = relationship_results["overall"].f1
    graph_f1 = graph_results["overall"].f1

    logger.info(f"  Entity F1:        {entity_f1:.4f} {'✓' if entity_f1 >= 0.85 else '✗'}")
    logger.info(f"  Relationship F1:  {rel_f1:.4f} {'✓' if rel_f1 >= 0.70 else '✗'}")
    logger.info(f"  Graph F1:         {graph_f1:.4f} {'✓' if graph_f1 >= 0.40 else '✗'}")

    # Detailed breakdown
    logger.info("\n" + "-" * 70)
    logger.info("Detailed Breakdown")
    logger.info("-" * 70)

    logger.info("\nEntity Extraction:")
    logger.info(f"  Precision: {entity_results['overall'].precision:.4f}")
    logger.info(f"  Recall:    {entity_results['overall'].recall:.4f}")
    logger.info(f"  F1 Score:  {entity_results['overall'].f1:.4f}")

    logger.info("\nRelationship Extraction:")
    logger.info(f"  Precision: {relationship_results['overall'].precision:.4f}")
    logger.info(f"  Recall:    {relationship_results['overall'].recall:.4f}")
    logger.info(f"  F1 Score:  {relationship_results['overall'].f1:.4f}")

    logger.info("\nGraph Construction:")
    logger.info(f"  Precision: {graph_results['overall'].precision:.4f}")
    logger.info(f"  Recall:    {graph_results['overall'].recall:.4f}")
    logger.info(f"  F1 Score:  {graph_results['overall'].f1:.4f}")

    # Overall assessment
    all_targets_met = entity_f1 >= 0.85 and rel_f1 >= 0.70 and graph_f1 >= 0.40

    logger.info("\n" + "=" * 70)
    if all_targets_met:
        logger.info("✓ ALL PERFORMANCE TARGETS MET")
    else:
        logger.info("⚠ SOME PERFORMANCE TARGETS NOT MET")
    logger.info("=" * 70 + "\n")

    # Save summary report
    output_dir = Path(__file__).parent.parent / "output"
    report_path = output_dir / "evaluation_summary.txt"

    with open(report_path, "w") as f:
        f.write("PROJECT ATTICUS - EVALUATION SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write("Performance Targets:\n")
        f.write("  Entity F1:        ≥ 0.85\n")
        f.write("  Relationship F1:  ≥ 0.70\n")
        f.write("  Graph F1:         ≥ 0.40\n\n")
        f.write("Actual Results:\n")
        f.write(f"  Entity F1:        {entity_f1:.4f}\n")
        f.write(f"  Relationship F1:  {rel_f1:.4f}\n")
        f.write(f"  Graph F1:         {graph_f1:.4f}\n\n")
        f.write(f"Status: {'ALL TARGETS MET' if all_targets_met else 'TARGETS NOT MET'}\n")

    logger.info(f"Summary report saved to: {report_path}")


def main():
    """Run all evaluation tests."""

    logger.info("=" * 70)
    logger.info("PROJECT ATTICUS - EVALUATION FRAMEWORK TESTS")
    logger.info("=" * 70)
    logger.info("\nThis script demonstrates the evaluation framework using sample data.")
    logger.info("In production, use real extracted data and ground truth annotations.\n")

    try:
        # Run evaluations
        entity_results = test_entity_evaluation()
        relationship_results = test_relationship_evaluation()
        graph_results = test_graph_evaluation()

        # Generate summary
        generate_summary_report(entity_results, relationship_results, graph_results)

        logger.info("✓ All evaluation tests completed successfully\n")

    except Exception as e:
        logger.error(f"\n✗ Evaluation tests failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
