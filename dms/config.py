"""Configuration management for DMS"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration"""
    api_key: str
    default_model: str = "anthropic/claude-3-sonnet"
    fallback_models: list = None
    base_url: str = "https://openrouter.ai/api/v1"
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = ["openai/gpt-4", "meta-llama/llama-2-70b-chat"]


@dataclass
class EmbeddingConfig:
    """Embedding model configuration"""
    model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"


@dataclass
class OCRConfig:
    """OCR processing configuration"""
    threshold: int = 50  # minimum characters per page to skip OCR
    language: str = "deu"
    tesseract_config: str = "--oem 3 --psm 6"


@dataclass
class DMSConfig:
    """Main DMS configuration"""
    openrouter: OpenRouterConfig
    embedding: EmbeddingConfig
    ocr: OCRConfig
    data_dir: str = "~/.dms"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'DMSConfig':
        """Load configuration from file or create default"""
        if config_path is None:
            config_path = Path.home() / ".dms" / "config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return cls(
                openrouter=OpenRouterConfig(**config_data.get('openrouter', {})),
                embedding=EmbeddingConfig(**config_data.get('embedding', {})),
                ocr=OCRConfig(**config_data.get('ocr', {})),
                data_dir=config_data.get('data_dir', '~/.dms'),
                chunk_size=config_data.get('chunk_size', 1000),
                chunk_overlap=config_data.get('chunk_overlap', 200)
            )
        else:
            # Create default config
            api_key = os.getenv('OPENROUTER_API_KEY', '')
            return cls(
                openrouter=OpenRouterConfig(api_key=api_key),
                embedding=EmbeddingConfig(),
                ocr=OCRConfig()
            )
    
    def save(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to file"""
        if config_path is None:
            config_path = Path.home() / ".dms" / "config.json"
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        config_dict = {
            'openrouter': asdict(self.openrouter),
            'embedding': asdict(self.embedding),
            'ocr': asdict(self.ocr),
            'data_dir': self.data_dir,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
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