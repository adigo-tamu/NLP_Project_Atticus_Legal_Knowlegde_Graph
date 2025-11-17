"""
Configuration management system for Project Atticus.

This module provides a centralized configuration system using Pydantic Settings
with support for YAML files and environment variables.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM configuration settings."""

    primary_model: str = "gpt-4o"
    fallback_model: str = "gpt-4"
    claude_model: str = "claude-3-5-sonnet-20241022"

    temperature: float = 0.1
    max_tokens: int = 4096
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    rate_limit: int = 60
    max_retries: int = 3
    retry_delay: int = 2
    timeout: int = 120

    use_cache: bool = True
    batch_processing: bool = True


class Neo4jConfig(BaseSettings):
    """Neo4j database configuration."""

    uri: str = Field(default="bolt://localhost:7687")
    database: str = "legal_kg"
    user: str = "neo4j"
    password: str = Field(default="")

    max_connection_lifetime: int = 3600
    max_connection_pool_size: int = 50
    connection_acquisition_timeout: int = 60

    create_constraints: bool = True
    create_indexes: bool = True
    enable_apoc: bool = True


class VectorDBConfig(BaseSettings):
    """Vector database configuration."""

    type: str = "chromadb"
    persist_directory: str = "./data/chroma"
    collection_name: str = "legal_embeddings"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    distance_metric: str = "cosine"

    top_k: int = 10
    score_threshold: float = 0.7


class ProcessingConfig(BaseSettings):
    """Document processing configuration."""

    chunk_size: int = 500
    chunk_overlap: int = 100
    chunking_strategy: str = "hierarchical"

    preserve_structure: bool = True
    extract_metadata: bool = True
    detect_language: bool = True

    lowercase: bool = False
    remove_special_chars: bool = False
    normalize_whitespace: bool = True

    batch_size: int = 10
    max_concurrent_docs: int = 5
    processing_timeout: int = 300

    supported_formats: List[str] = ["pdf", "docx", "doc", "txt", "json"]


class EntityExtractionConfig(BaseSettings):
    """Entity extraction configuration."""

    entity_types: List[str] = [
        "Legal_Party",
        "Legal_Concept",
        "Obligation",
        "Right",
        "Jurisdiction",
        "Temporal_Entity",
        "Financial_Term",
        "Clause_Reference",
    ]

    confidence_threshold: float = 0.7
    max_entities_per_chunk: int = 50
    enable_validation: bool = True
    enable_deduplication: bool = True

    extract_attributes: bool = True
    extract_context: bool = True
    context_window: int = 2

    use_coreference: bool = True
    merge_threshold: float = 0.85


class RelationshipExtractionConfig(BaseSettings):
    """Relationship extraction configuration."""

    relationship_types: List[str] = [
        "REFERENCES",
        "OBLIGATES",
        "GRANTS_RIGHT",
        "GOVERNS",
        "DEFINES",
        "MODIFIES",
        "DEPENDS_ON",
        "CONTRADICTS",
        "TEMPORALLY_PRECEDES",
        "FINANCIALLY_RELATES",
    ]

    confidence_threshold: float = 0.65
    max_relationships_per_chunk: int = 100
    enable_validation: bool = True

    enable_cot: bool = True
    cot_steps: int = 3
    extract_reasoning: bool = True

    enable_coreference: bool = True
    coreference_window: int = 5

    extract_evidence: bool = True
    extract_temporal: bool = True
    bidirectional_validation: bool = True


class GraphConstructionConfig(BaseSettings):
    """Knowledge graph construction configuration."""

    layers: List[str] = ["semantic", "structural", "metadata"]

    enable_disambiguation: bool = True
    similarity_threshold: float = 0.85
    disambiguation_method: str = "embedding"

    enable_validation: bool = True
    check_consistency: bool = True
    detect_cycles: bool = True
    detect_orphans: bool = True

    merge_duplicate_nodes: bool = True
    merge_duplicate_edges: bool = True
    prune_low_confidence: bool = False
    min_confidence: float = 0.5

    index_properties: List[str] = ["id", "text", "type", "document_id"]

    track_provenance: bool = True
    track_confidence: bool = True
    track_timestamps: bool = True


class RAGConfig(BaseSettings):
    """RAG system configuration."""

    retrieval_strategy: str = "hybrid"
    graph_traversal_depth: int = 3
    max_paths: int = 10

    vector_top_k: int = 5
    rerank: bool = True
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    fusion_method: str = "reciprocal_rank"
    graph_weight: float = 0.6
    vector_weight: float = 0.4

    max_context_length: int = 4000
    include_sources: bool = True
    include_reasoning: bool = True
    generate_explanations: bool = True


class EvaluationConfig(BaseSettings):
    """Evaluation configuration."""

    entity_f1_target: float = 0.85
    relationship_f1_target: float = 0.70
    graph_f1_target: float = 0.40
    query_accuracy_target: float = 0.80

    train_split: float = 0.6
    val_split: float = 0.2
    test_split: float = 0.2

    baselines: List[str] = ["rule_based", "fine_tuned_bert"]


class APIConfig(BaseSettings):
    """API server configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = True

    enable_cors: bool = True
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    enable_auth: bool = False
    jwt_expiration: int = 1800

    default_page_size: int = 20
    max_page_size: int = 100


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "detailed"

    file_enabled: bool = True
    file_path: str = "./logs/atticus.log"
    rotation: str = "500 MB"
    retention: str = "10 days"

    console_enabled: bool = True
    console_colors: bool = True

    log_api_requests: bool = True
    log_llm_calls: bool = True
    log_db_queries: bool = False
    log_processing: bool = True


class Config(BaseSettings):
    """Main configuration class for Project Atticus."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Application Settings
    app_name: str = Field(default="project-atticus", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=True, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # API Keys
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Neo4j
    neo4j_uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="", validation_alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="legal_kg", validation_alias="NEO4J_DATABASE")

    # Data Paths
    raw_data_dir: str = Field(default="./data/raw", validation_alias="RAW_DATA_DIR")
    processed_data_dir: str = Field(default="./data/processed", validation_alias="PROCESSED_DATA_DIR")
    graph_export_dir: str = Field(default="./data/graphs", validation_alias="GRAPH_EXPORT_DIR")
    models_dir: str = Field(default="./models", validation_alias="MODELS_DIR")

    # Sub-configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    entity_extraction: EntityExtractionConfig = Field(default_factory=EntityExtractionConfig)
    relationship_extraction: RelationshipExtractionConfig = Field(default_factory=RelationshipExtractionConfig)
    graph_construction: GraphConstructionConfig = Field(default_factory=GraphConstructionConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, config_path: str = "config/config.yaml") -> "Config":
        """Load configuration from YAML file."""
        config_file = Path(config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file, "r") as f:
            yaml_config = yaml.safe_load(f)

        # Create config instance
        config = cls()

        # Update with YAML values
        if yaml_config:
            if "llm" in yaml_config:
                config.llm = LLMConfig(**yaml_config["llm"])
            if "neo4j" in yaml_config:
                config.neo4j = Neo4jConfig(**yaml_config["neo4j"])
            if "vector_db" in yaml_config:
                config.vector_db = VectorDBConfig(**yaml_config["vector_db"])
            if "processing" in yaml_config:
                config.processing = ProcessingConfig(**yaml_config["processing"])
            if "entity_extraction" in yaml_config:
                config.entity_extraction = EntityExtractionConfig(**yaml_config["entity_extraction"])
            if "relationship_extraction" in yaml_config:
                config.relationship_extraction = RelationshipExtractionConfig(
                    **yaml_config["relationship_extraction"]
                )
            if "graph_construction" in yaml_config:
                config.graph_construction = GraphConstructionConfig(**yaml_config["graph_construction"])
            if "rag" in yaml_config:
                config.rag = RAGConfig(**yaml_config["rag"])
            if "evaluation" in yaml_config:
                config.evaluation = EvaluationConfig(**yaml_config["evaluation"])
            if "api" in yaml_config:
                config.api = APIConfig(**yaml_config["api"])
            if "logging" in yaml_config:
                config.logging = LoggingConfig(**yaml_config["logging"])

        return config

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.raw_data_dir,
            self.processed_data_dir,
            self.graph_export_dir,
            self.models_dir,
            "logs",
            self.vector_db.persist_directory,
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def validate_api_keys(self) -> bool:
        """Validate that required API keys are present."""
        if not self.openai_api_key and not self.anthropic_api_key:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "debug": self.debug,
            "llm": self.llm.model_dump(),
            "neo4j": self.neo4j.model_dump(),
            "vector_db": self.vector_db.model_dump(),
            "processing": self.processing.model_dump(),
            "entity_extraction": self.entity_extraction.model_dump(),
            "relationship_extraction": self.relationship_extraction.model_dump(),
            "graph_construction": self.graph_construction.model_dump(),
            "rag": self.rag.model_dump(),
            "evaluation": self.evaluation.model_dump(),
            "api": self.api.model_dump(),
            "logging": self.logging.model_dump(),
        }


@lru_cache
def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    Get cached configuration instance.

    Args:
        config_path: Path to configuration YAML file

    Returns:
        Config instance
    """
    config = Config.from_yaml(config_path)
    config.ensure_directories()
    return config
