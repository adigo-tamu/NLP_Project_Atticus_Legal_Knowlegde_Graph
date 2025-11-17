"""
Entity extraction module using LLM-based NER.

This module implements entity extraction from legal documents using
prompt engineering and LLM APIs (OpenAI, Anthropic).
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from atticus.core.config import get_config
from atticus.core.exceptions import EntityExtractionError
from atticus.core.logger import get_logger
from atticus.core.models import Document, DocumentChunk, Entity, EntityType, Position
from atticus.utils.llm_client import get_llm_client
from atticus.utils.text_utils import count_tokens

logger = get_logger(__name__)


class PromptManager:
    """Manager for loading and formatting entity extraction prompts."""

    def __init__(self, prompts_dir: str = "prompts/entity_extraction"):
        """
        Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt templates
        """
        self.prompts_dir = Path(prompts_dir)
        self.base_template = self._load_template("base_template.txt")
        self.contract_specific = self._load_template("contract_specific.txt")
        self.few_shot_examples = self._load_examples("few_shot_examples.json")

    def _load_template(self, filename: str) -> str:
        """Load a prompt template file."""
        template_path = self.prompts_dir / filename
        if template_path.exists():
            with open(template_path, "r") as f:
                return f.read()
        else:
            logger.warning(f"Prompt template not found: {template_path}")
            return ""

    def _load_examples(self, filename: str) -> List[Dict]:
        """Load few-shot examples from JSON."""
        examples_path = self.prompts_dir / filename
        if examples_path.exists():
            with open(examples_path, "r") as f:
                data = json.load(f)
                return data.get("examples", [])
        else:
            logger.warning(f"Examples file not found: {examples_path}")
            return []

    def format_prompt(
        self,
        chunk_text: str,
        document_type: str = "contract",
        include_examples: bool = True,
        num_examples: int = 2,
    ) -> str:
        """
        Format the entity extraction prompt.

        Args:
            chunk_text: Text chunk to extract entities from
            document_type: Type of document (contract, agreement, etc.)
            include_examples: Whether to include few-shot examples
            num_examples: Number of few-shot examples to include

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # Add base template
        base_prompt = self.base_template.format(chunk_text=chunk_text)
        prompt_parts.append(base_prompt)

        # Add document-specific instructions
        if document_type == "contract" and self.contract_specific:
            prompt_parts.append("\n" + self.contract_specific)

        # Add few-shot examples
        if include_examples and self.few_shot_examples:
            examples_text = "\n\nEXAMPLES:\n\n"
            for i, example in enumerate(self.few_shot_examples[:num_examples]):
                examples_text += f"Example {i+1}:\n"
                examples_text += f"Input: {example['input']}\n"
                examples_text += f"Output: {json.dumps(example['output'], indent=2)}\n\n"
            prompt_parts.append(examples_text)

        return "\n".join(prompt_parts)

    def get_system_prompt(self) -> str:
        """Get the system prompt for entity extraction."""
        return """You are a legal document analysis expert specializing in entity extraction.
You have deep knowledge of contract law, legal terminology, and document structure.
Your task is to accurately identify and extract entities from legal text with high precision.
Always return valid JSON and follow the specified schema exactly."""


class EntityExtractor:
    """LLM-based entity extractor for legal documents."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """
        Initialize entity extractor.

        Args:
            model: LLM model to use (default from config)
            provider: LLM provider (openai, anthropic)
        """
        self.config = get_config()
        self.llm_client = get_llm_client(model=model, provider=provider)
        self.prompt_manager = PromptManager()

        logger.info(f"Initialized EntityExtractor with model: {self.llm_client.model}")

    def extract_from_chunk(
        self,
        chunk: DocumentChunk,
        document_type: str = "contract",
    ) -> List[Entity]:
        """
        Extract entities from a document chunk.

        Args:
            chunk: Document chunk to process
            document_type: Type of document

        Returns:
            List of extracted Entity objects
        """
        try:
            # Format prompt
            prompt = self.prompt_manager.format_prompt(
                chunk_text=chunk.text,
                document_type=document_type,
                include_examples=True,
                num_examples=2,
            )

            # Get system prompt
            system_prompt = self.prompt_manager.get_system_prompt()

            # Call LLM
            logger.debug(f"Extracting entities from chunk {chunk.id} ({chunk.token_count} tokens)")
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                response_format="json",
            )

            # Parse response
            entities_data = self._parse_llm_response(response)

            # Convert to Entity objects
            entities = self._create_entity_objects(
                entities_data=entities_data,
                chunk=chunk,
            )

            logger.info(f"Extracted {len(entities)} entities from chunk {chunk.id}")
            return entities

        except Exception as e:
            error_msg = f"Failed to extract entities from chunk {chunk.id}: {str(e)}"
            logger.error(error_msg)
            raise EntityExtractionError(error_msg, chunk_id=chunk.id)

    def extract_from_document(
        self,
        document: Document,
        chunks: List[DocumentChunk],
    ) -> List[Entity]:
        """
        Extract entities from entire document.

        Args:
            document: Document object
            chunks: List of document chunks

        Returns:
            List of all extracted entities
        """
        all_entities = []

        logger.info(f"Extracting entities from document {document.id} ({len(chunks)} chunks)")

        for i, chunk in enumerate(chunks):
            try:
                # Skip document-level chunk (level 0) for entity extraction
                if chunk.level == 0:
                    continue

                entities = self.extract_from_chunk(
                    chunk=chunk,
                    document_type=document.document_type.value,
                )

                all_entities.extend(entities)

                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i+1}/{len(chunks)} chunks, {len(all_entities)} entities so far")

            except EntityExtractionError as e:
                logger.warning(f"Skipping chunk {chunk.id} due to error: {e}")
                continue

        logger.info(f"Completed extraction from document {document.id}: {len(all_entities)} total entities")
        return all_entities

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract entities data.

        Args:
            response: LLM response string

        Returns:
            List of entity dictionaries
        """
        try:
            # Try to parse as JSON
            parsed = self.llm_client.parse_json_response(response)

            # Extract entities array
            if isinstance(parsed, dict) and "entities" in parsed:
                return parsed["entities"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"Unexpected response format: {type(parsed)}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []

    def _create_entity_objects(
        self,
        entities_data: List[Dict[str, Any]],
        chunk: DocumentChunk,
    ) -> List[Entity]:
        """
        Create Entity objects from extracted data.

        Args:
            entities_data: List of entity dictionaries from LLM
            chunk: Source chunk

        Returns:
            List of Entity objects
        """
        entities = []

        for entity_dict in entities_data:
            try:
                # Generate entity ID
                entity_id = self._generate_entity_id(
                    text=entity_dict.get("text", ""),
                    entity_type=entity_dict.get("type", ""),
                    document_id=chunk.document_id,
                )

                # Determine position in chunk
                position = self._find_position_in_chunk(
                    entity_text=entity_dict.get("text", ""),
                    chunk=chunk,
                )

                # Map type string to EntityType enum
                entity_type = self._map_entity_type(entity_dict.get("type", ""))

                # Create Entity object
                entity = Entity(
                    id=entity_id,
                    text=entity_dict.get("text", ""),
                    type=entity_type,
                    confidence=float(entity_dict.get("confidence", 0.5)),
                    context=entity_dict.get("context"),
                    position=position,
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    section=chunk.metadata.get("section_title"),
                    attributes=entity_dict.get("attributes", {}),
                    extraction_method="llm",
                    model=self.llm_client.model,
                )

                entities.append(entity)

            except Exception as e:
                logger.warning(f"Failed to create entity from data {entity_dict}: {e}")
                continue

        return entities

    def _generate_entity_id(self, text: str, entity_type: str, document_id: str) -> str:
        """Generate unique entity ID."""
        # Use UUID for uniqueness
        return f"ent_{document_id}_{entity_type}_{uuid.uuid4().hex[:8]}"

    def _find_position_in_chunk(self, entity_text: str, chunk: DocumentChunk) -> Optional[Position]:
        """
        Find position of entity text within chunk.

        Args:
            entity_text: Entity text to find
            chunk: Document chunk

        Returns:
            Position object or None
        """
        try:
            # Find first occurrence in chunk
            start_pos = chunk.text.find(entity_text)

            if start_pos != -1:
                # Calculate absolute position in document
                abs_start = chunk.position.start + start_pos
                abs_end = abs_start + len(entity_text)

                return Position(
                    start=abs_start,
                    end=abs_end,
                )
        except Exception as e:
            logger.debug(f"Could not find position for entity '{entity_text[:50]}': {e}")

        return None

    def _map_entity_type(self, type_string: str) -> EntityType:
        """
        Map string type to EntityType enum.

        Args:
            type_string: Type as string

        Returns:
            EntityType enum value
        """
        type_mapping = {
            "Legal_Party": EntityType.LEGAL_PARTY,
            "Legal_Concept": EntityType.LEGAL_CONCEPT,
            "Obligation": EntityType.OBLIGATION,
            "Right": EntityType.RIGHT,
            "Jurisdiction": EntityType.JURISDICTION,
            "Temporal_Entity": EntityType.TEMPORAL_ENTITY,
            "Financial_Term": EntityType.FINANCIAL_TERM,
            "Clause_Reference": EntityType.CLAUSE_REFERENCE,
        }

        return type_mapping.get(type_string, EntityType.LEGAL_CONCEPT)

    def batch_extract(
        self,
        chunks: List[DocumentChunk],
        batch_size: Optional[int] = None,
    ) -> List[Entity]:
        """
        Extract entities from multiple chunks in batches.

        Args:
            chunks: List of document chunks
            batch_size: Batch size (default from config)

        Returns:
            List of all extracted entities
        """
        batch_size = batch_size or self.config.processing.batch_size
        all_entities = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} chunks)")

            for chunk in batch:
                try:
                    entities = self.extract_from_chunk(chunk)
                    all_entities.extend(entities)
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk.id}: {e}")
                    continue

        return all_entities
