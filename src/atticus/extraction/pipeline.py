"""
Complete entity extraction pipeline.

This module provides the main pipeline for extracting, validating,
deduplicating, and storing entities from legal documents.
"""

from typing import List, Optional

from atticus.core.config import get_config
from atticus.core.document_processor import DocumentProcessor
from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, Entity, ProcessingStatus
from atticus.extraction.entity_deduplicator import EntityDeduplicator
from atticus.extraction.entity_extractor import EntityExtractor
from atticus.extraction.entity_storage import EntityStorage
from atticus.extraction.entity_validator import EntityValidator
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class EntityExtractionPipeline:
    """Complete pipeline for entity extraction from legal documents."""

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        neo4j_manager: Optional[Neo4jManager] = None,
    ):
        """
        Initialize entity extraction pipeline.

        Args:
            llm_model: LLM model to use
            llm_provider: LLM provider (openai, anthropic)
            neo4j_manager: Neo4j manager instance
        """
        self.config = get_config()

        # Initialize components
        logger.info("Initializing entity extraction pipeline...")

        self.document_processor = DocumentProcessor()
        self.entity_extractor = EntityExtractor(model=llm_model, provider=llm_provider)
        self.entity_validator = EntityValidator()
        self.entity_deduplicator = EntityDeduplicator()
        self.entity_storage = EntityStorage(neo4j_manager=neo4j_manager)

        logger.info("Entity extraction pipeline initialized successfully")

    def process_document(
        self,
        document_path: str,
        store_in_graph: bool = True,
    ) -> tuple[Document, List[DocumentChunk], List[Entity]]:
        """
        Process a document end-to-end: parse, chunk, extract, validate, deduplicate, store.

        Args:
            document_path: Path to document file
            store_in_graph: Whether to store in Neo4j

        Returns:
            Tuple of (document, chunks, entities)
        """
        logger.info(f"=" * 60)
        logger.info(f"Processing document: {document_path}")
        logger.info(f"=" * 60)

        try:
            # Step 1: Parse document
            logger.info("Step 1/6: Parsing document...")
            document = self.document_processor.process_file(document_path)
            logger.info(f"✓ Document parsed: {document.title} (ID: {document.id})")

            # Step 2: Create chunks
            logger.info("Step 2/6: Creating document chunks...")
            chunks = self.document_processor.create_chunks(document)
            logger.info(f"✓ Created {len(chunks)} hierarchical chunks")

            # Step 3: Extract entities
            logger.info("Step 3/6: Extracting entities with LLM...")
            document.status = ProcessingStatus.ENTITY_EXTRACTION
            raw_entities = self.entity_extractor.extract_from_document(document, chunks)
            logger.info(f"✓ Extracted {len(raw_entities)} raw entities")

            # Step 4: Validate entities
            logger.info("Step 4/6: Validating entities...")
            valid_entities = self.entity_validator.validate_batch(raw_entities)
            logger.info(f"✓ {len(valid_entities)} entities passed validation")

            # Get entity statistics
            stats = self.entity_validator.get_entity_statistics(valid_entities)
            logger.info(f"  Entity statistics: {stats}")

            # Step 5: Deduplicate entities
            logger.info("Step 5/6: Deduplicating entities...")
            deduplicated_entities = self.entity_deduplicator.deduplicate(valid_entities)
            logger.info(f"✓ Deduplicated to {len(deduplicated_entities)} unique entities")

            # Step 6: Store in graph
            if store_in_graph:
                logger.info("Step 6/6: Storing entities in Neo4j...")
                stored_count = self.entity_storage.store_batch(deduplicated_entities)
                logger.info(f"✓ Stored {stored_count} entities in knowledge graph")

                # Update document status
                document.status = ProcessingStatus.COMPLETED
            else:
                logger.info("Step 6/6: Skipping graph storage (store_in_graph=False)")

            logger.info("=" * 60)
            logger.info(f"✓ Document processing completed successfully!")
            logger.info(f"  Document: {document.title}")
            logger.info(f"  Chunks: {len(chunks)}")
            logger.info(f"  Entities extracted: {len(raw_entities)}")
            logger.info(f"  Entities validated: {len(valid_entities)}")
            logger.info(f"  Entities deduplicated: {len(deduplicated_entities)}")
            logger.info(f"  Status: {document.status.value}")
            logger.info("=" * 60)

            return document, chunks, deduplicated_entities

        except Exception as e:
            logger.error(f"Failed to process document {document_path}: {e}")
            if 'document' in locals():
                document.status = ProcessingStatus.FAILED
            raise

    def process_batch(
        self,
        document_paths: List[str],
        store_in_graph: bool = True,
    ) -> List[tuple[Document, List[DocumentChunk], List[Entity]]]:
        """
        Process multiple documents in batch.

        Args:
            document_paths: List of document file paths
            store_in_graph: Whether to store in Neo4j

        Returns:
            List of (document, chunks, entities) tuples
        """
        logger.info(f"Processing batch of {len(document_paths)} documents...")

        results = []
        successful = 0
        failed = 0

        for i, doc_path in enumerate(document_paths):
            logger.info(f"\n--- Document {i+1}/{len(document_paths)} ---")

            try:
                result = self.process_document(doc_path, store_in_graph=store_in_graph)
                results.append(result)
                successful += 1

            except Exception as e:
                logger.error(f"Failed to process {doc_path}: {e}")
                failed += 1
                continue

        logger.info("\n" + "=" * 60)
        logger.info(f"BATCH PROCESSING COMPLETE")
        logger.info(f"  Total documents: {len(document_paths)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 60)

        return results

    def extract_entities_only(
        self,
        document: Document,
        chunks: List[DocumentChunk],
    ) -> List[Entity]:
        """
        Extract entities from pre-processed document and chunks.

        Args:
            document: Document object
            chunks: List of document chunks

        Returns:
            List of extracted entities
        """
        # Extract
        raw_entities = self.entity_extractor.extract_from_document(document, chunks)

        # Validate
        valid_entities = self.entity_validator.validate_batch(raw_entities)

        # Deduplicate
        deduplicated_entities = self.entity_deduplicator.deduplicate(valid_entities)

        return deduplicated_entities

    def reprocess_document(
        self,
        document_id: str,
        clear_existing: bool = True,
    ) -> List[Entity]:
        """
        Reprocess entities for an existing document.

        Args:
            document_id: Document ID
            clear_existing: Whether to clear existing entities first

        Returns:
            List of newly extracted entities
        """
        logger.info(f"Reprocessing entities for document {document_id}...")

        # Clear existing entities if requested
        if clear_existing:
            deleted = self.entity_storage.delete_entities_by_document(document_id)
            logger.info(f"Deleted {deleted} existing entities")

        # Retrieve document and chunks from storage
        # (This would require implementing document storage, which we'll add later)
        # For now, this is a placeholder

        logger.warning("Document reprocessing not fully implemented (requires document storage)")
        return []

    def get_extraction_stats(self, document_id: Optional[str] = None) -> dict:
        """
        Get extraction statistics.

        Args:
            document_id: Optional document ID filter

        Returns:
            Statistics dictionary
        """
        if document_id:
            entities = self.entity_storage.get_entities_by_document(document_id)
            stats = self.entity_validator.get_entity_statistics(entities)
            stats["document_id"] = document_id
        else:
            stats = self.entity_storage.get_statistics()

        return stats
