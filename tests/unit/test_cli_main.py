"""Tests for CLI main module"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json
import sys
from io import StringIO

from dms.cli.main import create_parser, main
from dms.config import DMSConfig


@pytest.fixture
def parser():
    """Create CLI argument parser"""
    return create_parser()


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestCLIMain:
    """Test main CLI functionality"""
    
    def test_parser_help(self, parser):
        """Test main parser help message"""
        help_text = parser.format_help()
        assert "Document Management System" in help_text
        assert "import-file" in help_text
        assert "query" in help_text
        assert "list" in help_text
    
    def test_parser_no_args(self, parser):
        """Test parser with no arguments"""
        args = parser.parse_args([])
        assert args.command is None
    
    def test_verbose_flag(self, parser):
        """Test verbose flag is processed"""
        args = parser.parse_args(["--verbose", "config", "--show"])
        assert args.verbose is True
        assert args.command == "config"
    
    def test_config_path_option(self, parser):
        """Test custom config path option"""
        args = parser.parse_args(["--config", "/path/to/config.json", "config", "--show"])
        assert args.config == "/path/to/config.json"
        assert args.command == "config"
    
    def test_data_dir_option(self, parser):
        """Test data directory override option"""
        args = parser.parse_args(["--data-dir", "/custom/path", "config", "--show"])
        assert args.data_dir == "/custom/path"
        assert args.command == "config"


class TestInitCommand:
    """Test init command"""
    
    def test_init_args_parsing(self, parser):
        """Test init command argument parsing"""
        args = parser.parse_args(["init", "--api-key", "test-key", "--data-dir", "/custom/data"])
        assert args.command == "init"
        assert args.api_key == "test-key"
        assert args.data_dir == "/custom/data"
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_init_with_api_key(self, mock_print, mock_load, mock_logging):
        """Test init command with API key"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.logs_path = Path("/tmp/test/logs")
        mock_config.openrouter.api_key = ""
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        # Mock sys.argv
        with patch.object(sys, 'argv', ['dms', 'init', '--api-key', 'test-key']):
            main()
        
        assert mock_config.openrouter.api_key == "test-key"
        mock_config.save.assert_called_once()
        mock_print.assert_any_call("✅ DMS initialized successfully!")
    
    @patch('dms.config.DMSConfig.load')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_init_error_handling(self, mock_print, mock_exit, mock_load):
        """Test init command error handling"""
        mock_load.side_effect = Exception("Config error")
        
        with patch.object(sys, 'argv', ['dms', 'init', '--api-key', 'test']):
            main()
        
        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("❌ Error initializing DMS: Config error", file=sys.stderr)


class TestConfigCommand:
    """Test config command"""
    
    def test_config_args_parsing(self, parser):
        """Test config command argument parsing"""
        args = parser.parse_args(["config", "--show"])
        assert args.command == "config"
        assert args.show is True
        
        args = parser.parse_args(["config", "--set-api-key", "new-key"])
        assert args.command == "config"
        assert args.set_api_key == "new-key"
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_show(self, mock_print, mock_load, mock_logging):
        """Test config show functionality"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.openrouter.api_key = "test-key"
        mock_config.openrouter.base_url = "https://openrouter.ai/api/v1"
        mock_config.openrouter.default_model = "gpt-4"
        mock_config.openrouter.fallback_models = ["model1", "model2"]
        mock_config.openrouter.timeout = 30
        mock_config.openrouter.max_retries = 3
        mock_config.embedding.model = "test-embedding"
        mock_config.embedding.device = "cpu"
        mock_config.embedding.cache_dir = None
        mock_config.ocr.enabled = True
        mock_config.ocr.threshold = 50
        mock_config.ocr.language = "deu"
        mock_config.ocr.tesseract_config = "--oem 3 --psm 6"
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = True
        mock_config.logging.console_enabled = True
        mock_config.logging.max_file_size = 10485760
        mock_config.logging.backup_count = 5
        mock_config.chunk_size = 1000
        mock_config.chunk_overlap = 200
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', '--show']):
            main()
        
        # Verify config sections were displayed
        mock_print.assert_any_call("🔗 OpenRouter Configuration:")
        mock_print.assert_any_call("🧠 Embedding Configuration:")
        mock_print.assert_any_call("👁️  OCR Configuration:")
        mock_print.assert_any_call("📝 Logging Configuration:")
        mock_print.assert_any_call("⚙️  General Configuration:")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_set_api_key(self, mock_print, mock_load, mock_logging):
        """Test setting API key via config command"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', '--set-api-key', 'new-key']):
            main()
        
        assert mock_config.openrouter.api_key == "new-key"
        mock_config.save.assert_called_once()
        mock_print.assert_any_call("✅ API key updated")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_no_changes(self, mock_print, mock_load, mock_logging):
        """Test config command with no changes"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config']):
            main()
        
        mock_print.assert_any_call("ℹ️  Use 'dms config show' to view configuration or 'dms config --help' for options.")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_set_subcommand(self, mock_print, mock_load, mock_logging):
        """Test config set subcommand"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'set', 'chunk_size', '1500']):
            main()
        
        mock_config.update_setting.assert_called_once_with('chunk_size', '1500')
        mock_config.validate_and_raise.assert_called_once()
        mock_config.save.assert_called_once()
        mock_print.assert_any_call("✅ Set chunk_size = 1500")
        mock_print.assert_any_call("💾 Configuration saved")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_get_subcommand(self, mock_print, mock_load, mock_logging):
        """Test config get subcommand"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.get_setting.return_value = "anthropic/claude-3-sonnet"
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'get', 'openrouter.default_model']):
            main()
        
        mock_config.get_setting.assert_called_once_with('openrouter.default_model')
        mock_print.assert_any_call("openrouter.default_model = anthropic/claude-3-sonnet")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_validate_subcommand(self, mock_print, mock_load, mock_logging):
        """Test config validate subcommand"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.validate.return_value = []  # No errors
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'validate']):
            main()
        
        mock_config.validate.assert_called_once()
        mock_print.assert_any_call("✅ Configuration is valid")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    @patch('sys.exit')
    def test_config_validate_with_errors(self, mock_exit, mock_print, mock_load, mock_logging):
        """Test config validate subcommand with validation errors"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.validate.return_value = ["API key is required", "Invalid model name"]
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'validate']):
            main()
        
        mock_config.validate.assert_called_once()
        mock_print.assert_any_call("❌ Configuration validation failed:")
        mock_print.assert_any_call("  - API key is required")
        mock_print.assert_any_call("  - Invalid model name")
        mock_exit.assert_called_with(1)
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('builtins.print')
    def test_config_test_subcommand(self, mock_print, mock_load, mock_logging):
        """Test config test subcommand"""
        mock_config = MagicMock()
        mock_config.data_path = Path("/tmp/test")
        mock_config.openrouter.test_connection.return_value = True
        mock_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'test', '--openrouter']):
            main()
        
        mock_config.openrouter.test_connection.assert_called_once()
        mock_print.assert_any_call("🧪 Testing OpenRouter connection...")
        mock_print.assert_any_call("✅ OpenRouter connection successful")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.create_default')
    @patch('builtins.print')
    @patch('builtins.input')
    def test_config_reset_subcommand(self, mock_input, mock_print, mock_create_default, mock_logging):
        """Test config reset subcommand"""
        mock_input.return_value = 'y'
        mock_config = MagicMock()
        mock_create_default.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'config', 'reset']):
            main()
        
        mock_create_default.assert_called_once()
        mock_config.save.assert_called_once()
        mock_print.assert_any_call("✅ Configuration reset to defaults")
        mock_print.assert_any_call("💾 Configuration saved")
    
    @patch('dms.config.DMSConfig.load')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_config_error_handling(self, mock_print, mock_exit, mock_load):
        """Test config command error handling"""
        mock_load.side_effect = Exception("Config error")
        
        with patch.object(sys, 'argv', ['dms', 'config', '--show']):
            main()
        
        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("❌ Error managing configuration: Config error", file=sys.stderr)


class TestImportCommands:
    """Test import command functionality"""
    
    def test_import_file_args_parsing(self, parser):
        """Test import-file command argument parsing"""
        args = parser.parse_args(["import-file", "/path/to/file.pdf"])
        assert args.command == "import-file"
        assert args.file_path == "/path/to/file.pdf"
        assert args.category is None
        assert args.force is False
        
        args = parser.parse_args(["import-file", "/path/to/file.pdf", "--category", "Rechnung", "--force"])
        assert args.command == "import-file"
        assert args.file_path == "/path/to/file.pdf"
        assert args.category == "Rechnung"
        assert args.force is True
    
    def test_import_directory_args_parsing(self, parser):
        """Test import-directory command argument parsing"""
        args = parser.parse_args(["import-directory", "/path/to/dir"])
        assert args.command == "import-directory"
        assert args.directory_path == "/path/to/dir"
        assert args.recursive is True  # Default
        assert args.pattern == "*.pdf"  # Default
        assert args.force is False
        
        args = parser.parse_args([
            "import-directory", "/path/to/dir", 
            "--no-recursive", "--pattern", "*.PDF", "--force"
        ])
        assert args.command == "import-directory"
        assert args.directory_path == "/path/to/dir"
        assert args.recursive is False
        assert args.pattern == "*.PDF"
        assert args.force is True
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('dms.processing.pdf_processor.PDFProcessor')
    @patch('dms.storage.metadata_manager.MetadataManager')
    @patch('dms.storage.vector_store.VectorStore')
    @patch('dms.categorization.engine.CategorizationEngine')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.suffix')
    @patch('builtins.print')
    def test_import_file_success(self, mock_print, mock_suffix, mock_exists, 
                                mock_cat_engine, mock_vector_store, mock_metadata_manager, 
                                mock_pdf_processor, mock_config_load, mock_logging):
        """Test successful file import"""
        # Setup mocks
        mock_exists.return_value = True
        mock_suffix.return_value = '.pdf'
        
        mock_config = MagicMock()
        mock_config.chunk_size = 1000
        mock_config.chunk_overlap = 200
        mock_config.data_path = Path("/tmp/test")
        mock_config_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        mock_processor = MagicMock()
        mock_document_content = MagicMock()
        mock_document_content.file_path = "/test/file.pdf"
        mock_document_content.page_count = 5
        mock_document_content.processing_time = 2.5
        mock_processor.extract_text_with_ocr_fallback.return_value = mock_document_content
        mock_chunks = [MagicMock() for _ in range(3)]
        mock_processor.create_chunks_from_document.return_value = mock_chunks
        mock_pdf_processor.return_value = mock_processor
        
        mock_metadata_mgr = MagicMock()
        mock_metadata_mgr.get_document_by_path.return_value = None  # Not already imported
        mock_metadata_mgr.add_document.return_value = 123  # Document ID
        mock_metadata_manager.return_value = mock_metadata_mgr
        
        mock_vector = MagicMock()
        mock_vector_store.return_value = mock_vector
        
        mock_categorizer = MagicMock()
        mock_category_result = MagicMock()
        mock_category_result.primary_category = "Rechnung"
        mock_category_result.confidence = 0.85
        mock_category_result.entities = {"rechnungssteller": "Test Company"}
        mock_categorizer.categorize_document.return_value = mock_category_result
        mock_cat_engine.return_value = mock_categorizer
        
        # Test import
        with patch.object(sys, 'argv', ['dms', 'import-file', '/test/file.pdf']):
            main()
        
        # Verify calls
        mock_processor.extract_text_with_ocr_fallback.assert_called_once_with('/test/file.pdf')
        mock_categorizer.categorize_document.assert_called_once()
        mock_processor.create_chunks_from_document.assert_called_once()
        mock_metadata_mgr.add_document.assert_called_once()
        mock_vector.add_documents.assert_called_once_with(mock_chunks)
        
        # Verify success message
        mock_print.assert_any_call("✅ Successfully imported: /test/file.pdf")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('pathlib.Path.exists')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_import_file_not_found(self, mock_print, mock_exit, mock_exists, mock_config_load, mock_logging):
        """Test import file when file doesn't exist"""
        mock_exists.return_value = False
        mock_config_load.return_value = MagicMock()
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'import-file', '/nonexistent/file.pdf']):
            main()
        
        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("❌ File not found: /nonexistent/file.pdf", file=sys.stderr)
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('dms.storage.metadata_manager.MetadataManager')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.suffix')
    @patch('builtins.print')
    def test_import_file_already_exists(self, mock_print, mock_suffix, mock_exists, 
                                       mock_metadata_manager, mock_config_load, mock_logging):
        """Test import file when file already exists and force is not enabled"""
        mock_exists.return_value = True
        mock_suffix.return_value = '.pdf'
        mock_config_load.return_value = MagicMock()
        mock_logging.return_value = MagicMock()
        
        mock_metadata_mgr = MagicMock()
        mock_metadata_mgr.get_document_by_path.return_value = {"id": 123}  # Already exists
        mock_metadata_manager.return_value = mock_metadata_mgr
        
        with patch.object(sys, 'argv', ['dms', 'import-file', '/test/file.pdf']):
            main()
        
        mock_print.assert_any_call("⚠️  File already imported: /test/file.pdf")
        mock_print.assert_any_call("   Use --force to reimport")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.glob')
    @patch('builtins.print')
    def test_import_directory_success(self, mock_print, mock_glob, mock_is_dir, 
                                     mock_exists, mock_config_load, mock_logging):
        """Test successful directory import"""
        # Setup mocks
        mock_exists.return_value = True
        mock_is_dir.return_value = True
        
        # Mock PDF files found
        mock_pdf1 = MagicMock()
        mock_pdf1.suffix = '.pdf'
        mock_pdf1.is_file.return_value = True
        mock_pdf1.name = 'file1.pdf'
        mock_pdf2 = MagicMock()
        mock_pdf2.suffix = '.pdf'
        mock_pdf2.is_file.return_value = True
        mock_pdf2.name = 'file2.pdf'
        mock_glob.return_value = [mock_pdf1, mock_pdf2]
        
        mock_config = MagicMock()
        mock_config.chunk_size = 1000
        mock_config.chunk_overlap = 200
        mock_config.data_path = Path("/tmp/test")
        mock_config_load.return_value = mock_config
        mock_logging.return_value = MagicMock()
        
        with patch('dms.processing.pdf_processor.PDFProcessor') as mock_pdf_processor, \
             patch('dms.storage.metadata_manager.MetadataManager') as mock_metadata_manager, \
             patch('dms.storage.vector_store.VectorStore') as mock_vector_store, \
             patch('dms.categorization.engine.CategorizationEngine') as mock_cat_engine:
            
            # Setup component mocks
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
            
            with patch.object(sys, 'argv', ['dms', 'import-directory', '/test/dir']):
                main()
        
        # Verify directory scanning
        mock_print.assert_any_call("📄 Found 2 PDF files")
        mock_print.assert_any_call("📊 Import Summary:")
    
    @patch('dms.logging_setup.setup_cli_logging')
    @patch('dms.config.DMSConfig.load')
    @patch('pathlib.Path.exists')
    @patch('sys.exit')
    @patch('builtins.print')
    def test_import_directory_not_found(self, mock_print, mock_exit, mock_exists, mock_config_load, mock_logging):
        """Test import directory when directory doesn't exist"""
        mock_exists.return_value = False
        mock_config_load.return_value = MagicMock()
        mock_logging.return_value = MagicMock()
        
        with patch.object(sys, 'argv', ['dms', 'import-directory', '/nonexistent/dir']):
            main()
        
        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("❌ Directory not found: /nonexistent/dir", file=sys.stderr)


class TestSubcommands:
    """Test subcommand integration"""
    
    def test_import_file_subcommand_available(self, parser):
        """Test import-file subcommand is available"""
        args = parser.parse_args(["import-file", "/path/to/file.pdf"])
        assert args.command == "import-file"
        assert args.file_path == "/path/to/file.pdf"
    
    def test_query_subcommand_available(self, parser):
        """Test query subcommand is available"""
        args = parser.parse_args(["query", "What is this about?"])
        assert args.command == "query"
        assert args.question == "What is this about?"
    
    def test_list_subcommand_available(self, parser):
        """Test list subcommand is available"""
        args = parser.parse_args(["list"])
        assert args.command == "list"
    
    def test_query_with_filters(self, parser):
        """Test query command with filters"""
        args = parser.parse_args([
            "query", "test question",
            "--model", "gpt-4",
            "--category", "invoice",
            "--directory", "2024/03",
            "--from", "2024-01-01",
            "--to", "2024-12-31",
            "--limit", "10",
            "--verbose"
        ])
        assert args.command == "query"
        assert args.question == "test question"
        assert args.model == "gpt-4"
        assert args.category == "invoice"
        assert args.directory == "2024/03"
        assert args.date_from == "2024-01-01"
        assert args.date_to == "2024-12-31"
        assert args.limit == 10
        assert args.verbose is True