#!/usr/bin/env python
"""
Database setup script for initializing Neo4j schema.

This script creates constraints, indexes, and initializes the knowledge graph schema.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from atticus.core.config import get_config
from atticus.core.logger import get_logger
from atticus.graph.neo4j_manager import Neo4jManager

logger = get_logger(__name__)


def main():
    """Initialize Neo4j database schema."""
    logger.info("Starting database initialization...")

    try:
        # Load configuration
        config = get_config()
        logger.info(f"Connecting to Neo4j at {config.neo4j.uri}")

        # Connect to Neo4j
        with Neo4jManager() as db:
            logger.info("Connected to Neo4j successfully")

            # Initialize schema
            logger.info("Creating constraints and indexes...")
            db.initialize_schema()

            # Get statistics
            stats = db.get_statistics()
            logger.info(f"Database statistics: {stats}")

            logger.info("Database initialization completed successfully!")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
