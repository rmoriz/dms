"""PDF processing functionality for text extraction and metadata handling"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import io

import pdfplumber
import pytesseract
from PIL import Image
import pdf2image

from dms.models import DocumentContent, DocumentMetadata, TextChunk
from dms.config import DMSConfig
from dms.errors import (
    handle_pdf_errors, CorruptedPDFError, OCRError, PDFProcessingError,
    retry_on_failure, TransientNetworkError
)
from dms.logging_setup import get_logger, log_performance


class PDFProcessor:
    """Handles PDF text extraction and metadata processing"""
    
    def __init__(self, config: Optional[DMSConfig] = None):
        """
        Initialize PDF processor with optional configuration
        
        Args:
            config: DMS configuration object. If None, loads default config.
        """
        self.config = config or DMSConfig.load()
        self.logger = get_logger(f"{__name__}.PDFProcessor")

    @handle_pdf_errors
    def extract_text(self, pdf_path: str) -> DocumentContent:
        """
        Extract text content from a PDF file using pdfplumber
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentContent object with extracted text and metadata
            
        Raises:
            CorruptedPDFError: If PDF is corrupted or unreadable
            PDFProcessingError: If PDF processing fails
        """
        with log_performance(f"Direct text extraction from {Path(pdf_path).name}", self.logger):
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    # Extract text from all pages
                    page_texts = []
                    for i, page in enumerate(pdf.pages):
                        try:
                            text = page.extract_text()
                            if text:
                                # Clean up whitespace while preserving structure
                                cleaned_text = text.strip()
                                page_texts.append(cleaned_text)
                            else:
                                page_texts.append("")
                        except Exception as e:
                            self.logger.warning(f"Failed to extract text from page {i+1}: {e}")
                            page_texts.append("")
                    
                    # Combine all page texts
                    full_text = "\n".join(page_texts)
                    page_count = len(pdf.pages)
                    
                    self.logger.debug(f"Extracted {len(full_text)} characters from {page_count} pages")
                    
            except Exception as e:
                self.logger.error(f"Failed to process PDF {pdf_path}: {e}")
                raise
            
            # Get file metadata
            try:
                file_size = os.path.getsize(pdf_path)
                creation_time = os.path.getctime(pdf_path)
                import_date = datetime.fromtimestamp(creation_time)
            except OSError as e:
                raise PDFProcessingError(
                    f"Cannot access file metadata for {pdf_path}",
                    "Check file permissions and ensure the file exists.",
                    e
                )
            
            # Extract directory structure
            path_obj = Path(pdf_path)
            if len(path_obj.parts) > 1:
                directory_structure = str(Path(*path_obj.parts[:-1]))
            else:
                directory_structure = ""
            
            processing_time = time.time() - time.time()  # Will be set by log_performance
            
            return DocumentContent(
                file_path=pdf_path,
                text=full_text,
                page_count=page_count,
                file_size=file_size,
                import_date=import_date,
                directory_structure=directory_structure,
                ocr_used=False,
                text_extraction_method="direct",
                processing_time=processing_time
            )

    @handle_pdf_errors
    def extract_metadata(self, pdf_path: str) -> DocumentMetadata:
        """
        Extract metadata from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentMetadata object with file information
            
        Raises:
            PDFProcessingError: If PDF file doesn't exist or cannot be processed
        """
        self.logger.debug(f"Extracting metadata from {pdf_path}")
        
        try:
            # Get file system metadata
            file_size = os.path.getsize(pdf_path)
            creation_time = os.path.getctime(pdf_path)
            modification_time = os.path.getmtime(pdf_path)
            
            creation_date = datetime.fromtimestamp(creation_time)
            modification_date = datetime.fromtimestamp(modification_time)
            
            # Get page count from PDF
            with pdfplumber.open(pdf_path) as pdf:
                page_count = len(pdf.pages)
            
            # Extract directory structure
            path_obj = Path(pdf_path)
            if len(path_obj.parts) > 1:
                directory_structure = str(Path(*path_obj.parts[:-1]))
            else:
                directory_structure = ""
            
            self.logger.debug(f"Metadata extracted: {page_count} pages, {file_size} bytes")
            
            return DocumentMetadata(
                file_path=path_obj,
                file_size=file_size,
                page_count=page_count,
                creation_date=creation_date,
                modification_date=modification_date,
                directory_structure=directory_structure
            )
            
        except FileNotFoundError as e:
            raise PDFProcessingError(
                f"PDF file not found: {pdf_path}",
                "Check the file path and ensure the file exists.",
                e
            )
        except Exception as e:
            self.logger.error(f"Failed to extract metadata from {pdf_path}: {e}")
            raise

    @handle_pdf_errors
    def needs_ocr(self, pdf_path: str, threshold: Optional[int] = None) -> bool:
        """
        Determine if a PDF needs OCR processing based on text density
        
        Args:
            pdf_path: Path to the PDF file
            threshold: Minimum characters per page to avoid OCR. If None, uses config value.
            
        Returns:
            True if OCR is needed, False otherwise
        """
        if threshold is None:
            threshold = self.config.ocr.threshold
            
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_chars = 0
                page_count = len(pdf.pages)
                
                if page_count == 0:
                    self.logger.warning(f"PDF has no pages: {pdf_path}")
                    return True
                
                for page in pdf.pages:
                    try:
                        text = page.extract_text()
                        if text:
                            # Strip whitespace and count meaningful characters
                            stripped_text = text.strip()
                            total_chars += len(stripped_text)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract text from page for OCR analysis: {e}")
                        continue
                
                avg_chars_per_page = total_chars / page_count
                needs_ocr = avg_chars_per_page < threshold
                
                self.logger.debug(
                    f"OCR analysis: {avg_chars_per_page:.1f} chars/page "
                    f"(threshold: {threshold}) -> {'OCR needed' if needs_ocr else 'Direct text OK'}"
                )
                
                return needs_ocr
                
        except Exception as e:
            # If we can't analyze the PDF, assume OCR is needed
            self.logger.warning(f"Cannot analyze PDF for OCR necessity: {e}. Assuming OCR needed.")
            return True

    @handle_pdf_errors
    @retry_on_failure(max_retries=2, delay=1.0, exceptions=(OCRError,))
    def extract_with_ocr(self, pdf_path: str) -> DocumentContent:
        """
        Extract text from PDF using OCR processing with Tesseract
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentContent object with OCR-extracted text and metadata
            
        Raises:
            OCRError: If OCR processing fails
            CorruptedPDFError: If PDF is corrupted or unreadable
            PDFProcessingError: If PDF processing fails
        """
        with log_performance(f"OCR text extraction from {Path(pdf_path).name}", self.logger):
            try:
                # First try to get any available direct text
                direct_text_pages = []
                with pdfplumber.open(pdf_path) as pdf:
                    page_count = len(pdf.pages)
                    for page in pdf.pages:
                        try:
                            text = page.extract_text()
                            direct_text_pages.append(text.strip() if text else "")
                        except Exception as e:
                            self.logger.warning(f"Failed to extract direct text from page: {e}")
                            direct_text_pages.append("")
                
                # Convert PDF pages to images for OCR
                try:
                    self.logger.debug(f"Converting PDF to images for OCR processing")
                    images = pdf2image.convert_from_path(pdf_path, dpi=300)
                except Exception as e:
                    raise OCRError(
                        pdf_path,
                        Exception(f"Failed to convert PDF to images: {str(e)}")
                    )
                
                if len(images) != page_count:
                    raise OCRError(
                        pdf_path,
                        Exception(f"Page count mismatch: PDF has {page_count} pages, got {len(images)} images")
                    )
                
                # Process each page with OCR
                ocr_text_pages = []
                successful_ocr_pages = 0
                
                for i, image in enumerate(images):
                    try:
                        # Preprocess image for better OCR results
                        processed_image = self._preprocess_image_for_ocr(image)
                        
                        # Configure Tesseract for German language
                        custom_config = self.config.ocr.tesseract_config
                        
                        # Extract text using OCR
                        ocr_text = pytesseract.image_to_string(
                            processed_image, 
                            lang=self.config.ocr.language,
                            config=custom_config
                        )
                        
                        ocr_text_pages.append(ocr_text.strip())
                        if ocr_text.strip():
                            successful_ocr_pages += 1
                        
                    except Exception as e:
                        # If OCR fails for a page, use empty string but log warning
                        ocr_text_pages.append("")
                        self.logger.warning(f"OCR failed for page {i+1}: {e}")
                
                self.logger.debug(f"OCR completed: {successful_ocr_pages}/{page_count} pages with text")
                
                # If OCR failed on all pages, raise an error
                if successful_ocr_pages == 0 and not any(direct_text_pages):
                    raise OCRError(
                        pdf_path,
                        Exception("OCR failed to extract text from any page")
                    )
                
                # Combine direct text and OCR text using hybrid approach
                combined_pages = self._combine_direct_and_ocr_text(direct_text_pages, ocr_text_pages)
                
                # Join all pages
                full_text = "\n".join(combined_pages)
                
                self.logger.debug(f"OCR extraction completed: {len(full_text)} characters extracted")
                
            except OCRError:
                # Re-raise OCR errors as-is
                raise
            except Exception as e:
                self.logger.error(f"Failed to process PDF with OCR {pdf_path}: {e}")
                raise OCRError(pdf_path, e)
            
            # Get file metadata
            try:
                file_size = os.path.getsize(pdf_path)
                creation_time = os.path.getctime(pdf_path)
                import_date = datetime.fromtimestamp(creation_time)
            except OSError as e:
                raise PDFProcessingError(
                    f"Cannot access file metadata for {pdf_path}",
                    "Check file permissions and ensure the file exists.",
                    e
                )
            
            # Extract directory structure
            path_obj = Path(pdf_path)
            if len(path_obj.parts) > 1:
                directory_structure = str(Path(*path_obj.parts[:-1]))
            else:
                directory_structure = ""
            
            processing_time = time.time() - time.time()  # Will be set by log_performance
            
            return DocumentContent(
                file_path=pdf_path,
                text=full_text,
                page_count=page_count,
                file_size=file_size,
                import_date=import_date,
                directory_structure=directory_structure,
                ocr_used=True,
                text_extraction_method="hybrid" if any(direct_text_pages) else "ocr",
                processing_time=processing_time
            )

    def _preprocess_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            Preprocessed PIL Image object
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast and sharpness if needed
        # For now, keep it simple - just return grayscale
        # Future improvements could include:
        # - Noise reduction
        # - Contrast enhancement
        # - Deskewing
        # - Border removal
        
        return image

    def _combine_direct_and_ocr_text(self, direct_pages: List[str], ocr_pages: List[str]) -> List[str]:
        """
        Combine direct text extraction and OCR results using hybrid approach
        
        Args:
            direct_pages: List of text extracted directly from PDF pages
            ocr_pages: List of text extracted via OCR from PDF pages
            
        Returns:
            List of combined text for each page
        """
        combined_pages = []
        
        for i, (direct_text, ocr_text) in enumerate(zip(direct_pages, ocr_pages)):
            direct_stripped = direct_text.strip()
            ocr_stripped = ocr_text.strip()
            
            # If direct text is substantial (>= threshold), prefer it
            if len(direct_stripped) >= self.config.ocr.threshold:
                combined_pages.append(direct_stripped)
            # If direct text is minimal but OCR found more text, use OCR
            elif len(ocr_stripped) > len(direct_stripped):
                combined_pages.append(ocr_stripped)
            # If both are minimal but present, combine them
            elif direct_stripped and ocr_stripped:
                # Simple combination - could be improved with deduplication
                combined_text = f"{direct_stripped}\n{ocr_stripped}"
                combined_pages.append(combined_text)
            # Use whichever has content
            elif direct_stripped:
                combined_pages.append(direct_stripped)
            elif ocr_stripped:
                combined_pages.append(ocr_stripped)
            else:
                combined_pages.append("")
        
        return combined_pages

    @handle_pdf_errors
    def extract_text_with_ocr_fallback(self, pdf_path: str) -> DocumentContent:
        """
        Extract text from PDF with intelligent OCR fallback
        
        This method first tries direct text extraction, then uses OCR if needed
        based on the needs_ocr analysis.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            DocumentContent object with extracted text and metadata
            
        Raises:
            CorruptedPDFError: If PDF is corrupted or unreadable
            OCRError: If OCR processing fails when needed
            PDFProcessingError: If PDF processing fails
        """
        self.logger.info(f"Processing PDF: {Path(pdf_path).name}")
        
        try:
            # Check if OCR is needed
            if not self.config.ocr.enabled:
                self.logger.debug("OCR disabled in configuration, using direct text extraction only")
                return self.extract_text(pdf_path)
            
            if self.needs_ocr(pdf_path):
                self.logger.debug("OCR needed based on text density analysis")
                return self.extract_with_ocr(pdf_path)
            else:
                self.logger.debug("Direct text extraction sufficient")
                try:
                    return self.extract_text(pdf_path)
                except (CorruptedPDFError, PDFProcessingError) as e:
                    # If direct extraction fails, try OCR as fallback
                    self.logger.warning(f"Direct extraction failed, trying OCR fallback: {e}")
                    return self.extract_with_ocr(pdf_path)
                    
        except Exception as e:
            self.logger.error(f"Failed to extract text from {pdf_path}: {e}")
            raise

    def create_chunks(self, text: str, chunk_size: int = 1000, overlap: int = 200, 
                     document_id: str = "", page_texts: Optional[List[str]] = None) -> List[TextChunk]:
        """
        Split text into overlapping chunks for vector storage
        
        Args:
            text: Text to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            document_id: ID of the document these chunks belong to
            page_texts: List of text content per page for page number tracking
            
        Returns:
            List of TextChunk objects
        """
        if not text or chunk_size <= 0:
            return []
        
        # Ensure overlap is not larger than chunk_size to prevent infinite loops
        overlap = min(overlap, chunk_size - 1) if chunk_size > 1 else 0
        
        chunks = []
        start = 0
        chunk_index = 0
        
        # Create page position mapping if page_texts provided
        page_positions = []
        if page_texts:
            current_pos = 0
            for page_num, page_text in enumerate(page_texts, 1):
                page_positions.append((current_pos, current_pos + len(page_text), page_num))
                current_pos += len(page_text) + 1  # +1 for newline separator
        
        while start < len(text):
            # Calculate end position
            end = min(start + chunk_size, len(text))
            
            # Extract chunk content
            chunk_content = text[start:end].strip()
            
            if chunk_content:  # Only create non-empty chunks
                # Determine page number for this chunk
                page_number = 1  # Default
                if page_positions:
                    chunk_middle = start + (end - start) // 2
                    for pos_start, pos_end, page_num in page_positions:
                        if pos_start <= chunk_middle < pos_end:
                            page_number = page_num
                            break
                
                chunk = TextChunk(
                    id=f"chunk_{chunk_index}",
                    document_id=document_id,
                    content=chunk_content,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    embedding=None
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move start position, accounting for overlap
            if end >= len(text):
                break
                
            # Calculate next start position with overlap
            next_start = end - overlap
            
            # Ensure we always make progress (prevent infinite loops)
            if next_start <= start:
                next_start = start + 1
                
            start = next_start
        
        return chunks

    def create_chunks_from_document(self, document_content: DocumentContent, 
                                   chunk_size: int = 1000, overlap: int = 200) -> List[TextChunk]:
        """
        Create chunks from a DocumentContent object with proper page tracking
        
        Args:
            document_content: DocumentContent object to chunk
            chunk_size: Maximum size of each chunk in characters
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of TextChunk objects with proper page number tracking
        """
        # Extract text from the document again to get page-by-page content
        try:
            with pdfplumber.open(document_content.file_path) as pdf:
                page_texts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        cleaned_text = text.strip()
                        page_texts.append(cleaned_text)
                    else:
                        page_texts.append("")
        except Exception:
            # Fallback to simple chunking if we can't re-read the PDF
            return self.create_chunks(document_content.text, chunk_size, overlap, 
                                    document_id=document_content.file_path)
        
        # Create document ID from file path
        document_id = document_content.file_path
        
        return self.create_chunks(document_content.text, chunk_size, overlap, 
                                document_id, page_texts)