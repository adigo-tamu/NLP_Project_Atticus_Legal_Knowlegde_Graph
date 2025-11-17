"""
FastAPI application for Legal Knowledge Graph API.

Provides REST endpoints for querying the knowledge graph using:
- Natural language queries
- Direct Cypher queries
- Entity and relationship search
- RAG-based question answering
- Graph analytics
"""

import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from atticus.api.models import (
    CypherQueryRequest,
    EntitySearchRequest,
    EntitySearchResponse,
    ErrorResponse,
    GraphPathRequest,
    GraphPathResponse,
    GraphStatsResponse,
    HealthResponse,
    NaturalLanguageQueryRequest,
    QueryResponse,
    QueryType,
    RAGQueryRequest,
    RAGResponse,
    RelationshipSearchRequest,
    RelationshipSearchResponse,
)
from atticus.api.nl_to_cypher import NLToCypherTranslator
from atticus.api.rag import GraphRAG
from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.graph.graph_analytics import GraphAnalytics
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)

# ============================================================
# Initialize FastAPI App
# ============================================================

app = FastAPI(
    title="Project Atticus - Legal Knowledge Graph API",
    description="""
    REST API for querying legal knowledge graphs constructed by Project Atticus.

    ## Features

    - **Natural Language Queries**: Ask questions in plain English
    - **Cypher Queries**: Execute direct Neo4j Cypher queries
    - **Entity Search**: Search entities by text, type, confidence
    - **Relationship Search**: Search relationships between entities
    - **RAG Q&A**: Question answering with retrieval-augmented generation
    - **Graph Analytics**: Get statistics and metrics
    - **Path Finding**: Find paths between entities

    ## Authentication

    Currently no authentication required (development mode).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Global Components
# ============================================================

config = get_config()
db: Optional[Neo4jManager] = None
nl_translator: Optional[NLToCypherTranslator] = None
rag_system: Optional[GraphRAG] = None
analytics: Optional[GraphAnalytics] = None


# ============================================================
# Startup & Shutdown
# ============================================================


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global db, nl_translator, rag_system, analytics

    logger.info("Starting API server...")

    try:
        # Initialize Neo4j connection
        db = Neo4jManager()
        logger.info("✓ Neo4j connected")

        # Initialize NL to Cypher translator
        nl_translator = NLToCypherTranslator(neo4j_manager=db)
        logger.info("✓ NL to Cypher translator initialized")

        # Initialize RAG system
        rag_system = GraphRAG(neo4j_manager=db)
        logger.info("✓ RAG system initialized")

        # Initialize analytics
        analytics = GraphAnalytics(neo4j_manager=db)
        logger.info("✓ Analytics initialized")

        logger.info("✓ API server started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global db

    logger.info("Shutting down API server...")

    if db:
        db.close()
        logger.info("✓ Neo4j connection closed")

    logger.info("✓ API server shutdown complete")


# ============================================================
# Health & Status Endpoints
# ============================================================


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
)
async def health_check():
    """Check API health and component status."""

    neo4j_connected = False
    llm_available = False

    try:
        # Check Neo4j
        if db:
            db.execute_query("RETURN 1")
            neo4j_connected = True

        # Check LLM (basic check)
        llm_available = config.validate_api_keys()

    except Exception as e:
        logger.error(f"Health check failed: {e}")

    status_value = "healthy" if (neo4j_connected and llm_available) else "degraded"

    return HealthResponse(
        status=status_value,
        neo4j_connected=neo4j_connected,
        llm_available=llm_available,
        version="1.0.0",
    )


@app.get(
    "/stats",
    response_model=GraphStatsResponse,
    tags=["Analytics"],
    summary="Get graph statistics",
)
async def get_graph_stats(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
):
    """Get comprehensive graph statistics."""

    try:
        stats = analytics.get_graph_statistics(document_id=document_id)

        return GraphStatsResponse(
            total_nodes=stats["basic"]["total_nodes"],
            total_relationships=stats["basic"]["total_relationships"],
            node_types={
                node_type: node_stats["count"]
                for node_type, node_stats in stats["nodes"].items()
            },
            relationship_types={
                rel_type: rel_stats["count"]
                for rel_type, rel_stats in stats["relationships"].items()
            },
            avg_degree=stats["basic"]["avg_degree"],
            density=stats["metrics"]["density"],
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Query Endpoints
# ============================================================


@app.post(
    "/query/natural-language",
    response_model=QueryResponse,
    tags=["Queries"],
    summary="Natural language query",
)
async def natural_language_query(request: NaturalLanguageQueryRequest):
    """
    Query the graph using natural language.

    The query is translated to Cypher using an LLM and executed against the graph.

    Example queries:
    - "What obligations does TechCorp have?"
    - "Find all relationships between ABC Corp and payment terms"
    - "Show me entities with high confidence scores"
    """

    start_time = time.time()

    try:
        results, cypher_query, reasoning = nl_translator.translate_and_execute(
            natural_language_query=request.query,
            document_id=request.document_id,
            include_reasoning=request.include_reasoning,
        )

        # Limit results
        results = results[: request.limit]

        execution_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            query=request.query,
            query_type=QueryType.NATURAL_LANGUAGE,
            results=results,
            count=len(results),
            execution_time_ms=execution_time_ms,
            cypher_query=cypher_query,
            reasoning=reasoning if request.include_reasoning else None,
        )

    except Exception as e:
        logger.error(f"Natural language query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/query/cypher",
    response_model=QueryResponse,
    tags=["Queries"],
    summary="Direct Cypher query",
)
async def cypher_query(request: CypherQueryRequest):
    """
    Execute a direct Cypher query against the graph.

    **Warning**: This endpoint allows arbitrary Cypher queries.
    In production, this should be restricted to read-only queries.

    Example:
    ```cypher
    MATCH (n:Legal_Party)
    RETURN n.text, n.confidence
    LIMIT 10
    ```
    """

    start_time = time.time()

    try:
        # Execute query
        results = nl_translator.execute_query(
            cypher=request.query,
            parameters=request.parameters,
        )

        execution_time_ms = (time.time() - start_time) * 1000

        return QueryResponse(
            query=request.query,
            query_type=QueryType.CYPHER,
            results=results,
            count=len(results),
            execution_time_ms=execution_time_ms,
            cypher_query=request.query,
        )

    except Exception as e:
        logger.error(f"Cypher query failed: {e}")
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


# ============================================================
# Search Endpoints
# ============================================================


@app.post(
    "/search/entities",
    response_model=EntitySearchResponse,
    tags=["Search"],
    summary="Search entities",
)
async def search_entities(request: EntitySearchRequest):
    """
    Search for entities in the graph.

    Supports filtering by:
    - Text (partial match, case-insensitive)
    - Entity type
    - Document ID
    - Minimum confidence score
    """

    start_time = time.time()

    try:
        # Build Cypher query
        conditions = []
        params = {}

        if request.text:
            conditions.append("toLower(n.text) CONTAINS toLower($text)")
            params["text"] = request.text

        if request.entity_type:
            conditions.append(f"n:{request.entity_type.value}")

        if request.document_id:
            conditions.append("n.document_id = $document_id")
            params["document_id"] = request.document_id

        conditions.append("n.confidence >= $min_confidence")
        params["min_confidence"] = request.min_confidence

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
        MATCH (n)
        WHERE {where_clause}
        RETURN n.id as id, n.text as text, n.type as type,
               n.confidence as confidence, n.document_id as document_id,
               n.context as context, labels(n) as labels
        ORDER BY n.confidence DESC
        LIMIT $limit
        """
        params["limit"] = request.limit

        results = db.execute_query(query, params)

        # Convert to response model
        from atticus.api.models import EntityResponse

        entities = [
            EntityResponse(
                id=record["id"],
                text=record["text"],
                type=record["type"],
                confidence=record["confidence"],
                document_id=record["document_id"],
                context=record.get("context"),
            )
            for record in results
        ]

        execution_time_ms = (time.time() - start_time) * 1000

        return EntitySearchResponse(
            entities=entities,
            count=len(entities),
            execution_time_ms=execution_time_ms,
        )

    except Exception as e:
        logger.error(f"Entity search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/search/relationships",
    response_model=RelationshipSearchResponse,
    tags=["Search"],
    summary="Search relationships",
)
async def search_relationships(request: RelationshipSearchRequest):
    """
    Search for relationships in the graph.

    Supports filtering by:
    - Source entity ID
    - Target entity ID
    - Relationship type
    - Document ID
    - Minimum confidence score
    """

    start_time = time.time()

    try:
        # Build Cypher query
        conditions = []
        params = {}

        if request.source_id:
            conditions.append("source.id = $source_id")
            params["source_id"] = request.source_id

        if request.target_id:
            conditions.append("target.id = $target_id")
            params["target_id"] = request.target_id

        if request.relationship_type:
            rel_pattern = f"[r:{request.relationship_type.value}]"
        else:
            rel_pattern = "[r]"

        if request.document_id:
            conditions.append("r.document_id = $document_id")
            params["document_id"] = request.document_id

        conditions.append("r.confidence >= $min_confidence")
        params["min_confidence"] = request.min_confidence

        where_clause = " AND ".join(conditions) if conditions else "true"

        query = f"""
        MATCH (source)-{rel_pattern}->(target)
        WHERE {where_clause}
        RETURN r.id as rel_id, type(r) as rel_type, r.confidence as confidence,
               r.evidence as evidence, r.document_id as document_id,
               source.id as source_id, source.text as source_text,
               source.type as source_type, source.confidence as source_confidence,
               target.id as target_id, target.text as target_text,
               target.type as target_type, target.confidence as target_confidence
        ORDER BY r.confidence DESC
        LIMIT $limit
        """
        params["limit"] = request.limit

        results = db.execute_query(query, params)

        # Convert to response model
        from atticus.api.models import EntityResponse, RelationshipResponse

        relationships = []
        for record in results:
            source = EntityResponse(
                id=record["source_id"],
                text=record["source_text"],
                type=record["source_type"],
                confidence=record["source_confidence"],
                document_id=record["document_id"],
            )
            target = EntityResponse(
                id=record["target_id"],
                text=record["target_text"],
                type=record["target_type"],
                confidence=record["target_confidence"],
                document_id=record["document_id"],
            )
            relationships.append(
                RelationshipResponse(
                    id=record["rel_id"],
                    source=source,
                    target=target,
                    type=record["rel_type"],
                    confidence=record["confidence"],
                    evidence=record.get("evidence"),
                    document_id=record["document_id"],
                )
            )

        execution_time_ms = (time.time() - start_time) * 1000

        return RelationshipSearchResponse(
            relationships=relationships,
            count=len(relationships),
            execution_time_ms=execution_time_ms,
        )

    except Exception as e:
        logger.error(f"Relationship search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# RAG Endpoints
# ============================================================


@app.post(
    "/rag/ask",
    response_model=RAGResponse,
    tags=["RAG"],
    summary="Answer question using RAG",
)
async def rag_ask(request: RAGQueryRequest):
    """
    Answer a question using Retrieval-Augmented Generation (RAG).

    The system:
    1. Retrieves relevant entities and relationships from the graph
    2. Uses an LLM to generate an answer based on the retrieved context
    3. Returns the answer with confidence score and sources

    Example questions:
    - "What are the main obligations in this contract?"
    - "Who are the parties involved?"
    - "What are the payment terms?"
    """

    start_time = time.time()

    try:
        answer_dict = rag_system.answer_question(
            question=request.question,
            document_id=request.document_id,
            max_context_entities=request.max_context_entities,
            max_context_relationships=request.max_context_relationships,
            include_sources=request.include_sources,
        )

        execution_time_ms = (time.time() - start_time) * 1000

        # Convert sources to EntityResponse
        from atticus.api.models import EntityResponse

        sources = None
        if request.include_sources and answer_dict.get("sources"):
            sources = [
                EntityResponse(
                    id=source["id"],
                    text=source["text"],
                    type=source.get("type", ""),
                    confidence=source["confidence"],
                    document_id=source["document_id"],
                    context=source.get("context"),
                )
                for source in answer_dict["sources"]
            ]

        return RAGResponse(
            question=request.question,
            answer=answer_dict["answer"],
            confidence=answer_dict["confidence"],
            sources=sources,
            context_used=answer_dict.get("context_used"),
            execution_time_ms=execution_time_ms,
        )

    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/rag/competency-questions",
    tags=["RAG"],
    summary="Get sample competency questions",
)
async def get_competency_questions():
    """Get a list of sample competency questions for legal contracts."""

    questions = rag_system.get_sample_competency_questions()

    return {
        "questions": questions,
        "count": len(questions),
    }


# ============================================================
# Graph Navigation Endpoints
# ============================================================


@app.post(
    "/graph/path",
    response_model=GraphPathResponse,
    tags=["Graph"],
    summary="Find paths between entities",
)
async def find_graph_path(request: GraphPathRequest):
    """
    Find paths between two entities in the graph.

    Uses shortest path algorithm to find connections up to max_depth.
    """

    start_time = time.time()

    try:
        # Build relationship type filter
        if request.relationship_types:
            rel_types = "|".join([rt.value for rt in request.relationship_types])
            rel_pattern = f"[r:{rel_types}*1..{request.max_depth}]"
        else:
            rel_pattern = f"[r*1..{request.max_depth}]"

        query = f"""
        MATCH path = (source {{id: $source_id}})-{rel_pattern}-(target {{id: $target_id}})
        WITH path, length(path) as path_length
        ORDER BY path_length
        LIMIT 10
        RETURN path, path_length
        """

        results = db.execute_query(
            query,
            {"source_id": request.source_id, "target_id": request.target_id},
        )

        # Convert paths to response format
        paths = []
        for record in results:
            path_data = []
            # Parse path (simplified - would need proper Neo4j path parsing)
            paths.append(path_data)

        # Get source and target entities
        source_query = "MATCH (n {id: $id}) RETURN n"
        target_query = "MATCH (n {id: $id}) RETURN n"

        source_result = db.execute_query(source_query, {"id": request.source_id})
        target_result = db.execute_query(target_query, {"id": request.target_id})

        from atticus.api.models import EntityResponse

        source_node = source_result[0]["n"] if source_result else None
        target_node = target_result[0]["n"] if target_result else None

        if not source_node or not target_node:
            raise HTTPException(status_code=404, detail="Source or target entity not found")

        source = EntityResponse(
            id=source_node["id"],
            text=source_node["text"],
            type=source_node.get("type", ""),
            confidence=source_node["confidence"],
            document_id=source_node["document_id"],
        )

        target = EntityResponse(
            id=target_node["id"],
            text=target_node["text"],
            type=target_node.get("type", ""),
            confidence=target_node["confidence"],
            document_id=target_node["document_id"],
        )

        execution_time_ms = (time.time() - start_time) * 1000

        return GraphPathResponse(
            source=source,
            target=target,
            paths=paths,
            count=len(paths),
            execution_time_ms=execution_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Path finding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Error Handlers
# ============================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ============================================================
# Root Endpoint
# ============================================================


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "name": "Project Atticus - Legal Knowledge Graph API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
