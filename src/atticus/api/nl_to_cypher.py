"""
Natural Language to Cypher Query Translation.

Uses LLMs to translate natural language questions into Cypher queries
for Neo4j graph database.
"""

import json
import re
from typing import Dict, List, Optional, Tuple

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.graph.neo4j_manager import Neo4jManager
from atticus.graph.schema import GraphSchema
from atticus.utils.llm_client import get_llm_client

logger = get_logger(__name__)


class NLToCypherTranslator:
    """Translate natural language queries to Cypher."""

    def __init__(
        self,
        llm_model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        neo4j_manager: Optional[Neo4jManager] = None,
    ):
        """
        Initialize NL to Cypher translator.

        Args:
            llm_model: LLM model to use
            llm_provider: LLM provider (openai, anthropic)
            neo4j_manager: Neo4j manager instance
        """
        self.config = get_config()
        self.llm_client = get_llm_client(
            model=llm_model or self.config.llm.model,
            provider=llm_provider or self.config.llm.provider,
        )
        self.db = neo4j_manager or Neo4jManager()
        self.schema = GraphSchema()

        # Build schema context for LLM
        self.schema_context = self._build_schema_context()

        logger.info("NL to Cypher translator initialized")

    def _build_schema_context(self) -> str:
        """Build schema context string for LLM prompt."""

        context = "# Neo4j Graph Schema\n\n"

        # Node types
        context += "## Node Types (Entity Types):\n"
        for node_type in self.schema.node_labels:
            context += f"- {node_type}\n"

        context += "\n## Relationship Types:\n"
        for rel_type in self.schema.relationship_types:
            context += f"- {rel_type}\n"

        context += "\n## Common Node Properties:\n"
        context += "- id: Unique identifier (string)\n"
        context += "- text: Entity text (string)\n"
        context += "- type: Entity type (string)\n"
        context += "- confidence: Confidence score (float, 0-1)\n"
        context += "- document_id: Source document ID (string)\n"
        context += "- context: Surrounding text context (string)\n"

        context += "\n## Common Relationship Properties:\n"
        context += "- id: Unique identifier (string)\n"
        context += "- confidence: Confidence score (float, 0-1)\n"
        context += "- evidence: Supporting text evidence (string)\n"
        context += "- document_id: Source document ID (string)\n"

        return context

    def translate(
        self,
        natural_language_query: str,
        document_id: Optional[str] = None,
        include_reasoning: bool = False,
    ) -> Tuple[str, Optional[str]]:
        """
        Translate natural language query to Cypher.

        Args:
            natural_language_query: Natural language question
            document_id: Optional document filter
            include_reasoning: Whether to return LLM reasoning

        Returns:
            Tuple of (cypher_query, reasoning)
        """
        logger.info(f"Translating NL query: {natural_language_query}")

        # Build prompt
        prompt = self._build_translation_prompt(
            natural_language_query=natural_language_query,
            document_id=document_id,
        )

        # System prompt
        system_prompt = """You are an expert Neo4j Cypher query translator.
Your task is to translate natural language questions into valid Cypher queries.

Important guidelines:
1. Generate ONLY valid Cypher syntax
2. Use MATCH patterns for graph traversal
3. Use WHERE clauses for filtering
4. Return relevant properties with RETURN
5. Add LIMIT clauses to prevent large result sets
6. Use parameters for values when appropriate
7. Consider case-insensitive matching with toLower() when appropriate
8. Use relationship direction carefully (-> vs --)

Output format:
{
  "cypher": "MATCH ... RETURN ...",
  "reasoning": "Brief explanation of the query logic"
}
"""

        # Get translation
        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="json",
        )

        # Parse response
        try:
            response_data = json.loads(response)
            cypher_query = response_data.get("cypher", "")
            reasoning = response_data.get("reasoning", "")

            # Validate and sanitize
            cypher_query = self._sanitize_cypher(cypher_query)

            logger.info(f"Generated Cypher: {cypher_query}")

            if include_reasoning:
                return cypher_query, reasoning
            else:
                return cypher_query, None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Try to extract Cypher from text
            cypher_query = self._extract_cypher_from_text(response)
            return cypher_query, None

    def _build_translation_prompt(
        self,
        natural_language_query: str,
        document_id: Optional[str] = None,
    ) -> str:
        """Build prompt for NL to Cypher translation."""

        prompt = f"""{self.schema_context}

# Task
Translate the following natural language question into a Neo4j Cypher query.

# Natural Language Question
"{natural_language_query}"
"""

        if document_id:
            prompt += f"""
# Additional Constraint
- Filter results to document_id: "{document_id}"
"""

        prompt += """
# Example Translations

Example 1:
Question: "What obligations does TechCorp have?"
Cypher: MATCH (party:Legal_Party)-[:OBLIGATES]->(obligation:Obligation)
        WHERE toLower(party.text) CONTAINS 'techcorp'
        RETURN party.text as party, obligation.text as obligation, obligation.confidence
        LIMIT 20

Example 2:
Question: "Find all relationships between ABC Corp and payment terms"
Cypher: MATCH (source {text: 'ABC Corp'})-[r]->(target)
        WHERE toLower(target.text) CONTAINS 'payment'
        RETURN source.text, type(r), target.text, r.confidence
        LIMIT 20

Example 3:
Question: "What legal concepts are referenced in the document?"
Cypher: MATCH (n:Legal_Concept)
        RETURN n.text, n.confidence, n.document_id
        ORDER BY n.confidence DESC
        LIMIT 20

Example 4:
Question: "Show me the path from Contract to Termination Clause"
Cypher: MATCH path = (source)-[*1..3]-(target)
        WHERE toLower(source.text) CONTAINS 'contract'
        AND toLower(target.text) CONTAINS 'termination'
        RETURN path
        LIMIT 5

# Your Translation
Generate a valid Cypher query for the question above. Return as JSON with fields "cypher" and "reasoning".
"""

        return prompt

    def _sanitize_cypher(self, cypher: str) -> str:
        """Sanitize and validate Cypher query."""

        # Remove markdown code blocks if present
        cypher = re.sub(r"```cypher\s*", "", cypher)
        cypher = re.sub(r"```\s*", "", cypher)

        # Remove leading/trailing whitespace
        cypher = cypher.strip()

        # Basic validation
        if not cypher.upper().startswith(("MATCH", "RETURN", "WITH", "CALL")):
            logger.warning(f"Potentially invalid Cypher query: {cypher}")

        # Ensure LIMIT clause exists (safety)
        if "LIMIT" not in cypher.upper():
            cypher += "\nLIMIT 20"

        return cypher

    def _extract_cypher_from_text(self, text: str) -> str:
        """Extract Cypher query from text response."""

        # Try to find MATCH ... RETURN pattern
        match = re.search(
            r"(MATCH.*?RETURN.*?)(?:\n|$)", text, re.IGNORECASE | re.DOTALL
        )

        if match:
            return self._sanitize_cypher(match.group(1))

        # Fallback: return simple query
        logger.warning("Could not extract Cypher from text, using fallback")
        return "MATCH (n) RETURN n LIMIT 10"

    def translate_with_examples(
        self,
        natural_language_query: str,
        few_shot_examples: List[Dict[str, str]],
        document_id: Optional[str] = None,
    ) -> str:
        """
        Translate with custom few-shot examples.

        Args:
            natural_language_query: Natural language question
            few_shot_examples: List of {"question": "...", "cypher": "..."} examples
            document_id: Optional document filter

        Returns:
            Cypher query
        """

        prompt = f"""{self.schema_context}

# Task
Translate the following natural language question into a Neo4j Cypher query.

# Examples
"""

        for i, example in enumerate(few_shot_examples, 1):
            prompt += f"""
Example {i}:
Question: "{example['question']}"
Cypher: {example['cypher']}
"""

        prompt += f"""
# Natural Language Question
"{natural_language_query}"
"""

        if document_id:
            prompt += f"""
# Constraint: Filter to document_id = "{document_id}"
"""

        prompt += """
# Your Translation
Generate a valid Cypher query as JSON: {"cypher": "...", "reasoning": "..."}
"""

        system_prompt = "You are an expert Neo4j Cypher query translator."

        response = self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            response_format="json",
        )

        try:
            response_data = json.loads(response)
            return self._sanitize_cypher(response_data.get("cypher", ""))
        except json.JSONDecodeError:
            return self._extract_cypher_from_text(response)

    def validate_query(self, cypher: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Cypher query syntax.

        Args:
            cypher: Cypher query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """

        try:
            # Try to explain the query (doesn't execute)
            self.db.execute_query(f"EXPLAIN {cypher}")
            return True, None
        except Exception as e:
            return False, str(e)

    def execute_query(
        self,
        cypher: str,
        parameters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Execute Cypher query and return results.

        Args:
            cypher: Cypher query
            parameters: Query parameters

        Returns:
            List of result records
        """

        logger.info(f"Executing Cypher: {cypher}")

        try:
            result = self.db.execute_query(cypher, parameters or {})
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def translate_and_execute(
        self,
        natural_language_query: str,
        document_id: Optional[str] = None,
        include_reasoning: bool = False,
    ) -> Tuple[List[Dict], str, Optional[str]]:
        """
        Translate and execute natural language query.

        Args:
            natural_language_query: Natural language question
            document_id: Optional document filter
            include_reasoning: Whether to return LLM reasoning

        Returns:
            Tuple of (results, cypher_query, reasoning)
        """

        # Translate
        cypher_query, reasoning = self.translate(
            natural_language_query=natural_language_query,
            document_id=document_id,
            include_reasoning=include_reasoning,
        )

        # Validate
        is_valid, error = self.validate_query(cypher_query)
        if not is_valid:
            logger.error(f"Invalid Cypher query: {error}")
            raise ValueError(f"Generated invalid Cypher: {error}")

        # Execute
        results = self.execute_query(cypher_query)

        return results, cypher_query, reasoning

    def get_common_queries(self) -> Dict[str, str]:
        """Get dictionary of common pre-defined queries."""

        return {
            "list_all_parties": """
                MATCH (n:Legal_Party)
                RETURN n.text as party, n.confidence, n.document_id
                ORDER BY n.confidence DESC
                LIMIT 20
            """,
            "list_all_obligations": """
                MATCH (n:Obligation)
                RETURN n.text as obligation, n.confidence, n.document_id
                ORDER BY n.confidence DESC
                LIMIT 20
            """,
            "find_high_confidence_entities": """
                MATCH (n)
                WHERE n.confidence > 0.9
                RETURN labels(n) as type, n.text, n.confidence, n.document_id
                ORDER BY n.confidence DESC
                LIMIT 20
            """,
            "relationship_distribution": """
                MATCH ()-[r]->()
                RETURN type(r) as relationship_type, count(r) as count
                ORDER BY count DESC
            """,
            "find_contradictions": """
                MATCH (source)-[r:CONTRADICTS]->(target)
                RETURN source.text, target.text, r.evidence, r.confidence
                LIMIT 20
            """,
        }
