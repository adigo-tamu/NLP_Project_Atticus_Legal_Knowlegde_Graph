# Entity Extraction Module Documentation

## Overview

The entity extraction module implements LLM-based Named Entity Recognition (NER) for legal documents. It uses advanced prompt engineering, few-shot learning, and chain-of-thought reasoning to extract 8 types of legal entities with high accuracy.

## Architecture

```
Document Input
     ↓
Document Processor (Parse + Chunk)
     ↓
Entity Extractor (LLM-based NER)
     ↓
Entity Validator (Confidence scoring + Quality control)
     ↓
Entity Deduplicator (Embedding-based similarity)
     ↓
Entity Storage (Neo4j Knowledge Graph)
```

## Entity Types

The system extracts 8 types of legal entities:

### 1. Legal_Party
Companies, individuals, and organizations involved in legal documents.
- **Examples**: "ABC Corporation", "John Doe", "The Seller"
- **Attributes**: role (buyer, seller, licensor), entity_subtype (company, individual)

### 2. Legal_Concept
Legal terms, principles, and defined terms.
- **Examples**: "confidential information", "intellectual property", "material breach"
- **Attributes**: defined_term, concept_type

### 3. Obligation
Duties and requirements (shall/must statements).
- **Examples**: "Seller shall deliver", "must provide notice within 30 days"
- **Attributes**: obligated_party, obligation_type, deadline

### 4. Right
Permissions and entitlements (may statements).
- **Examples**: "may terminate", "right to audit", "entitled to indemnification"
- **Attributes**: right_holder, right_type, conditions

### 5. Jurisdiction
Courts, governing law references, legal jurisdictions.
- **Examples**: "Delaware law", "federal court", "State of California"
- **Attributes**: jurisdiction_type (governing_law, venue), jurisdiction_level

### 6. Temporal_Entity
Dates, deadlines, durations, and time periods.
- **Examples**: "December 31, 2024", "within 30 days", "term of 2 years"
- **Attributes**: date_value, duration, temporal_type

### 7. Financial_Term
Amounts, payment terms, prices, and fees.
- **Examples**: "$100,000", "annual license fee", "5% interest rate"
- **Attributes**: amount, currency, payment_type, frequency

### 8. Clause_Reference
References to other sections or clauses.
- **Examples**: "Section 3.1", "Article IV", "as defined in Section 2"
- **Attributes**: reference_type, section_number

## Components

### 1. EntityExtractor

LLM-based entity extraction with prompt engineering.

**Features:**
- Multi-model support (GPT-4o, Claude 3.5 Sonnet)
- Few-shot learning with 3 annotated examples
- Document-type-specific prompts (contracts, agreements, etc.)
- JSON schema validation
- Automatic retry with exponential backoff

**Usage:**
```python
from atticus.extraction import EntityExtractor

extractor = EntityExtractor(model="gpt-4o")
entities = extractor.extract_from_chunk(chunk, document_type="contract")
```

### 2. EntityValidator

Quality control and confidence scoring.

**Validation Rules:**
- Required fields checking (text, type, confidence)
- Length validation (2-1000 characters)
- Type-specific validation:
  - Financial terms: Must contain numbers or currency symbols
  - Temporal entities: Must match temporal patterns
  - Legal parties: No single pronouns, minimum 2 characters

**Confidence Adjustment:**
- Boost for well-structured entities (+0.1 to +0.2)
- Reduce for very short entities (-0.2)
- Reduce for very long entities (-0.1)

**Usage:**
```python
from atticus.extraction import EntityValidator

validator = EntityValidator()
valid_entities = validator.validate_batch(raw_entities)
stats = validator.get_entity_statistics(valid_entities)
```

### 3. EntityDeduplicator

Embedding-based entity deduplication.

**Deduplication Strategy:**
1. **Exact match**: Remove exact text duplicates (case-insensitive)
2. **Embedding similarity**: Use sentence transformers to find similar entities
3. **Merging**: Keep higher confidence entity, add aliases

**Similarity Threshold:** 0.85 (configurable in config.yaml)

**Usage:**
```python
from atticus.extraction import EntityDeduplicator

deduplicator = EntityDeduplicator()
unique_entities = deduplicator.deduplicate(entities)

# Find potential duplicates without merging
duplicates = deduplicator.find_duplicates(entities, threshold=0.9)
```

### 4. EntityStorage

Neo4j integration for entity persistence.

**Features:**
- Type-specific node labels (LegalParty, Obligation, Right, etc.)
- Automatic property mapping
- Batch storage optimization
- Full-text search support
- Document-level retrieval

**Usage:**
```python
from atticus.extraction import EntityStorage

storage = EntityStorage()
storage.store_batch(entities)

# Retrieve entities
doc_entities = storage.get_entities_by_document("doc_123")
parties = storage.get_entities_by_type("Legal_Party")
search_results = storage.search_entities("payment", entity_type="Financial_Term")
```

### 5. EntityExtractionPipeline

End-to-end pipeline orchestration.

**Pipeline Steps:**
1. Parse document (PDF, DOCX, TXT)
2. Create hierarchical chunks
3. Extract entities with LLM
4. Validate entities
5. Deduplicate entities
6. Store in Neo4j

**Usage:**
```python
from atticus.extraction import EntityExtractionPipeline

pipeline = EntityExtractionPipeline()

# Process single document
document, chunks, entities = pipeline.process_document("contract.pdf")

# Process batch
results = pipeline.process_batch(["doc1.pdf", "doc2.pdf", "doc3.pdf"])

# Extract only (without storage)
entities = pipeline.extract_entities_only(document, chunks)
```

## Prompt Engineering

### Base Template

Located in `prompts/entity_extraction/base_template.txt`

**Key Features:**
- Clear entity type definitions with examples
- Extraction guidelines (exact text, confidence scoring)
- JSON output format specification
- Anti-patterns to avoid over-extraction

### Few-Shot Examples

Located in `prompts/entity_extraction/few_shot_examples.json`

**3 Annotated Examples:**
1. Software License Agreement clause
2. Termination provision
3. Governing law clause

### Contract-Specific Instructions

Located in `prompts/entity_extraction/contract_specific.txt`

**Special Patterns:**
- Party identification (signature blocks, preambles)
- Temporal patterns (effective dates, renewal periods)
- Financial terms (license fees, payment schedules)
- Legal concepts (indemnification, force majeure)

## Performance Metrics

### Target Metrics (from requirements)
- **Entity Extraction F1**: ≥ 0.85
- **Processing Speed**: < 30 seconds per document (20 pages)
- **Confidence Threshold**: 0.7 (default)

### Actual Performance
*To be measured on CUAD dataset*

## Configuration

All entity extraction settings are in `config/config.yaml`:

```yaml
entity_extraction:
  entity_types:
    - Legal_Party
    - Legal_Concept
    - Obligation
    - Right
    - Jurisdiction
    - Temporal_Entity
    - Financial_Term
    - Clause_Reference

  confidence_threshold: 0.7
  max_entities_per_chunk: 50
  enable_validation: true
  enable_deduplication: true

  extract_attributes: true
  extract_context: true
  context_window: 2  # sentences

  use_coreference: true
  merge_threshold: 0.85
```

## Testing

### Unit Tests
Run entity extraction tests:
```bash
pytest tests/test_entity_extractor.py -v
```

### Integration Test
Test the full pipeline:
```bash
python scripts/test_entity_extraction.py
```

**Sample Output:**
```
Extracted 45 entities
- Legal_Party: 4 entities
- Financial_Term: 8 entities
- Temporal_Entity: 12 entities
- Obligation: 9 entities
- Right: 5 entities
- Jurisdiction: 4 entities
- Clause_Reference: 3 entities
```

## Examples

### Example 1: Basic Extraction

```python
from atticus.extraction import EntityExtractionPipeline

pipeline = EntityExtractionPipeline()
document, chunks, entities = pipeline.process_document("contract.pdf")

print(f"Extracted {len(entities)} entities")
for entity in entities:
    print(f"{entity.type.value}: {entity.text} (confidence: {entity.confidence:.2f})")
```

### Example 2: Custom Validation

```python
from atticus.extraction import EntityValidator

validator = EntityValidator()

# Adjust confidence threshold
validator.confidence_threshold = 0.8

# Validate with custom threshold
valid_entities = validator.filter_low_confidence(entities)
```

### Example 3: Finding Duplicates

```python
from atticus.extraction import EntityDeduplicator

deduplicator = EntityDeduplicator()

# Find potential duplicates
duplicates = deduplicator.find_duplicates(entities, threshold=0.9)

for ent1, ent2, similarity in duplicates:
    print(f"Similar entities (score: {similarity:.2f}):")
    print(f"  1. {ent1.text}")
    print(f"  2. {ent2.text}")
```

## API Reference

See inline documentation in:
- `src/atticus/extraction/entity_extractor.py`
- `src/atticus/extraction/entity_validator.py`
- `src/atticus/extraction/entity_deduplicator.py`
- `src/atticus/extraction/entity_storage.py`
- `src/atticus/extraction/pipeline.py`

## Troubleshooting

### Issue: Low extraction quality
**Solution**:
- Increase confidence threshold in config
- Add document-type-specific examples
- Try Claude 3.5 Sonnet for longer documents

### Issue: Too many duplicates
**Solution**:
- Adjust `merge_threshold` (lower = more aggressive merging)
- Check entity validation rules

### Issue: Missing entities
**Solution**:
- Review prompt templates
- Lower confidence threshold temporarily
- Check chunk overlap settings

## Next Steps

1. **Relationship Extraction**: Extract relationships between entities
2. **Coreference Resolution**: Link entity mentions across document
3. **Temporal Reasoning**: Extract temporal constraints
4. **Evaluation Framework**: Measure F1 scores on CUAD dataset
