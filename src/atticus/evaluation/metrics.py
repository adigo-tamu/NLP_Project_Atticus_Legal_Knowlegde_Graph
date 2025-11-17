"""
Core evaluation metrics for knowledge graph construction.

Implements precision, recall, F1, and other metrics for evaluating:
- Entity extraction
- Relationship extraction
- Full graph triples (end-to-end)
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from atticus.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics."""

    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    support: int  # Total ground truth items

    def __str__(self) -> str:
        """Format metrics as string."""
        return (
            f"Precision: {self.precision:.4f}, "
            f"Recall: {self.recall:.4f}, "
            f"F1: {self.f1:.4f} "
            f"(TP={self.true_positives}, FP={self.false_positives}, "
            f"FN={self.false_negatives}, Support={self.support})"
        )


class MetricsCalculator:
    """Calculate evaluation metrics."""

    @staticmethod
    def calculate_metrics(
        true_positives: int,
        false_positives: int,
        false_negatives: int,
        support: int,
    ) -> EvaluationMetrics:
        """
        Calculate precision, recall, and F1 score.

        Args:
            true_positives: Number of correct predictions
            false_positives: Number of incorrect predictions
            false_negatives: Number of missed ground truth items
            support: Total ground truth items

        Returns:
            EvaluationMetrics object
        """
        # Calculate precision
        if true_positives + false_positives == 0:
            precision = 0.0
        else:
            precision = true_positives / (true_positives + false_positives)

        # Calculate recall
        if true_positives + false_negatives == 0:
            recall = 0.0
        else:
            recall = true_positives / (true_positives + false_negatives)

        # Calculate F1
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)

        return EvaluationMetrics(
            precision=precision,
            recall=recall,
            f1=f1,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            support=support,
        )

    @staticmethod
    def calculate_metrics_from_sets(
        predicted: Set,
        ground_truth: Set,
    ) -> EvaluationMetrics:
        """
        Calculate metrics from predicted and ground truth sets.

        Args:
            predicted: Set of predicted items
            ground_truth: Set of ground truth items

        Returns:
            EvaluationMetrics object
        """
        true_positives = len(predicted & ground_truth)
        false_positives = len(predicted - ground_truth)
        false_negatives = len(ground_truth - predicted)
        support = len(ground_truth)

        return MetricsCalculator.calculate_metrics(
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            support=support,
        )

    @staticmethod
    def calculate_metrics_by_type(
        predicted_by_type: Dict[str, Set],
        ground_truth_by_type: Dict[str, Set],
    ) -> Dict[str, EvaluationMetrics]:
        """
        Calculate metrics for each type separately.

        Args:
            predicted_by_type: Dictionary mapping types to predicted sets
            ground_truth_by_type: Dictionary mapping types to ground truth sets

        Returns:
            Dictionary mapping types to metrics
        """
        metrics_by_type = {}

        # Get all types
        all_types = set(predicted_by_type.keys()) | set(ground_truth_by_type.keys())

        for item_type in all_types:
            predicted = predicted_by_type.get(item_type, set())
            ground_truth = ground_truth_by_type.get(item_type, set())

            metrics = MetricsCalculator.calculate_metrics_from_sets(
                predicted=predicted,
                ground_truth=ground_truth,
            )

            metrics_by_type[item_type] = metrics

        return metrics_by_type

    @staticmethod
    def calculate_macro_average(
        metrics_by_type: Dict[str, EvaluationMetrics]
    ) -> EvaluationMetrics:
        """
        Calculate macro-averaged metrics (average across types).

        Args:
            metrics_by_type: Dictionary mapping types to metrics

        Returns:
            Macro-averaged metrics
        """
        if not metrics_by_type:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0, 0, 0, 0)

        avg_precision = sum(m.precision for m in metrics_by_type.values()) / len(
            metrics_by_type
        )
        avg_recall = sum(m.recall for m in metrics_by_type.values()) / len(
            metrics_by_type
        )
        avg_f1 = sum(m.f1 for m in metrics_by_type.values()) / len(metrics_by_type)

        total_tp = sum(m.true_positives for m in metrics_by_type.values())
        total_fp = sum(m.false_positives for m in metrics_by_type.values())
        total_fn = sum(m.false_negatives for m in metrics_by_type.values())
        total_support = sum(m.support for m in metrics_by_type.values())

        return EvaluationMetrics(
            precision=avg_precision,
            recall=avg_recall,
            f1=avg_f1,
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            support=total_support,
        )

    @staticmethod
    def calculate_micro_average(
        metrics_by_type: Dict[str, EvaluationMetrics]
    ) -> EvaluationMetrics:
        """
        Calculate micro-averaged metrics (aggregate counts then calculate).

        Args:
            metrics_by_type: Dictionary mapping types to metrics

        Returns:
            Micro-averaged metrics
        """
        if not metrics_by_type:
            return EvaluationMetrics(0.0, 0.0, 0.0, 0, 0, 0, 0)

        total_tp = sum(m.true_positives for m in metrics_by_type.values())
        total_fp = sum(m.false_positives for m in metrics_by_type.values())
        total_fn = sum(m.false_negatives for m in metrics_by_type.values())
        total_support = sum(m.support for m in metrics_by_type.values())

        return MetricsCalculator.calculate_metrics(
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            support=total_support,
        )


class ConfusionMatrix:
    """Confusion matrix for multi-class classification."""

    def __init__(self, classes: List[str]):
        """
        Initialize confusion matrix.

        Args:
            classes: List of class names
        """
        self.classes = classes
        self.matrix = {
            true_class: {pred_class: 0 for pred_class in classes}
            for true_class in classes
        }

    def add(self, true_class: str, predicted_class: str):
        """Add a prediction to the confusion matrix."""
        if true_class not in self.classes:
            self.classes.append(true_class)
            self.matrix[true_class] = {c: 0 for c in self.classes}

        if predicted_class not in self.classes:
            self.classes.append(predicted_class)
            for tc in self.matrix:
                self.matrix[tc][predicted_class] = 0

        self.matrix[true_class][predicted_class] += 1

    def get_metrics_for_class(self, class_name: str) -> EvaluationMetrics:
        """Get metrics for a specific class."""
        tp = self.matrix[class_name][class_name]
        fp = sum(
            self.matrix[other][class_name]
            for other in self.classes
            if other != class_name
        )
        fn = sum(
            self.matrix[class_name][other]
            for other in self.classes
            if other != class_name
        )
        support = sum(self.matrix[class_name].values())

        return MetricsCalculator.calculate_metrics(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            support=support,
        )

    def print_matrix(self):
        """Print confusion matrix."""
        # Header
        header = "True \\ Pred".ljust(15)
        for pred_class in self.classes:
            header += f"{pred_class[:10]:>12}"
        logger.info(header)
        logger.info("-" * (15 + 12 * len(self.classes)))

        # Rows
        for true_class in self.classes:
            row = f"{true_class[:15]:15}"
            for pred_class in self.classes:
                count = self.matrix[true_class][pred_class]
                row += f"{count:>12}"
            logger.info(row)


def calculate_confidence_calibration(
    predictions: List[Tuple[bool, float]]
) -> Dict[str, float]:
    """
    Calculate confidence calibration metrics.

    Measures how well predicted confidence scores match actual accuracy.

    Args:
        predictions: List of (is_correct, confidence) tuples

    Returns:
        Dictionary with calibration metrics
    """
    if not predictions:
        return {"ece": 0.0, "mce": 0.0}

    # Expected Calibration Error (ECE)
    # Divide predictions into bins by confidence
    num_bins = 10
    bins = [[] for _ in range(num_bins)]

    for is_correct, confidence in predictions:
        bin_idx = min(int(confidence * num_bins), num_bins - 1)
        bins[bin_idx].append(is_correct)

    ece = 0.0
    mce = 0.0

    for bin_idx, bin_predictions in enumerate(bins):
        if not bin_predictions:
            continue

        # Average confidence in this bin
        avg_confidence = (bin_idx + 0.5) / num_bins

        # Actual accuracy in this bin
        accuracy = sum(bin_predictions) / len(bin_predictions)

        # Calibration error for this bin
        bin_error = abs(avg_confidence - accuracy)

        # Weight by number of predictions in bin
        bin_weight = len(bin_predictions) / len(predictions)
        ece += bin_weight * bin_error

        # Track maximum calibration error
        mce = max(mce, bin_error)

    return {
        "ece": ece,  # Expected Calibration Error
        "mce": mce,  # Maximum Calibration Error
    }
