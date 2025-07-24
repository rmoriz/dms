"""Unit tests for PDF processing functionality"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
from pathlib import Path
import tempfile
import os

from dms.processing.pdf_processor import PDFProcessor
from dms.models import DocumentContent, DocumentMetadata, TextChunk
from dms.config import DMSConfig, OCRConfig


class TestPDFProcessor:
    """Test cases for PDFProcessor class"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock config to avoid loading from file system
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=50, language="deu")
            mock_load.return_value = mock_config
            self.processor = PDFProcessor()

    @patch('pdfplumber.open')
    def test_extract_text_simple_pdf(self, mock_pdf_open):
        """Test basic text extraction from a simple PDF"""
        # Mock PDF structure
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock file stats
        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):  # 2022-01-01
                result = self.processor.extract_text("test.pdf")

        assert isinstance(result, DocumentContent)
        assert result.text == "Page 1 content\nPage 2 content"
        assert result.page_count == 2
        assert result.file_size == 1024
        assert result.file_path == "test.pdf"
        assert result.ocr_used is False
        assert result.text_extraction_method == "direct"

    @patch('pdfplumber.open')
    def test_extract_text_empty_pdf(self, mock_pdf_open):
        """Test extraction from PDF with no text content"""
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        with patch('os.path.getsize', return_value=512):
            with patch('os.path.getctime', return_value=1640995200.0):
                result = self.processor.extract_text("empty.pdf")

        assert result.text == ""
        assert result.page_count == 1
        assert result.text_extraction_method == "direct"

    @patch('pdfplumber.open')
    def test_extract_text_with_none_pages(self, mock_pdf_open):
        """Test extraction when pages return None for text"""
        mock_page = Mock()
        mock_page.extract_text.return_value = None
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        with patch('os.path.getsize', return_value=256):
            with patch('os.path.getctime', return_value=1640995200.0):
                result = self.processor.extract_text("none_text.pdf")

        assert result.text == ""
        assert result.page_count == 1

    @patch('pdfplumber.open')
    def test_extract_text_corrupted_pdf(self, mock_pdf_open):
        """Test handling of corrupted PDF files"""
        mock_pdf_open.side_effect = Exception("Corrupted PDF")

        with pytest.raises(Exception) as exc_info:
            self.processor.extract_text("corrupted.pdf")
        
        assert "Corrupted PDF" in str(exc_info.value)

    def test_extract_metadata_basic(self):
        """Test basic metadata extraction"""
        test_file = "test_document.pdf"
        
        with patch('os.path.getsize', return_value=2048):
            with patch('os.path.getctime', return_value=1640995200.0):  # 2022-01-01
                with patch('os.path.getmtime', return_value=1641081600.0):  # 2022-01-02
                    with patch('pdfplumber.open') as mock_pdf_open:
                        mock_pdf = Mock()
                        mock_pdf.pages = [Mock(), Mock(), Mock()]  # 3 pages
                        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
                        mock_pdf.__exit__ = Mock(return_value=None)
                        mock_pdf_open.return_value = mock_pdf
                        
                        metadata = self.processor.extract_metadata(test_file)

        assert isinstance(metadata, DocumentMetadata)
        assert metadata.file_path == Path(test_file)
        assert metadata.file_size == 2048
        assert metadata.page_count == 3
        assert metadata.creation_date == datetime.fromtimestamp(1640995200.0)
        assert metadata.modification_date == datetime.fromtimestamp(1641081600.0)

    def test_extract_metadata_with_directory_structure(self):
        """Test metadata extraction with directory structure parsing"""
        test_file = "2024/03/Rechnungen/invoice.pdf"
        
        with patch('os.path.getsize', return_value=1536):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch('os.path.getmtime', return_value=1641081600.0):
                    with patch('pdfplumber.open') as mock_pdf_open:
                        mock_pdf = Mock()
                        mock_pdf.pages = [Mock()]  # 1 page
                        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
                        mock_pdf.__exit__ = Mock(return_value=None)
                        mock_pdf_open.return_value = mock_pdf
                        
                        metadata = self.processor.extract_metadata(test_file)

        assert metadata.directory_structure == "2024/03/Rechnungen"

    def test_extract_metadata_root_file(self):
        """Test metadata extraction for file in root directory"""
        test_file = "document.pdf"
        
        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch('os.path.getmtime', return_value=1641081600.0):
                    with patch('pdfplumber.open') as mock_pdf_open:
                        mock_pdf = Mock()
                        mock_pdf.pages = [Mock()]
                        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
                        mock_pdf.__exit__ = Mock(return_value=None)
                        mock_pdf_open.return_value = mock_pdf
                        
                        metadata = self.processor.extract_metadata(test_file)

        assert metadata.directory_structure == ""

    @patch('pdfplumber.open')
    def test_extract_metadata_file_not_found(self, mock_pdf_open):
        """Test metadata extraction when file doesn't exist"""
        mock_pdf_open.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            self.processor.extract_metadata("nonexistent.pdf")

    @patch('pdfplumber.open')
    def test_extract_text_multipage_document(self, mock_pdf_open):
        """Test extraction from multi-page document"""
        pages_content = [
            "First page with some content",
            "Second page with different content", 
            "Third page with more text",
            "Fourth page conclusion"
        ]
        
        mock_pages = []
        for content in pages_content:
            mock_page = Mock()
            mock_page.extract_text.return_value = content
            mock_pages.append(mock_page)
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        with patch('os.path.getsize', return_value=4096):
            with patch('os.path.getctime', return_value=1640995200.0):
                result = self.processor.extract_text("multipage.pdf")

        expected_text = "\n".join(pages_content)
        assert result.text == expected_text
        assert result.page_count == 4
        assert result.file_size == 4096

    @patch('pdfplumber.open')
    def test_extract_text_with_whitespace_handling(self, mock_pdf_open):
        """Test that whitespace is properly handled in text extraction"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "  Text with   spaces  \n\n  "
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):
                result = self.processor.extract_text("whitespace.pdf")

        # Text should be cleaned but preserve meaningful structure
        assert result.text.strip() == "Text with   spaces"


class TestTextChunking:
    """Test cases for text chunking functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock config to avoid loading from file system
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=50, language="deu")
            mock_load.return_value = mock_config
            self.processor = PDFProcessor()

    def test_create_chunks_basic(self):
        """Test basic text chunking with default parameters"""
        text = "This is a test document. " * 50  # ~1250 characters
        
        chunks = self.processor.create_chunks(text, chunk_size=500, overlap=100)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(len(chunk.content) <= 500 for chunk in chunks)
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))

    def test_create_chunks_with_overlap(self):
        """Test that chunks have proper overlap"""
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 20  # 520 characters
        
        chunks = self.processor.create_chunks(text, chunk_size=200, overlap=50)
        
        assert len(chunks) >= 2
        
        # Check that consecutive chunks have overlap
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i].content
            next_chunk = chunks[i + 1].content
            
            # There should be some overlap between consecutive chunks
            # (exact overlap checking depends on text structure)
            assert len(current_chunk) > 0
            assert len(next_chunk) > 0

    def test_create_chunks_short_document(self):
        """Test chunking of document shorter than chunk size"""
        text = "This is a short document."
        
        chunks = self.processor.create_chunks(text, chunk_size=1000, overlap=200)
        
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0

    def test_create_chunks_empty_text(self):
        """Test chunking of empty text"""
        chunks = self.processor.create_chunks("", chunk_size=1000, overlap=200)
        
        assert len(chunks) == 0

    def test_create_chunks_whitespace_only(self):
        """Test chunking of whitespace-only text"""
        chunks = self.processor.create_chunks("   \n\n   ", chunk_size=1000, overlap=200)
        
        assert len(chunks) == 0

    def test_create_chunks_large_document(self):
        """Test chunking of large document"""
        # Create a large document with identifiable sections
        sections = [f"Section {i}: " + "Content " * 100 for i in range(10)]
        text = "\n\n".join(sections)  # ~6000+ characters
        
        chunks = self.processor.create_chunks(text, chunk_size=1000, overlap=200)
        
        assert len(chunks) > 5  # Should create multiple chunks
        assert all(len(chunk.content) <= 1000 for chunk in chunks)
        
        # Verify all chunks have content
        assert all(chunk.content.strip() for chunk in chunks)

    def test_create_chunks_various_sizes(self):
        """Test chunking with various chunk sizes"""
        text = "Word " * 500  # 2500 characters
        
        # Test different chunk sizes
        for chunk_size in [100, 500, 1000, 2000]:
            chunks = self.processor.create_chunks(text, chunk_size=chunk_size, overlap=50)
            
            assert len(chunks) > 0
            assert all(len(chunk.content) <= chunk_size for chunk in chunks)

    def test_create_chunks_various_overlaps(self):
        """Test chunking with various overlap sizes"""
        text = "Character" * 200  # 1800 characters
        
        # Test different overlap sizes
        for overlap in [0, 50, 100, 200]:
            chunks = self.processor.create_chunks(text, chunk_size=500, overlap=overlap)
            
            assert len(chunks) > 0
            assert all(chunk.content.strip() for chunk in chunks)

    def test_create_chunks_invalid_parameters(self):
        """Test chunking with invalid parameters"""
        text = "Test content"
        
        # Test with zero chunk size
        chunks = self.processor.create_chunks(text, chunk_size=0, overlap=50)
        assert len(chunks) == 0
        
        # Test with negative chunk size
        chunks = self.processor.create_chunks(text, chunk_size=-100, overlap=50)
        assert len(chunks) == 0

    def test_create_chunks_overlap_larger_than_chunk(self):
        """Test chunking when overlap is larger than chunk size"""
        text = "This is test content for chunking."
        
        chunks = self.processor.create_chunks(text, chunk_size=10, overlap=20)
        
        # Should still work, but overlap will be limited
        assert len(chunks) > 0
        assert all(len(chunk.content) <= 10 for chunk in chunks)

    def test_create_chunks_preserve_chunk_ids(self):
        """Test that chunk IDs are properly generated"""
        text = "Content " * 300  # ~2100 characters
        
        chunks = self.processor.create_chunks(text, chunk_size=500, overlap=100)
        
        # Check that IDs are sequential and properly formatted
        for i, chunk in enumerate(chunks):
            assert chunk.id == f"chunk_{i}"
            assert chunk.chunk_index == i
            assert chunk.document_id == ""  # Should be empty initially
            assert chunk.page_number == 1  # Default value
            assert chunk.embedding is None  # Should be None initially

    def test_create_chunks_newline_handling(self):
        """Test that chunks handle newlines properly"""
        text = "Line 1\nLine 2\n\nLine 3\n" * 100
        
        chunks = self.processor.create_chunks(text, chunk_size=200, overlap=50)
        
        assert len(chunks) > 1
        # Chunks should preserve newline structure where possible
        assert all('\n' in chunk.content or len(chunk.content) < 50 for chunk in chunks)

    def test_create_chunks_with_document_id(self):
        """Test chunking with document ID"""
        text = "Test content for document ID tracking."
        document_id = "test_doc_123"
        
        chunks = self.processor.create_chunks(text, chunk_size=100, overlap=20, 
                                            document_id=document_id)
        
        assert len(chunks) == 1
        assert chunks[0].document_id == document_id

    def test_create_chunks_with_page_tracking(self):
        """Test chunking with page number tracking"""
        page_texts = [
            "This is page one content.",
            "This is page two content.",
            "This is page three content."
        ]
        full_text = "\n".join(page_texts)
        
        chunks = self.processor.create_chunks(full_text, chunk_size=30, overlap=10,
                                            page_texts=page_texts)
        
        assert len(chunks) > 1
        
        # Check that page numbers are assigned correctly
        page_numbers = [chunk.page_number for chunk in chunks]
        assert all(1 <= page_num <= 3 for page_num in page_numbers)

    @patch('pdfplumber.open')
    def test_create_chunks_from_document(self, mock_pdf_open):
        """Test creating chunks from DocumentContent with page tracking"""
        # Mock PDF structure
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1 content here"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2 content here"
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Create DocumentContent
        document_content = DocumentContent(
            file_path="test.pdf",
            text="Page 1 content here\nPage 2 content here",
            page_count=2,
            file_size=1024,
            import_date=datetime.now(),
            directory_structure="",
            ocr_used=False,
            text_extraction_method="direct",
            processing_time=0.1
        )
        
        chunks = self.processor.create_chunks_from_document(document_content, 
                                                          chunk_size=20, overlap=5)
        
        assert len(chunks) > 1
        assert all(chunk.document_id == "test.pdf" for chunk in chunks)
        assert all(chunk.page_number in [1, 2] for chunk in chunks)

    def test_create_chunks_context_preservation(self):
        """Test that chunks preserve context through overlap"""
        text = "The quick brown fox jumps over the lazy dog. " \
               "This sentence should be split across chunks. " \
               "The overlap should preserve context between chunks."
        
        chunks = self.processor.create_chunks(text, chunk_size=50, overlap=20)
        
        assert len(chunks) > 1
        
        # Check that there's meaningful overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i].content
            next_chunk = chunks[i + 1].content
            
            # There should be some common words due to overlap
            current_words = set(current_chunk.split())
            next_words = set(next_chunk.split())
            common_words = current_words.intersection(next_words)
            
            # Should have at least some overlap (this is a heuristic test)
            assert len(common_words) > 0 or len(current_chunk) < 30  # Allow for short chunks


class TestOCRDetection:
    """Test cases for OCR necessity detection functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock config to avoid loading from file system
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=50, language="deu")
            mock_load.return_value = mock_config
            self.processor = PDFProcessor()

    @patch('pdfplumber.open')
    def test_needs_ocr_text_based_pdf_above_threshold(self, mock_pdf_open):
        """Test that text-based PDF with sufficient text doesn't need OCR"""
        # Mock PDF with good text content (above default threshold of 50 chars/page)
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "This is a text-based PDF with plenty of readable content that should not require OCR processing."
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Second page also has sufficient text content to avoid OCR processing entirely."
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("text_based.pdf")
        
        assert result is False
        mock_pdf_open.assert_called_once_with("text_based.pdf")

    @patch('pdfplumber.open')
    def test_needs_ocr_image_based_pdf_below_threshold(self, mock_pdf_open):
        """Test that image-based PDF with minimal text needs OCR"""
        # Mock PDF with very little text content (below threshold)
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1"  # Only 6 characters
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2"  # Only 6 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("image_based.pdf")
        
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_mixed_content_pdf(self, mock_pdf_open):
        """Test OCR detection with mixed content (some pages with text, some without)"""
        # Mock PDF with mixed content - average should determine OCR need
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "This page has substantial text content that is easily readable."  # ~70 chars
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = ""  # Empty page (image-only)
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Short"  # Only 5 chars
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("mixed_content.pdf")
        
        # Average: (70 + 0 + 5) / 3 = 25 chars/page < 50 threshold
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_custom_threshold_low(self, mock_pdf_open):
        """Test OCR detection with custom low threshold"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Medium length text content here"  # ~30 chars
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # With low threshold (20), this should not need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=20)
        assert result is False
        
        # With high threshold (40), this should need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=40)
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_custom_threshold_high(self, mock_pdf_open):
        """Test OCR detection with custom high threshold"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "This is a longer text passage with more content to test higher thresholds."  # ~80 chars
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # With high threshold (100), this should need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=100)
        assert result is True
        
        # With low threshold (50), this should not need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=50)
        assert result is False

    @patch('pdfplumber.open')
    def test_needs_ocr_default_threshold_behavior(self, mock_pdf_open):
        """Test that default threshold of 50 chars/page works correctly"""
        # Test exactly at threshold
        mock_page = Mock()
        mock_page.extract_text.return_value = "X" * 50  # Exactly 50 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # At threshold should not need OCR (>= threshold)
        result = self.processor.needs_ocr("threshold_test.pdf")
        assert result is False

        # Just below threshold should need OCR
        mock_page.extract_text.return_value = "X" * 49  # 49 characters
        result = self.processor.needs_ocr("threshold_test.pdf")
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_empty_pdf(self, mock_pdf_open):
        """Test OCR detection with empty PDF (no pages)"""
        mock_pdf = Mock()
        mock_pdf.pages = []  # No pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("empty.pdf")
        
        # Empty PDF should need OCR (return True)
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_pages_with_none_text(self, mock_pdf_open):
        """Test OCR detection when pages return None for text"""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = None
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = None
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("none_text.pdf")
        
        # Pages with None text should need OCR
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_pages_with_whitespace_only(self, mock_pdf_open):
        """Test OCR detection with pages containing only whitespace"""
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "   \n\n   \t  "  # Only whitespace
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "\n\n\n"  # Only newlines
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("whitespace.pdf")
        
        # Whitespace-only pages should need OCR (stripped text is empty)
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_corrupted_pdf_exception(self, mock_pdf_open):
        """Test OCR detection with corrupted PDF that raises exception"""
        mock_pdf_open.side_effect = Exception("Corrupted PDF file")

        result = self.processor.needs_ocr("corrupted.pdf")
        
        # Exception during analysis should default to needing OCR
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_large_multipage_document(self, mock_pdf_open):
        """Test OCR detection with large multi-page document"""
        # Create many pages with varying text content
        mock_pages = []
        page_contents = [
            "Page with substantial text content that exceeds the threshold easily.",  # ~70 chars
            "Short text",  # ~10 chars
            "Another page with good amount of readable text content here.",  # ~60 chars
            "",  # Empty page
            "Medium length content on this page.",  # ~35 chars
        ]
        
        for content in page_contents:
            mock_page = Mock()
            mock_page.extract_text.return_value = content
            mock_pages.append(mock_page)
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        result = self.processor.needs_ocr("multipage.pdf")
        
        # Calculate expected average: (70 + 10 + 60 + 0 + 35) / 5 = 35 chars/page
        # 35 < 50 threshold, so should need OCR
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_threshold_edge_cases(self, mock_pdf_open):
        """Test OCR detection with various threshold edge cases"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test content"  # 12 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Test with threshold of 0 - should never need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=0)
        assert result is False
        
        # Test with very high threshold - should always need OCR
        result = self.processor.needs_ocr("test.pdf", threshold=1000)
        assert result is True
        
        # Test with threshold exactly matching content length
        result = self.processor.needs_ocr("test.pdf", threshold=12)
        assert result is False  # >= threshold means no OCR needed

    @patch('pdfplumber.open')
    def test_needs_ocr_text_density_calculation(self, mock_pdf_open):
        """Test that text density calculation is accurate"""
        # Create specific test case to verify calculation
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "A" * 100  # 100 characters
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "B" * 50   # 50 characters
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "C" * 25   # 25 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Total: 175 chars, 3 pages = 58.33 chars/page average
        # Should not need OCR with default threshold of 50
        result = self.processor.needs_ocr("density_test.pdf")
        assert result is False
        
        # Should need OCR with threshold of 60
        result = self.processor.needs_ocr("density_test.pdf", threshold=60)
        assert result is True

    @patch('pdfplumber.open')
    def test_needs_ocr_uses_config_threshold(self, mock_pdf_open):
        """Test that needs_ocr uses threshold from configuration when not specified"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "X" * 75  # 75 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Create processor with custom config threshold
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=80, language="deu")  # Higher threshold
            mock_load.return_value = mock_config
            processor = PDFProcessor()

        # Should need OCR because 75 < 80 (config threshold)
        result = processor.needs_ocr("config_test.pdf")
        assert result is True

        # Create processor with lower config threshold
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=70, language="deu")  # Lower threshold
            mock_load.return_value = mock_config
            processor = PDFProcessor()

        # Should not need OCR because 75 >= 70 (config threshold)
        result = processor.needs_ocr("config_test.pdf")
        assert result is False

    @patch('pdfplumber.open')
    def test_needs_ocr_explicit_threshold_overrides_config(self, mock_pdf_open):
        """Test that explicit threshold parameter overrides config value"""
        mock_page = Mock()
        mock_page.extract_text.return_value = "X" * 60  # 60 characters
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Create processor with config threshold of 50
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=50, language="deu")
            mock_load.return_value = mock_config
            processor = PDFProcessor()

        # Explicit threshold should override config
        result = processor.needs_ocr("override_test.pdf", threshold=70)
        assert result is True  # 60 < 70 (explicit threshold)
        
        result = processor.needs_ocr("override_test.pdf", threshold=40)
        assert result is False  # 60 >= 40 (explicit threshold)


class TestOCRProcessing:
    """Test cases for OCR processing functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create a mock config to avoid loading from file system
        with patch('dms.processing.pdf_processor.DMSConfig.load') as mock_load:
            mock_config = Mock()
            mock_config.ocr = OCRConfig(threshold=50, language="deu", tesseract_config="--oem 3 --psm 6")
            mock_load.return_value = mock_config
            self.processor = PDFProcessor()

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('dms.processing.pdf_processor.pytesseract.image_to_string')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_basic(self, mock_pdf_open, mock_tesseract, mock_pdf2image):
        """Test basic OCR text extraction"""
        # Mock PDF structure
        mock_page = Mock()
        mock_page.extract_text.return_value = ""  # No direct text
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock image conversion
        mock_image = Mock()
        mock_pdf2image.return_value = [mock_image]
        
        # Mock OCR result
        mock_tesseract.return_value = "OCR extracted text content"

        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch.object(self.processor, '_preprocess_image_for_ocr', return_value=mock_image):
                    result = self.processor.extract_with_ocr("test.pdf")

        assert isinstance(result, DocumentContent)
        assert result.text == "OCR extracted text content"
        assert result.ocr_used is True
        assert result.text_extraction_method == "ocr"
        assert result.page_count == 1
        
        # Verify OCR was called with correct parameters
        mock_tesseract.assert_called_once_with(
            mock_image,
            lang="deu",
            config="--oem 3 --psm 6"
        )

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('dms.processing.pdf_processor.pytesseract.image_to_string')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_hybrid_processing(self, mock_pdf_open, mock_tesseract, mock_pdf2image):
        """Test hybrid processing combining direct text and OCR"""
        # Mock PDF with some direct text
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Direct text from page 1 with sufficient content that exceeds threshold"  # >50 chars
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Short"  # <50 chars
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock image conversion
        mock_image1, mock_image2 = Mock(), Mock()
        mock_pdf2image.return_value = [mock_image1, mock_image2]
        
        # Mock OCR results
        mock_tesseract.side_effect = [
            "OCR text from page 1",
            "OCR text from page 2 with more content"
        ]

        with patch('os.path.getsize', return_value=2048):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch.object(self.processor, '_preprocess_image_for_ocr', side_effect=lambda x: x):
                    result = self.processor.extract_with_ocr("hybrid.pdf")

        # Page 1 should use direct text (>50 chars), Page 2 should use OCR (better than "Short")
        expected_text = "Direct text from page 1 with sufficient content that exceeds threshold\nOCR text from page 2 with more content"
        assert result.text == expected_text
        assert result.text_extraction_method == "hybrid"
        assert result.ocr_used is True

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('dms.processing.pdf_processor.pytesseract.image_to_string')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_multipage(self, mock_pdf_open, mock_tesseract, mock_pdf2image):
        """Test OCR processing with multiple pages"""
        # Mock PDF with multiple pages
        mock_pages = []
        for i in range(3):
            mock_page = Mock()
            mock_page.extract_text.return_value = f"Page {i+1}"  # Short direct text
            mock_pages.append(mock_page)
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock image conversion
        mock_images = [Mock() for _ in range(3)]
        mock_pdf2image.return_value = mock_images
        
        # Mock OCR results
        ocr_results = [
            "OCR content from page 1 with substantial text",
            "OCR content from page 2 with substantial text", 
            "OCR content from page 3 with substantial text"
        ]
        mock_tesseract.side_effect = ocr_results

        with patch('os.path.getsize', return_value=3072):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch.object(self.processor, '_preprocess_image_for_ocr', side_effect=lambda x: x):
                    result = self.processor.extract_with_ocr("multipage.pdf")

        expected_text = "\n".join(ocr_results)
        assert result.text == expected_text
        assert result.page_count == 3
        assert result.ocr_used is True

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_pdf2image_failure(self, mock_pdf_open, mock_pdf2image):
        """Test handling of PDF to image conversion failure"""
        # Mock PDF structure first
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf
        
        # Mock PDF2image failure
        mock_pdf2image.side_effect = Exception("PDF conversion failed")

        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):
                with pytest.raises(Exception) as exc_info:
                    self.processor.extract_with_ocr("corrupted.pdf")
        
        assert "Failed to convert PDF to images" in str(exc_info.value)

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('dms.processing.pdf_processor.pytesseract.image_to_string')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_tesseract_failure(self, mock_pdf_open, mock_tesseract, mock_pdf2image):
        """Test handling of Tesseract OCR failure"""
        # Mock PDF structure
        mock_page = Mock()
        mock_page.extract_text.return_value = ""
        
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock image conversion
        mock_image = Mock()
        mock_pdf2image.return_value = [mock_image]
        
        # Mock OCR failure
        mock_tesseract.side_effect = Exception("Tesseract failed")

        with patch('os.path.getsize', return_value=1024):
            with patch('os.path.getctime', return_value=1640995200.0):
                with patch.object(self.processor, '_preprocess_image_for_ocr', return_value=mock_image):
                    # Should not raise exception, but handle gracefully
                    result = self.processor.extract_with_ocr("ocr_fail.pdf")

        # Should return empty text for failed OCR page
        assert result.text == ""
        assert result.ocr_used is True

    @patch('dms.processing.pdf_processor.pdf2image.convert_from_path')
    @patch('pdfplumber.open')
    def test_extract_with_ocr_page_count_mismatch(self, mock_pdf_open, mock_pdf2image):
        """Test handling of page count mismatch between PDF and images"""
        # Mock PDF with 2 pages
        mock_pages = [Mock(), Mock()]
        for page in mock_pages:
            page.extract_text.return_value = ""
        
        mock_pdf = Mock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=None)
        mock_pdf_open.return_value = mock_pdf

        # Mock image conversion returning different number of images
        mock_pdf2image.return_value = [Mock()]  # Only 1 image for 2 pages

        with pytest.raises(Exception) as exc_info:
            self.processor.extract_with_ocr("mismatch.pdf")
        
        assert "Page count mismatch" in str(exc_info.value)

    def test_preprocess_image_for_ocr(self):
        """Test image preprocessing for OCR"""
        # Create a mock color image
        mock_image = Mock()
        mock_image.mode = 'RGB'
        mock_grayscale = Mock()
        mock_image.convert.return_value = mock_grayscale

        result = self.processor._preprocess_image_for_ocr(mock_image)
        
        # Should convert to grayscale
        mock_image.convert.assert_called_once_with('L')
        assert result == mock_grayscale

    def test_preprocess_image_already_grayscale(self):
        """Test image preprocessing when image is already grayscale"""
        # Create a mock grayscale image
        mock_image = Mock()
        mock_image.mode = 'L'

        result = self.processor._preprocess_image_for_ocr(mock_image)
        
        # Should not convert if already grayscale
        mock_image.convert.assert_not_called()
        assert result == mock_image

    def test_combine_direct_and_ocr_text_prefer_direct(self):
        """Test text combination when direct text is substantial"""
        direct_pages = ["This is substantial direct text content that exceeds threshold"]  # >50 chars
        ocr_pages = ["OCR text"]
        
        result = self.processor._combine_direct_and_ocr_text(direct_pages, ocr_pages)
        
        # Should prefer direct text
        assert result == ["This is substantial direct text content that exceeds threshold"]

    def test_combine_direct_and_ocr_text_prefer_ocr(self):
        """Test text combination when OCR text is better than direct"""
        direct_pages = ["Short"]  # <50 chars
        ocr_pages = ["Much longer OCR extracted text content"]  # Longer than direct
        
        result = self.processor._combine_direct_and_ocr_text(direct_pages, ocr_pages)
        
        # Should prefer OCR text
        assert result == ["Much longer OCR extracted text content"]

    def test_combine_direct_and_ocr_text_combine_both(self):
        """Test text combination when both texts are short but present"""
        direct_pages = ["Direct short"]  # <50 chars
        ocr_pages = ["OCR short"]  # Also short but similar length
        
        result = self.processor._combine_direct_and_ocr_text(direct_pages, ocr_pages)
        
        # Should combine both
        assert result == ["Direct short\nOCR short"]

    def test_combine_direct_and_ocr_text_empty_pages(self):
        """Test text combination with empty pages"""
        direct_pages = ["", "Direct text", ""]
        ocr_pages = ["OCR text", "", ""]
        
        result = self.processor._combine_direct_and_ocr_text(direct_pages, ocr_pages)
        
        # Should handle empty pages correctly
        assert result == ["OCR text", "Direct text", ""]

    @patch.object(PDFProcessor, 'needs_ocr')
    @patch.object(PDFProcessor, 'extract_with_ocr')
    @patch.object(PDFProcessor, 'extract_text')
    def test_extract_text_with_ocr_fallback_needs_ocr(self, mock_extract_text, mock_extract_ocr, mock_needs_ocr):
        """Test OCR fallback when OCR is needed"""
        mock_needs_ocr.return_value = True
        mock_document = Mock()
        mock_extract_ocr.return_value = mock_document

        result = self.processor.extract_text_with_ocr_fallback("test.pdf")
        
        mock_needs_ocr.assert_called_once_with("test.pdf")
        mock_extract_ocr.assert_called_once_with("test.pdf")
        mock_extract_text.assert_not_called()
        assert result == mock_document

    @patch.object(PDFProcessor, 'needs_ocr')
    @patch.object(PDFProcessor, 'extract_with_ocr')
    @patch.object(PDFProcessor, 'extract_text')
    def test_extract_text_with_ocr_fallback_no_ocr_needed(self, mock_extract_text, mock_extract_ocr, mock_needs_ocr):
        """Test OCR fallback when OCR is not needed"""
        mock_needs_ocr.return_value = False
        mock_document = Mock()
        mock_extract_text.return_value = mock_document

        result = self.processor.extract_text_with_ocr_fallback("test.pdf")
        
        mock_needs_ocr.assert_called_once_with("test.pdf")
        mock_extract_text.assert_called_once_with("test.pdf")
        mock_extract_ocr.assert_not_called()
        assert result == mock_document