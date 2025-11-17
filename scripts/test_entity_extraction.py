#!/usr/bin/env python
"""
Test script for entity extraction pipeline.

This script demonstrates the entity extraction functionality with a sample legal text.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, DocumentType, Position, ProcessingStatus
from atticus.extraction.pipeline import EntityExtractionPipeline

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
    a non-exclusive, non-transferable license to use the Software (as defined below) for a
    term of three (3) years from the Effective Date.

    2. PAYMENT TERMS

    Licensee shall pay to Licensor an annual license fee of Fifty Thousand Dollars ($50,000),
    payable within thirty (30) days of the Effective Date and on each anniversary thereof.
    Late payments shall accrue interest at a rate of 1.5% per month.

    3. TERMINATION

    Either party may terminate this Agreement upon thirty (30) days' written notice if the
    other party materially breaches any provision of this Agreement and fails to cure such
    breach within fifteen (15) days after receiving written notice thereof.

    4. GOVERNING LAW

    This Agreement shall be governed by and construed in accordance with the laws of the
    State of Delaware, without regard to its conflict of laws principles. Any disputes
    arising under this Agreement shall be subject to the exclusive jurisdiction of the
    courts located in Wilmington, Delaware.
    """

    # Create document
    document = Document(
        id="sample_doc_001",
        title="Software License Agreement - TechCorp/DataSystems",
        content=sample_text,
        document_type=DocumentType.LICENSE,
        parties=["TechCorp Inc.", "DataSystems LLC"],
        status=ProcessingStatus.PENDING,
    )

    # Create a single chunk for testing
    chunk = DocumentChunk(
        id="sample_doc_001_chunk_1",
        document_id=document.id,
        text=sample_text,
        position=Position(start=0, end=len(sample_text)),
        chunk_index=1,
        level=1,
        token_count=len(sample_text.split()),
    )

    return document, [chunk]


def main():
    """Run entity extraction test."""

    logger.info("=" * 70)
    logger.info("ENTITY EXTRACTION PIPELINE TEST")
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
        logger.info(f"  Content length: {len(document.content)} characters")

        # Initialize pipeline (without Neo4j for testing)
        logger.info("\nInitializing extraction pipeline...")
        pipeline = EntityExtractionPipeline()

        # Extract entities (without storing in graph)
        logger.info("\nExtracting entities...")
        entities = pipeline.extract_entities_only(document, chunks)

        # Display results
        logger.info("\n" + "=" * 70)
        logger.info(f"EXTRACTION RESULTS")
        logger.info("=" * 70)
        logger.info(f"Total entities extracted: {len(entities)}\n")

        # Group by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.type.value
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Display each type
        for entity_type, type_entities in sorted(entities_by_type.items()):
            logger.info(f"\n{entity_type} ({len(type_entities)}):")
            logger.info("-" * 70)

            for entity in type_entities:
                logger.info(f"  • \"{entity.text}\"")
                logger.info(f"    Confidence: {entity.confidence:.2f}")
                if entity.attributes:
                    logger.info(f"    Attributes: {entity.attributes}")

        # Statistics
        logger.info("\n" + "=" * 70)
        logger.info("STATISTICS")
        logger.info("=" * 70)
        stats = pipeline.entity_validator.get_entity_statistics(entities)
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")

        logger.info("\n" + "=" * 70)
        logger.info("✓ TEST COMPLETED SUCCESSFULLY")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
