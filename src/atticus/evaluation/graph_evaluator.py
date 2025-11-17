"""
Graph-level evaluator for complete triples (entity-relationship-entity).

Evaluates end-to-end performance by matching full triples:
(source_entity, relationship_type, target_entity)

This is the strictest evaluation requiring all three components to match.
"""

import json
from typing import Dict, List, Set, Tuple

from atticus.core.logger import get_logger
from atticus.core.models import Entity, Relationship
from atticus.evaluation.metrics import EvaluationMetrics, MetricsCalculator

logger = get_logger(__name__)


class GraphTriple:
    """Represents a complete graph triple."""

    def __init__(
        self,
        source_text: str,
        source_type: str,
        relationship_type: str,
        target_text: str,
        target_type: str,
        confidence: float = 1.0,
    ):
        """Initialize graph triple."""
        self.source_text = source_text.lower().strip()
        self.source_type = source_type
        self.relationship_type = relationship_type
        self.target_text = target_text.lower().strip()
        self.target_type = target_type
        self.confidence = confidence

    def __hash__(self):
        """Hash for set operations."""
        return hash(
            (
                self.source_text,
                self.source_type,
                self.relationship_type,
                self.target_text,
                self.target_type,
            )
        )

    def __eq__(self, other):
        """Equality check."""
        if not isinstance(other, GraphTriple):
            return False
        return (
            self.source_text == other.source_text
            and self.source_type == other.source_type
            and self.relationship_type == other.relationship_type
            and self.target_text == other.target_text
            and self.target_type == other.target_type
        )

    def __str__(self):
        """String representation."""
        return (
            f"({self.source_text}:{self.source_type}) "
            f"-[{self.relationship_type}]-> "
            f"({self.target_text}:{self.target_type})"
        )


class GraphEvaluator:
    """Evaluate graph construction at the triple level."""

    def __init__(self, matching_strategy: str = "exact"):
        """
        Initialize graph evaluator.

        Args:
            matching_strategy: Matching strategy ("exact", "relaxed")
                - exact: All components must match exactly
                - relaxed: Allow some flexibility in entity text matching
        """
        self.matching_strategy = matching_strategy

    def evaluate(
        self,
        predicted_entities: List[Entity],
        predicted_relationships: List[Relationship],
        ground_truth_entities: List[Entity],
        ground_truth_relationships: List[Relationship],
        by_relationship_type: bool = True,
    ) -> Dict:
        """
        Evaluate graph construction performance.

        Args:
            predicted_entities: Predicted entities
            predicted_relationships: Predicted relationships
            ground_truth_entities: Ground truth entities
            ground_truth_relationships: Ground truth relationships
            by_relationship_type: Whether to calculate metrics by relationship type

        Returns:
            Dictionary with evaluation results
        """
        logger.info(f"Evaluating graph construction (full triples)...")

        # Build entity lookup maps
        pred_entity_map = {e.id: e for e in predicted_entities}
        gt_entity_map = {e.id: e for e in ground_truth_entities}

        # Convert to triples
        predicted_triples = self._build_triples(
            predicted_relationships, pred_entity_map
        )
        ground_truth_triples = self._build_triples(
            ground_truth_relationships, gt_entity_map
        )

        logger.info(f"  Predicted triples: {len(predicted_triples)}")
        logger.info(f"  Ground truth triples: {len(ground_truth_triples)}")

        results = {
            "matching_strategy": self.matching_strategy,
            "predicted_count": len(predicted_triples),
            "ground_truth_count": len(ground_truth_triples),
        }

        # Match triples
        matched, unmatched_pred, unmatched_gt = self._match_triples(
            predicted_triples, ground_truth_triples
        )

        logger.info(f"  Matched triples: {len(matched)}")
        logger.info(f"  Unmatched predicted: {len(unmatched_pred)}")
        logger.info(f"  Unmatched ground truth: {len(unmatched_gt)}")

        # Overall metrics
        overall_metrics = MetricsCalculator.calculate_metrics_from_sets(
            predicted=set(predicted_triples),
            ground_truth=set(ground_truth_triples),
        )

        results["overall"] = overall_metrics

        # Metrics by relationship type
        if by_relationship_type:
            metrics_by_type = self._calculate_metrics_by_type(
                predicted_triples, ground_truth_triples
            )
            results["by_relationship_type"] = metrics_by_type

            # Averages
            results["macro_average"] = MetricsCalculator.calculate_macro_average(
                metrics_by_type
            )
            results["micro_average"] = MetricsCalculator.calculate_micro_average(
                metrics_by_type
            )

        # Detailed error analysis
        results["errors"] = self._analyze_errors(unmatched_pred, unmatched_gt)

        # Component-wise breakdown
        results["component_analysis"] = self._analyze_components(
            predicted_triples,
            ground_truth_triples,
            matched,
        )

        return results

    def _build_triples(
        self,
        relationships: List[Relationship],
        entity_map: Dict[str, Entity],
    ) -> Set[GraphTriple]:
        """Build set of graph triples from relationships and entities."""
        triples = set()

        for rel in relationships:
            # Get source and target entities
            source = entity_map.get(rel.source_id)
            target = entity_map.get(rel.target_id)

            if not source or not target:
                logger.warning(
                    f"Skipping relationship {rel.id}: missing entity "
                    f"(source={rel.source_id}, target={rel.target_id})"
                )
                continue

            triple = GraphTriple(
                source_text=source.text,
                source_type=source.type.value,
                relationship_type=rel.type.value,
                target_text=target.text,
                target_type=target.type.value,
                confidence=rel.confidence,
            )

            triples.add(triple)

        return triples

    def _match_triples(
        self,
        predicted: Set[GraphTriple],
        ground_truth: Set[GraphTriple],
    ) -> Tuple[Set[GraphTriple], Set[GraphTriple], Set[GraphTriple]]:
        """
        Match predicted triples to ground truth.

        Returns:
            Tuple of (matched, unmatched_predicted, unmatched_ground_truth)
        """
        if self.matching_strategy == "exact":
            # Exact set intersection
            matched = predicted & ground_truth
            unmatched_pred = predicted - ground_truth
            unmatched_gt = ground_truth - predicted

        elif self.matching_strategy == "relaxed":
            # Allow fuzzy entity text matching
            matched = set()
            unmatched_pred = set(predicted)
            unmatched_gt = set(ground_truth)

            for pred_triple in predicted:
                for gt_triple in ground_truth:
                    if self._fuzzy_triple_match(pred_triple, gt_triple):
                        matched.add(gt_triple)
                        if pred_triple in unmatched_pred:
                            unmatched_pred.remove(pred_triple)
                        if gt_triple in unmatched_gt:
                            unmatched_gt.remove(gt_triple)
                        break

        else:
            matched = predicted & ground_truth
            unmatched_pred = predicted - ground_truth
            unmatched_gt = ground_truth - predicted

        return matched, unmatched_pred, unmatched_gt

    def _fuzzy_triple_match(
        self, triple1: GraphTriple, triple2: GraphTriple
    ) -> bool:
        """Check if two triples match with fuzzy text matching."""
        from difflib import SequenceMatcher

        # Types and relationship must match exactly
        if (
            triple1.source_type != triple2.source_type
            or triple1.relationship_type != triple2.relationship_type
            or triple1.target_type != triple2.target_type
        ):
            return False

        # Allow fuzzy text matching (80% threshold)
        source_sim = SequenceMatcher(
            None, triple1.source_text, triple2.source_text
        ).ratio()
        target_sim = SequenceMatcher(
            None, triple1.target_text, triple2.target_text
        ).ratio()

        return source_sim >= 0.8 and target_sim >= 0.8

    def _calculate_metrics_by_type(
        self,
        predicted_triples: Set[GraphTriple],
        ground_truth_triples: Set[GraphTriple],
    ) -> Dict[str, EvaluationMetrics]:
        """Calculate metrics for each relationship type."""
        # Group by relationship type
        pred_by_type = {}
        for triple in predicted_triples:
            rel_type = triple.relationship_type
            if rel_type not in pred_by_type:
                pred_by_type[rel_type] = set()
            pred_by_type[rel_type].add(triple)

        gt_by_type = {}
        for triple in ground_truth_triples:
            rel_type = triple.relationship_type
            if rel_type not in gt_by_type:
                gt_by_type[rel_type] = set()
            gt_by_type[rel_type].add(triple)

        # Calculate metrics per type
        return MetricsCalculator.calculate_metrics_by_type(
            predicted_by_type=pred_by_type,
            ground_truth_by_type=gt_by_type,
        )

    def _analyze_errors(
        self, unmatched_pred: Set[GraphTriple], unmatched_gt: Set[GraphTriple]
    ) -> Dict:
        """Analyze error patterns."""
        return {
            "false_positives": {
                "count": len(unmatched_pred),
                "by_relationship_type": self._count_by_rel_type(unmatched_pred),
                "examples": [str(t) for t in list(unmatched_pred)[:10]],
            },
            "false_negatives": {
                "count": len(unmatched_gt),
                "by_relationship_type": self._count_by_rel_type(unmatched_gt),
                "examples": [str(t) for t in list(unmatched_gt)[:10]],
            },
        }

    def _count_by_rel_type(self, triples: Set[GraphTriple]) -> Dict[str, int]:
        """Count triples by relationship type."""
        counts = {}
        for triple in triples:
            rel_type = triple.relationship_type
            counts[rel_type] = counts.get(rel_type, 0) + 1
        return counts

    def _analyze_components(
        self,
        predicted: Set[GraphTriple],
        ground_truth: Set[GraphTriple],
        matched: Set[GraphTriple],
    ) -> Dict:
        """
        Analyze which components are causing failures.

        Helps identify if errors are primarily in:
        - Entity extraction (source/target)
        - Relationship type classification
        - End-to-end connection
        """
        analysis = {
            "correct_entities_wrong_relationship": 0,
            "correct_relationship_wrong_source": 0,
            "correct_relationship_wrong_target": 0,
            "correct_source_target_wrong_relationship": 0,
        }

        # Analyze unmatched predicted triples
        unmatched_pred = predicted - matched

        for pred_triple in unmatched_pred:
            # Check if entities exist with different relationship
            for gt_triple in ground_truth:
                if (
                    pred_triple.source_text == gt_triple.source_text
                    and pred_triple.target_text == gt_triple.target_text
                    and pred_triple.relationship_type != gt_triple.relationship_type
                ):
                    analysis["correct_source_target_wrong_relationship"] += 1
                    break

                # Check if relationship exists with wrong source
                if (
                    pred_triple.relationship_type == gt_triple.relationship_type
                    and pred_triple.target_text == gt_triple.target_text
                    and pred_triple.source_text != gt_triple.source_text
                ):
                    analysis["correct_relationship_wrong_source"] += 1
                    break

                # Check if relationship exists with wrong target
                if (
                    pred_triple.relationship_type == gt_triple.relationship_type
                    and pred_triple.source_text == gt_triple.source_text
                    and pred_triple.target_text != gt_triple.target_text
                ):
                    analysis["correct_relationship_wrong_target"] += 1
                    break

        return analysis

    def print_results(self, results: Dict):
        """Print evaluation results in readable format."""
        logger.info("\n" + "=" * 70)
        logger.info("GRAPH EVALUATION RESULTS (Full Triples)")
        logger.info("=" * 70)

        logger.info(f"\nMatching Strategy: {results['matching_strategy']}")
        logger.info(f"Predicted: {results['predicted_count']} triples")
        logger.info(f"Ground Truth: {results['ground_truth_count']} triples")

        # Overall metrics
        logger.info("\n" + "-" * 70)
        logger.info("OVERALL METRICS")
        logger.info("-" * 70)
        overall = results["overall"]
        logger.info(f"Precision: {overall.precision:.4f}")
        logger.info(f"Recall:    {overall.recall:.4f}")
        logger.info(f"F1 Score:  {overall.f1:.4f}")
        logger.info(
            f"TP={overall.true_positives}, FP={overall.false_positives}, "
            f"FN={overall.false_negatives}"
        )

        # By relationship type
        if "by_relationship_type" in results:
            logger.info("\n" + "-" * 70)
            logger.info("METRICS BY RELATIONSHIP TYPE")
            logger.info("-" * 70)
            for rel_type, metrics in results["by_relationship_type"].items():
                logger.info(f"\n{rel_type}:")
                logger.info(f"  Precision: {metrics.precision:.4f}")
                logger.info(f"  Recall:    {metrics.recall:.4f}")
                logger.info(f"  F1 Score:  {metrics.f1:.4f}")
                logger.info(f"  Support:   {metrics.support}")

        # Averages
        if "macro_average" in results:
            logger.info("\n" + "-" * 70)
            logger.info("MACRO AVERAGE")
            logger.info("-" * 70)
            macro = results["macro_average"]
            logger.info(f"Precision: {macro.precision:.4f}")
            logger.info(f"Recall:    {macro.recall:.4f}")
            logger.info(f"F1 Score:  {macro.f1:.4f}")

        # Component analysis
        if "component_analysis" in results:
            logger.info("\n" + "-" * 70)
            logger.info("COMPONENT ANALYSIS")
            logger.info("-" * 70)
            comp = results["component_analysis"]
            logger.info(
                f"Correct entities, wrong relationship: "
                f"{comp['correct_source_target_wrong_relationship']}"
            )
            logger.info(
                f"Correct relationship, wrong source: "
                f"{comp['correct_relationship_wrong_source']}"
            )
            logger.info(
                f"Correct relationship, wrong target: "
                f"{comp['correct_relationship_wrong_target']}"
            )

        # Errors
        if "errors" in results:
            logger.info("\n" + "-" * 70)
            logger.info("ERROR ANALYSIS")
            logger.info("-" * 70)
            errors = results["errors"]
            logger.info(f"\nFalse Positives: {errors['false_positives']['count']}")
            for rel_type, count in errors["false_positives"][
                "by_relationship_type"
            ].items():
                logger.info(f"  {rel_type}: {count}")

            logger.info(f"\nFalse Negatives: {errors['false_negatives']['count']}")
            for rel_type, count in errors["false_negatives"][
                "by_relationship_type"
            ].items():
                logger.info(f"  {rel_type}: {count}")

        logger.info("\n" + "=" * 70 + "\n")

    def export_results(self, results: Dict, output_path: str):
        """Export results to JSON file."""
        # Convert metrics to serializable format
        serializable_results = self._make_serializable(results)

        with open(output_path, "w") as f:
            json.dump(serializable_results, f, indent=2)

        logger.info(f"Results exported to {output_path}")

    def _make_serializable(self, obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, EvaluationMetrics):
            return {
                "precision": obj.precision,
                "recall": obj.recall,
                "f1": obj.f1,
                "true_positives": obj.true_positives,
                "false_positives": obj.false_positives,
                "false_negatives": obj.false_negatives,
                "support": obj.support,
            }
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, set)):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj
