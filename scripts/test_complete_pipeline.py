#!/usr/bin/env python
"""
Test script for complete extraction pipeline (entities + relationships).

This script demonstrates the full extraction functionality with chain-of-thought reasoning.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, DocumentType, Position, ProcessingStatus
from atticus.extraction.complete_pipeline import CompleteExtractionPipeline

logger = get_logger(__name__)


def create_sample_document() -> tuple[Document, list[DocumentChunk]]:
    """Create a sample legal document for testing."""

    sample_text = """
    SOFTWARE LICENSE AGREEMENT

    This Software License Agreement ("Agreement") is entered into as of January 15, 2024,
    by and between TechCorp Inc., a Delaware corporation ("Licensor"), and DataSystems LLC
    ("Licensee").

    1. GRANT OF LICENSE

    Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee
    a non-exclusive, non-transferable license to use the Software (as defined in Section 5.1)
    for a term of three (3) years from the Effective Date.

    2. PAYMENT TERMS

    Licensee shall pay to Licensor an annual license fee of Fifty Thousand Dollars ($50,000),
    payable within thirty (30) days of the Effective Date and on each anniversary thereof.
    Late payments shall accrue interest at a rate of 1.5% per month.

    3. TERMINATION

    Either party may terminate this Agreement upon thirty (30) days' written notice if the
    other party materially breaches any provision of Section 2 (Payment Terms) and fails to
    cure such breach within fifteen (15) days after receiving written notice thereof.

    Upon termination, all rights granted under Section 1 shall immediately cease, and
    Licensee shall immediately cease all use of the Software and return or destroy all
    copies.

    4. GOVERNING LAW

    This Agreement shall be governed by and construed in accordance with the laws of the
    State of Delaware, without regard to its conflict of laws principles. Any disputes
    arising under this Agreement shall be subject to the exclusive jurisdiction of the
    courts located in Wilmington, Delaware.

    5. DEFINITIONS

    5.1 "Software" means the proprietary software application known as "TechCorp DataAnalyzer
    Pro" including all updates, modifications, and documentation.

    5.2 "Effective Date" means the date first written above, January 15, 2024.
    """

    # Create document
    document = Document(
        id="sample_doc_phase3",
        title="Software License Agreement - TechCorp/DataSystems",
        content=sample_text,
        document_type=DocumentType.LICENSE,
        parties=["TechCorp Inc.", "DataSystems LLC"],
        status=ProcessingStatus.PENDING,
    )

    # Create chunks
    chunks = []

    # Section 1 - Grant of License
    section1_text = """Subject to the terms and conditions of this Agreement, Licensor hereby grants to Licensee
    a non-exclusive, non-transferable license to use the Software (as defined in Section 5.1)
    for a term of three (3) years from the Effective Date."""

    chunks.append(DocumentChunk(
        id=f"{document.id}_chunk_1",
        document_id=document.id,
        text=section1_text,
        position=Position(start=0, end=len(section1_text)),
        chunk_index=1,
        level=2,
        token_count=len(section1_text.split()),
        metadata={"section_title": "Grant of License"},
    ))

    # Section 2 - Payment Terms
    section2_text = """Licensee shall pay to Licensor an annual license fee of Fifty Thousand Dollars ($50,000),
    payable within thirty (30) days of the Effective Date and on each anniversary thereof.
    Late payments shall accrue interest at a rate of 1.5% per month."""

    chunks.append(DocumentChunk(
        id=f"{document.id}_chunk_2",
        document_id=document.id,
        text=section2_text,
        position=Position(start=len(section1_text), end=len(section1_text) + len(section2_text)),
        chunk_index=2,
        level=2,
        token_count=len(section2_text.split()),
        metadata={"section_title": "Payment Terms"},
    ))

    # Section 3 - Termination
    section3_text = """Either party may terminate this Agreement upon thirty (30) days' written notice if the
    other party materially breaches any provision of Section 2 (Payment Terms) and fails to
    cure such breach within fifteen (15) days after receiving written notice thereof.

    Upon termination, all rights granted under Section 1 shall immediately cease, and
    Licensee shall immediately cease all use of the Software and return or destroy all
    copies."""

    chunks.append(DocumentChunk(
        id=f"{document.id}_chunk_3",
        document_id=document.id,
        text=section3_text,
        position=Position(start=len(section1_text) + len(section2_text),
                         end=len(section1_text) + len(section2_text) + len(section3_text)),
        chunk_index=3,
        level=2,
        token_count=len(section3_text.split()),
        metadata={"section_title": "Termination"},
    ))

    return document, chunks


def main():
    """Run complete extraction pipeline test."""

    logger.info("=" * 70)
    logger.info("COMPLETE EXTRACTION PIPELINE TEST")
    logger.info("Testing: Entity + Relationship Extraction with Chain-of-Thought")
    logger.info("=" * 70)

    try:
        # Check API keys
        config = get_config()
        if not config.validate_api_keys():
            logger.error("API keys not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")
            logger.info("Copy .env.example to .env and add your API keys")
            return

        # Create sample document
        logger.info("\nCreating sample legal document...")
        document, chunks = create_sample_document()
        logger.info(f"✓ Created document: {document.title}")
        logger.info(f"  Document type: {document.document_type.value}")
        logger.info(f"  Parties: {', '.join(document.parties)}")
        logger.info(f"  Chunks: {len(chunks)}")

        # Initialize pipeline
        logger.info("\nInitializing complete extraction pipeline...")
        pipeline = CompleteExtractionPipeline()

        # Extract entities and relationships
        logger.info("\nExtracting entities and relationships...")
        entities, relationships = pipeline.extract_only(
            document=document,
            chunks=chunks,
            extract_relationships=True,
        )

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info("EXTRACTION RESULTS")
        logger.info("=" * 70)

        # Entities
        logger.info(f"\nENTITIES: {len(entities)} extracted\n")
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.type.value
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        for entity_type, type_entities in sorted(entities_by_type.items()):
            logger.info(f"{entity_type} ({len(type_entities)}):")
            for entity in type_entities[:5]:  # Show first 5
                logger.info(f"  • \"{entity.text}\" (conf: {entity.confidence:.2f})")
            if len(type_entities) > 5:
                logger.info(f"  ... and {len(type_entities) - 5} more")
            logger.info("")

        # Relationships
        logger.info(f"\nRELATIONSHIPS: {len(relationships)} extracted\n")
        relationships_by_type = {}
        for rel in relationships:
            rel_type = rel.relationship_type.value
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(rel)

        # Build entity lookup for display
        entity_lookup = {e.id: e.text for e in entities}

        for rel_type, type_rels in sorted(relationships_by_type.items()):
            logger.info(f"{rel_type} ({len(type_rels)}):")
            for rel in type_rels:
                source_text = entity_lookup.get(rel.source_entity_id, "Unknown")[:40]
                target_text = entity_lookup.get(rel.target_entity_id, "Unknown")[:40]
                logger.info(f"  • \"{source_text}\" → \"{target_text}\"")
                logger.info(f"    Confidence: {rel.confidence:.2f}")
                if rel.evidence:
                    logger.info(f"    Evidence: \"{rel.evidence[:100]}...\"")
                if rel.reasoning:
                    logger.info(f"    Reasoning: \"{rel.reasoning[:150]}...\"")
                logger.info("")

        # Statistics
        logger.info("\n" + "=" * 70)
        logger.info("STATISTICS")
        logger.info("=" * 70)
        logger.info(f"  Total entities: {len(entities)}")
        logger.info(f"  Total relationships: {len(relationships)}")
        logger.info(f"  Entity types: {len(entities_by_type)}")
        logger.info(f"  Relationship types: {len(relationships_by_type)}")

        avg_entity_conf = sum(e.confidence for e in entities) / len(entities) if entities else 0
        avg_rel_conf = sum(r.confidence for r in relationships) / len(relationships) if relationships else 0

        logger.info(f"  Avg entity confidence: {avg_entity_conf:.3f}")
        logger.info(f"  Avg relationship confidence: {avg_rel_conf:.3f}")

        logger.info("\n" + "=" * 70)
        logger.info("✓ TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
