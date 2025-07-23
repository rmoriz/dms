"""Pytest configuration and fixtures"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_pdf_path():
    """Path to sample PDF for testing"""
    return Path("tests/data/sample.pdf")


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    return {
        "openrouter": {
            "api_key": "test-key",
            "default_model": "test-model",
            "fallback_models": ["fallback-model"]
        },
        "embedding": {
            "model": "test-embedding-model"
        },
        "ocr": {
            "threshold": 50,
            "language": "deu"
        }
    }