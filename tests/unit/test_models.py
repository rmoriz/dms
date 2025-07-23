"""Unit tests for data models"""

import pytest
from datetime import datetime
from dms.models import DocumentContent, TextChunk, CategoryResult


class TestDocumentContent:
    """Test DocumentContent model"""
    
    def test_document_content_creation(self):
        """Test creating DocumentContent instance"""
        doc = DocumentContent(
            file_path="/path/to/doc.pdf",
            text="Sample text content",
            page_count=5,
            file_size=1024,
            import_date=datetime.now(),
            directory_structure="2024/03/Rechnungen",
            ocr_used=False,
            text_extraction_method="direct",
            processing_time=1.5
        )
        
        assert doc.file_path == "/path/to/doc.pdf"
        assert doc.text == "Sample text content"
        assert doc.page_count == 5
        assert doc.ocr_used is False


class TestTextChunk:
    """Test TextChunk model"""
    
    def test_text_chunk_creation(self):
        """Test creating TextChunk instance"""
        chunk = TextChunk(
            id="chunk_1",
            document_id="doc_1",
            content="This is a text chunk",
            page_number=1,
            chunk_index=0
        )
        
        assert chunk.id == "chunk_1"
        assert chunk.document_id == "doc_1"
        assert chunk.content == "This is a text chunk"
        assert chunk.embedding is None


class TestCategoryResult:
    """Test CategoryResult model"""
    
    def test_category_result_creation(self):
        """Test creating CategoryResult instance"""
        result = CategoryResult(
            primary_category="Rechnung",
            confidence=0.85,
            entities={"issuer": "Test Company"},
            suggested_categories=[("Rechnung", 0.85), ("Vertrag", 0.15)]
        )
        
        assert result.primary_category == "Rechnung"
        assert result.confidence == 0.85
        assert result.entities["issuer"] == "Test Company"
        assert len(result.suggested_categories) == 2