"""
RAG (Retrieval-Augmented Generation) for Legal Knowledge Graph.

Implements question answering by retrieving relevant graph context
and generating answers using LLMs.
"""

import json
from typing import Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.core.models import Entity, Relationship
from atticus.graph.neo4j_manager import Neo4jManager
from atticus.utils.llm_client import get_llm_client

logger = get_logger(__name__)


class GraphRAG:
    """RAG system for legal knowledge graph question answering."""

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        neo4j_manager: Optional[Neo4jManager] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize Graph RAG system.

        Args:
            llm_model: LLM model for generation
            llm_provider: LLM provider (openai, anthropic)
            neo4j_manager: Neo4j manager instance
            embedding_model: Sentence transformer model
        """
        self.config = get_config()
        self.llm_client = get_llm_client(
            model=llm_model or self.config.llm.model,
            provider=llm_provider or self.config.llm.provider,
        )
        self.db = neo4j_manager or Neo4jManager()

        # Initialize embedding model for semantic search
        self.embedding_model_name = (
            embedding_model or self.config.entity_extraction.deduplication.embedding_model
        )
        logger.info(f"Loading embedding model: {self.embedding_model_name}")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

        logger.info("Graph RAG system initialized")

    def answer_question(
        self,
        question: str,
        document_id: Optional[str] = None,
        max_context_entities: int = 10,
        max_context_relationships: int = 10,
        include_sources: bool = True,
    ) -> Dict:
        """
        Answer question using graph RAG.

        Args:
            question: Question to answer
            document_id: Optional document filter
            max_context_entities: Max entities to retrieve
            max_context_relationships: Max relationships to retrieve
            include_sources: Include source entities in response

        Returns:
            Answer dictionary with answer, confidence, sources
        """
        logger.info(f"Answering question: {question}")

        # Step 1: Retrieve relevant context from graph
        context = self._retrieve_context(
            question=question,
            document_id=document_id,
            max_entities=max_context_entities,
            max_relationships=max_context_relationships,
        )

        # Step 2: Generate answer using LLM with retrieved context
        answer, confidence = self._generate_answer(
            question=question,
            context=context,
        )

        # Step 3: Build response
        response = {
            "question": question,
            "answer": answer,
            "confidence": confidence,
        }

        if include_sources:
            response["sources"] = context.get("entities", [])

        response["context_used"] = {
            "num_entities": len(context.get("entities", [])),
            "num_relationships": len(context.get("relationships", [])),
        }

        logger.info(f"Answer generated with confidence: {confidence}")

        return response

    def _retrieve_context(
        self,
        question: str,
        document_id: Optional[str] = None,
        max_entities: int = 10,
        max_relationships: int = 10,
    ) -> Dict:
        """
        Retrieve relevant context from graph.

        Uses multiple retrieval strategies:
        1. Keyword-based entity search
        2. Semantic similarity search (embeddings)
        3. Relationship traversal from relevant entities

        Args:
            question: Question text
            document_id: Optional document filter
            max_entities: Maximum entities to retrieve
            max_relationships: Maximum relationships to retrieve

        Returns:
            Context dictionary with entities and relationships
        """
        logger.info("Retrieving context from graph...")

        context = {
            "entities": [],
            "relationships": [],
        }

        # Strategy 1: Keyword-based search
        keywords = self._extract_keywords(question)
        keyword_entities = self._search_entities_by_keywords(
            keywords=keywords,
            document_id=document_id,
            limit=max_entities // 2,
        )

        # Strategy 2: Semantic similarity search
        semantic_entities = self._search_entities_by_similarity(
            query=question,
            document_id=document_id,
            limit=max_entities // 2,
        )

        # Combine and deduplicate entities
        all_entities = keyword_entities + semantic_entities
        unique_entities = self._deduplicate_entities(all_entities)[:max_entities]

        context["entities"] = unique_entities

        # Strategy 3: Get relationships involving retrieved entities
        if unique_entities:
            entity_ids = [e["id"] for e in unique_entities]
            relationships = self._get_relationships_for_entities(
                entity_ids=entity_ids,
                limit=max_relationships,
            )
            context["relationships"] = relationships

        logger.info(
            f"Retrieved {len(context['entities'])} entities, "
            f"{len(context['relationships'])} relationships"
        )

        return context

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""

        # Simple keyword extraction (can be improved with NER or KeyBERT)
        import re

        # Remove common words
        stop_words = {
            "what", "which", "who", "when", "where", "why", "how",
            "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did",
            "the", "a", "an", "and", "or", "but", "in", "on", "at",
            "to", "for", "of", "with", "by", "from", "as",
        }

        # Extract words
        words = re.findall(r"\b[a-z]+\b", text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        # Keep unique keywords
        return list(set(keywords))[:5]  # Top 5 keywords

    def _search_entities_by_keywords(
        self,
        keywords: List[str],
        document_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        """Search entities by keywords."""

        if not keywords:
            return []

        # Build keyword filter
        keyword_conditions = " OR ".join(
            [f"toLower(n.text) CONTAINS '{kw}'" for kw in keywords]
        )

        query = f"""
        MATCH (n)
        WHERE {keyword_conditions}
        """

        if document_id:
            query += f" AND n.document_id = '{document_id}'"

        query += """
        RETURN n.id as id, n.text as text, n.type as type,
               n.confidence as confidence, n.document_id as document_id,
               n.context as context, labels(n) as labels
        ORDER BY n.confidence DESC
        LIMIT $limit
        """

        try:
            result = self.db.execute_query(query, {"limit": limit})
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _search_entities_by_similarity(
        self,
        query: str,
        document_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        """Search entities by semantic similarity."""

        # Get all entities
        cypher_query = "MATCH (n)"

        if document_id:
            cypher_query += f" WHERE n.document_id = '{document_id}'"

        cypher_query += """
        RETURN n.id as id, n.text as text, n.type as type,
               n.confidence as confidence, n.document_id as document_id,
               n.context as context, labels(n) as labels
        LIMIT 100
        """

        try:
            result = self.db.execute_query(cypher_query)
            entities = [dict(record) for record in result]

            if not entities:
                return []

            # Compute embeddings
            query_embedding = self.embedding_model.encode(query)
            entity_texts = [e["text"] for e in entities]
            entity_embeddings = self.embedding_model.encode(entity_texts)

            # Compute similarities
            from sklearn.metrics.pairwise import cosine_similarity

            similarities = cosine_similarity([query_embedding], entity_embeddings)[0]

            # Sort by similarity
            entity_similarity_pairs = list(zip(entities, similarities))
            entity_similarity_pairs.sort(key=lambda x: x[1], reverse=True)

            # Return top k
            return [entity for entity, _ in entity_similarity_pairs[:limit]]

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Deduplicate entities by ID."""

        seen_ids = set()
        unique = []

        for entity in entities:
            if entity["id"] not in seen_ids:
                seen_ids.add(entity["id"])
                unique.append(entity)

        return unique

    def _get_relationships_for_entities(
        self,
        entity_ids: List[str],
        limit: int = 10,
    ) -> List[Dict]:
        """Get relationships involving specified entities."""

        query = """
        MATCH (source)-[r]->(target)
        WHERE source.id IN $entity_ids OR target.id IN $entity_ids
        RETURN source.id as source_id, source.text as source_text,
               type(r) as relationship_type, r.confidence as confidence,
               r.evidence as evidence,
               target.id as target_id, target.text as target_text
        ORDER BY r.confidence DESC
        LIMIT $limit
        """

        try:
            result = self.db.execute_query(query, {"entity_ids": entity_ids, "limit": limit})
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Relationship retrieval failed: {e}")
            return []

    def _generate_answer(
        self,
        question: str,
        context: Dict,
    ) -> Tuple[str, float]:
        """
        Generate answer using LLM with retrieved context.

        Args:
            question: Question to answer
            context: Retrieved graph context

        Returns:
            Tuple of (answer, confidence)
        """
        logger.info("Generating answer with LLM...")

        # Build context string
        context_str = self._format_context(context)

        # Build prompt
        prompt = f"""# Knowledge Graph Context

{context_str}

# Question
{question}

# Task
Answer the question using ONLY the information provided in the knowledge graph context above.
If the context does not contain sufficient information to answer the question, say so explicitly.

Provide your answer in the following JSON format:
{{
  "answer": "Your detailed answer here",
  "confidence": 0.85,
  "reasoning": "Brief explanation of how you derived the answer"
}}

The confidence should be between 0 and 1, reflecting how well the context supports your answer.
"""

        system_prompt = """You are a legal knowledge graph assistant.
Your role is to answer questions based on information retrieved from a legal knowledge graph.
Be precise, cite specific entities and relationships when possible, and always indicate your confidence level."""

        # Generate answer
        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="json",
        )

        try:
            response_data = json.loads(response)
            answer = response_data.get("answer", "Unable to generate answer")
            confidence = float(response_data.get("confidence", 0.5))

            return answer, confidence

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return "Unable to generate answer due to parsing error", 0.0

    def _format_context(self, context: Dict) -> str:
        """Format context for LLM prompt."""

        formatted = ""

        # Format entities
        if context.get("entities"):
            formatted += "## Entities\n\n"
            for i, entity in enumerate(context["entities"], 1):
                formatted += f"{i}. **{entity['text']}** ({entity.get('labels', ['Entity'])[0]})\n"
                formatted += f"   - Confidence: {entity['confidence']}\n"
                if entity.get("context"):
                    formatted += f"   - Context: {entity['context'][:100]}...\n"
                formatted += "\n"

        # Format relationships
        if context.get("relationships"):
            formatted += "## Relationships\n\n"
            for i, rel in enumerate(context["relationships"], 1):
                formatted += (
                    f"{i}. {rel['source_text']} "
                    f"--[{rel['relationship_type']}]--> "
                    f"{rel['target_text']}\n"
                )
                formatted += f"   - Confidence: {rel['confidence']}\n"
                if rel.get("evidence"):
                    formatted += f"   - Evidence: {rel['evidence'][:100]}...\n"
                formatted += "\n"

        if not formatted:
            formatted = "No relevant context found in the knowledge graph.\n"

        return formatted

    def answer_competency_questions(
        self,
        questions: List[str],
        document_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Answer multiple competency questions.

        Args:
            questions: List of questions
            document_id: Optional document filter

        Returns:
            List of answer dictionaries
        """
        logger.info(f"Answering {len(questions)} competency questions...")

        answers = []

        for i, question in enumerate(questions, 1):
            logger.info(f"Processing question {i}/{len(questions)}: {question}")

            try:
                answer = self.answer_question(
                    question=question,
                    document_id=document_id,
                )
                answers.append(answer)

            except Exception as e:
                logger.error(f"Failed to answer question: {e}")
                answers.append({
                    "question": question,
                    "answer": f"Error: {str(e)}",
                    "confidence": 0.0,
                })

        return answers

    def get_sample_competency_questions(self) -> List[str]:
        """Get sample competency questions for legal contracts."""

        return [
            "What parties are involved in this contract?",
            "What are the main obligations of each party?",
            "What are the payment terms?",
            "What is the termination clause?",
            "What jurisdiction governs this agreement?",
            "Are there any confidentiality obligations?",
            "What are the liability limitations?",
            "What intellectual property rights are granted?",
            "What is the contract duration?",
            "Are there any indemnification clauses?",
        ]
