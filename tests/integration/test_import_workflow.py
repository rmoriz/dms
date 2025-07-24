"""Integration tests for import workflow"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

from dms.cli.main import main
from dms.config import DMSConfig


class TestImportWorkflow:
    """Test complete import workflow integration"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create mock configuration"""
        from dms.config import DMSConfig, OpenRouterConfig, EmbeddingConfig, OCRConfig, LoggingConfig
        
        # Create a real config object with test paths
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig(),
            data_dir=str(temp_dir / "data"),
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Ensure data directory exists
        config.data_path.mkdir(parents=True, exist_ok=True)
        return config
    
    def test_import_directory_empty(self, temp_dir, mock_config, capsys):
        """Test importing empty directory"""
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch.object(sys, 'argv', ['dms', 'import-directory', str(temp_dir)]):
            
            main()
            
            captured = capsys.readouterr()
            assert "📭 No PDF files found matching pattern '*.pdf'" in captured.out
    
    def test_import_directory_with_non_pdf_files(self, temp_dir, mock_config, capsys):
        """Test importing directory with non-PDF files"""
        # Create some non-PDF files
        (temp_dir / "document.txt").write_text("This is a text file")
        (temp_dir / "image.jpg").write_bytes(b"fake image data")
        (temp_dir / "spreadsheet.xlsx").write_bytes(b"fake excel data")
        
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch.object(sys, 'argv', ['dms', 'import-directory', str(temp_dir)]):
            
            main()
            
            captured = capsys.readouterr()
            assert "📭 No PDF files found matching pattern '*.pdf'" in captured.out
    
    def test_import_file_wrong_extension(self, temp_dir, mock_config, capsys):
        """Test importing file with wrong extension"""
        text_file = temp_dir / "document.txt"
        text_file.write_text("This is not a PDF")
        
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch.object(sys, 'argv', ['dms', 'import-file', str(text_file)]), \
             pytest.raises(SystemExit) as exc_info:
            
            main()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "❌ File is not a PDF" in captured.err
    
    def test_import_directory_file_discovery(self, temp_dir, mock_config, capsys):
        """Test file discovery logic for directory import"""
        # Create subdirectory structure
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        # Create fake PDF files
        (temp_dir / "root.pdf").write_bytes(b"fake pdf")
        (subdir / "sub.pdf").write_bytes(b"fake pdf")
        (temp_dir / "not_pdf.txt").write_text("not a pdf")
        
        # Test non-recursive scanning
        from pathlib import Path
        directory_path = Path(temp_dir)
        
        # Non-recursive glob
        pdf_files = list(directory_path.glob("*.pdf"))
        pdf_files = [f for f in pdf_files if f.suffix.lower() == '.pdf' and f.is_file()]
        assert len(pdf_files) == 1
        assert pdf_files[0].name == "root.pdf"
        
        # Recursive glob
        pdf_files = list(directory_path.glob("**/*.pdf"))
        pdf_files = [f for f in pdf_files if f.suffix.lower() == '.pdf' and f.is_file()]
        assert len(pdf_files) == 2
        file_names = {f.name for f in pdf_files}
        assert file_names == {"root.pdf", "sub.pdf"}
    
    def test_import_directory_custom_pattern(self, temp_dir, mock_config, capsys):
        """Test directory import with custom file pattern"""
        # Create files with different extensions
        (temp_dir / "document.pdf").write_bytes(b"fake pdf")
        (temp_dir / "DOCUMENT.PDF").write_bytes(b"fake pdf")
        (temp_dir / "other.txt").write_text("not a pdf")
        
        # Test with uppercase pattern
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch.object(sys, 'argv', ['dms', 'import-directory', str(temp_dir), '--pattern', '*.PDF']):
            
            main()
            
            captured = capsys.readouterr()
            assert "📄 Found 1 PDF files" in captured.out
    
    def test_import_keyboard_interrupt(self, temp_dir, mock_config, capsys):
        """Test handling of keyboard interrupt during import"""
        # Create a PDF file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_bytes(b"fake pdf")
        
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch('dms.processing.pdf_processor.PDFProcessor') as mock_processor, \
             patch.object(sys, 'argv', ['dms', 'import-directory', str(temp_dir)]), \
             pytest.raises(SystemExit) as exc_info:
            
            # Mock processor to raise KeyboardInterrupt
            mock_processor.return_value.extract_text_with_ocr_fallback.side_effect = KeyboardInterrupt()
            
            main()
            
            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "❌ Import cancelled by user" in captured.out
    
    def test_import_progress_reporting(self, temp_dir, mock_config, capsys):
        """Test that import progress is properly reported"""
        # Create multiple PDF files
        for i in range(3):
            (temp_dir / f"document_{i}.pdf").write_bytes(b"fake pdf")
        
        with patch('dms.config.DMSConfig.load', return_value=mock_config), \
             patch('dms.processing.pdf_processor.PDFProcessor') as mock_pdf_processor, \
             patch('dms.storage.metadata_manager.MetadataManager') as mock_metadata_manager, \
             patch('dms.storage.vector_store.VectorStore') as mock_vector_store, \
             patch('dms.categorization.engine.CategorizationEngine') as mock_cat_engine, \
             patch.object(sys, 'argv', ['dms', 'import-directory', str(temp_dir)]):
            
            # Setup mocks for successful processing
            mock_processor = MagicMock()
            mock_document_content = MagicMock()
            mock_document_content.processing_time = 1.0
            mock_processor.extract_text_with_ocr_fallback.return_value = mock_document_content
            mock_processor.create_chunks_from_document.return_value = [MagicMock()]
            mock_pdf_processor.return_value = mock_processor
            
            mock_metadata_mgr = MagicMock()
            mock_metadata_mgr.get_document_by_path.return_value = None
            mock_metadata_mgr.add_document.return_value = 123
            mock_metadata_manager.return_value = mock_metadata_mgr
            
            mock_vector = MagicMock()
            mock_vector_store.return_value = mock_vector
            
            mock_categorizer = MagicMock()
            mock_category_result = MagicMock()
            mock_category_result.primary_category = "Rechnung"
            mock_categorizer.categorize_document.return_value = mock_category_result
            mock_cat_engine.return_value = mock_categorizer
            
            main()
            
            captured = capsys.readouterr()
            
            # Check that progress is shown for each file
            assert "[1/3] Processing:" in captured.out
            assert "[2/3] Processing:" in captured.out
            assert "[3/3] Processing:" in captured.out
            
            # Check final summary
            assert "📊 Import Summary:" in captured.out
            assert "✅ Processed: 3" in captured.out
            assert "⏭️  Skipped: 0" in captured.out
            assert "❌ Failed: 0" in captured.out