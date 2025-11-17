# Evaluation Framework

**Phase 6 Implementation Documentation**

Comprehensive evaluation framework for measuring knowledge graph construction performance with precision, recall, and F1 metrics.

---

## Overview

The evaluation framework provides three levels of evaluation:

1. **Entity Extraction**: Measures entity identification and classification accuracy
2. **Relationship Extraction**: Measures relationship identification and classification accuracy
3. **Graph Construction**: End-to-end evaluation of complete triples (source-relationship-target)

### Performance Targets

According to the technical specification:

| Metric | Target | Description |
|--------|--------|-------------|
| **Entity F1** | ≥ 0.85 | Entity extraction F1 score |
| **Relationship F1** | ≥ 0.70 | Relationship extraction F1 score |
| **Graph F1** | ≥ 0.40 | Full triple (end-to-end) F1 score |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Evaluation Framework                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │   Entity     │   │Relationship  │   │    Graph     │    │
│  │  Evaluator   │   │  Evaluator   │   │  Evaluator   │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                   │                   │             │
│         └───────────────────┴───────────────────┘             │
│                              │                                 │
│                    ┌─────────▼─────────┐                     │
│                    │ Metrics Calculator │                     │
│                    │  - Precision       │                     │
│                    │  - Recall          │                     │
│                    │  - F1 Score        │                     │
│                    │  - Confusion Matrix│                     │
│                    │  - Calibration     │                     │
│                    └────────────────────┘                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. Entity Extraction Evaluation

**Module**: `atticus.evaluation.entity_evaluator`

Evaluates entity extraction performance by comparing predicted entities against ground truth annotations.

### Matching Strategies

#### Exact Match (default)
- Entities must have identical text (case-insensitive) and type
- Strictest matching, suitable for well-defined entity boundaries

#### Overlap Match
- Uses character position overlap
- Requires ≥ 50% overlap between predicted and ground truth spans
- Useful for fuzzy entity boundaries

#### Fuzzy Match
- Uses text similarity (Levenshtein distance)
- Requires ≥ 80% text similarity
- Handles minor variations in entity text

### Usage

```python
from atticus.evaluation import EntityEvaluator

# Initialize evaluator
evaluator = EntityEvaluator(matching_strategy="exact")

# Run evaluation
results = evaluator.evaluate(
    predicted_entities=predicted_entities,
    ground_truth_entities=ground_truth_entities,
    by_type=True  # Calculate metrics per entity type
)

# Print results
evaluator.print_results(results)

# Export to JSON
evaluator.export_results(results, "entity_evaluation.json")
```

### Results Structure

```python
{
    "matching_strategy": "exact",
    "predicted_count": 245,
    "ground_truth_count": 250,
    "overall": {
        "precision": 0.8980,
        "recall": 0.8800,
        "f1": 0.8889,
        "true_positives": 220,
        "false_positives": 25,
        "false_negatives": 30,
        "support": 250
    },
    "by_type": {
        "Legal_Party": {...},
        "Legal_Concept": {...},
        "Obligation": {...}
    },
    "macro_average": {...},
    "micro_average": {...},
    "confusion_matrix": {...},
    "calibration": {
        "ece": 0.0234,  # Expected Calibration Error
        "mce": 0.0512   # Maximum Calibration Error
    },
    "errors": {
        "false_positives": {...},
        "false_negatives": {...}
    }
}
```

### Metrics by Entity Type

The evaluator calculates separate metrics for each entity type:

- Legal_Party
- Legal_Concept
- Obligation
- Right
- Jurisdiction
- Temporal_Entity
- Financial_Term
- Clause_Reference

### Confidence Calibration

Measures how well predicted confidence scores match actual accuracy:

- **ECE (Expected Calibration Error)**: Average calibration error across confidence bins
- **MCE (Maximum Calibration Error)**: Maximum calibration error in any bin

Lower values indicate better calibration (confidence = accuracy).

---

## 2. Relationship Extraction Evaluation

**Module**: `atticus.evaluation.relationship_evaluator`

Evaluates relationship extraction performance by comparing predicted relationships against ground truth.

### Matching Strategies

#### Exact Match (default)
- Relationships must have identical source ID, target ID, and type
- Strictest matching

#### Fuzzy Match
- Allows fuzzy entity text matching
- Useful when entity IDs differ but refer to same entities

### Usage

```python
from atticus.evaluation import RelationshipEvaluator

# Initialize evaluator
evaluator = RelationshipEvaluator(matching_strategy="exact")

# Run evaluation
results = evaluator.evaluate(
    predicted_relationships=predicted_relationships,
    ground_truth_relationships=ground_truth_relationships,
    by_type=True  # Calculate metrics per relationship type
)

# Print and export
evaluator.print_results(results)
evaluator.export_results(results, "relationship_evaluation.json")
```

### Results Structure

Similar to entity evaluation, but organized by relationship type:

- REFERENCES
- OBLIGATES
- GRANTS_RIGHT
- GOVERNS
- DEFINES
- MODIFIES
- DEPENDS_ON
- CONTRADICTS
- TEMPORALLY_PRECEDES
- FINANCIALLY_RELATES

### Example Output

```
RELATIONSHIP EXTRACTION EVALUATION RESULTS
======================================================================

Matching Strategy: exact
Predicted: 156 relationships
Ground Truth: 165 relationships

OVERALL METRICS
----------------------------------------------------------------------
Precision: 0.8654
Recall:    0.8182
F1 Score:  0.8411
TP=135, FP=21, FN=30

METRICS BY RELATIONSHIP TYPE
----------------------------------------------------------------------

OBLIGATES:
  Precision: 0.9200
  Recall:    0.8800
  F1 Score:  0.8996
  Support:   50

REFERENCES:
  Precision: 0.8500
  Recall:    0.8095
  F1 Score:  0.8293
  Support:   42
```

---

## 3. Graph Construction Evaluation

**Module**: `atticus.evaluation.graph_evaluator`

End-to-end evaluation of complete graph triples: (source_entity, relationship_type, target_entity)

This is the **strictest evaluation**, requiring all three components to match.

### Graph Triple

A triple consists of:
1. Source entity (text + type)
2. Relationship type
3. Target entity (text + type)

Example: `(TechCorp Inc.:Legal_Party) -[OBLIGATES]-> (Payment of $10,000:Financial_Term)`

### Matching Strategies

#### Exact Match (default)
- All three components must match exactly
- Source text, source type, relationship type, target text, target type

#### Relaxed Match
- Allows fuzzy entity text matching (80% similarity)
- Types and relationship must still match exactly

### Usage

```python
from atticus.evaluation import GraphEvaluator

# Initialize evaluator
evaluator = GraphEvaluator(matching_strategy="exact")

# Run evaluation
results = evaluator.evaluate(
    predicted_entities=predicted_entities,
    predicted_relationships=predicted_relationships,
    ground_truth_entities=ground_truth_entities,
    ground_truth_relationships=ground_truth_relationships,
    by_relationship_type=True
)

# Print and export
evaluator.print_results(results)
evaluator.export_results(results, "graph_evaluation.json")
```

### Component Analysis

The graph evaluator provides detailed analysis of error sources:

```python
"component_analysis": {
    "correct_entities_wrong_relationship": 15,    # Entities right, relationship wrong
    "correct_relationship_wrong_source": 8,       # Relationship + target right, source wrong
    "correct_relationship_wrong_target": 12,      # Relationship + source right, target wrong
    "correct_source_target_wrong_relationship": 5 # Both entities right, relationship wrong
}
```

This helps identify whether errors are primarily in:
- Entity extraction (wrong entities)
- Relationship classification (wrong relationship type)
- Entity linking (right entities, wrong connections)

### Example Output

```
GRAPH EVALUATION RESULTS (Full Triples)
======================================================================

Matching Strategy: exact
Predicted: 156 triples
Ground Truth: 165 triples

OVERALL METRICS
----------------------------------------------------------------------
Precision: 0.7628
Recall:    0.7212
F1 Score:  0.7414
TP=119, FP=37, FN=46

COMPONENT ANALYSIS
----------------------------------------------------------------------
Correct entities, wrong relationship: 15
Correct relationship, wrong source: 8
Correct relationship, wrong target: 12
```

---

## Running Evaluations

### Test Script

```bash
# Run comprehensive evaluation test
python scripts/test_evaluation.py

# Output:
# - Entity evaluation results
# - Relationship evaluation results
# - Graph evaluation results
# - Summary report
# - JSON files in output/
```

### With Real Data

```python
from atticus.evaluation import EntityEvaluator, RelationshipEvaluator, GraphEvaluator
from atticus.extraction import CompleteExtractionPipeline

# Extract from document
pipeline = CompleteExtractionPipeline()
document, chunks, predicted_entities, predicted_relationships = pipeline.process_document(
    "contract.pdf"
)

# Load ground truth annotations
ground_truth_entities = load_ground_truth_entities("annotations/contract.json")
ground_truth_relationships = load_ground_truth_relationships("annotations/contract.json")

# Evaluate entities
entity_eval = EntityEvaluator()
entity_results = entity_eval.evaluate(predicted_entities, ground_truth_entities)
print(f"Entity F1: {entity_results['overall'].f1:.4f}")

# Evaluate relationships
rel_eval = RelationshipEvaluator()
rel_results = rel_eval.evaluate(predicted_relationships, ground_truth_relationships)
print(f"Relationship F1: {rel_results['overall'].f1:.4f}")

# Evaluate graph (end-to-end)
graph_eval = GraphEvaluator()
graph_results = graph_eval.evaluate(
    predicted_entities, predicted_relationships,
    ground_truth_entities, ground_truth_relationships
)
print(f"Graph F1: {graph_results['overall'].f1:.4f}")

# Check targets
assert entity_results['overall'].f1 >= 0.85, "Entity F1 below target"
assert rel_results['overall'].f1 >= 0.70, "Relationship F1 below target"
assert graph_results['overall'].f1 >= 0.40, "Graph F1 below target"
```

---

## Metrics Explanation

### Precision

Proportion of predicted items that are correct:

```
Precision = TP / (TP + FP)
```

- **High precision**: Few false positives, predictions are reliable
- **Low precision**: Many false positives, system over-predicts

### Recall

Proportion of ground truth items that are found:

```
Recall = TP / (TP + FN)
```

- **High recall**: Few false negatives, system finds most items
- **Low recall**: Many false negatives, system misses items

### F1 Score

Harmonic mean of precision and recall:

```
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

- Balances precision and recall
- Single metric for comparing systems
- Used as primary evaluation metric

### Macro vs. Micro Averaging

**Macro Average:**
- Calculate metrics for each type separately
- Average the metrics
- Gives equal weight to each type (regardless of frequency)

**Micro Average:**
- Aggregate counts across all types
- Calculate metrics on aggregated counts
- Gives more weight to frequent types

---

## Ground Truth Formats

### Entity Annotation Format

```json
{
  "document_id": "contract_123",
  "entities": [
    {
      "id": "ent_1",
      "text": "TechCorp Inc.",
      "type": "Legal_Party",
      "start": 10,
      "end": 23,
      "page": 1
    },
    {
      "id": "ent_2",
      "text": "Payment of $10,000",
      "type": "Financial_Term",
      "start": 50,
      "end": 68,
      "page": 1
    }
  ]
}
```

### Relationship Annotation Format

```json
{
  "document_id": "contract_123",
  "relationships": [
    {
      "id": "rel_1",
      "source_id": "ent_1",
      "target_id": "ent_2",
      "type": "OBLIGATES",
      "evidence": "TechCorp Inc. shall pay $10,000..."
    }
  ]
}
```

---

## Interpreting Results

### High Precision, Low Recall
- System is conservative, only extracts high-confidence items
- Missing many valid entities/relationships
- **Solution**: Lower confidence thresholds, improve extraction coverage

### Low Precision, High Recall
- System is aggressive, extracts too many items
- Many false positives
- **Solution**: Raise confidence thresholds, improve extraction quality

### Balanced Low Performance
- System needs fundamental improvements
- **Solutions**:
  - Improve prompts
  - Use better LLM models
  - Add more few-shot examples
  - Enhance preprocessing

### Type-Specific Issues

If certain entity/relationship types have low F1:
1. Add more examples for that type in prompts
2. Improve type definitions
3. Enhance validation logic for that type

---

## Baseline Comparisons

### Comparing Models

```python
# Evaluate with GPT-4
pipeline_gpt4 = CompleteExtractionPipeline(llm_model="gpt-4o")
results_gpt4 = evaluate_pipeline(pipeline_gpt4, test_set)

# Evaluate with Claude
pipeline_claude = CompleteExtractionPipeline(llm_model="claude-3-5-sonnet-20241022", llm_provider="anthropic")
results_claude = evaluate_pipeline(pipeline_claude, test_set)

# Compare
print(f"GPT-4 F1:   {results_gpt4['overall'].f1:.4f}")
print(f"Claude F1:  {results_claude['overall'].f1:.4f}")
```

### Ablation Studies

Test impact of different components:

```python
# Without chain-of-thought reasoning
results_no_cot = evaluate_pipeline(pipeline, test_set, use_cot=False)

# Without coreference resolution
results_no_coref = evaluate_pipeline(pipeline, test_set, use_coref=False)

# Without validation
results_no_validation = evaluate_pipeline(pipeline, test_set, validate=False)

# Compare impact
print(f"Full system:     {results_full['overall'].f1:.4f}")
print(f"No CoT:          {results_no_cot['overall'].f1:.4f}")
print(f"No Coreference:  {results_no_coref['overall'].f1:.4f}")
print(f"No Validation:   {results_no_validation['overall'].f1:.4f}")
```

---

## Error Analysis

### Common Error Patterns

1. **Entity Boundary Errors**: Wrong span detection
2. **Type Confusion**: Correct entity, wrong type
3. **Missed Entities**: False negatives
4. **Hallucinated Entities**: False positives
5. **Relationship Direction**: Source/target swapped
6. **Relationship Type Errors**: Wrong relationship classification

### Analyzing Errors

```python
# Get false positives
false_positives = results["errors"]["false_positives"]["examples"]

# Analyze patterns
for fp in false_positives:
    print(f"FP: {fp['text']} (type: {fp['type']}, conf: {fp['confidence']})")

# Get false negatives
false_negatives = results["errors"]["false_negatives"]["examples"]

for fn in false_negatives:
    print(f"FN: {fn['text']} (type: {fn['type']})")
```

### Confidence Analysis

```python
# Check if low-confidence predictions are less accurate
low_conf = [e for e in predicted_entities if e.confidence < 0.7]
high_conf = [e for e in predicted_entities if e.confidence >= 0.9]

# Evaluate separately
results_low = evaluator.evaluate(low_conf, ground_truth)
results_high = evaluator.evaluate(high_conf, ground_truth)

print(f"Low confidence F1:  {results_low['overall'].f1:.4f}")
print(f"High confidence F1: {results_high['overall'].f1:.4f}")
```

---

## Performance Optimization

### Meeting Targets

If performance is below targets:

**For Entity F1 < 0.85:**
1. Enhance entity type descriptions in prompts
2. Add more few-shot examples per type
3. Improve entity validation logic
4. Use better embedding models for deduplication

**For Relationship F1 < 0.70:**
1. Improve chain-of-thought reasoning prompts
2. Enhance coreference resolution
3. Add more relationship examples
4. Improve evidence extraction

**For Graph F1 < 0.40:**
1. Focus on entity linking accuracy
2. Improve entity disambiguation
3. Enhance relationship validation
4. Check entity ID assignment consistency

---

## Integration with CUAD Dataset

The CUAD (Contract Understanding Atticus Dataset) contains 510 legal contracts with 13,000+ annotations.

### Loading CUAD Annotations

```python
from atticus.evaluation import load_cuad_annotations

# Load CUAD ground truth
contracts = load_cuad_annotations("data/cuad/")

for contract in contracts:
    # Extract predictions
    predicted = pipeline.process_document(contract.path)

    # Evaluate
    results = evaluator.evaluate(
        predicted_entities=predicted.entities,
        ground_truth_entities=contract.entities
    )

    print(f"{contract.name}: F1 = {results['overall'].f1:.4f}")
```

---

## Next Steps

**Phase 7**: Documentation and Deployment
- Complete user documentation
- Deployment guides
- CI/CD pipeline setup
- Docker containerization
- Performance benchmarks

---

## References

- [Precision and Recall](https://en.wikipedia.org/wiki/Precision_and_recall)
- [F1 Score](https://en.wikipedia.org/wiki/F-score)
- [CUAD Dataset](https://www.atticusprojectai.org/cuad)
- [Information Extraction Evaluation](https://aclanthology.org/W02-2024/)
