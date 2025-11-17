#!/usr/bin/env python
"""
Run the Project Atticus API server.

This script starts the FastAPI server with uvicorn.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import uvicorn

from atticus.core.config import get_config
from atticus.core.logger import get_logger

logger = get_logger(__name__)


def main():
    """Run API server."""

    logger.info("=" * 70)
    logger.info("PROJECT ATTICUS - REST API SERVER")
    logger.info("=" * 70)

    try:
        # Check configuration
        config = get_config()

        logger.info("\nConfiguration:")
        logger.info(f"  Neo4j URI: {config.neo4j.uri}")
        logger.info(f"  LLM Provider: {config.llm.provider}")
        logger.info(f"  LLM Model: {config.llm.model}")

        # Check API keys
        if not config.validate_api_keys():
            logger.warning("\n⚠ WARNING: No API keys configured!")
            logger.warning("  Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env")
            logger.warning("  Some features may not work without valid API keys.\n")

        # API server configuration
        host = "0.0.0.0"
        port = 8000
        reload = True  # Enable auto-reload in development

        logger.info(f"\nStarting API server on http://{host}:{port}")
        logger.info(f"  Docs: http://{host}:{port}/docs")
        logger.info(f"  ReDoc: http://{host}:{port}/redoc")
        logger.info(f"  Health: http://{host}:{port}/health")
        logger.info("\n" + "=" * 70 + "\n")

        # Run server
        uvicorn.run(
            "atticus.api.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )

    except KeyboardInterrupt:
        logger.info("\n\nShutting down server...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"\n✗ Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
