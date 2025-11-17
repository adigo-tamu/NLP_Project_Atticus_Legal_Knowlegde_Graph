"""
Entity extraction evaluator.

Evaluates entity extraction performance against ground truth annotations.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from atticus.core.logger import get_logger
from atticus.core.models import Entity, EntityType
from atticus.evaluation.metrics import (
    ConfusionMatrix,
    EvaluationMetrics,
    MetricsCalculator,
    calculate_confidence_calibration,
)

logger = get_logger(__name__)


class EntityEvaluator:
    """Evaluate entity extraction performance."""

    def __init__(self, matching_strategy: str = "exact"):
        """
        Initialize entity evaluator.

        Args:
            matching_strategy: How to match entities ("exact", "overlap", "fuzzy")
        """
        self.matching_strategy = matching_strategy

    def evaluate(
        self,
        predicted_entities: List[Entity],
        ground_truth_entities: List[Entity],
        by_type: bool = True,
    ) -> Dict:
        """
        Evaluate entity extraction.

        Args:
            predicted_entities: Predicted entities
            ground_truth_entities: Ground truth entities
            by_type: Whether to calculate metrics by entity type

        Returns:
            Dictionary with evaluation results
        """
        logger.info(f"Evaluating entity extraction...")
        logger.info(f"  Predicted: {len(predicted_entities)} entities")
        logger.info(f"  Ground truth: {len(ground_truth_entities)} entities")

        results = {
            "matching_strategy": self.matching_strategy,
            "predicted_count": len(predicted_entities),
            "ground_truth_count": len(ground_truth_entities),
        }

        # Match entities
        matched_pairs, unmatched_predicted, unmatched_ground_truth = (
            self._match_entities(predicted_entities, ground_truth_entities)
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

        # Confusion matrix for entity types
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

    def _match_entities(
        self,
        predicted: List[Entity],
        ground_truth: List[Entity],
    ) -> Tuple[List[Tuple[Entity, Entity]], List[Entity], List[Entity]]:
        """
        Match predicted entities to ground truth.

        Returns:
            Tuple of (matched_pairs, unmatched_predicted, unmatched_ground_truth)
        """
        matched_pairs = []
        unmatched_predicted = list(predicted)
        unmatched_ground_truth = list(ground_truth)

        # Build matching based on strategy
        if self.matching_strategy == "exact":
            # Exact text match
            for pred in predicted:
                for gt in ground_truth:
                    if self._exact_match(pred, gt):
                        matched_pairs.append((pred, gt))
                        if pred in unmatched_predicted:
                            unmatched_predicted.remove(pred)
                        if gt in unmatched_ground_truth:
                            unmatched_ground_truth.remove(gt)
                        break

        elif self.matching_strategy == "overlap":
            # Position overlap (if positions available)
            for pred in predicted:
                best_overlap = 0
                best_match = None

                for gt in ground_truth:
                    overlap = self._calculate_overlap(pred, gt)
                    if overlap > best_overlap and overlap >= 0.5:  # 50% threshold
                        best_overlap = overlap
                        best_match = gt

                if best_match:
                    matched_pairs.append((pred, best_match))
                    if pred in unmatched_predicted:
                        unmatched_predicted.remove(pred)
                    if best_match in unmatched_ground_truth:
                        unmatched_ground_truth.remove(best_match)

        elif self.matching_strategy == "fuzzy":
            # Fuzzy text matching
            for pred in predicted:
                best_similarity = 0
                best_match = None

                for gt in ground_truth:
                    similarity = self._fuzzy_match(pred, gt)
                    if similarity > best_similarity and similarity >= 0.8:  # 80% threshold
                        best_similarity = similarity
                        best_match = gt

                if best_match:
                    matched_pairs.append((pred, best_match))
                    if pred in unmatched_predicted:
                        unmatched_predicted.remove(pred)
                    if best_match in unmatched_ground_truth:
                        unmatched_ground_truth.remove(best_match)

        return matched_pairs, unmatched_predicted, unmatched_ground_truth

    def _exact_match(self, entity1: Entity, entity2: Entity) -> bool:
        """Check if two entities match exactly."""
        return (
            entity1.text.lower().strip() == entity2.text.lower().strip()
            and entity1.type == entity2.type
        )

    def _calculate_overlap(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate position overlap between two entities."""
        if not entity1.position or not entity2.position:
            # Fall back to text match
            return 1.0 if entity1.text.lower() == entity2.text.lower() else 0.0

        # Calculate character-level overlap
        start1, end1 = entity1.position.start, entity1.position.end
        start2, end2 = entity2.position.start, entity2.position.end

        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_end <= overlap_start:
            return 0.0

        overlap_length = overlap_end - overlap_start
        union_length = max(end1, end2) - min(start1, start2)

        return overlap_length / union_length if union_length > 0 else 0.0

    def _fuzzy_match(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate fuzzy similarity between two entities."""
        from difflib import SequenceMatcher

        text_similarity = SequenceMatcher(
            None, entity1.text.lower(), entity2.text.lower()
        ).ratio()

        # Must be same type
        if entity1.type != entity2.type:
            return 0.0

        return text_similarity

    def _calculate_overall_metrics(
        self,
        matched_pairs: List[Tuple[Entity, Entity]],
        unmatched_predicted: List[Entity],
        unmatched_ground_truth: List[Entity],
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
        matched_pairs: List[Tuple[Entity, Entity]],
        unmatched_predicted: List[Entity],
        unmatched_ground_truth: List[Entity],
    ) -> Dict[str, EvaluationMetrics]:
        """Calculate metrics for each entity type."""
        # Group by type
        matched_by_type = {}
        for pred, gt in matched_pairs:
            entity_type = gt.type.value
            if entity_type not in matched_by_type:
                matched_by_type[entity_type] = []
            matched_by_type[entity_type].append((pred, gt))

        unmatched_pred_by_type = {}
        for entity in unmatched_predicted:
            entity_type = entity.type.value
            if entity_type not in unmatched_pred_by_type:
                unmatched_pred_by_type[entity_type] = []
            unmatched_pred_by_type[entity_type].append(entity)

        unmatched_gt_by_type = {}
        for entity in unmatched_ground_truth:
            entity_type = entity.type.value
            if entity_type not in unmatched_gt_by_type:
                unmatched_gt_by_type[entity_type] = []
            unmatched_gt_by_type[entity_type].append(entity)

        # Calculate metrics for each type
        metrics_by_type = {}
        all_types = set(matched_by_type.keys()) | set(
            unmatched_pred_by_type.keys()
        ) | set(unmatched_gt_by_type.keys())

        for entity_type in all_types:
            tp = len(matched_by_type.get(entity_type, []))
            fp = len(unmatched_pred_by_type.get(entity_type, []))
            fn = len(unmatched_gt_by_type.get(entity_type, []))
            support = tp + fn

            metrics = MetricsCalculator.calculate_metrics(
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                support=support,
            )

            metrics_by_type[entity_type] = metrics

        return metrics_by_type

    def _build_confusion_matrix(
        self, matched_pairs: List[Tuple[Entity, Entity]]
    ) -> ConfusionMatrix:
        """Build confusion matrix for entity types."""
        # Get all entity types
        all_types = [et.value for et in EntityType]

        confusion = ConfusionMatrix(classes=all_types)

        for pred, gt in matched_pairs:
            confusion.add(
                true_class=gt.type.value,
                predicted_class=pred.type.value,
            )

        return confusion

    def _calculate_confidence_calibration(
        self, matched_pairs: List[Tuple[Entity, Entity]]
    ) -> Dict:
        """Calculate confidence calibration metrics."""
        predictions = []

        for pred, gt in matched_pairs:
            # Check if prediction is correct (type must match)
            is_correct = pred.type == gt.type
            predictions.append((is_correct, pred.confidence))

        return calculate_confidence_calibration(predictions)

    def _analyze_errors(
        self, unmatched_predicted: List[Entity], unmatched_ground_truth: List[Entity]
    ) -> Dict:
        """Analyze common error patterns."""
        return {
            "false_positives": {
                "count": len(unmatched_predicted),
                "by_type": self._count_by_type(unmatched_predicted),
                "examples": [
                    {"text": e.text, "type": e.type.value, "confidence": e.confidence}
                    for e in unmatched_predicted[:10]
                ],
            },
            "false_negatives": {
                "count": len(unmatched_ground_truth),
                "by_type": self._count_by_type(unmatched_ground_truth),
                "examples": [
                    {"text": e.text, "type": e.type.value}
                    for e in unmatched_ground_truth[:10]
                ],
            },
        }

    def _count_by_type(self, entities: List[Entity]) -> Dict[str, int]:
        """Count entities by type."""
        counts = {}
        for entity in entities:
            entity_type = entity.type.value
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts

    def print_results(self, results: Dict):
        """Print evaluation results in readable format."""
        logger.info("\n" + "=" * 70)
        logger.info("ENTITY EXTRACTION EVALUATION RESULTS")
        logger.info("=" * 70)

        logger.info(f"\nMatching Strategy: {results['matching_strategy']}")
        logger.info(f"Predicted: {results['predicted_count']} entities")
        logger.info(f"Ground Truth: {results['ground_truth_count']} entities")

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
            logger.info("METRICS BY ENTITY TYPE")
            logger.info("-" * 70)
            for entity_type, metrics in results["by_type"].items():
                logger.info(f"\n{entity_type}:")
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
            for entity_type, count in errors["false_positives"]["by_type"].items():
                logger.info(f"  {entity_type}: {count}")

            logger.info(f"\nFalse Negatives: {errors['false_negatives']['count']}")
            for entity_type, count in errors["false_negatives"]["by_type"].items():
                logger.info(f"  {entity_type}: {count}")

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
