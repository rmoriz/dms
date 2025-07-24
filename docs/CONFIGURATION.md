# DMS Configuration Guide

Complete guide to configuring DMS for optimal performance.

## Table of Contents

- [Quick Setup](#quick-setup)
- [OpenRouter Configuration](#openrouter-configuration)
- [Embedding Configuration](#embedding-configuration)
- [OCR Configuration](#ocr-configuration)
- [Logging Configuration](#logging-configuration)
- [Performance Tuning](#performance-tuning)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Quick Setup

### 1. Get OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Sign up for an account
3. Navigate to "Keys" section
4. Create a new API key
5. Copy the key (starts with `sk-or-`)

### 2. Initialize DMS

```bash
# Initialize with API key
dms init --api-key sk-or-your-api-key-here

# Or initialize and set key later
dms init
dms config set openrouter.api_key sk-or-your-api-key-here
```

### 3. Verify Setup

```bash
# Test configuration
dms config test

# View current settings
dms config show

# Test with a simple query
dms query "test" --verbose
```

## OpenRouter Configuration

OpenRouter provides access to multiple LLM providers through a single API.

### Basic Settings

```bash
# Set API key
dms config set openrouter.api_key sk-or-your-key

# Set default model
dms config set openrouter.default_model anthropic/claude-3-sonnet

# Set timeout (seconds)
dms config set openrouter.timeout 60

# Set max retries
dms config set openrouter.max_retries 3
```

### Model Selection

**Popular models for document analysis:**

```bash
# Claude 3 Sonnet (recommended for accuracy)
dms config set openrouter.default_model anthropic/claude-3-sonnet

# GPT-4 (good balance of speed and quality)
dms config set openrouter.default_model openai/gpt-4

# GPT-3.5 Turbo (faster, lower cost)
dms config set openrouter.default_model openai/gpt-3.5-turbo

# Llama 2 70B (open source alternative)
dms config set openrouter.default_model meta-llama/llama-2-70b-chat
```

**View available models:**
```bash
dms models-list
```

### Fallback Models

Configure fallback models for reliability:

```bash
# View current fallback models
dms config get openrouter.fallback_models

# Set fallback models (JSON array format)
dms config set openrouter.fallback_models '["openai/gpt-4", "openai/gpt-3.5-turbo", "meta-llama/llama-2-70b-chat"]'
```

### Cost Optimization

**Lower-cost models for basic queries:**
- `openai/gpt-3.5-turbo`: Fast and economical
- `meta-llama/llama-2-70b-chat`: Open source, good quality
- `mistralai/mistral-7b-instruct`: Very fast, basic tasks

**Higher-quality models for complex analysis:**
- `anthropic/claude-3-sonnet`: Best for document analysis
- `openai/gpt-4`: Excellent reasoning
- `anthropic/claude-3-opus`: Highest quality (most expensive)

### API Configuration

```bash
# Custom base URL (if using proxy)
dms config set openrouter.base_url https://your-proxy.com/api/v1

# Increase timeout for large documents
dms config set openrouter.timeout 120

# Reduce retries for faster failure
dms config set openrouter.max_retries 1
```

## Embedding Configuration

Embeddings are used for semantic search. DMS uses local models by default.

### Basic Settings

```bash
# View current embedding model
dms config get embedding.model

# Set embedding model
dms config set embedding.model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Set device (cpu/cuda)
dms config set embedding.device cpu

# Set custom cache directory
dms config set embedding.cache_dir /path/to/cache
```

### Model Options

**Multilingual models (recommended for German documents):**
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (default)
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- `sentence-transformers/distiluse-base-multilingual-cased`

**English-only models (faster):**
- `sentence-transformers/all-MiniLM-L6-v2`
- `sentence-transformers/all-mpnet-base-v2`

### GPU Acceleration

If you have a CUDA-compatible GPU:

```bash
# Enable GPU acceleration
dms config set embedding.device cuda

# Verify GPU is available
python -c "import torch; print(torch.cuda.is_available())"
```

## OCR Configuration

OCR (Optical Character Recognition) is used for image-based PDFs.

### Basic Settings

```bash
# Enable/disable OCR
dms config set ocr.enabled true

# Set OCR threshold (characters per page)
dms config set ocr.threshold 50

# Set language
dms config set ocr.language deu

# Set Tesseract configuration
dms config set ocr.tesseract_config "--psm 6"
```

### Language Support

**Install additional languages:**

```bash
# macOS
brew install tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr-deu tesseract-ocr-eng

# Windows
# Download language packs from GitHub
```

**Configure language:**
```bash
# German
dms config set ocr.language deu

# English
dms config set ocr.language eng

# Multiple languages
dms config set ocr.language "deu+eng"
```

### OCR Threshold Tuning

The threshold determines when OCR is triggered:

```bash
# Conservative (more OCR)
dms config set ocr.threshold 25

# Default
dms config set ocr.threshold 50

# Aggressive (less OCR)
dms config set ocr.threshold 100

# Disable OCR completely
dms config set ocr.enabled false
```

### Tesseract Configuration

Advanced Tesseract settings:

```bash
# Page segmentation modes
dms config set ocr.tesseract_config "--psm 6"  # Uniform block of text
dms config set ocr.tesseract_config "--psm 3"  # Fully automatic (default)
dms config set ocr.tesseract_config "--psm 1"  # Automatic with OSD

# OCR Engine Mode
dms config set ocr.tesseract_config "--oem 3"  # Default (LSTM + Legacy)
dms config set ocr.tesseract_config "--oem 1"  # LSTM only (faster)

# Combined settings
dms config set ocr.tesseract_config "--psm 6 --oem 1"
```

## Logging Configuration

Configure logging for debugging and monitoring.

### Basic Settings

```bash
# Set log level
dms config set logging.level INFO

# Enable/disable file logging
dms config set logging.file_enabled true

# Enable/disable console logging
dms config set logging.console_enabled true

# Set max log file size (bytes)
dms config set logging.max_file_size 10485760  # 10MB

# Set number of backup files
dms config set logging.backup_count 5
```

### Log Levels

```bash
# Debug (very verbose)
dms config set logging.level DEBUG

# Info (default)
dms config set logging.level INFO

# Warning (only warnings and errors)
dms config set logging.level WARNING

# Error (only errors)
dms config set logging.level ERROR
```

### Log File Location

Logs are stored in `~/.dms/logs/dms.log`

```bash
# View recent logs
tail -f ~/.dms/logs/dms.log

# Search for errors
grep ERROR ~/.dms/logs/dms.log

# View logs with timestamps
cat ~/.dms/logs/dms.log | grep "2024-03-15"
```

## Performance Tuning

### Chunk Size Optimization

Chunk size affects search quality and performance:

```bash
# Small chunks (better precision, more chunks)
dms config set chunk_size 500
dms config set chunk_overlap 100

# Default chunks (balanced)
dms config set chunk_size 1000
dms config set chunk_overlap 200

# Large chunks (better context, fewer chunks)
dms config set chunk_size 2000
dms config set chunk_overlap 400
```

### Memory Optimization

For systems with limited memory:

```bash
# Reduce chunk size
dms config set chunk_size 500

# Reduce overlap
dms config set chunk_overlap 50

# Use smaller embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2

# Disable OCR for text-based PDFs
dms config set ocr.threshold 100
```

### Speed Optimization

For faster processing:

```bash
# Use faster embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2

# Reduce API timeout
dms config set openrouter.timeout 30

# Use faster LLM model
dms config set openrouter.default_model openai/gpt-3.5-turbo

# Disable OCR if not needed
dms config set ocr.enabled false
```

## Security Considerations

### API Key Security

**Best practices:**

1. **Use environment variables:**
   ```bash
   export OPENROUTER_API_KEY=sk-or-your-key
   # Don't store in config file
   ```

2. **Restrict file permissions:**
   ```bash
   chmod 600 ~/.dms/config.json
   ```

3. **Use separate keys for different environments:**
   ```bash
   # Development
   dms config set openrouter.api_key sk-or-dev-key

   # Production
   dms config set openrouter.api_key sk-or-prod-key
   ```

### Data Privacy

**Local data storage:**
- All documents and embeddings stored locally
- No document content sent to external services (except for LLM queries)
- Vector database is fully local (ChromaDB)

**Network considerations:**
- Only LLM queries sent to OpenRouter
- Embedding generation is local
- OCR processing is local

### Access Control

**File system permissions:**
```bash
# Secure data directory
chmod 700 ~/.dms
chmod 600 ~/.dms/config.json
chmod 600 ~/.dms/metadata.sqlite
```

**Multi-user setup:**
```bash
# Create shared data directory
sudo mkdir /shared/dms
sudo chown dms-group:dms-group /shared/dms
sudo chmod 770 /shared/dms

# Configure DMS to use shared directory
dms config set data_dir /shared/dms
```

## Troubleshooting

### Configuration Issues

**Invalid configuration:**
```bash
# Validate configuration
dms config validate

# Reset to defaults
dms config reset --confirm

# Show current configuration
dms config show
```

**API connection issues:**
```bash
# Test OpenRouter connection
dms config test --openrouter

# Check API key format
dms config get openrouter.api_key

# Try different model
dms models-test --model openai/gpt-3.5-turbo
```

### Performance Issues

**Slow queries:**
```bash
# Use faster model
dms config set openrouter.default_model openai/gpt-3.5-turbo

# Reduce chunk size
dms config set chunk_size 500

# Increase timeout
dms config set openrouter.timeout 120
```

**High memory usage:**
```bash
# Use CPU for embeddings
dms config set embedding.device cpu

# Reduce chunk overlap
dms config set chunk_overlap 50

# Use smaller embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2
```

### OCR Issues

**Tesseract not found:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Check installation
tesseract --version
```

**Poor OCR quality:**
```bash
# Install language packs
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-deu  # Ubuntu

# Adjust PSM mode
dms config set ocr.tesseract_config "--psm 6"

# Try different language
dms config set ocr.language "deu+eng"
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Enable debug logging
dms config set logging.level DEBUG

# Run command with verbose output
dms query "test" --verbose

# Check logs
tail -f ~/.dms/logs/dms.log
```

## Configuration File Reference

Complete `~/.dms/config.json` example:

```json
{
  "openrouter": {
    "api_key": "sk-or-your-api-key",
    "default_model": "anthropic/claude-3-sonnet",
    "fallback_models": [
      "openai/gpt-4",
      "openai/gpt-3.5-turbo",
      "meta-llama/llama-2-70b-chat"
    ],
    "base_url": "https://openrouter.ai/api/v1",
    "timeout": 60,
    "max_retries": 3
  },
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cpu",
    "cache_dir": null
  },
  "ocr": {
    "enabled": true,
    "threshold": 50,
    "language": "deu",
    "tesseract_config": "--psm 6"
  },
  "logging": {
    "level": "INFO",
    "file_enabled": true,
    "console_enabled": true,
    "max_file_size": 10485760,
    "backup_count": 5
  },
  "chunk_size": 1000,
  "chunk_overlap": 200,
  "data_dir": "~/.dms"
}
```