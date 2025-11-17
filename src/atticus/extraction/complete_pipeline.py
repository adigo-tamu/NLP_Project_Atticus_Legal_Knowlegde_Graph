"""
Complete extraction pipeline for entities and relationships.

This module provides the main pipeline for extracting entities, relationships,
and building the complete knowledge graph from legal documents.
"""

from typing import List, Optional, Tuple

from atticus.core.config import get_config
from atticus.core.document_processor import DocumentProcessor
from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, Entity, ProcessingStatus, Relationship
from atticus.extraction.coreference_resolver import CoreferenceResolver
from atticus.extraction.entity_deduplicator import EntityDeduplicator
from atticus.extraction.entity_extractor import EntityExtractor
from atticus.extraction.entity_storage import EntityStorage
from atticus.extraction.entity_validator import EntityValidator
from atticus.extraction.relationship_extractor import RelationshipExtractor
from atticus.extraction.relationship_storage import RelationshipStorage
from atticus.extraction.relationship_validator import RelationshipValidator
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


class CompleteExtractionPipeline:
    """Complete pipeline for entity and relationship extraction from legal documents."""

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        neo4j_manager: Optional[Neo4jManager] = None,
    ):
        """
        Initialize complete extraction pipeline.

        Args:
            llm_model: LLM model to use
            llm_provider: LLM provider (openai, anthropic)
            neo4j_manager: Neo4j manager instance
        """
        self.config = get_config()

        # Initialize components
        logger.info("Initializing complete extraction pipeline...")

        self.document_processor = DocumentProcessor()

        # Entity extraction components
        self.entity_extractor = EntityExtractor(model=llm_model, provider=llm_provider)
        self.entity_validator = EntityValidator()
        self.entity_deduplicator = EntityDeduplicator()
        self.entity_storage = EntityStorage(neo4j_manager=neo4j_manager)

        # Relationship extraction components
        self.relationship_extractor = RelationshipExtractor(model=llm_model, provider=llm_provider)
        self.relationship_validator = RelationshipValidator()
        self.coreference_resolver = CoreferenceResolver()
        self.relationship_storage = RelationshipStorage(neo4j_manager=neo4j_manager)

        logger.info("Complete extraction pipeline initialized successfully")

    def process_document(
        self,
        document_path: str,
        store_in_graph: bool = True,
        extract_relationships: bool = True,
    ) -> Tuple[Document, List[DocumentChunk], List[Entity], List[Relationship]]:
        """
        Process a document end-to-end: entities + relationships.

        Args:
            document_path: Path to document file
            store_in_graph: Whether to store in Neo4j
            extract_relationships: Whether to extract relationships (slower but more complete)

        Returns:
            Tuple of (document, chunks, entities, relationships)
        """
        logger.info("=" * 70)
        logger.info(f"COMPLETE PIPELINE: Processing {document_path}")
        logger.info("=" * 70)

        try:
            # ============================================================
            # PHASE 1: DOCUMENT PROCESSING
            # ============================================================
            logger.info("\n[1/8] Parsing document...")
            document = self.document_processor.process_file(document_path)
            logger.info(f"✓ Document parsed: {document.title} (ID: {document.id})")

            logger.info("\n[2/8] Creating document chunks...")
            chunks = self.document_processor.create_chunks(document)
            logger.info(f"✓ Created {len(chunks)} hierarchical chunks")

            # ============================================================
            # PHASE 2: ENTITY EXTRACTION
            # ============================================================
            logger.info("\n[3/8] Extracting entities with LLM...")
            document.status = ProcessingStatus.ENTITY_EXTRACTION
            raw_entities = self.entity_extractor.extract_from_document(document, chunks)
            logger.info(f"✓ Extracted {len(raw_entities)} raw entities")

            logger.info("\n[4/8] Validating entities...")
            valid_entities = self.entity_validator.validate_batch(raw_entities)
            logger.info(f"✓ {len(valid_entities)} entities passed validation")

            entity_stats = self.entity_validator.get_entity_statistics(valid_entities)
            logger.info(f"  Entity statistics: {entity_stats['by_type']}")

            logger.info("\n[5/8] Deduplicating entities...")
            deduplicated_entities = self.entity_deduplicator.deduplicate(valid_entities)
            logger.info(f"✓ Deduplicated to {len(deduplicated_entities)} unique entities")

            # Build coreference map
            self.coreference_resolver.build_coreference_map(deduplicated_entities)

            # ============================================================
            # PHASE 3: RELATIONSHIP EXTRACTION (if enabled)
            # ============================================================
            relationships = []

            if extract_relationships and len(deduplicated_entities) >= 2:
                logger.info("\n[6/8] Extracting relationships with chain-of-thought...")
                document.status = ProcessingStatus.RELATIONSHIP_EXTRACTION

                raw_relationships = []
                for chunk in chunks:
                    if chunk.level == 0:  # Skip document-level chunk
                        continue

                    chunk_entities = [e for e in deduplicated_entities if e.chunk_id == chunk.id]

                    if len(chunk_entities) >= 2:
                        try:
                            chunk_rels = self.relationship_extractor.extract_from_chunk(
                                chunk=chunk,
                                entities=chunk_entities,
                                use_cot=True,
                            )
                            raw_relationships.extend(chunk_rels)
                        except Exception as e:
                            logger.warning(f"Failed to extract relationships from chunk {chunk.id}: {e}")
                            continue

                logger.info(f"✓ Extracted {len(raw_relationships)} raw relationships")

                logger.info("\n[7/8] Validating relationships...")
                valid_relationships = self.relationship_validator.validate_batch(raw_relationships)
                logger.info(f"✓ {len(valid_relationships)} relationships passed validation")

                # Deduplicate relationships
                relationships = self.relationship_validator.deduplicate_relationships(valid_relationships)
                logger.info(f"✓ Deduplicated to {len(relationships)} unique relationships")

                rel_stats = self.relationship_validator.get_relationship_statistics(relationships)
                logger.info(f"  Relationship statistics: {rel_stats['by_type']}")
            else:
                logger.info("\n[6/8] Skipping relationship extraction (disabled or < 2 entities)")
                logger.info("\n[7/8] Skipping relationship validation (no relationships)")

            # ============================================================
            # PHASE 4: GRAPH STORAGE
            # ============================================================
            if store_in_graph:
                logger.info("\n[8/8] Storing in knowledge graph...")

                # Store entities
                entity_count = self.entity_storage.store_batch(deduplicated_entities)
                logger.info(f"✓ Stored {entity_count} entities in Neo4j")

                # Store relationships
                if relationships:
                    rel_count = self.relationship_storage.store_batch(relationships)
                    logger.info(f"✓ Stored {rel_count} relationships in Neo4j")

                document.status = ProcessingStatus.COMPLETED
            else:
                logger.info("\n[8/8] Skipping graph storage (store_in_graph=False)")

            # ============================================================
            # SUMMARY
            # ============================================================
            logger.info("\n" + "=" * 70)
            logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("=" * 70)
            logger.info(f"  Document: {document.title}")
            logger.info(f"  Chunks: {len(chunks)}")
            logger.info(f"  Entities extracted: {len(raw_entities)}")
            logger.info(f"  Entities validated: {len(valid_entities)}")
            logger.info(f"  Entities deduplicated: {len(deduplicated_entities)}")
            logger.info(f"  Relationships extracted: {len(relationships)}")
            logger.info(f"  Status: {document.status.value}")
            logger.info("=" * 70 + "\n")

            return document, chunks, deduplicated_entities, relationships

        except Exception as e:
            logger.error(f"Pipeline failed for document {document_path}: {e}")
            if 'document' in locals():
                document.status = ProcessingStatus.FAILED
            raise

    def process_batch(
        self,
        document_paths: List[str],
        store_in_graph: bool = True,
        extract_relationships: bool = True,
    ) -> List[Tuple[Document, List[DocumentChunk], List[Entity], List[Relationship]]]:
        """
        Process multiple documents in batch.

        Args:
            document_paths: List of document file paths
            store_in_graph: Whether to store in Neo4j
            extract_relationships: Whether to extract relationships

        Returns:
            List of (document, chunks, entities, relationships) tuples
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"BATCH PROCESSING: {len(document_paths)} documents")
        logger.info(f"{'='*70}\n")

        results = []
        successful = 0
        failed = 0

        for i, doc_path in enumerate(document_paths):
            logger.info(f"\n{'='*70}")
            logger.info(f"DOCUMENT {i+1}/{len(document_paths)}: {doc_path}")
            logger.info(f"{'='*70}\n")

            try:
                result = self.process_document(
                    doc_path,
                    store_in_graph=store_in_graph,
                    extract_relationships=extract_relationships,
                )
                results.append(result)
                successful += 1

            except Exception as e:
                logger.error(f"Failed to process {doc_path}: {e}")
                failed += 1
                continue

        logger.info("\n" + "=" * 70)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 70)
        logger.info(f"  Total documents: {len(document_paths)}")
        logger.info(f"  Successful: {successful}")
        logger.info(f"  Failed: {failed}")
        logger.info("=" * 70 + "\n")

        return results

    def extract_only(
        self,
        document: Document,
        chunks: List[DocumentChunk],
        extract_relationships: bool = True,
    ) -> Tuple[List[Entity], List[Relationship]]:
        """
        Extract entities and relationships from pre-processed document.

        Args:
            document: Document object
            chunks: List of document chunks
            extract_relationships: Whether to extract relationships

        Returns:
            Tuple of (entities, relationships)
        """
        # Extract entities
        raw_entities = self.entity_extractor.extract_from_document(document, chunks)
        valid_entities = self.entity_validator.validate_batch(raw_entities)
        entities = self.entity_deduplicator.deduplicate(valid_entities)

        # Build coreference map
        self.coreference_resolver.build_coreference_map(entities)

        # Extract relationships
        relationships = []
        if extract_relationships and len(entities) >= 2:
            raw_relationships = []
            for chunk in chunks:
                if chunk.level == 0:
                    continue

                chunk_entities = [e for e in entities if e.chunk_id == chunk.id]
                if len(chunk_entities) >= 2:
                    try:
                        chunk_rels = self.relationship_extractor.extract_from_chunk(
                            chunk, chunk_entities, use_cot=True
                        )
                        raw_relationships.extend(chunk_rels)
                    except:
                        continue

            valid_relationships = self.relationship_validator.validate_batch(raw_relationships)
            relationships = self.relationship_validator.deduplicate_relationships(valid_relationships)

        return entities, relationships

    def get_extraction_stats(self, document_id: Optional[str] = None) -> dict:
        """
        Get extraction statistics.

        Args:
            document_id: Optional document ID filter

        Returns:
            Statistics dictionary
        """
        stats = {}

        # Entity statistics
        if document_id:
            entities = self.entity_storage.get_entities_by_document(document_id)
            stats["entities"] = self.entity_validator.get_entity_statistics(entities)

            relationships = self.relationship_storage.get_relationships_by_document(document_id)
            stats["relationships"] = self.relationship_validator.get_relationship_statistics(relationships)

            stats["document_id"] = document_id
        else:
            stats["entities"] = self.entity_storage.get_statistics()
            stats["relationships"] = self.relationship_storage.get_statistics()

        return stats
