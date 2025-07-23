"""Unit tests for configuration management"""

import pytest
import json
import tempfile
from pathlib import Path
from dms.config import DMSConfig, OpenRouterConfig, EmbeddingConfig, OCRConfig


class TestDMSConfig:
    """Test DMSConfig functionality"""
    
    def test_default_config_creation(self):
        """Test creating default configuration"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig()
        )
        
        assert config.openrouter.api_key == "test-key"
        assert config.embedding.model == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert config.ocr.threshold == 50
        assert config.chunk_size == 1000
    
    def test_config_save_and_load(self, temp_dir):
        """Test saving and loading configuration"""
        config_path = temp_dir / "config.json"
        
        # Create and save config
        original_config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig()
        )
        original_config.save(config_path)
        
        # Load config
        loaded_config = DMSConfig.load(config_path)
        
        assert loaded_config.openrouter.api_key == "test-key"
        assert loaded_config.embedding.model == original_config.embedding.model
        assert loaded_config.ocr.threshold == original_config.ocr.threshold
    
    def test_data_path_properties(self):
        """Test data path properties"""
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            data_dir="~/.dms"
        )
        
        assert config.data_path == Path.home() / ".dms"
        assert config.chroma_path == Path.home() / ".dms" / "chroma.db"
        assert config.metadata_db_path == Path.home() / ".dms" / "metadata.sqlite"