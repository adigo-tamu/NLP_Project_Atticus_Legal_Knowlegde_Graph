"""
Relationship extraction module using LLM with chain-of-thought reasoning.

This module implements relationship extraction between entities using
advanced prompt engineering and reasoning chains.
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from atticus.core.config import get_config
from atticus.core.exceptions import RelationshipExtractionError
from atticus.core.logger import get_logger
from atticus.core.models import DocumentChunk, Entity, Relationship, RelationshipType
from atticus.utils.llm_client import get_llm_client

logger = get_logger(__name__)


class RelationshipPromptManager:
    """Manager for loading and formatting relationship extraction prompts."""

    def __init__(self, prompts_dir: str = "prompts/relationship_extraction"):
        """
        Initialize relationship prompt manager.

        Args:
            prompts_dir: Directory containing prompt templates
        """
        self.prompts_dir = Path(prompts_dir)
        self.base_template = self._load_template("base_template.txt")
        self.coreference_guide = self._load_template("coreference_resolution.txt")
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
        entities: List[Entity],
        include_examples: bool = True,
        include_coreference: bool = True,
        num_examples: int = 2,
    ) -> str:
        """
        Format the relationship extraction prompt.

        Args:
            chunk_text: Text chunk containing entities
            entities: List of extracted entities
            include_examples: Whether to include few-shot examples
            include_coreference: Whether to include coreference guidelines
            num_examples: Number of few-shot examples

        Returns:
            Formatted prompt string
        """
        # Format entities as JSON for the prompt
        entities_json = self._format_entities_for_prompt(entities)

        # Format base template
        base_prompt = self.base_template.format(
            chunk_text=chunk_text,
            entities_json=entities_json,
        )

        prompt_parts = [base_prompt]

        # Add coreference resolution guidelines
        if include_coreference and self.coreference_guide:
            prompt_parts.append("\n" + self.coreference_guide)

        # Add few-shot examples
        if include_examples and self.few_shot_examples:
            examples_text = "\n\nFEW-SHOT EXAMPLES:\n\n"
            for i, example in enumerate(self.few_shot_examples[:num_examples]):
                examples_text += f"Example {i+1}:\n"
                examples_text += f"Text: {example['input']['text']}\n"
                examples_text += f"Entities: {json.dumps(example['input']['entities'], indent=2)}\n"
                examples_text += f"Output: {json.dumps(example['output'], indent=2)}\n\n"
            prompt_parts.append(examples_text)

        return "\n".join(prompt_parts)

    def _format_entities_for_prompt(self, entities: List[Entity]) -> str:
        """Format entities as JSON for inclusion in prompt."""
        entities_data = []
        for entity in entities:
            entities_data.append({
                "id": entity.id,
                "text": entity.text,
                "type": entity.type.value,
                "confidence": entity.confidence,
            })
        return json.dumps(entities_data, indent=2)

    def get_system_prompt(self) -> str:
        """Get the system prompt for relationship extraction."""
        return """You are a legal document analysis expert specializing in relationship extraction.
You have deep knowledge of contract law, legal relationships, and semantic analysis.
Your task is to identify relationships between entities with chain-of-thought reasoning.
Always think step-by-step, provide reasoning, and return valid JSON."""


class RelationshipExtractor:
    """LLM-based relationship extractor with chain-of-thought reasoning."""

    def __init__(
        self,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        """
        Initialize relationship extractor.

        Args:
            model: LLM model to use (default from config)
            provider: LLM provider (openai, anthropic)
        """
        self.config = get_config()
        self.llm_client = get_llm_client(model=model, provider=provider)
        self.prompt_manager = RelationshipPromptManager()

        logger.info(f"Initialized RelationshipExtractor with model: {self.llm_client.model}")

    def extract_from_chunk(
        self,
        chunk: DocumentChunk,
        entities: List[Entity],
        use_cot: bool = True,
    ) -> List[Relationship]:
        """
        Extract relationships from a chunk with its entities.

        Args:
            chunk: Document chunk
            entities: Entities already extracted from this chunk
            use_cot: Whether to use chain-of-thought reasoning

        Returns:
            List of extracted Relationship objects
        """
        # Filter entities for this chunk
        chunk_entities = [e for e in entities if e.chunk_id == chunk.id]

        if len(chunk_entities) < 2:
            logger.debug(f"Chunk {chunk.id} has < 2 entities, skipping relationship extraction")
            return []

        try:
            # Format prompt
            prompt = self.prompt_manager.format_prompt(
                chunk_text=chunk.text,
                entities=chunk_entities,
                include_examples=True,
                include_coreference=True,
                num_examples=2,
            )

            # Get system prompt
            system_prompt = self.prompt_manager.get_system_prompt()

            # Call LLM
            logger.debug(
                f"Extracting relationships from chunk {chunk.id} "
                f"({len(chunk_entities)} entities)"
            )

            if use_cot:
                # Use chain-of-thought generation
                response_dict = self.llm_client.generate_with_thinking(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
                response = response_dict["response"]
            else:
                response = self.llm_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_format="json",
                )

            # Parse response
            relationships_data = self._parse_llm_response(response)

            # Convert to Relationship objects
            relationships = self._create_relationship_objects(
                relationships_data=relationships_data,
                chunk=chunk,
                entities=chunk_entities,
            )

            logger.info(f"Extracted {len(relationships)} relationships from chunk {chunk.id}")
            return relationships

        except Exception as e:
            error_msg = f"Failed to extract relationships from chunk {chunk.id}: {str(e)}"
            logger.error(error_msg)
            raise RelationshipExtractionError(error_msg, chunk_id=chunk.id)

    def extract_from_entities(
        self,
        entities: List[Entity],
        document_text: str,
    ) -> List[Relationship]:
        """
        Extract relationships from entities across entire document.

        Args:
            entities: All entities from document
            document_text: Full document text

        Returns:
            List of all extracted relationships
        """
        all_relationships = []

        # Group entities by chunk
        entities_by_chunk = {}
        for entity in entities:
            chunk_id = entity.chunk_id
            if chunk_id not in entities_by_chunk:
                entities_by_chunk[chunk_id] = []
            entities_by_chunk[chunk_id].append(entity)

        logger.info(f"Extracting relationships from {len(entities_by_chunk)} chunks")

        # Process each chunk
        for chunk_id, chunk_entities in entities_by_chunk.items():
            if len(chunk_entities) < 2:
                continue

            try:
                # Create a pseudo-chunk for extraction
                # In practice, you'd retrieve the actual chunk from storage
                chunk_text = self._extract_chunk_text(
                    entities=chunk_entities,
                    full_text=document_text,
                )

                from atticus.core.models import DocumentChunk, Position

                pseudo_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=chunk_entities[0].document_id,
                    text=chunk_text,
                    position=Position(start=0, end=len(chunk_text)),
                    chunk_index=0,
                    level=1,
                    token_count=len(chunk_text.split()),
                )

                relationships = self.extract_from_chunk(pseudo_chunk, chunk_entities)
                all_relationships.extend(relationships)

            except Exception as e:
                logger.warning(f"Failed to extract relationships from chunk {chunk_id}: {e}")
                continue

        logger.info(f"Extracted total of {len(all_relationships)} relationships")
        return all_relationships

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response to extract relationships data.

        Args:
            response: LLM response string

        Returns:
            List of relationship dictionaries
        """
        try:
            # Try to parse as JSON
            parsed = self.llm_client.parse_json_response(response)

            # Extract relationships array
            if isinstance(parsed, dict) and "relationships" in parsed:
                return parsed["relationships"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"Unexpected response format: {type(parsed)}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response: {response[:500]}")
            return []

    def _create_relationship_objects(
        self,
        relationships_data: List[Dict[str, Any]],
        chunk: DocumentChunk,
        entities: List[Entity],
    ) -> List[Relationship]:
        """
        Create Relationship objects from extracted data.

        Args:
            relationships_data: List of relationship dictionaries
            chunk: Source chunk
            entities: Available entities

        Returns:
            List of Relationship objects
        """
        relationships = []

        # Build entity lookup
        entity_lookup = {e.id: e for e in entities}

        for rel_dict in relationships_data:
            try:
                # Validate entity IDs
                source_id = rel_dict.get("source_entity_id")
                target_id = rel_dict.get("target_entity_id")

                if source_id not in entity_lookup:
                    logger.debug(f"Source entity {source_id} not found, skipping")
                    continue

                if target_id not in entity_lookup:
                    logger.debug(f"Target entity {target_id} not found, skipping")
                    continue

                # Generate relationship ID
                rel_id = self._generate_relationship_id(
                    source_id=source_id,
                    target_id=target_id,
                    rel_type=rel_dict.get("relationship_type", ""),
                )

                # Map type string to RelationshipType enum
                rel_type = self._map_relationship_type(rel_dict.get("relationship_type", ""))

                # Create Relationship object
                relationship = Relationship(
                    id=rel_id,
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relationship_type=rel_type,
                    confidence=float(rel_dict.get("confidence", 0.5)),
                    evidence=rel_dict.get("evidence"),
                    reasoning=rel_dict.get("reasoning"),
                    document_id=chunk.document_id,
                    chunk_id=chunk.id,
                    properties=rel_dict.get("properties", {}),
                    extraction_method="llm",
                    model=self.llm_client.model,
                )

                relationships.append(relationship)

            except Exception as e:
                logger.warning(f"Failed to create relationship from data {rel_dict}: {e}")
                continue

        return relationships

    def _generate_relationship_id(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
    ) -> str:
        """Generate unique relationship ID."""
        return f"rel_{source_id}_{target_id}_{rel_type}_{uuid.uuid4().hex[:8]}"

    def _map_relationship_type(self, type_string: str) -> RelationshipType:
        """
        Map string type to RelationshipType enum.

        Args:
            type_string: Type as string

        Returns:
            RelationshipType enum value
        """
        type_mapping = {
            "REFERENCES": RelationshipType.REFERENCES,
            "OBLIGATES": RelationshipType.OBLIGATES,
            "GRANTS_RIGHT": RelationshipType.GRANTS_RIGHT,
            "GOVERNS": RelationshipType.GOVERNS,
            "DEFINES": RelationshipType.DEFINES,
            "MODIFIES": RelationshipType.MODIFIES,
            "DEPENDS_ON": RelationshipType.DEPENDS_ON,
            "CONTRADICTS": RelationshipType.CONTRADICTS,
            "TEMPORALLY_PRECEDES": RelationshipType.TEMPORALLY_PRECEDES,
            "FINANCIALLY_RELATES": RelationshipType.FINANCIALLY_RELATES,
        }

        return type_mapping.get(type_string, RelationshipType.REFERENCES)

    def _extract_chunk_text(
        self,
        entities: List[Entity],
        full_text: str,
        context_window: int = 500,
    ) -> str:
        """
        Extract text chunk containing entities with context.

        Args:
            entities: Entities to include
            full_text: Full document text
            context_window: Characters of context to include

        Returns:
            Chunk text
        """
        # Find min and max positions
        positions = [e.position for e in entities if e.position]

        if not positions:
            # Fallback: use entity context
            contexts = [e.context for e in entities if e.context]
            return " ".join(contexts) if contexts else ""

        min_pos = min(p.start for p in positions)
        max_pos = max(p.end for p in positions)

        # Add context window
        start = max(0, min_pos - context_window)
        end = min(len(full_text), max_pos + context_window)

        return full_text[start:end]
