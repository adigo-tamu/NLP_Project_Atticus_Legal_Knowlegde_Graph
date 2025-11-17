"""
Neo4j graph schema definitions for legal knowledge graph.

This module defines the multi-layer graph schema including node types,
relationship types, constraints, and indexes.
"""

from typing import Dict, List

# Node Type Definitions
NODE_TYPES = {
    "Entity": {
        "description": "Generic entity node",
        "properties": [
            "id",  # Unique identifier
            "text",  # Entity text
            "type",  # Entity type
            "confidence",  # Extraction confidence
            "document_id",  # Source document
            "chunk_id",  # Source chunk
            "section",  # Document section
            "position_start",  # Start position
            "position_end",  # End position
            "extraction_method",  # Extraction method
            "model",  # Model used
            "timestamp",  # Extraction timestamp
        ],
        "indexes": ["id", "text", "type", "document_id"],
        "constraints": ["id"],  # Unique constraint
    },
    "LegalParty": {
        "description": "Legal party entity (company, individual, organization)",
        "properties": [
            "id",
            "name",
            "type",  # company, individual, organization
            "role",  # plaintiff, defendant, buyer, seller, etc.
            "aliases",  # JSON array of aliases
            "confidence",
            "document_id",
        ],
        "indexes": ["id", "name", "document_id"],
        "constraints": ["id"],
    },
    "Obligation": {
        "description": "Legal obligation or duty",
        "properties": [
            "id",
            "text",
            "obligated_party",
            "obligation_type",  # payment, performance, delivery, etc.
            "deadline",  # Temporal constraint
            "confidence",
            "document_id",
            "clause_reference",
        ],
        "indexes": ["id", "document_id"],
        "constraints": ["id"],
    },
    "Right": {
        "description": "Legal right or entitlement",
        "properties": [
            "id",
            "text",
            "right_holder",
            "right_type",  # termination, modification, access, etc.
            "conditions",  # Conditions for exercise
            "confidence",
            "document_id",
            "clause_reference",
        ],
        "indexes": ["id", "document_id"],
        "constraints": ["id"],
    },
    "LegalConcept": {
        "description": "Legal term or concept",
        "properties": [
            "id",
            "term",
            "definition",
            "domain",  # contract law, tort law, etc.
            "synonyms",  # JSON array
            "confidence",
            "document_id",
        ],
        "indexes": ["id", "term"],
        "constraints": ["id"],
    },
    "Jurisdiction": {
        "description": "Legal jurisdiction",
        "properties": [
            "id",
            "name",
            "type",  # court, state, country, etc.
            "level",  # federal, state, local
            "document_id",
        ],
        "indexes": ["id", "name"],
        "constraints": ["id"],
    },
    "TemporalEntity": {
        "description": "Date, deadline, or time period",
        "properties": [
            "id",
            "text",
            "date_value",  # Normalized date
            "duration",  # For time periods
            "temporal_type",  # deadline, effective_date, term_length, etc.
            "confidence",
            "document_id",
        ],
        "indexes": ["id", "document_id"],
        "constraints": ["id"],
    },
    "FinancialTerm": {
        "description": "Financial amount or payment term",
        "properties": [
            "id",
            "text",
            "amount",  # Numeric value
            "currency",  # USD, EUR, etc.
            "payment_type",  # upfront, recurring, penalty, etc.
            "frequency",  # one-time, monthly, annual, etc.
            "confidence",
            "document_id",
        ],
        "indexes": ["id", "document_id"],
        "constraints": ["id"],
    },
    "Document": {
        "description": "Legal document",
        "properties": [
            "id",
            "title",
            "document_type",
            "date",
            "language",
            "file_path",
            "page_count",
            "status",
            "created_at",
            "updated_at",
        ],
        "indexes": ["id", "title", "document_type"],
        "constraints": ["id"],
    },
    "Clause": {
        "description": "Document clause or section",
        "properties": [
            "id",
            "text",
            "clause_number",
            "clause_type",  # payment, termination, indemnification, etc.
            "section",
            "level",  # Hierarchical level
            "document_id",
            "parent_clause_id",
        ],
        "indexes": ["id", "document_id", "clause_type"],
        "constraints": ["id"],
    },
}

# Relationship Type Definitions
RELATIONSHIP_TYPES = {
    "REFERENCES": {
        "description": "Entity references another entity",
        "properties": ["confidence", "evidence", "position", "timestamp"],
        "valid_source_types": ["Entity", "Clause"],
        "valid_target_types": ["Entity", "Clause", "LegalConcept"],
    },
    "OBLIGATES": {
        "description": "Party obligates another party to perform action",
        "properties": ["confidence", "evidence", "deadline", "conditions", "timestamp"],
        "valid_source_types": ["LegalParty", "Clause"],
        "valid_target_types": ["LegalParty", "Obligation"],
    },
    "GRANTS_RIGHT": {
        "description": "Party grants right to another party",
        "properties": ["confidence", "evidence", "conditions", "timestamp"],
        "valid_source_types": ["LegalParty", "Clause"],
        "valid_target_types": ["LegalParty", "Right"],
    },
    "GOVERNS": {
        "description": "Jurisdiction governs contract or clause",
        "properties": ["confidence", "evidence", "scope", "timestamp"],
        "valid_source_types": ["Jurisdiction"],
        "valid_target_types": ["Document", "Clause"],
    },
    "DEFINES": {
        "description": "Clause defines legal concept",
        "properties": ["confidence", "evidence", "timestamp"],
        "valid_source_types": ["Clause"],
        "valid_target_types": ["LegalConcept"],
    },
    "MODIFIES": {
        "description": "Clause modifies another clause",
        "properties": ["confidence", "evidence", "modification_type", "timestamp"],
        "valid_source_types": ["Clause"],
        "valid_target_types": ["Clause"],
    },
    "DEPENDS_ON": {
        "description": "Clause depends on another clause",
        "properties": ["confidence", "evidence", "dependency_type", "timestamp"],
        "valid_source_types": ["Clause", "Obligation"],
        "valid_target_types": ["Clause", "Obligation"],
    },
    "CONTRADICTS": {
        "description": "Potential conflict between clauses",
        "properties": ["confidence", "evidence", "conflict_type", "severity", "timestamp"],
        "valid_source_types": ["Clause"],
        "valid_target_types": ["Clause"],
    },
    "TEMPORALLY_PRECEDES": {
        "description": "Event or obligation temporally precedes another",
        "properties": ["confidence", "evidence", "time_gap", "timestamp"],
        "valid_source_types": ["TemporalEntity", "Obligation"],
        "valid_target_types": ["TemporalEntity", "Obligation"],
    },
    "FINANCIALLY_RELATES": {
        "description": "Financial relationship between entities",
        "properties": ["confidence", "evidence", "relationship_nature", "timestamp"],
        "valid_source_types": ["LegalParty", "Obligation"],
        "valid_target_types": ["FinancialTerm"],
    },
    "CONTAINS": {
        "description": "Document contains clause",
        "properties": ["order", "level"],
        "valid_source_types": ["Document", "Clause"],
        "valid_target_types": ["Clause"],
    },
    "MENTIONS": {
        "description": "Clause mentions entity",
        "properties": ["confidence", "count", "positions"],
        "valid_source_types": ["Clause"],
        "valid_target_types": ["Entity", "LegalParty", "LegalConcept"],
    },
    "HAS_PARTY": {
        "description": "Document has party",
        "properties": ["role"],
        "valid_source_types": ["Document"],
        "valid_target_types": ["LegalParty"],
    },
}


class GraphSchema:
    """Graph schema manager for creating constraints and indexes."""

    @staticmethod
    def get_constraint_queries() -> List[str]:
        """
        Get Cypher queries for creating uniqueness constraints.

        Returns:
            List of Cypher queries
        """
        queries = []

        for node_type, config in NODE_TYPES.items():
            for constraint_prop in config.get("constraints", []):
                query = f"""
                CREATE CONSTRAINT {node_type.lower()}_{constraint_prop}_unique IF NOT EXISTS
                FOR (n:{node_type})
                REQUIRE n.{constraint_prop} IS UNIQUE
                """
                queries.append(query.strip())

        return queries

    @staticmethod
    def get_index_queries() -> List[str]:
        """
        Get Cypher queries for creating indexes.

        Returns:
            List of Cypher queries
        """
        queries = []

        for node_type, config in NODE_TYPES.items():
            for index_prop in config.get("indexes", []):
                # Skip if property is already a constraint (constraints auto-create indexes)
                if index_prop in config.get("constraints", []):
                    continue

                query = f"""
                CREATE INDEX {node_type.lower()}_{index_prop}_index IF NOT EXISTS
                FOR (n:{node_type})
                ON (n.{index_prop})
                """
                queries.append(query.strip())

        return queries

    @staticmethod
    def get_fulltext_index_queries() -> List[str]:
        """
        Get Cypher queries for creating full-text search indexes.

        Returns:
            List of Cypher queries
        """
        queries = [
            """
            CREATE FULLTEXT INDEX entity_text_fulltext IF NOT EXISTS
            FOR (n:Entity)
            ON EACH [n.text]
            """,
            """
            CREATE FULLTEXT INDEX clause_text_fulltext IF NOT EXISTS
            FOR (n:Clause)
            ON EACH [n.text]
            """,
            """
            CREATE FULLTEXT INDEX legal_concept_fulltext IF NOT EXISTS
            FOR (n:LegalConcept)
            ON EACH [n.term, n.definition]
            """,
        ]

        return [q.strip() for q in queries]

    @staticmethod
    def get_node_types() -> Dict[str, Dict]:
        """Get all node type definitions."""
        return NODE_TYPES

    @staticmethod
    def get_relationship_types() -> Dict[str, Dict]:
        """Get all relationship type definitions."""
        return RELATIONSHIP_TYPES

    @staticmethod
    def validate_node_type(node_type: str) -> bool:
        """Validate if node type exists in schema."""
        return node_type in NODE_TYPES

    @staticmethod
    def validate_relationship_type(rel_type: str) -> bool:
        """Validate if relationship type exists in schema."""
        return rel_type in RELATIONSHIP_TYPES

    @staticmethod
    def get_required_properties(node_type: str) -> List[str]:
        """Get required properties for a node type."""
        if node_type not in NODE_TYPES:
            return []
        return NODE_TYPES[node_type].get("properties", [])
