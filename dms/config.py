"""Configuration management for DMS"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import re
import requests
from urllib.parse import urlparse


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration"""
    api_key: str
    default_model: str = "anthropic/claude-3-sonnet"
    fallback_models: list = None
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = ["openai/gpt-4", "meta-llama/llama-2-70b-chat"]
    
    def validate(self) -> List[str]:
        """Validate OpenRouter configuration"""
        errors = []
        
        # Validate API key format
        if not self.api_key:
            errors.append("OpenRouter API key is required")
        elif not self.api_key.startswith(('sk-or-', 'sk-')):
            errors.append("OpenRouter API key should start with 'sk-or-' or 'sk-'")
        
        # Validate base URL
        try:
            parsed = urlparse(self.base_url)
            if not parsed.scheme or not parsed.netloc:
                errors.append("Invalid OpenRouter base URL format")
        except Exception:
            errors.append("Invalid OpenRouter base URL")
        
        # Validate model names
        if not self.default_model:
            errors.append("Default model is required")
        elif not self._is_valid_model_name(self.default_model):
            errors.append(f"Invalid default model name format: {self.default_model}")
        
        # Validate fallback models
        for model in self.fallback_models or []:
            if not self._is_valid_model_name(model):
                errors.append(f"Invalid fallback model name format: {model}")
        
        # Validate timeout and retries
        if self.timeout <= 0:
            errors.append("Timeout must be positive")
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        
        return errors
    
    def _is_valid_model_name(self, model: str) -> bool:
        """Check if model name follows expected format (provider/model)"""
        return bool(re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$', model))
    
    def test_connection(self) -> bool:
        """Test connection to OpenRouter API"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logging.warning(f"OpenRouter connection test failed: {e}")
            return False


@dataclass
class EmbeddingConfig:
    """Embedding model configuration"""
    model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"
    cache_dir: Optional[str] = None
    
    def validate(self) -> List[str]:
        """Validate embedding configuration"""
        errors = []
        
        # Validate device
        if self.device not in ["cpu", "cuda", "mps"]:
            errors.append(f"Invalid device '{self.device}'. Must be 'cpu', 'cuda', or 'mps'")
        
        # Validate model name
        if not self.model:
            errors.append("Embedding model name is required")
        
        # Validate cache directory if provided
        if self.cache_dir:
            try:
                cache_path = Path(self.cache_dir).expanduser()
                if not cache_path.parent.exists():
                    errors.append(f"Cache directory parent does not exist: {cache_path.parent}")
            except Exception:
                errors.append(f"Invalid cache directory path: {self.cache_dir}")
        
        return errors


@dataclass
class OCRConfig:
    """OCR processing configuration"""
    threshold: int = 50  # minimum characters per page to skip OCR
    language: str = "deu"
    tesseract_config: str = "--oem 3 --psm 6"
    enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate OCR configuration"""
        errors = []
        
        # Validate threshold
        if self.threshold < 0:
            errors.append("OCR threshold cannot be negative")
        
        # Validate language code
        if not self.language or len(self.language) != 3:
            errors.append("OCR language must be a 3-letter code (e.g., 'deu', 'eng')")
        
        # Validate tesseract config
        if not self.tesseract_config:
            errors.append("Tesseract config cannot be empty")
        
        return errors


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    def validate(self) -> List[str]:
        """Validate logging configuration"""
        errors = []
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            errors.append(f"Invalid log level '{self.level}'. Must be one of: {valid_levels}")
        
        if self.max_file_size <= 0:
            errors.append("Max file size must be positive")
        
        if self.backup_count < 0:
            errors.append("Backup count cannot be negative")
        
        return errors


@dataclass
class DMSConfig:
    """Main DMS configuration"""
    openrouter: OpenRouterConfig
    embedding: EmbeddingConfig
    ocr: OCRConfig
    logging: LoggingConfig
    data_dir: str = "~/.dms"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'DMSConfig':
        """Load configuration from file or create default"""
        if config_path is None:
            config_path = Path.home() / ".dms" / "config.json"
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Handle missing API key gracefully
                openrouter_data = config_data.get('openrouter', {})
                if not isinstance(openrouter_data, dict):
                    openrouter_data = {}
                if not openrouter_data.get('api_key'):
                    openrouter_data['api_key'] = os.getenv('OPENROUTER_API_KEY', '')
                
                # Ensure all config sections are dictionaries
                embedding_data = config_data.get('embedding', {})
                if not isinstance(embedding_data, dict):
                    embedding_data = {}
                
                ocr_data = config_data.get('ocr', {})
                if not isinstance(ocr_data, dict):
                    ocr_data = {}
                
                logging_data = config_data.get('logging', {})
                if not isinstance(logging_data, dict):
                    logging_data = {}
                
                return cls(
                    openrouter=OpenRouterConfig(**openrouter_data),
                    embedding=EmbeddingConfig(**embedding_data),
                    ocr=OCRConfig(**ocr_data),
                    logging=LoggingConfig(**logging_data),
                    data_dir=config_data.get('data_dir', '~/.dms'),
                    chunk_size=config_data.get('chunk_size', 1000),
                    chunk_overlap=config_data.get('chunk_overlap', 200)
                )
            else:
                # Create default config
                return cls.create_default()
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logging.warning(f"Failed to load config from {config_path}: {e}")
            logging.info("Creating default configuration")
            return cls.create_default()
    
    @classmethod
    def create_default(cls) -> 'DMSConfig':
        """Create default configuration"""
        api_key = os.getenv('OPENROUTER_API_KEY', '')
        return cls(
            openrouter=OpenRouterConfig(api_key=api_key),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig()
        )
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        if config_path is None:
            config_path = Path.home() / ".dms" / "config.json"
        
        try:
            # Ensure directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save
            config_dict = {
                'openrouter': asdict(self.openrouter),
                'embedding': asdict(self.embedding),
                'ocr': asdict(self.ocr),
                'logging': asdict(self.logging),
                'data_dir': self.data_dir,
                'chunk_size': self.chunk_size,
                'chunk_overlap': self.chunk_overlap
            }
            
            # Create backup if file exists
            if config_path.exists():
                backup_path = config_path.with_suffix('.json.backup')
                config_path.rename(backup_path)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise ConfigValidationError(f"Failed to save configuration: {e}")
    
    def validate(self) -> List[str]:
        """Validate entire configuration"""
        errors = []
        
        # Validate sub-configurations
        errors.extend(self.openrouter.validate())
        errors.extend(self.embedding.validate())
        errors.extend(self.ocr.validate())
        errors.extend(self.logging.validate())
        
        # Validate chunk settings
        if self.chunk_size <= 0:
            errors.append("Chunk size must be positive")
        if self.chunk_overlap < 0:
            errors.append("Chunk overlap cannot be negative")
        if self.chunk_overlap >= self.chunk_size:
            errors.append("Chunk overlap must be less than chunk size")
        
        # Validate data directory
        try:
            data_path = Path(self.data_dir).expanduser()
            if not data_path.parent.exists():
                errors.append(f"Data directory parent does not exist: {data_path.parent}")
        except Exception:
            errors.append(f"Invalid data directory path: {self.data_dir}")
        
        return errors
    
    def validate_and_raise(self) -> None:
        """Validate configuration and raise exception if invalid"""
        errors = self.validate()
        if errors:
            raise ConfigValidationError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def update_setting(self, key_path: str, value: Any) -> None:
        """Update a configuration setting using dot notation"""
        keys = key_path.split('.')
        obj = self
        
        # Navigate to the parent object
        for key in keys[:-1]:
            if not hasattr(obj, key):
                raise ConfigValidationError(f"Invalid configuration path: {key_path}")
            obj = getattr(obj, key)
        
        # Set the final value
        final_key = keys[-1]
        if not hasattr(obj, final_key):
            raise ConfigValidationError(f"Invalid configuration key: {final_key}")
        
        # Type conversion based on current value type
        current_value = getattr(obj, final_key)
        if isinstance(current_value, bool):
            if isinstance(value, str):
                value = value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(current_value, int):
            value = int(value)
        elif isinstance(current_value, float):
            value = float(value)
        elif isinstance(current_value, list):
            if isinstance(value, str):
                value = [item.strip() for item in value.split(',')]
        
        setattr(obj, final_key, value)
    
    def get_setting(self, key_path: str) -> Any:
        """Get a configuration setting using dot notation"""
        keys = key_path.split('.')
        obj = self
        
        for key in keys:
            if not hasattr(obj, key):
                raise ConfigValidationError(f"Invalid configuration path: {key_path}")
            obj = getattr(obj, key)
        
        return obj
    
    @property
    def data_path(self) -> Path:
        """Get expanded data directory path"""
        return Path(self.data_dir).expanduser()
    
    @property
    def chroma_path(self) -> Path:
        """Get ChromaDB path"""
        return self.data_path / "chroma.db"
    
    @property
    def metadata_db_path(self) -> Path:
        """Get metadata SQLite database path"""
        return self.data_path / "metadata.sqlite"
    
    @property
    def logs_path(self) -> Path:
        """Get logs directory path"""
        return self.data_path / "logs"