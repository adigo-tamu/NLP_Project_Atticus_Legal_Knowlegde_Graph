# API Documentation

**Phase 5: REST API and RAG Integration**

Complete REST API for querying the Legal Knowledge Graph with natural language support and RAG-based question answering.

---

## Overview

The Project Atticus API provides a comprehensive REST interface for interacting with the legal knowledge graph through:

1. **Natural Language Queries**: Ask questions in plain English, automatically translated to Cypher
2. **Direct Cypher Queries**: Execute custom Neo4j Cypher queries
3. **Entity & Relationship Search**: Search and filter graph elements
4. **RAG Question Answering**: Answer questions using retrieval-augmented generation
5. **Graph Analytics**: Get statistics and quality metrics
6. **Path Finding**: Find connections between entities

---

## Quick Start

### Starting the API Server

```bash
# Start the API server
python scripts/run_api.py

# Or using uvicorn directly
uvicorn atticus.api.app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)
- **Health Check**: `http://localhost:8000/health`

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      FastAPI Application                      │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐   ┌─────────────────┐   ┌────────────┐ │
│  │  NL to Cypher   │   │   GraphRAG      │   │ Analytics  │ │
│  │   Translator    │   │    System       │   │   Module   │ │
│  └────────┬────────┘   └────────┬────────┘   └─────┬──────┘ │
│           │                      │                   │         │
│           └──────────────────────┴───────────────────┘         │
│                              │                                 │
│                    ┌─────────▼─────────┐                      │
│                    │  Neo4j Manager    │                      │
│                    └─────────┬─────────┘                      │
└──────────────────────────────┼──────────────────────────────┘
                                │
                        ┌───────▼────────┐
                        │  Neo4j Graph   │
                        │    Database    │
                        └────────────────┘
```

---

## Endpoints

### Health & Status

#### `GET /health`

Check API health and component status.

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "llm_available": true,
  "version": "1.0.0"
}
```

#### `GET /stats`

Get comprehensive graph statistics.

**Query Parameters:**
- `document_id` (optional): Filter by document ID

**Response:**
```json
{
  "total_nodes": 1247,
  "total_relationships": 3521,
  "node_types": {
    "Legal_Party": 142,
    "Legal_Concept": 387,
    "Obligation": 298
  },
  "relationship_types": {
    "REFERENCES": 1234,
    "OBLIGATES": 567
  },
  "avg_degree": 5.64,
  "density": 0.0023
}
```

---

### Query Endpoints

#### `POST /query/natural-language`

Query the graph using natural language.

**Request Body:**
```json
{
  "query": "What obligations does TechCorp have?",
  "document_id": "contract_123",
  "limit": 10,
  "include_reasoning": false
}
```

**Response:**
```json
{
  "query": "What obligations does TechCorp have?",
  "query_type": "natural_language",
  "results": [
    {
      "party": "TechCorp Inc.",
      "obligation": "Payment of license fees within 30 days",
      "confidence": 0.89
    }
  ],
  "count": 5,
  "execution_time_ms": 245.6,
  "cypher_query": "MATCH (party:Legal_Party)-[:OBLIGATES]->(obligation:Obligation) WHERE ...",
  "reasoning": "Identified obligations by following OBLIGATES relationships from TechCorp entity"
}
```

**Example Queries:**
- "What obligations does TechCorp have?"
- "Find all relationships between ABC Corp and payment terms"
- "Show me entities with high confidence scores"
- "What legal concepts are referenced in this document?"
- "Who are the parties involved in this agreement?"

#### `POST /query/cypher`

Execute a direct Cypher query.

**Request Body:**
```json
{
  "query": "MATCH (n:Legal_Party) RETURN n.text, n.confidence LIMIT 10",
  "parameters": {}
}
```

**Response:**
```json
{
  "query": "MATCH (n:Legal_Party) RETURN n.text, n.confidence LIMIT 10",
  "query_type": "cypher",
  "results": [
    {"n.text": "TechCorp Inc.", "n.confidence": 0.95},
    {"n.text": "ABC Corporation", "n.confidence": 0.92}
  ],
  "count": 10,
  "execution_time_ms": 12.3,
  "cypher_query": "MATCH (n:Legal_Party) RETURN n.text, n.confidence LIMIT 10"
}
```

**⚠️ Warning**: In production, this endpoint should be restricted to read-only queries.

---

### Search Endpoints

#### `POST /search/entities`

Search for entities in the graph.

**Request Body:**
```json
{
  "text": "techcorp",
  "entity_type": "Legal_Party",
  "document_id": "contract_123",
  "min_confidence": 0.8,
  "limit": 10
}
```

**Response:**
```json
{
  "entities": [
    {
      "id": "entity_123",
      "text": "TechCorp Inc.",
      "type": "Legal_Party",
      "confidence": 0.95,
      "document_id": "contract_123",
      "context": "...TechCorp Inc. ('Licensor') hereby grants..."
    }
  ],
  "count": 3,
  "execution_time_ms": 15.2
}
```

**Filters:**
- `text`: Partial text match (case-insensitive)
- `entity_type`: One of: `Legal_Party`, `Legal_Concept`, `Obligation`, `Right`, `Jurisdiction`, `Temporal_Entity`, `Financial_Term`, `Clause_Reference`
- `document_id`: Filter by document
- `min_confidence`: Minimum confidence score (0-1)
- `limit`: Maximum results (1-100)

#### `POST /search/relationships`

Search for relationships in the graph.

**Request Body:**
```json
{
  "source_id": "entity_123",
  "target_id": "entity_456",
  "relationship_type": "OBLIGATES",
  "document_id": "contract_123",
  "min_confidence": 0.7,
  "limit": 10
}
```

**Response:**
```json
{
  "relationships": [
    {
      "id": "rel_789",
      "source": {
        "id": "entity_123",
        "text": "TechCorp Inc.",
        "type": "Legal_Party",
        "confidence": 0.95,
        "document_id": "contract_123"
      },
      "target": {
        "id": "entity_456",
        "text": "Payment of $10,000",
        "type": "Obligation",
        "confidence": 0.87,
        "document_id": "contract_123"
      },
      "type": "OBLIGATES",
      "confidence": 0.89,
      "evidence": "Licensor shall pay the sum of $10,000...",
      "document_id": "contract_123"
    }
  ],
  "count": 5,
  "execution_time_ms": 23.4
}
```

**Filters:**
- `source_id`: Filter by source entity ID
- `target_id`: Filter by target entity ID
- `relationship_type`: One of: `REFERENCES`, `OBLIGATES`, `GRANTS_RIGHT`, `GOVERNS`, `DEFINES`, `MODIFIES`, `DEPENDS_ON`, `CONTRADICTS`, `TEMPORALLY_PRECEDES`, `FINANCIALLY_RELATES`
- `document_id`: Filter by document
- `min_confidence`: Minimum confidence score (0-1)
- `limit`: Maximum results (1-100)

---

### RAG Endpoints

#### `POST /rag/ask`

Answer a question using Retrieval-Augmented Generation.

**Request Body:**
```json
{
  "question": "What are the main obligations in this contract?",
  "document_id": "contract_123",
  "max_context_entities": 10,
  "max_context_relationships": 10,
  "include_sources": true
}
```

**Response:**
```json
{
  "question": "What are the main obligations in this contract?",
  "answer": "The main obligations in this contract include: 1) TechCorp must pay $10,000 within 30 days, 2) The licensee must maintain confidentiality of proprietary information, 3) Both parties must comply with applicable data privacy laws.",
  "confidence": 0.87,
  "sources": [
    {
      "id": "entity_123",
      "text": "Payment obligation of $10,000",
      "type": "Obligation",
      "confidence": 0.92,
      "document_id": "contract_123"
    }
  ],
  "context_used": {
    "num_entities": 8,
    "num_relationships": 12
  },
  "execution_time_ms": 567.8
}
```

**How it works:**

1. **Retrieval**: System retrieves relevant entities and relationships using:
   - Keyword-based search
   - Semantic similarity (embeddings)
   - Relationship traversal

2. **Context Building**: Formats retrieved information into structured context

3. **Generation**: LLM generates answer based on retrieved context

4. **Confidence Scoring**: Assigns confidence based on context quality and LLM certainty

#### `GET /rag/competency-questions`

Get sample competency questions for legal contracts.

**Response:**
```json
{
  "questions": [
    "What parties are involved in this contract?",
    "What are the main obligations of each party?",
    "What are the payment terms?",
    "What is the termination clause?",
    "What jurisdiction governs this agreement?"
  ],
  "count": 10
}
```

---

### Graph Navigation

#### `POST /graph/path`

Find paths between two entities in the graph.

**Request Body:**
```json
{
  "source_id": "entity_123",
  "target_id": "entity_456",
  "max_depth": 3,
  "relationship_types": ["REFERENCES", "DEFINES"]
}
```

**Response:**
```json
{
  "source": {
    "id": "entity_123",
    "text": "Software License Agreement",
    "type": "Legal_Concept",
    "confidence": 0.94,
    "document_id": "contract_123"
  },
  "target": {
    "id": "entity_456",
    "text": "Termination Clause",
    "type": "Clause_Reference",
    "confidence": 0.88,
    "document_id": "contract_123"
  },
  "paths": [
    [
      {"entity": "Software License Agreement", "relationship": "DEFINES"},
      {"entity": "Terms and Conditions", "relationship": "REFERENCES"},
      {"entity": "Termination Clause"}
    ]
  ],
  "count": 3,
  "execution_time_ms": 45.2
}
```

---

## Natural Language to Cypher Translation

### How It Works

The NL to Cypher translator uses LLMs to convert natural language questions into valid Cypher queries.

**Translation Process:**

1. **Schema Context**: System provides graph schema to LLM
2. **Few-Shot Examples**: LLM learns from example translations
3. **Query Generation**: LLM generates Cypher query
4. **Validation**: Query syntax is validated
5. **Execution**: Query is executed against Neo4j

**Example Translations:**

| Natural Language | Generated Cypher |
|-----------------|------------------|
| "What obligations does TechCorp have?" | `MATCH (party:Legal_Party)-[:OBLIGATES]->(obligation:Obligation) WHERE toLower(party.text) CONTAINS 'techcorp' RETURN party.text, obligation.text LIMIT 20` |
| "Find high confidence entities" | `MATCH (n) WHERE n.confidence > 0.9 RETURN n.text, n.confidence ORDER BY n.confidence DESC LIMIT 20` |
| "Show contradictions" | `MATCH (source)-[r:CONTRADICTS]->(target) RETURN source.text, target.text, r.evidence LIMIT 20` |

### Safety Features

- **Query Validation**: All generated queries are validated before execution
- **LIMIT Clauses**: Automatic addition of LIMIT to prevent large result sets
- **Read-Only**: Production deployments should restrict to read-only queries
- **Sanitization**: Input sanitization to prevent injection attacks

---

## RAG System Architecture

### Retrieval Strategies

**1. Keyword-Based Search**
- Extracts keywords from question
- Searches entity text fields
- Fast and precise for explicit mentions

**2. Semantic Similarity Search**
- Encodes question using sentence-transformers
- Computes cosine similarity with entity embeddings
- Captures semantic meaning beyond keywords

**3. Relationship Traversal**
- Retrieves relationships involving found entities
- Provides graph context around relevant entities
- Enables multi-hop reasoning

### Context Formatting

Retrieved information is formatted for LLM:

```
## Entities

1. **TechCorp Inc.** (Legal_Party)
   - Confidence: 0.95
   - Context: "TechCorp Inc. ('Licensor') hereby grants..."

2. **Payment obligation of $10,000** (Obligation)
   - Confidence: 0.92
   - Context: "...shall pay the sum of $10,000 within 30 days..."

## Relationships

1. TechCorp Inc. --[OBLIGATES]--> Payment obligation of $10,000
   - Confidence: 0.89
   - Evidence: "Licensor shall pay the sum of $10,000..."
```

### Answer Generation

LLM generates answer following guidelines:
- Use ONLY retrieved context
- Cite specific entities/relationships
- Indicate if context insufficient
- Provide confidence score

---

## Usage Examples

### Python Client

```python
import requests

API_URL = "http://localhost:8000"

# Natural language query
response = requests.post(
    f"{API_URL}/query/natural-language",
    json={
        "query": "What are the payment terms?",
        "limit": 10,
        "include_reasoning": True
    }
)
print(response.json())

# RAG question answering
response = requests.post(
    f"{API_URL}/rag/ask",
    json={
        "question": "Who are the parties in this contract?",
        "include_sources": True
    }
)
answer = response.json()
print(f"Answer: {answer['answer']}")
print(f"Confidence: {answer['confidence']}")

# Entity search
response = requests.post(
    f"{API_URL}/search/entities",
    json={
        "text": "payment",
        "entity_type": "Financial_Term",
        "min_confidence": 0.8
    }
)
entities = response.json()["entities"]
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Natural language query
curl -X POST http://localhost:8000/query/natural-language \
  -H "Content-Type: application/json" \
  -d '{"query": "What obligations does TechCorp have?", "limit": 10}'

# RAG question answering
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main terms of this contract?"}'

# Entity search
curl -X POST http://localhost:8000/search/entities \
  -H "Content-Type: application/json" \
  -d '{"text": "payment", "min_confidence": 0.8, "limit": 5}'
```

---

## Configuration

API configuration is managed through `config/config.yaml`:

```yaml
llm:
  provider: "openai"  # or "anthropic"
  model: "gpt-4o"
  temperature: 0.0
  max_tokens: 4000

neo4j:
  uri: "bolt://localhost:7687"
  username: "neo4j"
  password: "password"

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]  # Restrict in production
  log_level: "info"
```

Environment variables (`.env`):
```bash
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

---

## Performance

### Response Times (Average)

| Endpoint | Average Response Time |
|----------|----------------------|
| Health Check | < 10 ms |
| Entity Search | 15-50 ms |
| Relationship Search | 20-80 ms |
| Cypher Query | 10-100 ms (depends on complexity) |
| NL to Cypher | 200-500 ms (LLM latency) |
| RAG Answer | 500-1500 ms (retrieval + LLM) |

### Optimization Tips

1. **Caching**: Cache common queries and NL translations
2. **Indexing**: Ensure Neo4j indexes on frequently queried properties
3. **Batching**: Use batch endpoints for multiple queries
4. **Limiting**: Use appropriate limit values to reduce data transfer
5. **Filtering**: Apply document_id filters to narrow search space

---

## Error Handling

### Standard Error Response

```json
{
  "error": "Query execution failed",
  "detail": "Invalid Cypher syntax: unexpected token...",
  "query": "MATCH (n) RETRN n"
}
```

### HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid input or query syntax
- `404 Not Found`: Entity or resource not found
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Database connection failed

---

## Security Considerations

### Production Deployment

1. **Authentication**: Add JWT or API key authentication
2. **Rate Limiting**: Implement rate limiting to prevent abuse
3. **Query Restrictions**: Restrict Cypher endpoint to read-only queries
4. **CORS**: Configure allowed origins appropriately
5. **Input Validation**: Validate and sanitize all inputs
6. **Logging**: Log all queries for audit trail
7. **HTTPS**: Use HTTPS in production
8. **Secrets Management**: Use proper secrets management for credentials

### Example Security Middleware

```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

API_KEY = "your-secret-api-key"
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Add to endpoint
@app.get("/protected", dependencies=[Depends(verify_api_key)])
async def protected_endpoint():
    return {"message": "Access granted"}
```

---

## Testing

Run API tests:

```bash
# Start the API server
python scripts/run_api.py

# In another terminal, run tests
python scripts/test_api.py

# Or use pytest
pytest tests/api/
```

---

## Next Steps

**Phase 6**: Evaluation Framework
- Entity extraction F1 score calculation
- Relationship extraction F1 score calculation
- Graph F1 score (full triples)
- Baseline comparisons
- Error analysis

See: [EVALUATION.md](EVALUATION.md) (to be created)

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/)
- [Sentence Transformers](https://www.sbert.net/)
- [RAG Systems Overview](https://arxiv.org/abs/2005.11401)
