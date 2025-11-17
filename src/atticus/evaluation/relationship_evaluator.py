"""
Relationship extraction evaluator.

Evaluates relationship extraction performance against ground truth annotations.
"""

import json
from typing import Dict, List, Tuple

from atticus.core.logger import get_logger
from atticus.core.models import Relationship
from atticus.evaluation.metrics import (
    ConfusionMatrix,
    EvaluationMetrics,
    MetricsCalculator,
    calculate_confidence_calibration,
)

logger = get_logger(__name__)


class RelationshipEvaluator:
    """Evaluate relationship extraction performance."""

    def __init__(self, matching_strategy: str = "exact"):
        """
        Initialize relationship evaluator.

        Args:
            matching_strategy: How to match relationships ("exact", "fuzzy")
        """
        self.matching_strategy = matching_strategy

    def evaluate(
        self,
        predicted_relationships: List[Relationship],
        ground_truth_relationships: List[Relationship],
        by_type: bool = True,
    ) -> Dict:
        """
        Evaluate relationship extraction.

        Args:
            predicted_relationships: Predicted relationships
            ground_truth_relationships: Ground truth relationships
            by_type: Whether to calculate metrics by relationship type

        Returns:
            Dictionary with evaluation results
        """
        logger.info(f"Evaluating relationship extraction...")
        logger.info(f"  Predicted: {len(predicted_relationships)} relationships")
        logger.info(
            f"  Ground truth: {len(ground_truth_relationships)} relationships"
        )

        results = {
            "matching_strategy": self.matching_strategy,
            "predicted_count": len(predicted_relationships),
            "ground_truth_count": len(ground_truth_relationships),
        }

        # Match relationships
        matched_pairs, unmatched_predicted, unmatched_ground_truth = (
            self._match_relationships(
                predicted_relationships, ground_truth_relationships
            )
        )

        logger.info(f"  Matched pairs: {len(matched_pairs)}")
        logger.info(f"  Unmatched predicted: {len(unmatched_predicted)}")
        logger.info(f"  Unmatched ground truth: {len(unmatched_ground_truth)}")

        # Overall metrics
        overall_metrics = self._calculate_overall_metrics(
            matched_pairs=matched_pairs,
            unmatched_predicted=unmatched_predicted,
            unmatched_ground_truth=unmatched_ground_truth,
        )

        results["overall"] = overall_metrics

        # Metrics by type
        if by_type:
            metrics_by_type = self._calculate_metrics_by_type(
                matched_pairs=matched_pairs,
                unmatched_predicted=unmatched_predicted,
                unmatched_ground_truth=unmatched_ground_truth,
            )
            results["by_type"] = metrics_by_type

            # Macro and micro averages
            results["macro_average"] = MetricsCalculator.calculate_macro_average(
                metrics_by_type
            )
            results["micro_average"] = MetricsCalculator.calculate_micro_average(
                metrics_by_type
            )

        # Confusion matrix for relationship types
        confusion_matrix = self._build_confusion_matrix(matched_pairs)
        results["confusion_matrix"] = confusion_matrix

        # Confidence calibration
        calibration = self._calculate_confidence_calibration(matched_pairs)
        results["calibration"] = calibration

        # Error analysis
        results["errors"] = self._analyze_errors(
            unmatched_predicted, unmatched_ground_truth
        )

        return results

    def _match_relationships(
        self,
        predicted: List[Relationship],
        ground_truth: List[Relationship],
    ) -> Tuple[List[Tuple[Relationship, Relationship]], List[Relationship], List[Relationship]]:
        """
        Match predicted relationships to ground truth.

        Returns:
            Tuple of (matched_pairs, unmatched_predicted, unmatched_ground_truth)
        """
        matched_pairs = []
        unmatched_predicted = list(predicted)
        unmatched_ground_truth = list(ground_truth)

        if self.matching_strategy == "exact":
            # Exact match: same source ID, target ID, and relationship type
            for pred in predicted:
                for gt in ground_truth:
                    if self._exact_match(pred, gt):
                        matched_pairs.append((pred, gt))
                        if pred in unmatched_predicted:
                            unmatched_predicted.remove(pred)
                        if gt in unmatched_ground_truth:
                            unmatched_ground_truth.remove(gt)
                        break

        elif self.matching_strategy == "fuzzy":
            # Fuzzy match: same entity texts (case-insensitive) and relationship type
            for pred in predicted:
                for gt in ground_truth:
                    if self._fuzzy_match(pred, gt):
                        matched_pairs.append((pred, gt))
                        if pred in unmatched_predicted:
                            unmatched_predicted.remove(pred)
                        if gt in unmatched_ground_truth:
                            unmatched_ground_truth.remove(gt)
                        break

        return matched_pairs, unmatched_predicted, unmatched_ground_truth

    def _exact_match(
        self, rel1: Relationship, rel2: Relationship
    ) -> bool:
        """Check if two relationships match exactly."""
        return (
            rel1.source_id == rel2.source_id
            and rel1.target_id == rel2.target_id
            and rel1.type == rel2.type
        )

    def _fuzzy_match(
        self, rel1: Relationship, rel2: Relationship
    ) -> bool:
        """Check if two relationships match fuzzily."""
        # Match by entity texts (case-insensitive) and relationship type
        # This is useful when entity IDs don't match but the relationships refer
        # to the same conceptual entities

        # For now, we'll use entity IDs since we don't have entity text in Relationship
        # In practice, you'd retrieve the entity text from the entity objects
        return self._exact_match(rel1, rel2)

    def _calculate_overall_metrics(
        self,
        matched_pairs: List[Tuple[Relationship, Relationship]],
        unmatched_predicted: List[Relationship],
        unmatched_ground_truth: List[Relationship],
    ) -> EvaluationMetrics:
        """Calculate overall metrics."""
        true_positives = len(matched_pairs)
        false_positives = len(unmatched_predicted)
        false_negatives = len(unmatched_ground_truth)
        support = true_positives + false_negatives

        return MetricsCalculator.calculate_metrics(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            support=support,
        )

    def _calculate_metrics_by_type(
        self,
        matched_pairs: List[Tuple[Relationship, Relationship]],
        unmatched_predicted: List[Relationship],
        unmatched_ground_truth: List[Relationship],
    ) -> Dict[str, EvaluationMetrics]:
        """Calculate metrics for each relationship type."""
        # Group by type
        matched_by_type = {}
        for pred, gt in matched_pairs:
            rel_type = gt.type.value
            if rel_type not in matched_by_type:
                matched_by_type[rel_type] = []
            matched_by_type[rel_type].append((pred, gt))

        unmatched_pred_by_type = {}
        for rel in unmatched_predicted:
            rel_type = rel.type.value
            if rel_type not in unmatched_pred_by_type:
                unmatched_pred_by_type[rel_type] = []
            unmatched_pred_by_type[rel_type].append(rel)

        unmatched_gt_by_type = {}
        for rel in unmatched_ground_truth:
            rel_type = rel.type.value
            if rel_type not in unmatched_gt_by_type:
                unmatched_gt_by_type[rel_type] = []
            unmatched_gt_by_type[rel_type].append(rel)

        # Calculate metrics for each type
        metrics_by_type = {}
        all_types = set(matched_by_type.keys()) | set(
            unmatched_pred_by_type.keys()
        ) | set(unmatched_gt_by_type.keys())

        for rel_type in all_types:
            tp = len(matched_by_type.get(rel_type, []))
            fp = len(unmatched_pred_by_type.get(rel_type, []))
            fn = len(unmatched_gt_by_type.get(rel_type, []))
            support = tp + fn

            metrics = MetricsCalculator.calculate_metrics(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                support=support,
            )

            metrics_by_type[rel_type] = metrics

        return metrics_by_type

    def _build_confusion_matrix(
        self, matched_pairs: List[Tuple[Relationship, Relationship]]
    ) -> ConfusionMatrix:
        """Build confusion matrix for relationship types."""
        from atticus.core.models import RelationshipType

        all_types = [rt.value for rt in RelationshipType]

        confusion = ConfusionMatrix(classes=all_types)

        for pred, gt in matched_pairs:
            confusion.add(
                true_class=gt.type.value,
                predicted_class=pred.type.value,
            )

        return confusion

    def _calculate_confidence_calibration(
        self, matched_pairs: List[Tuple[Relationship, Relationship]]
    ) -> Dict:
        """Calculate confidence calibration metrics."""
        predictions = []

        for pred, gt in matched_pairs:
            # Check if prediction is correct (type must match)
            is_correct = pred.type == gt.type
            predictions.append((is_correct, pred.confidence))

        return calculate_confidence_calibration(predictions)

    def _analyze_errors(
        self,
        unmatched_predicted: List[Relationship],
        unmatched_ground_truth: List[Relationship],
    ) -> Dict:
        """Analyze common error patterns."""
        return {
            "false_positives": {
                "count": len(unmatched_predicted),
                "by_type": self._count_by_type(unmatched_predicted),
                "examples": [
                    {
                        "source_id": r.source_id,
                        "target_id": r.target_id,
                        "type": r.type.value,
                        "confidence": r.confidence,
                        "evidence": r.evidence[:100] if r.evidence else None,
                    }
                    for r in unmatched_predicted[:10]
                ],
            },
            "false_negatives": {
                "count": len(unmatched_ground_truth),
                "by_type": self._count_by_type(unmatched_ground_truth),
                "examples": [
                    {
                        "source_id": r.source_id,
                        "target_id": r.target_id,
                        "type": r.type.value,
                    }
                    for r in unmatched_ground_truth[:10]
                ],
            },
        }

    def _count_by_type(self, relationships: List[Relationship]) -> Dict[str, int]:
        """Count relationships by type."""
        counts = {}
        for rel in relationships:
            rel_type = rel.type.value
            counts[rel_type] = counts.get(rel_type, 0) + 1
        return counts

    def print_results(self, results: Dict):
        """Print evaluation results in readable format."""
        logger.info("\n" + "=" * 70)
        logger.info("RELATIONSHIP EXTRACTION EVALUATION RESULTS")
        logger.info("=" * 70)

        logger.info(f"\nMatching Strategy: {results['matching_strategy']}")
        logger.info(f"Predicted: {results['predicted_count']} relationships")
        logger.info(f"Ground Truth: {results['ground_truth_count']} relationships")

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

        # By type
        if "by_type" in results:
            logger.info("\n" + "-" * 70)
            logger.info("METRICS BY RELATIONSHIP TYPE")
            logger.info("-" * 70)
            for rel_type, metrics in results["by_type"].items():
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

        # Calibration
        if "calibration" in results:
            logger.info("\n" + "-" * 70)
            logger.info("CONFIDENCE CALIBRATION")
            logger.info("-" * 70)
            cal = results["calibration"]
            logger.info(f"Expected Calibration Error (ECE): {cal['ece']:.4f}")
            logger.info(f"Maximum Calibration Error (MCE): {cal['mce']:.4f}")

        # Errors
        if "errors" in results:
            logger.info("\n" + "-" * 70)
            logger.info("ERROR ANALYSIS")
            logger.info("-" * 70)
            errors = results["errors"]
            logger.info(f"\nFalse Positives: {errors['false_positives']['count']}")
            for rel_type, count in errors["false_positives"]["by_type"].items():
                logger.info(f"  {rel_type}: {count}")

            logger.info(f"\nFalse Negatives: {errors['false_negatives']['count']}")
            for rel_type, count in errors["false_negatives"]["by_type"].items():
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
        elif isinstance(obj, ConfusionMatrix):
            return {
                "classes": obj.classes,
                "matrix": obj.matrix,
            }
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj
