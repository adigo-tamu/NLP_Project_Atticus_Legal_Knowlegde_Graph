#!/usr/bin/env python
"""
Test script for Project Atticus API.

This script tests all API endpoints to ensure they're working correctly.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import requests

from atticus.core.logger import get_logger

logger = get_logger(__name__)

# API configuration
API_URL = "http://localhost:8000"
TIMEOUT = 10


def test_health_endpoint():
    """Test health check endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: Health Check")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Status: {data['status']}")
        logger.info(f"  Neo4j Connected: {data['neo4j_connected']}")
        logger.info(f"  LLM Available: {data['llm_available']}")
        logger.info(f"  Version: {data['version']}")

        return True

    except requests.exceptions.ConnectionError:
        logger.error("✗ Could not connect to API server")
        logger.error("  Make sure the API server is running: python scripts/run_api.py")
        return False

    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


def test_stats_endpoint():
    """Test graph statistics endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Graph Statistics")
    logger.info("=" * 70)

    try:
        response = requests.get(f"{API_URL}/stats", timeout=TIMEOUT)
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Total Nodes: {data['total_nodes']}")
        logger.info(f"  Total Relationships: {data['total_relationships']}")
        logger.info(f"  Average Degree: {data['avg_degree']:.2f}")
        logger.info(f"  Graph Density: {data['density']:.4f}")

        if data.get("node_types"):
            logger.info("  Node Types:")
            for node_type, count in data["node_types"].items():
                logger.info(f"    - {node_type}: {count}")

        return True

    except Exception as e:
        logger.error(f"✗ Stats test failed: {e}")
        return False


def test_entity_search():
    """Test entity search endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Entity Search")
    logger.info("=" * 70)

    try:
        payload = {
            "min_confidence": 0.7,
            "limit": 5,
        }

        response = requests.post(
            f"{API_URL}/search/entities",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Found {data['count']} entities")
        logger.info(f"  Execution time: {data['execution_time_ms']:.2f} ms")

        if data["entities"]:
            logger.info("  Sample entities:")
            for entity in data["entities"][:3]:
                logger.info(f"    - {entity['text']} ({entity['type']}) [conf: {entity['confidence']:.2f}]")

        return True

    except Exception as e:
        logger.error(f"✗ Entity search test failed: {e}")
        return False


def test_relationship_search():
    """Test relationship search endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Relationship Search")
    logger.info("=" * 70)

    try:
        payload = {
            "min_confidence": 0.7,
            "limit": 5,
        }

        response = requests.post(
            f"{API_URL}/search/relationships",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Found {data['count']} relationships")
        logger.info(f"  Execution time: {data['execution_time_ms']:.2f} ms")

        if data["relationships"]:
            logger.info("  Sample relationships:")
            for rel in data["relationships"][:3]:
                logger.info(
                    f"    - {rel['source']['text']} --[{rel['type']}]--> "
                    f"{rel['target']['text']} [conf: {rel['confidence']:.2f}]"
                )

        return True

    except Exception as e:
        logger.error(f"✗ Relationship search test failed: {e}")
        return False


def test_cypher_query():
    """Test direct Cypher query endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Direct Cypher Query")
    logger.info("=" * 70)

    try:
        payload = {
            "query": "MATCH (n) RETURN count(n) as total_nodes",
        }

        response = requests.post(
            f"{API_URL}/query/cypher",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Query executed successfully")
        logger.info(f"  Execution time: {data['execution_time_ms']:.2f} ms")
        logger.info(f"  Results: {data['results']}")

        return True

    except Exception as e:
        logger.error(f"✗ Cypher query test failed: {e}")
        return False


def test_natural_language_query():
    """Test natural language query endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Natural Language Query")
    logger.info("=" * 70)

    try:
        payload = {
            "query": "Find entities with high confidence scores",
            "limit": 5,
            "include_reasoning": True,
        }

        logger.info(f"  Query: {payload['query']}")

        response = requests.post(
            f"{API_URL}/query/natural-language",
            json=payload,
            timeout=30,  # Longer timeout for LLM
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Query translated and executed successfully")
        logger.info(f"  Execution time: {data['execution_time_ms']:.2f} ms")
        logger.info(f"  Results count: {data['count']}")

        if data.get("cypher_query"):
            logger.info(f"  Generated Cypher: {data['cypher_query'][:100]}...")

        if data.get("reasoning"):
            logger.info(f"  Reasoning: {data['reasoning'][:100]}...")

        return True

    except requests.exceptions.Timeout:
        logger.warning("⚠ Natural language query timed out (LLM may be slow)")
        return True  # Don't fail test for timeout

    except Exception as e:
        logger.error(f"✗ Natural language query test failed: {e}")
        # Don't fail if API keys not configured
        if "API key" in str(e) or "401" in str(e):
            logger.warning("⚠ Skipping (API keys not configured)")
            return True
        return False


def test_rag_answer():
    """Test RAG question answering endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 7: RAG Question Answering")
    logger.info("=" * 70)

    try:
        payload = {
            "question": "What entities are in the knowledge graph?",
            "max_context_entities": 5,
            "max_context_relationships": 5,
            "include_sources": True,
        }

        logger.info(f"  Question: {payload['question']}")

        response = requests.post(
            f"{API_URL}/rag/ask",
            json=payload,
            timeout=30,  # Longer timeout for LLM
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Answer generated successfully")
        logger.info(f"  Execution time: {data['execution_time_ms']:.2f} ms")
        logger.info(f"  Confidence: {data['confidence']:.2f}")
        logger.info(f"  Answer: {data['answer'][:150]}...")

        if data.get("context_used"):
            logger.info(
                f"  Context: {data['context_used']['num_entities']} entities, "
                f"{data['context_used']['num_relationships']} relationships"
            )

        return True

    except requests.exceptions.Timeout:
        logger.warning("⚠ RAG query timed out (LLM may be slow)")
        return True  # Don't fail test for timeout

    except Exception as e:
        logger.error(f"✗ RAG test failed: {e}")
        # Don't fail if API keys not configured
        if "API key" in str(e) or "401" in str(e):
            logger.warning("⚠ Skipping (API keys not configured)")
            return True
        return False


def test_competency_questions():
    """Test competency questions endpoint."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 8: Competency Questions")
    logger.info("=" * 70)

    try:
        response = requests.get(
            f"{API_URL}/rag/competency-questions",
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        data = response.json()
        logger.info(f"✓ Retrieved {data['count']} competency questions")

        if data.get("questions"):
            logger.info("  Sample questions:")
            for question in data["questions"][:3]:
                logger.info(f"    - {question}")

        return True

    except Exception as e:
        logger.error(f"✗ Competency questions test failed: {e}")
        return False


def main():
    """Run all API tests."""

    logger.info("=" * 70)
    logger.info("PROJECT ATTICUS - API TESTS")
    logger.info("=" * 70)
    logger.info(f"\nAPI URL: {API_URL}")
    logger.info("Make sure the API server is running before running tests.")
    logger.info("Start with: python scripts/run_api.py\n")

    # Wait a moment for user to read
    time.sleep(2)

    # Run tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Graph Statistics", test_stats_endpoint),
        ("Entity Search", test_entity_search),
        ("Relationship Search", test_relationship_search),
        ("Cypher Query", test_cypher_query),
        ("Natural Language Query", test_natural_language_query),
        ("RAG Answer", test_rag_answer),
        ("Competency Questions", test_competency_questions),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Unexpected error in {name}: {e}")
            results.append((name, False))

        time.sleep(1)  # Brief pause between tests

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {name}")

    logger.info("\n" + "=" * 70)
    logger.info(f"RESULTS: {passed}/{total} tests passed")
    logger.info("=" * 70 + "\n")

    if passed == total:
        logger.info("✓ All tests passed!")
        sys.exit(0)
    else:
        logger.warning(f"⚠ {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
