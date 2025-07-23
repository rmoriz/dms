"""Core data models for DMS"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path


@dataclass
class DocumentContent:
    """Represents the content and metadata of a processed document"""
    file_path: str
    text: str
    page_count: int
    file_size: int
    import_date: datetime
    directory_structure: str  # e.g. "2024/03/Rechnungen"
    ocr_used: bool
    text_extraction_method: str  # "direct", "ocr", "hybrid"
    processing_time: float


@dataclass
class TextChunk:
    """Represents a chunk of text from a document for vector storage"""
    id: str
    document_id: str
    content: str
    page_number: int
    chunk_index: int
    embedding: Optional[List[float]] = None


@dataclass
class CategoryResult:
    """Result of document categorization"""
    primary_category: str  # "Rechnung", "Kontoauszug", etc.
    confidence: float
    entities: Dict[str, Any]  # Rechnungssteller, Bank, Beträge
    suggested_categories: List[Tuple[str, float]]


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document"""
    file_path: Path
    file_size: int
    page_count: int
    creation_date: Optional[datetime]
    modification_date: datetime
    directory_structure: str


@dataclass
class SearchResult:
    """Result from vector similarity search"""
    chunk: TextChunk
    similarity_score: float
    document_path: str
    page_number: int


@dataclass
class Source:
    """Source reference for RAG responses"""
    document_path: str
    page_number: int
    chunk_content: str
    relevance_score: float


@dataclass
class RAGResponse:
    """Response from RAG query"""
    answer: str
    sources: List[Source]
    confidence: float
    search_results_count: int