"""
API models for REST endpoints.

Pydantic models for request/response validation.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================


class QueryType(str, Enum):
    """Supported query types."""

    NATURAL_LANGUAGE = "natural_language"
    CYPHER = "cypher"
    ENTITY_SEARCH = "entity_search"
    RELATIONSHIP_SEARCH = "relationship_search"


class EntityTypeFilter(str, Enum):
    """Entity type filters."""

    LEGAL_PARTY = "Legal_Party"
    LEGAL_CONCEPT = "Legal_Concept"
    OBLIGATION = "Obligation"
    RIGHT = "Right"
    JURISDICTION = "Jurisdiction"
    TEMPORAL_ENTITY = "Temporal_Entity"
    FINANCIAL_TERM = "Financial_Term"
    CLAUSE_REFERENCE = "Clause_Reference"


class RelationshipTypeFilter(str, Enum):
    """Relationship type filters."""

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


# ============================================================
# Request Models
# ============================================================


class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language queries."""

    query: str = Field(..., description="Natural language query", min_length=1)
    document_id: Optional[str] = Field(None, description="Filter by document ID")
    limit: int = Field(10, description="Maximum results to return", ge=1, le=100)
    include_reasoning: bool = Field(
        False, description="Include LLM reasoning in response"
    )


class CypherQueryRequest(BaseModel):
    """Request model for direct Cypher queries."""

    query: str = Field(..., description="Cypher query", min_length=1)
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Query parameters"
    )


class EntitySearchRequest(BaseModel):
    """Request model for entity search."""

    text: Optional[str] = Field(None, description="Text search term")
    entity_type: Optional[EntityTypeFilter] = Field(
        None, description="Filter by entity type"
    )
    document_id: Optional[str] = Field(None, description="Filter by document ID")
    min_confidence: float = Field(
        0.0, description="Minimum confidence score", ge=0.0, le=1.0
    )
    limit: int = Field(10, description="Maximum results", ge=1, le=100)


class RelationshipSearchRequest(BaseModel):
    """Request model for relationship search."""

    source_id: Optional[str] = Field(None, description="Source entity ID")
    target_id: Optional[str] = Field(None, description="Target entity ID")
    relationship_type: Optional[RelationshipTypeFilter] = Field(
        None, description="Filter by relationship type"
    )
    document_id: Optional[str] = Field(None, description="Filter by document ID")
    min_confidence: float = Field(
        0.0, description="Minimum confidence score", ge=0.0, le=1.0
    )
    limit: int = Field(10, description="Maximum results", ge=1, le=100)


class RAGQueryRequest(BaseModel):
    """Request model for RAG-based question answering."""

    question: str = Field(..., description="Question to answer", min_length=1)
    document_id: Optional[str] = Field(None, description="Filter by document ID")
    max_context_entities: int = Field(
        10, description="Max entities to retrieve for context", ge=1, le=50
    )
    max_context_relationships: int = Field(
        10, description="Max relationships to retrieve for context", ge=1, le=50
    )
    include_sources: bool = Field(
        True, description="Include source entities in response"
    )


class GraphPathRequest(BaseModel):
    """Request model for finding paths between entities."""

    source_id: str = Field(..., description="Source entity ID")
    target_id: str = Field(..., description="Target entity ID")
    max_depth: int = Field(
        3, description="Maximum path depth", ge=1, le=5
    )
    relationship_types: Optional[List[RelationshipTypeFilter]] = Field(
        None, description="Filter by relationship types"
    )


# ============================================================
# Response Models
# ============================================================


class EntityResponse(BaseModel):
    """Response model for entity data."""

    id: str
    text: str
    type: str
    confidence: float
    document_id: str
    context: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class RelationshipResponse(BaseModel):
    """Response model for relationship data."""

    id: str
    source: EntityResponse
    target: EntityResponse
    type: str
    confidence: float
    evidence: Optional[str] = None
    document_id: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    """Generic query response."""

    query: str
    query_type: QueryType
    results: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    cypher_query: Optional[str] = None
    reasoning: Optional[str] = None


class EntitySearchResponse(BaseModel):
    """Response model for entity search."""

    entities: List[EntityResponse]
    count: int
    execution_time_ms: float


class RelationshipSearchResponse(BaseModel):
    """Response model for relationship search."""

    relationships: List[RelationshipResponse]
    count: int
    execution_time_ms: float


class RAGResponse(BaseModel):
    """Response model for RAG question answering."""

    question: str
    answer: str
    confidence: float
    sources: Optional[List[EntityResponse]] = None
    context_used: Optional[Dict[str, Any]] = None
    execution_time_ms: float


class GraphPathResponse(BaseModel):
    """Response model for graph path queries."""

    source: EntityResponse
    target: EntityResponse
    paths: List[List[Dict[str, Any]]]
    count: int
    execution_time_ms: float


class GraphStatsResponse(BaseModel):
    """Response model for graph statistics."""

    total_nodes: int
    total_relationships: int
    node_types: Dict[str, int]
    relationship_types: Dict[str, int]
    avg_degree: float
    density: float
    document_count: Optional[int] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    neo4j_connected: bool
    llm_available: bool
    version: str


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: Optional[str] = None
    query: Optional[str] = None
