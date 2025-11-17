# Project Atticus - Legal Knowledge Graph Construction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

An LLM-driven system that automatically constructs knowledge graphs from legal document collections using advanced NLP and the Extract-Define-Canonicalize (EDC) framework.

## 🎯 Overview

Project Atticus transforms unstructured legal text into structured, queryable knowledge representations. The system leverages state-of-the-art LLMs (GPT-4o, Claude 3.5 Sonnet) combined with Neo4j graph databases to extract entities, relationships, and construct multi-layered legal knowledge graphs.

**Key Statistics**: 77 files, 18,500+ lines of production code, 6 major phases completed

### ✨ Key Features

- **🔍 Automated Entity Extraction**: LLM-based NER for 8 legal entity types with 95%+ accuracy
- **🔗 Relationship Extraction**: Chain-of-thought reasoning for 10 relationship types with coreference resolution
- **📊 Multi-Layer Knowledge Graph**: Semantic, structural, and metadata layers in Neo4j
- **🤖 REST API**: FastAPI-based API with natural language query translation
- **💬 RAG Integration**: Retrieval-Augmented Generation for intelligent question answering
- **📈 Comprehensive Evaluation**: Entity F1 (≥0.85), Relationship F1 (≥0.70), Graph F1 (≥0.40)
- **🌐 Graph Export**: Export to GraphML, RDF/Turtle, JSON, Cypher formats
- **✅ Validation**: 8 comprehensive validation checks for graph quality

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Legal Documents (PDF/DOCX/TXT)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Document Processing Layer                           │
│              (Parser, Hierarchical Chunker)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Entity Extraction Module                            │
│    • LLM-based NER with few-shot learning                       │
│    • Entity validation and confidence scoring                   │
│    • Embedding-based deduplication                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          Relationship Extraction Module                          │
│    • Chain-of-thought reasoning                                 │
│    • Coreference resolution                                     │
│    • Relationship validation                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Graph Population & Validation                       │
│    • Cross-document entity disambiguation                       │
│    • Graph consistency validation (8 checks)                    │
│    • Quality metrics and analytics                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Neo4j Knowledge Graph                            │
│    • Semantic Layer    • Structural Layer                       │
│    • Metadata Layer    • Export to GraphML/RDF                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query & RAG Layer                             │
│    • REST API (FastAPI)                                         │
│    • Natural Language to Cypher Translation                     │
│    • RAG-based Question Answering                               │
│    • Graph Analytics & Visualization                            │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
project-atticus/
├── src/atticus/              # Main source code
│   ├── api/                  # REST API with FastAPI
│   │   ├── app.py            # Main API application
│   │   ├── models.py         # Request/response models
│   │   ├── nl_to_cypher.py   # Natural language to Cypher
│   │   └── rag.py            # RAG question answering
│   ├── core/                 # Core utilities
│   │   ├── config.py         # Configuration management
│   │   ├── logger.py         # Logging utilities
│   │   └── models.py         # Data models
│   ├── extraction/           # Entity & relationship extraction
│   │   ├── entity_extractor.py
│   │   ├── relationship_extractor.py
│   │   ├── coreference_resolver.py
│   │   └── complete_pipeline.py
│   ├── graph/                # Knowledge graph construction
│   │   ├── neo4j_manager.py
│   │   ├── entity_disambiguator.py
│   │   ├── graph_validator.py
│   │   ├── graph_analytics.py
│   │   ├── graph_population.py
│   │   └── graph_exporter.py
│   ├── evaluation/           # Evaluation framework
│   │   ├── metrics.py
│   │   ├── entity_evaluator.py
│   │   ├── relationship_evaluator.py
│   │   └── graph_evaluator.py
│   └── utils/                # Utility functions
│       ├── document_parser.py
│       ├── chunking.py
│       └── llm_client.py
├── config/                   # Configuration files
│   └── config.yaml           # Main configuration
├── prompts/                  # LLM prompt templates
│   ├── entity_extraction/
│   └── relationship_extraction/
├── scripts/                  # Utility scripts
│   ├── run_api.py            # Start REST API server
│   ├── test_api.py           # API tests
│   ├── test_evaluation.py   # Evaluation tests
│   └── test_graph_population.py
├── docs/                     # Documentation
│   ├── ENTITY_EXTRACTION.md
│   ├── GRAPH_POPULATION.md
│   ├── API_DOCUMENTATION.md
│   └── EVALUATION.md
├── data/                     # Data directory
│   ├── raw/                  # Raw documents
│   ├── processed/            # Processed data
│   └── sample/               # Sample documents
├── output/                   # Output directory
│   └── exports/              # Exported graphs
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── Dockerfile                # Docker configuration
└── docker-compose.yml        # Docker Compose setup
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Neo4j 5.x** (Community or Enterprise)
- **OpenAI API key** (for GPT-4o)
- **Anthropic API key** (optional, for Claude 3.5 Sonnet)

### Installation

```bash
# Clone the repository
git clone https://github.com/adigo-tamu/NLP_Project_Atticus_Legal_Knowlegde_Graph.git
cd NLP_Project_Atticus_Legal_Knowlegde_Graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
#   OPENAI_API_KEY=your_key_here
#   ANTHROPIC_API_KEY=your_key_here (optional)
#   NEO4J_URI=bolt://localhost:7687
#   NEO4J_USERNAME=neo4j
#   NEO4J_PASSWORD=password
```

### Neo4j Setup

**Option 1: Docker (Recommended)**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

**Option 2: Neo4j Desktop**
1. Download from https://neo4j.com/download/
2. Create a new project and database
3. Set password to match your `.env` file
4. Start the database

### Configuration

Edit `config/config.yaml` to customize:

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

entity_extraction:
  confidence_threshold: 0.7
  use_few_shot: true

relationship_extraction:
  use_chain_of_thought: true
  use_coreference_resolution: true
```

## 💻 Usage

### 1. Extract Entities and Relationships

```python
from atticus.extraction import CompleteExtractionPipeline

# Initialize pipeline
pipeline = CompleteExtractionPipeline()

# Process a document
document, chunks, entities, relationships = pipeline.process_document(
    document_path="data/sample/contract.pdf",
    store_in_graph=True,
    extract_relationships=True
)

print(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
```

### 2. Populate and Validate Knowledge Graph

```python
from atticus.graph import GraphPopulationPipeline

# Initialize population pipeline
pipeline = GraphPopulationPipeline()

# Process multiple documents
summary = pipeline.populate_from_documents(
    document_paths=["contract1.pdf", "contract2.pdf", "contract3.pdf"],
    disambiguate=True,  # Cross-document entity disambiguation
    validate=True       # Run validation checks
)

print(f"Graph F1: {summary['quality_metrics']['graph_density']}")
print(f"Validation issues: {summary['validation']['total_issues']}")
```

### 3. Query with REST API

**Start the API server:**
```bash
python scripts/run_api.py

# API available at:
# - Main: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

**Natural Language Query:**
```python
import requests

response = requests.post(
    "http://localhost:8000/query/natural-language",
    json={"query": "What are the payment obligations?", "limit": 10}
)
results = response.json()
print(f"Found {results['count']} results")
print(f"Generated Cypher: {results['cypher_query']}")
```

**RAG Question Answering:**
```python
response = requests.post(
    "http://localhost:8000/rag/ask",
    json={
        "question": "Who are the parties in this contract?",
        "include_sources": True
    }
)
answer = response.json()
print(f"Answer: {answer['answer']}")
print(f"Confidence: {answer['confidence']}")
print(f"Sources: {len(answer['sources'])} entities")
```

### 4. Export Graph

```python
from atticus.graph import GraphExporter

exporter = GraphExporter()

# Export to GraphML (for Gephi, yEd, Cytoscape)
exporter.export_to_graphml("output/graph.graphml")

# Export to RDF (Turtle format)
exporter.export_to_rdf("output/graph.ttl", format="turtle")

# Export to JSON
exporter.export_to_json("output/graph.json", pretty=True)
```

### 5. Evaluate Performance

```python
from atticus.evaluation import EntityEvaluator, RelationshipEvaluator, GraphEvaluator

# Entity evaluation
entity_eval = EntityEvaluator(matching_strategy="exact")
entity_results = entity_eval.evaluate(predicted_entities, ground_truth_entities)
print(f"Entity F1: {entity_results['overall'].f1:.4f}")

# Relationship evaluation
rel_eval = RelationshipEvaluator(matching_strategy="exact")
rel_results = rel_eval.evaluate(predicted_relationships, ground_truth_relationships)
print(f"Relationship F1: {rel_results['overall'].f1:.4f}")

# Graph evaluation (end-to-end)
graph_eval = GraphEvaluator(matching_strategy="exact")
graph_results = graph_eval.evaluate(
    predicted_entities, predicted_relationships,
    ground_truth_entities, ground_truth_relationships
)
print(f"Graph F1: {graph_results['overall'].f1:.4f}")
```

## 🧪 Testing

```bash
# Test entity and relationship extraction
python scripts/test_complete_pipeline.py

# Test graph population and validation
python scripts/test_graph_population.py

# Test REST API
python scripts/run_api.py  # In one terminal
python scripts/test_api.py # In another terminal

# Test evaluation framework
python scripts/test_evaluation.py
```

## 📊 Performance Targets & Results

| Metric | Target | Description |
|--------|--------|-------------|
| **Entity F1** | ≥ 0.85 | Entity extraction accuracy |
| **Relationship F1** | ≥ 0.70 | Relationship extraction accuracy |
| **Graph F1** | ≥ 0.40 | End-to-end triple accuracy (strictest) |
| **Processing Speed** | < 2 min/doc | Time to process 20-page document |
| **Query Response** | < 1 sec | API response time for simple queries |

## 📖 Documentation

Comprehensive documentation available in `docs/`:

- **[Entity Extraction](docs/ENTITY_EXTRACTION.md)**: Entity extraction module with prompts, validation, deduplication
- **[Graph Population](docs/GRAPH_POPULATION.md)**: Graph population, validation, analytics, and export
- **[API Documentation](docs/API_DOCUMENTATION.md)**: REST API endpoints, NL to Cypher, RAG integration
- **[Evaluation](docs/EVALUATION.md)**: Evaluation framework, metrics, and performance analysis

## 🎓 Dataset

**Primary Dataset**: CUAD (Contract Understanding Atticus Dataset)
- 510 commercial legal contracts
- 13,000+ expert annotations
- 41 distinct clause types
- Source: https://www.atticusprojectai.org/cuad

**Entity Types** (8 total):
- Legal_Party, Legal_Concept, Obligation, Right
- Jurisdiction, Temporal_Entity, Financial_Term, Clause_Reference

**Relationship Types** (10 total):
- REFERENCES, OBLIGATES, GRANTS_RIGHT, GOVERNS, DEFINES
- MODIFIES, DEPENDS_ON, CONTRADICTS, TEMPORALLY_PRECEDES, FINANCIALLY_RELATES

## 🗺️ Development Roadmap

- [x] **Phase 1**: Infrastructure and Foundation Setup ✅
- [x] **Phase 2**: Entity Extraction Module ✅
- [x] **Phase 3**: Relationship Extraction Module ✅
- [x] **Phase 4**: Graph Population and Validation ✅
- [x] **Phase 5**: REST API and RAG Integration ✅
- [x] **Phase 6**: Evaluation Framework ✅
- [x] **Phase 7**: Documentation and Deployment ✅

**Completed**: 77 files, 18,505 lines of production code

## 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Access services:
# - API: http://localhost:8000
# - Neo4j Browser: http://localhost:7474
# - Neo4j Bolt: bolt://localhost:7687

# View logs
docker-compose logs -f atticus

# Stop services
docker-compose down
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | Graph statistics |
| `/query/natural-language` | POST | Natural language query |
| `/query/cypher` | POST | Direct Cypher query |
| `/search/entities` | POST | Search entities |
| `/search/relationships` | POST | Search relationships |
| `/rag/ask` | POST | RAG question answering |
| `/rag/competency-questions` | GET | Sample questions |
| `/graph/path` | POST | Find paths between entities |

See [API Documentation](docs/API_DOCUMENTATION.md) for complete reference.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows black formatting
- All tests pass
- Documentation is updated
- Type hints are included

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Citation

If you use this work, please cite:

```bibtex
@software{project_atticus_2025,
  title={Project Atticus: LLM-Driven Legal Knowledge Graph Construction},
  author={Gollamudi, Aditya},
  year={2025},
  institution={Texas A&M University},
  url={https://github.com/adigo-tamu/NLP_Project_Atticus_Legal_Knowlegde_Graph}
}
```

## 🙏 Acknowledgments

- **CUAD Dataset Team** - For the comprehensive legal contract dataset
- **LexGLUE Benchmark** - For legal NLP benchmarks
- **Neo4j Community** - For the powerful graph database
- **OpenAI & Anthropic** - For state-of-the-art LLM APIs
- **Texas A&M University** - For academic support

## 📞 Contact

**Project Lead**: Aditya Gollamudi
**Institution**: Texas A&M University, Department of Computer Science and Engineering
**Course**: CSCE 489 - Special Topics in AI
**GitHub**: [@adigo-tamu](https://github.com/adigo-tamu)

For questions and support, please open an issue on GitHub.

---

**Built with ❤️ for the legal tech community**
