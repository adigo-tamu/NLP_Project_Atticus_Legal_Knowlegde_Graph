"""
Core data models and schemas for Project Atticus.

This module defines Pydantic models for entities, relationships, documents,
and other core data structures used throughout the system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """Legal entity types."""

    LEGAL_PARTY = "Legal_Party"
    LEGAL_CONCEPT = "Legal_Concept"
    OBLIGATION = "Obligation"
    RIGHT = "Right"
    JURISDICTION = "Jurisdiction"
    TEMPORAL_ENTITY = "Temporal_Entity"
    FINANCIAL_TERM = "Financial_Term"
    CLAUSE_REFERENCE = "Clause_Reference"


class RelationshipType(str, Enum):
    """Relationship types between entities."""

    REFERENCES = "REFERENCES"
    OBLIGATES = "OBLIGATES"
    GRANTS_RIGHT = "GRANTS_RIGHT"
    GOVERNS = "GOVERNS"
    DEFINES = "DEFINES"
    MODIFIES = "MODIFIES"
    DEPENDS_ON = "DEPENDS_ON"
    CONTRADICTS = "CONTRADICTS"
    TEMPORALLY_PRECEDES = "TEMPORALLY_PRECEDES"
    FINANCIALLY_RELATES = "FINANCIALLY_RELATES"


class DocumentType(str, Enum):
    """Legal document types."""

    CONTRACT = "contract"
    AGREEMENT = "agreement"
    LICENSE = "license"
    AMENDMENT = "amendment"
    ADDENDUM = "addendum"
    POLICY = "policy"
    STATUTE = "statute"
    REGULATION = "regulation"
    CASE_LAW = "case_law"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    GRAPH_CONSTRUCTION = "graph_construction"
    COMPLETED = "completed"
    FAILED = "failed"


class Position(BaseModel):
    """Text position in document."""

    start: int = Field(..., description="Start character position")
    end: int = Field(..., description="End character position")
    start_line: Optional[int] = Field(None, description="Start line number")
    end_line: Optional[int] = Field(None, description="End line number")


class Entity(BaseModel):
    """Entity extracted from legal text."""

    id: str = Field(..., description="Unique entity identifier")
    text: str = Field(..., description="Entity text as it appears in document")
    type: EntityType = Field(..., description="Entity type classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")

    # Context
    context: Optional[str] = Field(None, description="Surrounding context")
    position: Optional[Position] = Field(None, description="Position in document")

    # Metadata
    document_id: str = Field(..., description="Source document ID")
    chunk_id: Optional[str] = Field(None, description="Source chunk ID")
    section: Optional[str] = Field(None, description="Document section")

    # Attributes
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional entity attributes")
    aliases: List[str] = Field(default_factory=list, description="Entity aliases or mentions")

    # Provenance
    extraction_method: str = Field(default="llm", description="Extraction method used")
    model: Optional[str] = Field(None, description="Model used for extraction")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")


class Relationship(BaseModel):
    """Relationship between entities."""

    id: str = Field(..., description="Unique relationship identifier")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: RelationshipType = Field(..., description="Relationship type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")

    # Evidence
    evidence: Optional[str] = Field(None, description="Text supporting this relationship")
    reasoning: Optional[str] = Field(None, description="Chain-of-thought reasoning")

    # Context
    document_id: str = Field(..., description="Source document ID")
    chunk_id: Optional[str] = Field(None, description="Source chunk ID")
    position: Optional[Position] = Field(None, description="Position in document")

    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional relationship properties")
    temporal_info: Optional[Dict[str, Any]] = Field(None, description="Temporal information")

    # Provenance
    extraction_method: str = Field(default="llm", description="Extraction method used")
    model: Optional[str] = Field(None, description="Model used for extraction")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")


class DocumentChunk(BaseModel):
    """Chunk of a legal document."""

    id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    text: str = Field(..., description="Chunk text content")

    # Position
    position: Position = Field(..., description="Position in document")
    chunk_index: int = Field(..., description="Index of chunk in document")

    # Hierarchy
    level: int = Field(default=0, description="Hierarchical level (0=document, 1=section, 2=clause)")
    parent_chunk_id: Optional[str] = Field(None, description="Parent chunk ID")
    section_title: Optional[str] = Field(None, description="Section title if applicable")

    # Metadata
    token_count: int = Field(..., description="Number of tokens in chunk")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Document(BaseModel):
    """Legal document."""

    id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Full document content")

    # Classification
    document_type: DocumentType = Field(default=DocumentType.OTHER, description="Document type")
    language: str = Field(default="en", description="Document language")

    # Metadata
    file_path: Optional[str] = Field(None, description="Source file path")
    file_format: Optional[str] = Field(None, description="Source file format (pdf, docx, etc.)")
    date: Optional[datetime] = Field(None, description="Document date")
    parties: List[str] = Field(default_factory=list, description="Document parties")
    jurisdiction: Optional[str] = Field(None, description="Governing jurisdiction")

    # Structure
    sections: List[str] = Field(default_factory=list, description="Document sections")
    page_count: Optional[int] = Field(None, description="Number of pages")

    # Processing
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING, description="Processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class GraphNode(BaseModel):
    """Knowledge graph node."""

    id: str = Field(..., description="Node ID")
    labels: List[str] = Field(..., description="Node labels")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")


class GraphEdge(BaseModel):
    """Knowledge graph edge."""

    id: str = Field(..., description="Edge ID")
    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")


class KnowledgeGraph(BaseModel):
    """Knowledge graph representation."""

    document_id: str = Field(..., description="Source document ID")
    nodes: List[GraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[GraphEdge] = Field(default_factory=list, description="Graph edges")

    # Statistics
    entity_count: int = Field(default=0, description="Number of entities")
    relationship_count: int = Field(default=0, description="Number of relationships")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class QueryResult(BaseModel):
    """Query result from knowledge graph or RAG system."""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Answer confidence")

    # Sources
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents/chunks")
    graph_paths: List[List[str]] = Field(default_factory=list, description="Graph traversal paths")

    # Reasoning
    reasoning: Optional[str] = Field(None, description="Reasoning explanation")
    supporting_evidence: List[str] = Field(default_factory=list, description="Supporting evidence")

    # Metadata
    retrieval_time: float = Field(..., description="Time taken for retrieval (seconds)")
    generation_time: float = Field(..., description="Time taken for generation (seconds)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EvaluationMetrics(BaseModel):
    """Evaluation metrics for system performance."""

    # Entity Metrics
    entity_precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    entity_recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    entity_f1: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Relationship Metrics
    relationship_precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    relationship_recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    relationship_f1: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Graph Metrics
    graph_precision: Optional[float] = Field(None, ge=0.0, le=1.0)
    graph_recall: Optional[float] = Field(None, ge=0.0, le=1.0)
    graph_f1: Optional[float] = Field(None, ge=0.0, le=1.0)

    # RAG Metrics
    query_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    retrieval_precision: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Performance
    avg_processing_time: Optional[float] = Field(None, description="Average processing time (seconds)")
    throughput: Optional[float] = Field(None, description="Documents processed per hour")

    # Additional metrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Additional metrics")
