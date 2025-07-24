"""Unit tests for configuration management"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from dms.config import (
    DMSConfig, OpenRouterConfig, EmbeddingConfig, OCRConfig, LoggingConfig,
    ConfigValidationError
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests"""
    return {
        "openrouter": {
            "api_key": "sk-or-test-key-123",
            "default_model": "anthropic/claude-3-sonnet",
            "fallback_models": ["openai/gpt-4", "meta-llama/llama-2-70b-chat"],
            "base_url": "https://openrouter.ai/api/v1",
            "timeout": 30,
            "max_retries": 3
        },
        "embedding": {
            "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "device": "cpu",
            "cache_dir": None
        },
        "ocr": {
            "threshold": 50,
            "language": "deu",
            "tesseract_config": "--oem 3 --psm 6",
            "enabled": True
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_enabled": True,
            "console_enabled": True,
            "max_file_size": 10485760,
            "backup_count": 5
        },
        "data_dir": "~/.dms",
        "chunk_size": 1000,
        "chunk_overlap": 200
    }


class TestOpenRouterConfig:
    """Test OpenRouterConfig functionality"""
    
    def test_valid_config(self):
        """Test valid OpenRouter configuration"""
        config = OpenRouterConfig(api_key="sk-or-test-123")
        errors = config.validate()
        assert errors == []
    
    def test_invalid_api_key(self):
        """Test invalid API key validation"""
        config = OpenRouterConfig(api_key="invalid-key")
        errors = config.validate()
        assert any("API key should start with" in error for error in errors)
    
    def test_empty_api_key(self):
        """Test empty API key validation"""
        config = OpenRouterConfig(api_key="")
        errors = config.validate()
        assert any("API key is required" in error for error in errors)
    
    def test_invalid_model_name(self):
        """Test invalid model name validation"""
        config = OpenRouterConfig(api_key="sk-or-test-123", default_model="invalid_model")
        errors = config.validate()
        assert any("Invalid default model name format" in error for error in errors)
    
    def test_invalid_base_url(self):
        """Test invalid base URL validation"""
        config = OpenRouterConfig(api_key="sk-or-test-123", base_url="not-a-url")
        errors = config.validate()
        assert any("Invalid OpenRouter base URL" in error for error in errors)
    
    def test_negative_timeout(self):
        """Test negative timeout validation"""
        config = OpenRouterConfig(api_key="sk-or-test-123", timeout=-1)
        errors = config.validate()
        assert any("Timeout must be positive" in error for error in errors)
    
    def test_negative_retries(self):
        """Test negative retries validation"""
        config = OpenRouterConfig(api_key="sk-or-test-123", max_retries=-1)
        errors = config.validate()
        assert any("Max retries cannot be negative" in error for error in errors)
    
    @patch('requests.get')
    def test_connection_test_success(self, mock_get):
        """Test successful connection test"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        config = OpenRouterConfig(api_key="sk-or-test-123")
        assert config.test_connection() is True
        
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://openrouter.ai/api/v1/models"
        assert kwargs['headers']['Authorization'] == "Bearer sk-or-test-123"
    
    @patch('requests.get')
    def test_connection_test_failure(self, mock_get):
        """Test failed connection test"""
        mock_get.side_effect = Exception("Connection failed")
        
        config = OpenRouterConfig(api_key="sk-or-test-123")
        assert config.test_connection() is False
    
    def test_invalid_base_url_exception(self):
        """Test base URL validation with exception"""
        config = OpenRouterConfig(api_key="sk-or-test-123", base_url="http://[invalid")
        errors = config.validate()
        assert any("Invalid OpenRouter base URL" in error for error in errors)
    
    def test_model_name_validation_edge_cases(self):
        """Test model name validation edge cases"""
        config = OpenRouterConfig(api_key="sk-or-test-123")
        
        # Test valid model names
        assert config._is_valid_model_name("provider/model-name")
        assert config._is_valid_model_name("provider/model_name")
        assert config._is_valid_model_name("provider/model.name")
        
        # Test invalid model names
        assert not config._is_valid_model_name("invalid")
        assert not config._is_valid_model_name("provider/")
        assert not config._is_valid_model_name("/model")
    
    def test_fallback_models_validation(self):
        """Test fallback models validation"""
        config = OpenRouterConfig(
            api_key="sk-or-test-123",
            fallback_models=["valid/model", "invalid_model", "another/valid"]
        )
        errors = config.validate()
        assert any("Invalid fallback model name format: invalid_model" in error for error in errors)


class TestEmbeddingConfig:
    """Test EmbeddingConfig functionality"""
    
    def test_valid_config(self):
        """Test valid embedding configuration"""
        config = EmbeddingConfig()
        errors = config.validate()
        assert errors == []
    
    def test_invalid_device(self):
        """Test invalid device validation"""
        config = EmbeddingConfig(device="invalid")
        errors = config.validate()
        assert any("Invalid device" in error for error in errors)
    
    def test_empty_model(self):
        """Test empty model validation"""
        config = EmbeddingConfig(model="")
        errors = config.validate()
        assert any("Embedding model name is required" in error for error in errors)
    
    def test_invalid_cache_dir(self):
        """Test invalid cache directory validation"""
        config = EmbeddingConfig(cache_dir="/nonexistent/parent/cache")
        errors = config.validate()
        assert any("Cache directory parent does not exist" in error for error in errors)


class TestOCRConfig:
    """Test OCRConfig functionality"""
    
    def test_valid_config(self):
        """Test valid OCR configuration"""
        config = OCRConfig()
        errors = config.validate()
        assert errors == []
    
    def test_negative_threshold(self):
        """Test negative threshold validation"""
        config = OCRConfig(threshold=-1)
        errors = config.validate()
        assert any("OCR threshold cannot be negative" in error for error in errors)
    
    def test_invalid_language(self):
        """Test invalid language validation"""
        config = OCRConfig(language="en")  # Should be 3 letters
        errors = config.validate()
        assert any("OCR language must be a 3-letter code" in error for error in errors)
    
    def test_empty_tesseract_config(self):
        """Test empty tesseract config validation"""
        config = OCRConfig(tesseract_config="")
        errors = config.validate()
        assert any("Tesseract config cannot be empty" in error for error in errors)


class TestLoggingConfig:
    """Test LoggingConfig functionality"""
    
    def test_valid_config(self):
        """Test valid logging configuration"""
        config = LoggingConfig()
        errors = config.validate()
        assert errors == []
    
    def test_invalid_log_level(self):
        """Test invalid log level validation"""
        config = LoggingConfig(level="INVALID")
        errors = config.validate()
        assert any("Invalid log level" in error for error in errors)
    
    def test_negative_file_size(self):
        """Test negative file size validation"""
        config = LoggingConfig(max_file_size=-1)
        errors = config.validate()
        assert any("Max file size must be positive" in error for error in errors)
    
    def test_negative_backup_count(self):
        """Test negative backup count validation"""
        config = LoggingConfig(backup_count=-1)
        errors = config.validate()
        assert any("Backup count cannot be negative" in error for error in errors)


class TestDMSConfig:
    """Test DMSConfig functionality"""
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        assert config.openrouter.api_key == "sk-or-test-key"
        assert config.embedding.model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert config.ocr.threshold == 50
        assert config.chunk_size == 1000
    
    def test_config_save_and_load(self, temp_dir):
        """Test saving and loading configuration"""
        config_path = temp_dir / "config.json"
        
        # Create and save config
        original_config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        original_config.save(config_path)
        
        # Load config
        loaded_config = DMSConfig.load(config_path)
        
        assert loaded_config.openrouter.api_key == "sk-or-test-key"
        assert loaded_config.embedding.model == original_config.embedding.model
        assert loaded_config.ocr.threshold == original_config.ocr.threshold
    
    def test_load_with_missing_file(self, temp_dir):
        """Test loading configuration with missing file creates default"""
        config_path = temp_dir / "nonexistent.json"
        config = DMSConfig.load(config_path)
        
        # Should create default config
        assert isinstance(config, DMSConfig)
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
    
    def test_load_with_corrupted_json(self, temp_dir):
        """Test loading configuration with corrupted JSON"""
        config_path = temp_dir / "corrupted.json"
        config_path.write_text("{ invalid json")
        
        config = DMSConfig.load(config_path)
        
        # Should fallback to default config
        assert isinstance(config, DMSConfig)
        assert config.chunk_size == 1000
    
    def test_load_from_environment_variable(self, temp_dir):
        """Test loading API key from environment variable"""
        config_path = temp_dir / "config.json"
        config_data = {
            "openrouter": {},  # No API key in config
            "embedding": {},
            "ocr": {},
            "logging": {}
        }
        config_path.write_text(json.dumps(config_data))
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-or-env-key'}):
            config = DMSConfig.load(config_path)
            assert config.openrouter.api_key == 'sk-or-env-key'
    
    def test_create_default_with_env_key(self):
        """Test creating default config with environment API key"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'sk-or-env-key'}):
            config = DMSConfig.create_default()
            assert config.openrouter.api_key == 'sk-or-env-key'
    
    def test_save_creates_backup(self, temp_dir):
        """Test that save creates backup of existing config"""
        config_path = temp_dir / "config.json"
        backup_path = temp_dir / "config.json.backup"
        
        # Create initial config
        config_path.write_text('{"test": "original"}')
        
        # Save new config
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        config.save(config_path)
        
        # Check backup was created
        assert backup_path.exists()
        assert json.loads(backup_path.read_text())["test"] == "original"
    
    def test_validation_errors(self):
        """Test configuration validation with errors"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key=""),  # Invalid
            embedding=EmbeddingConfig(device="invalid"),  # Invalid
            ocr=OCRConfig(threshold=-1),  # Invalid
            logging=LoggingConfig(level="INVALID"),  # Invalid
            chunk_size=-1,  # Invalid
            chunk_overlap=2000  # Invalid (greater than chunk_size)
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("API key is required" in error for error in errors)
        assert any("Invalid device" in error for error in errors)
        assert any("OCR threshold cannot be negative" in error for error in errors)
        assert any("Invalid log level" in error for error in errors)
        assert any("Chunk size must be positive" in error for error in errors)
        assert any("Chunk overlap must be less than chunk size" in error for error in errors)
    
    def test_validate_and_raise(self):
        """Test validate_and_raise method"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key=""),  # Invalid
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig(),
            chunk_size=-1  # Invalid
        )
        
        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate_and_raise()
        
        assert "Configuration validation failed" in str(exc_info.value)
    
    def test_update_setting(self):
        """Test updating configuration settings"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        # Test updating nested setting
        config.update_setting("openrouter.default_model", "openai/gpt-4")
        assert config.openrouter.default_model == "openai/gpt-4"
        
        # Test updating top-level setting
        config.update_setting("chunk_size", "1500")
        assert config.chunk_size == 1500
        
        # Test updating boolean setting
        config.update_setting("ocr.enabled", "false")
        assert config.ocr.enabled is False
        
        # Test updating list setting
        config.update_setting("openrouter.fallback_models", "model1,model2,model3")
        assert config.openrouter.fallback_models == ["model1", "model2", "model3"]
    
    def test_update_setting_invalid_path(self):
        """Test updating setting with invalid path"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        with pytest.raises(ConfigValidationError) as exc_info:
            config.update_setting("invalid.path", "value")
        
        assert "Invalid configuration path" in str(exc_info.value)
    
    def test_get_setting(self):
        """Test getting configuration settings"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        # Test getting nested setting
        assert config.get_setting("openrouter.api_key") == "sk-or-test-key"
        
        # Test getting top-level setting
        assert config.get_setting("chunk_size") == 1000
        
        # Test getting object setting
        ocr_config = config.get_setting("ocr")
        assert isinstance(ocr_config, OCRConfig)
    
    def test_get_setting_invalid_path(self):
        """Test getting setting with invalid path"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        with pytest.raises(ConfigValidationError) as exc_info:
            config.get_setting("invalid.path")
        
        assert "Invalid configuration path" in str(exc_info.value)
    
    def test_data_path_properties(self):
        """Test data path properties"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig(),
            data_dir="~/.dms"
        )
        
        assert config.data_path == Path.home() / ".dms"
        assert config.chroma_path == Path.home() / ".dms" / "chroma.db"
        assert config.metadata_db_path == Path.home() / ".dms" / "metadata.sqlite"
        assert config.logs_path == Path.home() / ".dms" / "logs"
    
    def test_load_with_json_decode_error(self, temp_dir):
        """Test loading configuration with JSON decode error"""
        config_path = temp_dir / "invalid.json"
        config_path.write_text('{"invalid": json}')  # Invalid JSON
        
        with patch('dms.config.logging.warning') as mock_warning:
            config = DMSConfig.load(config_path)
            mock_warning.assert_called()
            assert isinstance(config, DMSConfig)
    
    def test_load_with_type_error(self, temp_dir):
        """Test loading configuration with type error"""
        config_path = temp_dir / "type_error.json"
        config_path.write_text('{"openrouter": "invalid_type"}')  # Should be dict
        
        # The config should load successfully by handling the type error gracefully
        config = DMSConfig.load(config_path)
        assert isinstance(config, DMSConfig)
        # The invalid openrouter data should be replaced with empty dict
        assert config.openrouter.api_key == os.getenv('OPENROUTER_API_KEY', '')
    
    def test_save_with_exception(self, temp_dir):
        """Test save configuration with exception"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        # Mock open to raise an exception
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(ConfigValidationError) as exc_info:
                config.save(temp_dir / "config.json")
            
            assert "Failed to save configuration" in str(exc_info.value)
    
    def test_update_setting_type_conversions(self):
        """Test update_setting with various type conversions"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="sk-or-test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
        
        # Test boolean conversion
        config.update_setting("ocr.enabled", "false")
        assert config.ocr.enabled is False
        
        config.update_setting("ocr.enabled", "true")
        assert config.ocr.enabled is True
        
        config.update_setting("ocr.enabled", "0")
        assert config.ocr.enabled is False
        
        config.update_setting("ocr.enabled", "1")
        assert config.ocr.enabled is True
        
        # Test int conversion
        config.update_setting("ocr.threshold", "100")
        assert config.ocr.threshold == 100
        
        # Test float conversion (if we had float fields)
        # Test list conversion
        config.update_setting("openrouter.fallback_models", "model1, model2, model3")
        assert config.openrouter.fallback_models == ["model1", "model2", "model3"]