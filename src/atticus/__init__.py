"""
Project Atticus - Legal Knowledge Graph Construction System

An LLM-driven system for automatically constructing knowledge graphs from legal documents.
"""

__version__ = "1.0.0"
__author__ = "Aditya Gollamudi"
__license__ = "MIT"

from atticus.core.config import Config, get_config
from atticus.core.logger import get_logger

__all__ = ["Config", "get_config", "get_logger", "__version__"]
