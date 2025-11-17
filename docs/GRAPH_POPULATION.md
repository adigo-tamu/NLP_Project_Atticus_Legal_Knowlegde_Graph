# Graph Population and Validation

**Phase 4 Implementation Documentation**

This document describes the graph population, validation, and export capabilities of Project Atticus.

---

## Overview

The graph population phase provides comprehensive tools for:

1. **Entity Disambiguation**: Cross-document entity resolution using embeddings
2. **Graph Validation**: Quality checks and consistency validation
3. **Graph Analytics**: Statistical analysis and quality metrics
4. **Graph Population**: End-to-end pipeline with validation
5. **Graph Export**: Export to standard formats (GraphML, RDF, JSON, Cypher)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Graph Population Pipeline                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [1] Document Processing                                         │
│       ↓                                                           │
│  [2] Entity + Relationship Extraction                            │
│       ↓                                                           │
│  [3] Cross-Document Disambiguation ← EntityDisambiguator        │
│       ↓                                                           │
│  [4] Graph Validation ← GraphValidator                           │
│       ↓                                                           │
│  [5] Quality Metrics ← GraphAnalytics                            │
│       ↓                                                           │
│  [6] Export ← GraphExporter                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Entity Disambiguation

**Module**: `atticus.graph.entity_disambiguator`

Cross-document entity resolution identifies when entities in different documents refer to the same real-world entity.

### Features

- **Exact Matching**: Fast exact text matching for obvious duplicates
- **Embedding Similarity**: Semantic similarity using sentence-transformers
- **Type-Based Grouping**: Only compare entities of the same type
- **Configurable Thresholds**: Adjust similarity thresholds per entity type

### Usage

```python
from atticus.graph import EntityDisambiguator

disambiguator = EntityDisambiguator()

# Disambiguate entities across documents
results = disambiguator.disambiguate_entities(
    entities=all_entities,
    group_by_type=True  # Compare only same types
)

# Results contain:
# - clusters: List of entity clusters
# - merged_count: Number of entities merged
# - mapping: Entity ID to cluster ID mapping
```

### Algorithm

1. **Exact Match Clustering**:
   - Group entities with identical text (case-insensitive)
   - Fast O(n) operation

2. **Embedding-Based Clustering**:
   - Compute embeddings for remaining entities using sentence-transformers
   - Calculate pairwise cosine similarity
   - Cluster entities above threshold (default: 0.90 for cross-document)

3. **Merge Strategy**:
   - Select representative entity (highest confidence)
   - Merge metadata from all cluster members
   - Update Neo4j to consolidate entities

### Configuration

```yaml
entity_extraction:
  deduplication:
    exact_match_enabled: true
    embedding_similarity_threshold: 0.85  # Within-document
    cross_document_threshold: 0.90         # Cross-document (higher bar)
    embedding_model: "all-MiniLM-L6-v2"
```

---

## 2. Graph Validation

**Module**: `atticus.graph.graph_validator`

Comprehensive validation system with 8 quality checks.

### Validation Checks

#### 1. Orphan Nodes
**Description**: Nodes with zero relationships (disconnected from graph)

**Query**:
```cypher
MATCH (n)
WHERE NOT (n)--()
RETURN n
```

**Fix**: Remove orphan nodes or investigate why they're disconnected

#### 2. Dangling Relationships
**Description**: Relationships pointing to non-existent entities

**Impact**: Data integrity violation, query errors

**Fix**: Remove dangling relationships

#### 3. Self-Loops
**Description**: Relationships from node to itself

**Query**:
```cypher
MATCH (n)-[r]->(n)
RETURN n, r
```

**Fix**: Remove self-loops (usually extraction errors)

#### 4. Duplicate Relationships
**Description**: Multiple identical relationships between same node pair

**Query**:
```cypher
MATCH (source)-[r]->(target)
WITH source, target, type(r) as rel_type, count(r) as count
WHERE count > 1
RETURN source, target, rel_type, count
```

**Fix**: Deduplicate, keeping relationship with highest confidence

#### 5. Missing Properties
**Description**: Required properties are null or missing

**Required Properties**:
- Entities: `id`, `text`, `type`, `confidence`, `document_id`
- Relationships: `id`, `confidence`, `document_id`

**Fix**: Re-extract or set default values

#### 6. Invalid Confidence Scores
**Description**: Confidence values outside [0, 1] range

**Fix**: Clamp to valid range or re-extract

#### 7. Circular Dependencies
**Description**: Cycles in DEPENDS_ON relationships

**Query**:
```cypher
MATCH path = (n)-[:DEPENDS_ON*]->(n)
RETURN path
```

**Fix**: Remove one edge to break cycle or investigate logical error

#### 8. Semantic Consistency
**Description**: Relationships with semantically incorrect entity types

**Rules**:
- `OBLIGATES`: source must be `Legal_Party` or `Clause_Reference`
- `GRANTS_RIGHT`: source must be `Legal_Party` or `Legal_Concept`
- `GOVERNS`: source must be `Jurisdiction` or `Legal_Concept`
- `FINANCIALLY_RELATES`: source/target must be `Financial_Term`

**Fix**: Correct entity types or remove invalid relationships

### Usage

```python
from atticus.graph import GraphValidator

validator = GraphValidator()

# Full validation report
report = validator.validate_graph()

print(f"Total issues: {report['summary']['total_issues']}")

# Check-specific results
for check_name, issues in report['checks'].items():
    if issues:
        print(f"{check_name}: {len(issues)} issues")

# Validate specific document
doc_report = validator.validate_graph(document_id="contract_123")

# Auto-repair (removes orphans)
removed = validator.remove_orphan_nodes()
```

### Validation Report Structure

```python
{
    "summary": {
        "total_issues": 42,
        "issues_by_check": {
            "orphan_nodes": 10,
            "dangling_relationships": 0,
            "self_loops": 2,
            # ... etc
        }
    },
    "checks": {
        "orphan_nodes": [
            {"node_id": "entity_123", "text": "ABC Corp", ...},
            # ...
        ],
        # ... other checks
    }
}
```

---

## 3. Graph Analytics

**Module**: `atticus.graph.graph_analytics`

Statistical analysis and quality metrics for the knowledge graph.

### Available Metrics

#### Basic Statistics
- Total nodes and relationships
- Average degree
- Degree distribution (min, max, median)

#### Node Statistics
- Count by entity type
- Average/min/max confidence per type

#### Relationship Statistics
- Count by relationship type
- Average/min/max confidence per type

#### Connectivity Metrics
- Hub nodes (highest degree)
- Degree centrality
- Clustering coefficient (planned)

#### Graph Metrics
- Graph density: `actual_edges / possible_edges`
- Average path length (sample-based for large graphs)
- Connected components (planned)

### Usage

```python
from atticus.graph import GraphAnalytics

analytics = GraphAnalytics()

# Get comprehensive statistics
stats = analytics.get_graph_statistics()

# Print formatted summary
summary = analytics.export_graph_summary()
print(summary)

# Find central entities
central = analytics.find_central_entities(
    top_k=10,
    centrality_type="degree"  # or "pagerank"
)

# Analyze specific document
doc_analysis = analytics.analyze_document_graph(
    document_id="contract_123"
)
```

### Sample Statistics Output

```
======================================================================
KNOWLEDGE GRAPH SUMMARY
======================================================================

BASIC STATISTICS:
  Total Nodes: 1,247
  Total Relationships: 3,521
  Average Degree: 5.64

NODE TYPES:
  Legal_Party: 142 nodes
    Avg confidence: 0.892
  Legal_Concept: 387 nodes
    Avg confidence: 0.756
  Obligation: 298 nodes
    Avg confidence: 0.821

RELATIONSHIP TYPES:
  REFERENCES: 1,234 relationships
    Avg confidence: 0.781
  OBLIGATES: 567 relationships
    Avg confidence: 0.845

CONNECTIVITY:
  Min Degree: 0
  Max Degree: 47
  Avg Degree: 5.64
  Median Degree: 3

HUB NODES (Highest Degree):
  - "TechCorp Inc." (degree: 47)
  - "License Agreement" (degree: 32)
  - "Payment Terms" (degree: 28)

GRAPH METRICS:
  Density: 0.0023
  Avg Path Length: 3.2
======================================================================
```

---

## 4. Graph Population Pipeline

**Module**: `atticus.graph.graph_population`

End-to-end pipeline orchestrating extraction, disambiguation, validation, and metrics.

### Pipeline Phases

#### Phase 1: Extraction
- Process all documents
- Extract entities and relationships
- Store in Neo4j

#### Phase 2: Cross-Document Disambiguation
- Identify duplicate entities across documents
- Merge duplicates
- Update relationships

#### Phase 3: Validation
- Run all validation checks
- Report issues
- Optional auto-repair

#### Phase 4: Quality Metrics
- Calculate graph statistics
- Identify hub nodes
- Compute quality scores

### Usage

```python
from atticus.graph import GraphPopulationPipeline

pipeline = GraphPopulationPipeline()

# Process multiple documents
summary = pipeline.populate_from_documents(
    document_paths=[
        "contracts/license_agreement.pdf",
        "contracts/service_agreement.pdf",
        "contracts/nda.pdf",
    ],
    disambiguate=True,  # Run cross-document disambiguation
    validate=True,      # Run validation checks
)

# Check results
print(f"Processed: {summary['successful']}/{summary['total_documents']}")
print(f"Entities: {summary['total_entities']}")
print(f"Relationships: {summary['total_relationships']}")
print(f"Validation issues: {summary['validation']['total_issues']}")
print(f"Graph density: {summary['quality_metrics']['graph_density']}")

# Validate and repair existing graph
repair_report = pipeline.validate_and_repair()

# Export summary report
pipeline.export_summary_report("output/graph_summary.txt")
```

---

## 5. Graph Export

**Module**: `atticus.graph.graph_exporter`

Export knowledge graph to standard formats for interoperability.

### Supported Formats

#### GraphML
XML-based format supported by:
- Gephi (graph visualization)
- yEd (graph editor)
- Cytoscape (network analysis)
- Neo4j (import/export)

```python
from atticus.graph import GraphExporter

exporter = GraphExporter()

exporter.export_to_graphml(
    output_path="output/knowledge_graph.graphml",
    include_metadata=True  # Include all properties
)
```

**Sample Output**:
```xml
<graphml>
  <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>
  <graph id="KnowledgeGraph" edgedefault="directed">
    <node id="entity_123">
      <data key="text">TechCorp Inc.</data>
      <data key="type">Legal_Party</data>
      <data key="confidence">0.95</data>
    </node>
    <edge source="entity_123" target="entity_456">
      <data key="label">OBLIGATES</data>
    </edge>
  </graph>
</graphml>
```

#### RDF/Turtle
Semantic web format (RDF with Turtle syntax):

```python
exporter.export_to_rdf(
    output_path="output/knowledge_graph.ttl",
    format="turtle",  # or "ntriples"
    namespace="http://atticus.legal/"
)
```

**Sample Output**:
```turtle
@prefix atticus: <http://atticus.legal/> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<entity/entity_123>
  rdf:type atticus:Legal_Party ;
  rdfs:label "TechCorp Inc." ;
  atticus:confidence "0.95"^^xsd:double ;
  atticus:OBLIGATES <entity/entity_456> .
```

#### JSON
Simple JSON format for programmatic access:

```python
exporter.export_to_json(
    output_path="output/knowledge_graph.json",
    pretty=True
)
```

**Sample Output**:
```json
{
  "metadata": {
    "node_count": 1247,
    "edge_count": 3521
  },
  "nodes": [
    {
      "id": "entity_123",
      "text": "TechCorp Inc.",
      "type": "Legal_Party",
      "confidence": 0.95
    }
  ],
  "edges": [
    {
      "source": "entity_123",
      "target": "entity_456",
      "type": "OBLIGATES"
    }
  ]
}
```

#### Cypher
Neo4j Cypher CREATE statements for recreating graph:

```python
exporter.export_to_cypher(
    output_path="output/knowledge_graph.cypher"
)
```

**Sample Output**:
```cypher
// Knowledge Graph Export
CREATE (:Legal_Party {id: 'entity_123', text: 'TechCorp Inc.', confidence: 0.95});
MATCH (source {id: 'entity_123'}), (target {id: 'entity_456'})
CREATE (source)-[:OBLIGATES {confidence: 0.87}]->(target);
```

---

## Testing

### Run Tests

```bash
# Test graph population pipeline
python scripts/test_graph_population.py

# Test individual components
python -c "
from atticus.graph import EntityDisambiguator, GraphValidator, GraphAnalytics

# Test disambiguation
disambiguator = EntityDisambiguator()
# ...

# Test validation
validator = GraphValidator()
report = validator.validate_graph()
print(report['summary'])

# Test analytics
analytics = GraphAnalytics()
stats = analytics.get_graph_statistics()
print(stats['basic'])
"
```

---

## Performance Considerations

### Entity Disambiguation
- **Exact matching**: O(n) - very fast
- **Embedding similarity**: O(n²) in worst case
- **Optimization**: Batch encode entities, use approximate nearest neighbors for large graphs

### Graph Validation
- **Simple checks** (orphans, self-loops): O(n) or O(m)
- **Circular dependencies**: O(n + m) with cycle detection
- **Optimization**: Run checks in parallel, cache results

### Analytics
- **Basic statistics**: O(n + m)
- **Path length**: Sample-based (limit to 1000 pairs for large graphs)
- **Centrality**: O(n²) for betweenness, O(n + m) for degree

### Export
- **GraphML/RDF/JSON**: O(n + m) single pass
- **Optimization**: Stream large graphs, batch write operations

---

## Quality Metrics

### Target Metrics (from specification)

- **Entity Extraction F1**: ≥ 0.85
- **Relationship Extraction F1**: ≥ 0.70
- **Graph F1** (full triples): ≥ 0.40

### Current Monitoring

```python
stats = pipeline.get_population_statistics()

# Entity quality
avg_entity_confidence = stats['extraction']['entities']['avg_confidence']

# Relationship quality
avg_rel_confidence = stats['extraction']['relationships']['avg_confidence']

# Graph quality
graph_density = stats['quality_metrics']['graph_density']
validation_issues = stats['validation']['total_issues']

# Quality score (0-100)
quality_score = (
    avg_entity_confidence * 40 +      # 40% weight on entity quality
    avg_rel_confidence * 40 +          # 40% weight on relationship quality
    (1 - validation_issues/total_nodes) * 20  # 20% weight on validation
) * 100
```

---

## Troubleshooting

### Common Issues

#### 1. Too Many Orphan Nodes
**Cause**: Relationship extraction failed or confidence threshold too high

**Fix**:
- Lower relationship confidence threshold
- Investigate extraction failures
- Run auto-repair: `validator.remove_orphan_nodes()`

#### 2. Low Graph Density
**Cause**: Not enough relationships extracted

**Fix**:
- Enable chain-of-thought reasoning
- Lower confidence threshold
- Check for entity deduplication issues

#### 3. High Disambiguation Merge Rate
**Cause**: Similarity threshold too low

**Fix**:
- Increase `cross_document_threshold` in config
- Review entity extraction quality
- Check for overly generic entity names

#### 4. Slow Export
**Cause**: Large graph (>10K nodes)

**Fix**:
- Export by document: `exporter.export_to_graphml(document_id="...")`
- Use streaming export for very large graphs
- Consider pagination

---

## Next Steps

**Phase 5**: REST API and RAG Integration
- FastAPI endpoints for graph queries
- Natural language to Cypher translation
- RAG-based question answering

See: [API_INTEGRATION.md](API_INTEGRATION.md) (to be created)

---

## References

- [Neo4j Documentation](https://neo4j.com/docs/)
- [GraphML Specification](http://graphml.graphdrawing.org/)
- [RDF Primer](https://www.w3.org/TR/rdf11-primer/)
- [Sentence Transformers](https://www.sbert.net/)
