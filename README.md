# Project Atticus - Legal Knowledge Graph Construction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An LLM-driven system that automatically constructs knowledge graphs from legal document collections using the Extract-Define-Canonicalize (EDC) framework.

## Overview

Project Atticus transforms unstructured legal text into structured, queryable knowledge representations. The system leverages state-of-the-art LLMs (GPT-4o, Claude 3.5 Sonnet) combined with Neo4j graph databases to extract entities, relationships, and construct multi-layered legal knowledge graphs.

### Key Features

- **Automated Entity Extraction**: LLM-based NER for 8 legal entity types (parties, obligations, rights, jurisdictions, etc.)
- **Relationship Extraction**: Chain-of-thought reasoning for 10 relationship types with coreference resolution
- **Multi-Layer Knowledge Graph**: Semantic, structural, and metadata layers in Neo4j
- **RAG Integration**: Hybrid retrieval combining graph traversal and vector similarity
- **Competency Question Answering**: Natural language queries over legal documents
- **Comprehensive Evaluation**: Entity F1, Relationship F1, and Graph-level F1 metrics

## Architecture

```
Legal Documents (PDF/DOCX/TXT)
           ↓
Document Processing Layer (Parser, Chunker)
           ↓
Stage 1: Entity Extraction (LLM-based NER)
           ↓
Stage 2: Relationship Extraction (Prompt Engineering + CoT)
           ↓
Stage 3: Knowledge Graph Construction (Neo4j Multi-layer)
           ↓
Query & RAG Layer (Graph Queries + Vector Search)
```

## Project Structure

```
├── src/atticus/              # Main source code
│   ├── core/                 # Core utilities and base classes
│   ├── extraction/           # Entity and relationship extraction
│   ├── graph/                # Knowledge graph construction
│   ├── api/                  # REST API endpoints
│   ├── rag/                  # RAG integration
│   ├── evaluation/           # Evaluation metrics and baselines
│   └── utils/                # Utility functions
├── data/                     # Data directory
│   ├── raw/                  # Raw legal documents
│   ├── processed/            # Processed data
│   └── graphs/               # Exported graphs
├── config/                   # Configuration files
├── prompts/                  # LLM prompt templates
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
├── notebooks/                # Jupyter notebooks
└── docs/                     # Documentation
```

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j 5.x (Community or Enterprise)
- OpenAI API key
- Anthropic API key (optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/project-atticus.git
cd project-atticus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `config/config.yaml` to configure:
- LLM models and parameters
- Neo4j connection settings
- Processing parameters
- Evaluation targets

### Usage

```python
from atticus.core.pipeline import LegalKGPipeline

# Initialize pipeline
pipeline = LegalKGPipeline(config_path="config/config.yaml")

# Process a legal document
result = pipeline.process_document("path/to/contract.pdf")

# Query the knowledge graph
answer = pipeline.query("What are the payment obligations for Party A?")
```

## Development Roadmap

- [x] Phase 1: Infrastructure Setup
- [ ] Phase 2: Entity Extraction Module
- [ ] Phase 3: Relationship Extraction Module
- [ ] Phase 4: Knowledge Graph Construction
- [ ] Phase 5: Query Interface and RAG Integration
- [ ] Phase 6: Evaluation and Optimization
- [ ] Phase 7: Documentation and Release

## Performance Targets

- **Entity Extraction F1**: ≥ 0.85
- **Relationship Extraction F1**: ≥ 0.70
- **Graph-level F1**: ≥ 0.40
- **Processing Speed**: < 2 minutes per document (20 pages)
- **Query Response**: < 5 seconds

## Dataset

Primary dataset: **CUAD (Contract Understanding Atticus Dataset)**
- 510 commercial legal contracts
- 13,000+ expert annotations
- 41 distinct clause types
- Source: https://www.atticusprojectai.org/cuad

## Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Citation

If you use this work, please cite:

```bibtex
@software{project_atticus_2025,
  title={Project Atticus: LLM-Driven Legal Knowledge Graph Construction},
  author={Gollamudi, Aditya},
  year={2025},
  institution={Texas A&M University}
}
```

## Acknowledgments

- CUAD Dataset Team
- LexGLUE Benchmark contributors
- Neo4j Community
- OpenAI and Anthropic teams

## Contact

**Project Lead**: Aditya Gollamudi
**Institution**: Texas A&M Engineering
**Course**: CSCE 489

For questions and support, please open an issue on GitHub.
