# DMS Troubleshooting Guide

Common issues and solutions for DMS (Document Management System).

## Table of Contents

- [Installation Issues](#installation-issues)
- [Configuration Problems](#configuration-problems)
- [Import/Processing Issues](#importprocessing-issues)
- [Query/Search Problems](#querysearch-problems)
- [Performance Issues](#performance-issues)
- [OCR Problems](#ocr-problems)
- [API/Network Issues](#apinetwork-issues)
- [Database Issues](#database-issues)
- [General Debugging](#general-debugging)

## Installation Issues

### Python Version Compatibility

**Problem:** `dms` command not found or import errors

**Solutions:**
```bash
# Check Python version (requires 3.9+)
python --version
python3 --version

# Install with correct Python version
python3.9 -m pip install dms-rag
# or
python3.11 -m pip install dms-rag

# Verify installation
which dms
dms --help
```

### Virtual Environment Issues

**Problem:** Package conflicts or installation errors

**Solutions:**
```bash
# Create fresh virtual environment
python3 -m venv dms-env
source dms-env/bin/activate  # Linux/macOS
# or
dms-env\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip

# Install DMS
pip install dms-rag

# Verify installation
dms --help
```

### System Dependencies Missing

**Problem:** Tesseract or other system dependencies not found

**Solutions:**

**macOS:**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Tesseract
brew install tesseract tesseract-lang

# Verify installation
tesseract --version
```

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt-get update

# Install Tesseract and language packs
sudo apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng

# Verify installation
tesseract --version
```

**Windows:**
```bash
# Download and install from:
# https://github.com/UB-Mannheim/tesseract/wiki

# Add to PATH or set environment variable
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Configuration Problems

### API Key Issues

**Problem:** "No OpenRouter API key configured"

**Solutions:**
```bash
# Set API key via config
dms config set openrouter.api_key sk-or-your-key-here

# Or use environment variable
export OPENROUTER_API_KEY=sk-or-your-key-here

# Verify API key is set
dms config get openrouter.api_key

# Test API connection
dms config test --openrouter
```

**Problem:** "Invalid API key format"

**Solutions:**
```bash
# Check API key format (should start with sk-or-)
dms config get openrouter.api_key

# Get new API key from https://openrouter.ai/
# Set correct API key
dms config set openrouter.api_key sk-or-correct-key-format
```

### Configuration File Corruption

**Problem:** Configuration validation errors or JSON parsing errors

**Solutions:**
```bash
# Validate current configuration
dms config validate

# Show current configuration
dms config show

# Reset to defaults if corrupted
dms config reset --confirm

# Manually edit configuration file
nano ~/.dms/config.json

# Re-initialize if needed
dms init --api-key sk-or-your-key
```

### Permission Issues

**Problem:** "Permission denied" when accessing configuration or data

**Solutions:**
```bash
# Fix data directory permissions
chmod -R 755 ~/.dms
chmod 600 ~/.dms/config.json

# Check ownership
ls -la ~/.dms/

# Fix ownership if needed
chown -R $USER:$USER ~/.dms/

# Create data directory if missing
mkdir -p ~/.dms
dms init
```

## Import/Processing Issues

### PDF Processing Failures

**Problem:** "Failed to process PDF" errors

**Solutions:**
```bash
# Check if file exists and is readable
ls -la /path/to/file.pdf
file /path/to/file.pdf

# Try with verbose output for more details
dms import-file problem.pdf --verbose

# Check if PDF is password-protected
# Use PDF viewer to verify file integrity

# Try force import
dms import-file problem.pdf --force

# Skip problematic files in directory import
dms import-directory /path/to/dir --recursive
```

**Problem:** "Corrupted PDF" or "Invalid PDF format"

**Solutions:**
```bash
# Verify PDF integrity
pdfinfo /path/to/file.pdf

# Try to repair PDF with external tools
# - Adobe Acrobat
# - PDFtk: pdftk input.pdf output repaired.pdf

# Convert to new PDF format
# Use online converters or tools like LibreOffice

# Skip corrupted files
dms import-directory /path/to/dir --recursive
# (DMS will skip corrupted files and continue)
```

### OCR Processing Issues

**Problem:** OCR takes too long or fails

**Solutions:**
```bash
# Check OCR configuration
dms config show --section ocr

# Disable OCR if not needed
dms config set ocr.enabled false

# Adjust OCR threshold
dms config set ocr.threshold 100  # Less aggressive OCR

# Check Tesseract installation
tesseract --version
tesseract --list-langs

# Install missing language packs
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-deu  # Ubuntu
```

### Memory Issues During Import

**Problem:** Out of memory errors or system slowdown

**Solutions:**
```bash
# Reduce chunk size
dms config set chunk_size 500
dms config set chunk_overlap 50

# Process files individually instead of directory import
for file in *.pdf; do
    dms import-file "$file"
done

# Use smaller embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2

# Monitor memory usage
top -p $(pgrep -f dms)
```

### Directory Import Issues

**Problem:** Directory import stops or skips files

**Solutions:**
```bash
# Use verbose mode to see what's happening
dms import-directory /path/to/dir --verbose

# Check file permissions
ls -la /path/to/dir/*.pdf

# Use specific pattern
dms import-directory /path/to/dir --pattern "*.pdf"

# Force reimport existing files
dms import-directory /path/to/dir --force

# Import non-recursively if having issues
dms import-directory /path/to/dir --no-recursive
```

## Query/Search Problems

### No Results Found

**Problem:** "No relevant documents found" for valid queries

**Solutions:**
```bash
# Check if documents are imported
dms list

# Try broader search terms
dms query "document" --verbose

# Check filters aren't too restrictive
dms query "test" --category "Invoice" --verbose

# Verify document content was extracted
dms list --details

# Try different models
dms query "test" --model openai/gpt-3.5-turbo
```

### Poor Search Quality

**Problem:** Irrelevant results or missing relevant documents

**Solutions:**
```bash
# Use more specific queries
dms query "invoice from March 2024" --directory "2024/03"

# Adjust chunk size for better context
dms config set chunk_size 1500
dms config set chunk_overlap 300

# Try different embedding model
dms config set embedding.model sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# Use verbose mode to see search details
dms query "test" --verbose
```

### LLM Response Issues

**Problem:** Poor quality answers or hallucinations

**Solutions:**
```bash
# Try different models
dms query "test" --model anthropic/claude-3-sonnet
dms query "test" --model openai/gpt-4

# Use more specific queries
dms query "What is the total amount on invoice INV-001?"

# Increase result limit for more context
dms query "test" --limit 10

# Check source documents
dms query "test" --verbose
```

## Performance Issues

### Slow Queries

**Problem:** Queries take too long to complete

**Solutions:**
```bash
# Use faster model
dms config set openrouter.default_model openai/gpt-3.5-turbo

# Reduce search scope
dms query "test" --category "Invoice" --limit 3

# Increase API timeout if needed
dms config set openrouter.timeout 120

# Check network connection
dms config test --openrouter

# Use local embedding model optimization
dms config set embedding.device cpu
```

### High Memory Usage

**Problem:** DMS uses too much memory

**Solutions:**
```bash
# Use CPU instead of GPU for embeddings
dms config set embedding.device cpu

# Reduce chunk size and overlap
dms config set chunk_size 500
dms config set chunk_overlap 50

# Use smaller embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2

# Process documents in smaller batches
# Instead of: dms import-directory large-dir
# Use: find large-dir -name "*.pdf" | head -10 | xargs -I {} dms import-file {}
```

### Slow Import Processing

**Problem:** Document import takes too long

**Solutions:**
```bash
# Disable OCR if not needed
dms config set ocr.enabled false

# Use smaller chunks
dms config set chunk_size 800

# Process files individually to track progress
for file in *.pdf; do
    echo "Processing $file"
    dms import-file "$file"
done

# Use faster embedding model
dms config set embedding.model sentence-transformers/all-MiniLM-L6-v2
```

## OCR Problems

### Tesseract Not Found

**Problem:** "Tesseract not found" or OCR failures

**Solutions:**
```bash
# Check Tesseract installation
which tesseract
tesseract --version

# Install Tesseract
# macOS:
brew install tesseract tesseract-lang

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-deu

# Set custom Tesseract path if needed
export TESSERACT_CMD=/usr/local/bin/tesseract

# Verify installation
tesseract --list-langs
```

### Poor OCR Quality

**Problem:** OCR produces garbled or incorrect text

**Solutions:**
```bash
# Install language packs
brew install tesseract-lang  # macOS
sudo apt-get install tesseract-ocr-deu tesseract-ocr-eng  # Ubuntu

# Configure language
dms config set ocr.language deu
# or for multiple languages:
dms config set ocr.language "deu+eng"

# Adjust page segmentation mode
dms config set ocr.tesseract_config "--psm 6"  # Uniform block
dms config set ocr.tesseract_config "--psm 3"  # Fully automatic

# Try different OCR engine mode
dms config set ocr.tesseract_config "--oem 1"  # LSTM only
```

### OCR Too Aggressive/Conservative

**Problem:** OCR runs on text-based PDFs or doesn't run on image PDFs

**Solutions:**
```bash
# Adjust OCR threshold
dms config set ocr.threshold 25   # More aggressive (more OCR)
dms config set ocr.threshold 100  # Less aggressive (less OCR)

# Check current threshold
dms config get ocr.threshold

# Disable OCR completely if not needed
dms config set ocr.enabled false

# Test with specific file
dms import-file test.pdf --verbose
```

## API/Network Issues

### OpenRouter API Errors

**Problem:** "LLM API error" or connection timeouts

**Solutions:**
```bash
# Test API connection
dms config test --openrouter

# Check API key
dms config get openrouter.api_key

# Try different model
dms models-list
dms query "test" --model openai/gpt-3.5-turbo

# Increase timeout
dms config set openrouter.timeout 120

# Check network connectivity
curl -H "Authorization: Bearer $(dms config get openrouter.api_key)" \
     https://openrouter.ai/api/v1/models
```

### Rate Limiting

**Problem:** "Rate limit exceeded" errors

**Solutions:**
```bash
# Increase retry delay
dms config set openrouter.max_retries 5

# Use different model with higher limits
dms config set openrouter.default_model openai/gpt-3.5-turbo

# Process queries with delays
dms query "query 1"
sleep 5
dms query "query 2"

# Check OpenRouter dashboard for usage limits
```

### Network Connectivity Issues

**Problem:** Connection errors or timeouts

**Solutions:**
```bash
# Check internet connection
ping openrouter.ai

# Test with curl
curl -I https://openrouter.ai/api/v1/models

# Check proxy settings if behind corporate firewall
export https_proxy=http://proxy.company.com:8080

# Use custom base URL if needed
dms config set openrouter.base_url https://your-proxy.com/api/v1
```

## Database Issues

### Database Corruption

**Problem:** SQLite or ChromaDB errors

**Solutions:**
```bash
# Check database integrity
sqlite3 ~/.dms/metadata.sqlite "PRAGMA integrity_check;"

# Backup current data
cp -r ~/.dms ~/.dms-backup-$(date +%Y%m%d)

# Reset databases (will lose data)
rm -rf ~/.dms/chroma.db
rm ~/.dms/metadata.sqlite
dms init

# Restore from backup if needed
cp -r ~/.dms-backup-20240315 ~/.dms
```

### Database Locked Errors

**Problem:** "Database is locked" errors

**Solutions:**
```bash
# Stop all DMS processes
pkill -f dms

# Check for lock files
ls -la ~/.dms/*.lock

# Remove lock files if safe
rm ~/.dms/*.lock

# Restart DMS
dms list
```

### Vector Store Issues

**Problem:** ChromaDB errors or embedding issues

**Solutions:**
```bash
# Check ChromaDB directory
ls -la ~/.dms/chroma.db/

# Reset vector store (will lose embeddings)
rm -rf ~/.dms/chroma.db

# Re-import documents to rebuild embeddings
dms import-directory /path/to/docs --force

# Check embedding model
dms config get embedding.model
```

## General Debugging

### Enable Debug Logging

```bash
# Enable debug logging
dms config set logging.level DEBUG

# Run command with verbose output
dms query "test" --verbose

# Check logs
tail -f ~/.dms/logs/dms.log

# Search for specific errors
grep ERROR ~/.dms/logs/dms.log
grep -A 5 -B 5 "specific error" ~/.dms/logs/dms.log
```

### System Information

```bash
# Check Python version
python --version

# Check DMS installation
pip show dms-rag

# Check system resources
df -h ~/.dms  # Disk space
free -h       # Memory (Linux)
top           # CPU usage

# Check Tesseract
tesseract --version
tesseract --list-langs
```

### Configuration Debugging

```bash
# Validate configuration
dms config validate

# Show all configuration
dms config show

# Test all connections
dms config test

# Check specific settings
dms config get openrouter.api_key
dms config get embedding.model
dms config get ocr.enabled
```

### Clean Reinstall

If all else fails, perform a clean reinstall:

```bash
# Backup data
cp -r ~/.dms ~/.dms-backup

# Uninstall DMS
pip uninstall dms-rag

# Remove data directory
rm -rf ~/.dms

# Reinstall DMS
pip install dms-rag

# Reinitialize
dms init --api-key sk-or-your-key

# Restore documents if needed
dms import-directory /path/to/original/docs
```

## Getting Help

### Built-in Help

```bash
# General help
dms --help

# Command-specific help
dms query --help
dms import-file --help
dms config --help
```

### Log Analysis

```bash
# View recent logs
tail -100 ~/.dms/logs/dms.log

# Search for errors
grep -i error ~/.dms/logs/dms.log

# View logs by date
grep "2024-03-15" ~/.dms/logs/dms.log

# Follow logs in real-time
tail -f ~/.dms/logs/dms.log
```

### System Diagnostics

```bash
# Check system requirements
python --version  # Should be 3.9+
tesseract --version
pip list | grep -E "(dms-rag|torch|transformers|chromadb)"

# Check data directory
ls -la ~/.dms/
du -sh ~/.dms/

# Check configuration
dms config validate
dms config test
```

### Reporting Issues

When reporting issues, include:

1. **System information:**
   ```bash
   python --version
   uname -a  # Linux/macOS
   dms config show
   ```

2. **Error messages:**
   ```bash
   # Full error output
   dms command-that-fails --verbose 2>&1

   # Recent logs
   tail -50 ~/.dms/logs/dms.log
   ```

3. **Configuration:**
   ```bash
   dms config show
   # (Remove sensitive information like API keys)
   ```

4. **Steps to reproduce the issue**

5. **Expected vs actual behavior**