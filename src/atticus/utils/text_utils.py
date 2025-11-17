"""
Text processing utilities for document handling and chunking.

This module provides utilities for tokenization, text normalization,
and chunking strategies.
"""

import re
from typing import List, Optional

import tiktoken

from atticus.core.logger import get_logger

logger = get_logger(__name__)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Input text
        model: Model name for tokenizer

    Returns:
        Number of tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"Failed to count tokens with tiktoken: {e}. Using approximation.")
        # Fallback: approximate 1 token = 4 characters
        return len(text) // 4


def normalize_text(
    text: str,
    lowercase: bool = False,
    remove_special_chars: bool = False,
    normalize_whitespace: bool = True,
) -> str:
    """
    Normalize text with various options.

    Args:
        text: Input text
        lowercase: Convert to lowercase
        remove_special_chars: Remove special characters
        normalize_whitespace: Normalize whitespace

    Returns:
        Normalized text
    """
    if lowercase:
        text = text.lower()

    if remove_special_chars:
        # Keep alphanumeric, spaces, and basic punctuation
        text = re.sub(r"[^a-zA-Z0-9\s.,;:!?-]", "", text)

    if normalize_whitespace:
        # Replace multiple spaces/newlines with single space
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

    return text


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    separator: str = "\n",
) -> List[str]:
    """
    Chunk text with overlap.

    Args:
        text: Input text
        chunk_size: Target chunk size in tokens
        overlap: Overlap size in tokens
        separator: Preferred split separator

    Returns:
        List of text chunks
    """
    # Split by separator first
    segments = text.split(separator)

    chunks = []
    current_chunk = []
    current_size = 0

    for segment in segments:
        segment_tokens = count_tokens(segment)

        # If single segment exceeds chunk size, split it
        if segment_tokens > chunk_size:
            # Add current chunk if not empty
            if current_chunk:
                chunks.append(separator.join(current_chunk))
                current_chunk = []
                current_size = 0

            # Split large segment
            words = segment.split()
            temp_chunk = []
            temp_size = 0

            for word in words:
                word_tokens = count_tokens(word)
                if temp_size + word_tokens > chunk_size:
                    if temp_chunk:
                        chunks.append(" ".join(temp_chunk))
                    temp_chunk = [word]
                    temp_size = word_tokens
                else:
                    temp_chunk.append(word)
                    temp_size += word_tokens

            if temp_chunk:
                chunks.append(" ".join(temp_chunk))

        # Add segment to current chunk
        elif current_size + segment_tokens <= chunk_size:
            current_chunk.append(segment)
            current_size += segment_tokens
        else:
            # Start new chunk
            chunks.append(separator.join(current_chunk))

            # Add overlap from previous chunk
            overlap_segments = []
            overlap_size = 0
            for seg in reversed(current_chunk):
                seg_tokens = count_tokens(seg)
                if overlap_size + seg_tokens <= overlap:
                    overlap_segments.insert(0, seg)
                    overlap_size += seg_tokens
                else:
                    break

            current_chunk = overlap_segments + [segment]
            current_size = overlap_size + segment_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(separator.join(current_chunk))

    return chunks


def chunk_text_hierarchical(
    text: str,
    section_size: int = 1000,
    clause_size: int = 500,
    overlap: int = 100,
) -> List[dict]:
    """
    Hierarchical chunking strategy for legal documents.

    Creates chunks at multiple levels:
    - Level 0: Full document
    - Level 1: Sections (larger chunks)
    - Level 2: Clauses (smaller chunks)

    Args:
        text: Input text
        section_size: Target size for section-level chunks
        clause_size: Target size for clause-level chunks
        overlap: Overlap size

    Returns:
        List of chunk dictionaries with metadata
    """
    chunks = []

    # Level 0: Full document
    chunks.append(
        {
            "text": text,
            "level": 0,
            "chunk_type": "document",
            "index": 0,
            "parent_index": None,
        }
    )

    # Level 1: Sections (split by double newlines or section markers)
    section_pattern = r"\n\n+|(?:Section|Article|Clause)\s+\d+"
    sections = re.split(section_pattern, text)

    section_chunks = []
    for i, section in enumerate(sections):
        if section.strip():
            section_chunks.append(
                {
                    "text": section.strip(),
                    "level": 1,
                    "chunk_type": "section",
                    "index": len(chunks),
                    "parent_index": 0,
                }
            )
            chunks.append(section_chunks[-1])

    # Level 2: Clauses (further split sections)
    for section_chunk in section_chunks:
        clause_texts = chunk_text(
            section_chunk["text"],
            chunk_size=clause_size,
            overlap=overlap,
            separator="\n",
        )

        for j, clause_text in enumerate(clause_texts):
            chunks.append(
                {
                    "text": clause_text,
                    "level": 2,
                    "chunk_type": "clause",
                    "index": len(chunks),
                    "parent_index": section_chunk["index"],
                }
            )

    return chunks


def extract_sections(text: str) -> List[dict]:
    """
    Extract sections from legal document.

    Identifies section headers and extracts content.

    Args:
        text: Input text

    Returns:
        List of sections with titles and content
    """
    sections = []

    # Common section patterns in legal documents
    patterns = [
        r"(?:Section|Article|Clause)\s+(\d+(?:\.\d+)*)\s*[:\-]?\s*([^\n]+)",
        r"(\d+(?:\.\d+)*)\.\s+([A-Z][^\n]+)",
        r"([A-Z\s]+):\s*\n",
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            section_num = match.group(1) if len(match.groups()) > 1 else None
            section_title = match.group(2) if len(match.groups()) > 1 else match.group(1)

            sections.append(
                {
                    "number": section_num,
                    "title": section_title.strip(),
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                }
            )

    # Extract content between sections
    for i, section in enumerate(sections):
        start = section["end_pos"]
        end = sections[i + 1]["start_pos"] if i + 1 < len(sections) else len(text)
        section["content"] = text[start:end].strip()

    return sections


def detect_legal_entities(text: str) -> List[str]:
    """
    Simple regex-based detection of potential legal entities.

    This is a basic heuristic for initial entity detection.

    Args:
        text: Input text

    Returns:
        List of potential entity mentions
    """
    entities = []

    # Company names (Inc., LLC, Corp., etc.)
    company_pattern = r'\b[A-Z][a-zA-Z\s&]+(?:Inc\.|LLC|Corp\.|Corporation|Company|Ltd\.)\b'
    entities.extend(re.findall(company_pattern, text))

    # Dates
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
    entities.extend(re.findall(date_pattern, text))

    # Currency amounts
    currency_pattern = r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?'
    entities.extend(re.findall(currency_pattern, text))

    # Clause references
    clause_ref_pattern = r'(?:Section|Article|Clause)\s+\d+(?:\.\d+)*'
    entities.extend(re.findall(clause_ref_pattern, text))

    return list(set(entities))


def clean_legal_text(text: str) -> str:
    """
    Clean legal document text while preserving structure.

    Args:
        text: Input text

    Returns:
        Cleaned text
    """
    # Remove excessive whitespace but preserve paragraph breaks
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n\n\n+", "\n\n", text)

    # Remove page numbers and headers/footers (common patterns)
    text = re.sub(r"\n\s*Page\s+\d+\s*\n", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)

    # Fix common OCR errors in legal docs
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ;", ";")

    return text.strip()


def merge_fragmented_text(chunks: List[str], min_chunk_size: int = 100) -> List[str]:
    """
    Merge small fragmented chunks into larger ones.

    Args:
        chunks: List of text chunks
        min_chunk_size: Minimum chunk size in tokens

    Returns:
        Merged chunks
    """
    merged = []
    current = []
    current_size = 0

    for chunk in chunks:
        chunk_size = count_tokens(chunk)

        if chunk_size < min_chunk_size:
            current.append(chunk)
            current_size += chunk_size
        else:
            if current:
                merged.append(" ".join(current))
                current = []
                current_size = 0
            merged.append(chunk)

    if current:
        merged.append(" ".join(current))

    return merged
