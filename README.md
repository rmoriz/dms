# DMS - Document Management System

A RAG (Retrieval-Augmented Generation) powered PDF search and query tool that makes your documents searchable and queryable using natural language.

## Features

- 📄 **PDF Processing**: Extract text from PDFs with intelligent OCR fallback
- 🧠 **AI-Powered Search**: Query your documents using natural language
- 🏷️ **Auto-Categorization**: Automatically categorize documents (invoices, bank statements, contracts)
- 📁 **Directory Structure**: Preserve and search by directory structure (YEAR/MONTH/Category)
- 🔍 **Advanced Filtering**: Filter by date ranges, categories, and directory paths
- 💾 **Local Storage**: All data stored locally with ChromaDB and SQLite
- 🌐 **Multiple LLM Support**: Use various models via OpenRouter API
- ⚡ **CLI Interface**: Powerful command-line interface for all operations

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Tesseract OCR (for image-based PDFs)
- OpenRouter API key (for AI queries)

### Installation

1. **Install system dependencies:**

   **macOS (using Homebrew):**
   ```bash
   brew install tesseract tesseract-lang
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-deu
   ```

   **Windows:**
   Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

2. **Install DMS:**
   ```bash
   pip install dms-rag
   ```

3. **Initialize DMS:**
   ```bash
   dms init --api-key your-openrouter-api-key
   ```

### Basic Usage

1. **Import a PDF file:**
   ```bash
   dms import-file /path/to/document.pdf
   ```

2. **Import a directory:**
   ```bash
   dms import-directory /path/to/documents --recursive
   ```

3. **Query your documents:**
   ```bash
   dms query "What invoices did I receive in March 2024?"
   ```

4. **List imported documents:**
   ```bash
   dms list --details
   ```

## Installation Guide

### Virtual Environment Setup (Recommended)

Using a virtual environment is strongly recommended to avoid conflicts with other Python packages.

#### Option 1: Using venv (Built-in)

1. **Create a virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv dms-env
   
   # Activate virtual environment
   # On Linux/macOS:
   source dms-env/bin/activate
   
   # On Windows:
   dms-env\Scripts\activate
   ```

2. **Upgrade pip and install DMS:**
   ```bash
   # Upgrade pip to latest version
   pip install --upgrade pip
   
   # Install DMS
   pip install dms-rag
   ```

3. **Verify installation:**
   ```bash
   dms --help
   ```

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

#### Option 2: Using conda

1. **Create conda environment:**
   ```bash
   # Create environment with Python 3.11
   conda create -n dms-env python=3.11
   
   # Activate environment
   conda activate dms-env
   ```

2. **Install DMS:**
   ```bash
   pip install dms-rag
   ```

3. **Verify installation:**
   ```bash
   dms --help
   ```

#### Option 3: Using pyenv + virtualenv

1. **Install specific Python version:**
   ```bash
   # Install Python 3.11 (or your preferred version)
   pyenv install 3.11.0
   pyenv local 3.11.0
   ```

2. **Create virtual environment:**
   ```bash
   # Create virtual environment
   python -m venv dms-env
   source dms-env/bin/activate
   ```

3. **Install DMS:**
   ```bash
   pip install --upgrade pip
   pip install dms-rag
   ```

#### Virtual Environment Best Practices

- **Always activate** your virtual environment before using DMS
- **Keep environments separate** for different projects
- **Document your environment** by saving requirements:
  ```bash
  pip freeze > my-dms-requirements.txt
  ```
- **Recreate environment** from requirements:
  ```bash
  pip install -r my-dms-requirements.txt
  ```

### Development Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rmoriz/dms.git
   cd dms
   ```

2. **Create virtual environment:**
   ```bash
   python3.13 -m venv venv
   source venv/bin/activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

4. **Run tests:**
   ```bash
   pytest
   ```

## Configuration

### Initial Setup

Run the initialization command to set up DMS:

```bash
dms init --api-key your-openrouter-api-key --data-dir ~/.dms
```

### Configuration Management

**View current configuration:**
```bash
dms config show
```

**Set configuration values:**
```bash
dms config set openrouter.api_key your-new-api-key
dms config set openrouter.default_model anthropic/claude-3-sonnet
dms config set chunk_size 1000
```

**Test configuration:**
```bash
dms config test --openrouter
```

**Reset to defaults:**
```bash
dms config reset --confirm
```

### OpenRouter Setup

1. **Get an API key:**
   - Visit https://openrouter.ai/
   - Sign up and get your API key
   - The key should start with `sk-or-`

2. **Set your API key:**
   ```bash
   dms config set openrouter.api_key sk-or-your-api-key-here
   ```

3. **Choose your preferred model:**
   ```bash
   dms models-list  # See available models
   dms models-set anthropic/claude-3-sonnet  # Set default model
   ```

### Configuration File

DMS stores configuration in `~/.dms/config.json`. Example configuration:

```json
{
  "openrouter": {
    "api_key": "sk-or-your-api-key",
    "default_model": "anthropic/claude-3-sonnet",
    "fallback_models": ["openai/gpt-4", "meta-llama/llama-2-70b-chat"],
    "base_url": "https://openrouter.ai/api/v1",
    "timeout": 30,
    "max_retries": 3
  },
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "device": "cpu"
  },
  "ocr": {
    "enabled": true,
    "threshold": 50,
    "language": "deu"
  },
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

## Usage Guide

### Importing Documents

**Import a single PDF:**
```bash
dms import-file invoice.pdf
dms import-file contract.pdf --category "Contract"  # Override auto-detection
dms import-file old-scan.pdf --force  # Force reimport
```

**Import directory with structure:**
```bash
# Import with directory structure preservation
dms import-directory ~/Documents/2024 --recursive
dms import-directory ~/Documents/Invoices --pattern "*.pdf"
dms import-directory ~/Scans --no-recursive  # Only current directory
```

**Directory structure example:**
```
~/Documents/
├── 2024/
│   ├── 01/
│   │   ├── Invoices/
│   │   │   ├── invoice-001.pdf
│   │   │   └── invoice-002.pdf
│   │   └── Bank/
│   │       └── statement-jan.pdf
│   └── 02/
│       └── Contracts/
│           └── lease-agreement.pdf
```

### Querying Documents

**Basic queries:**
```bash
dms query "What invoices did I receive last month?"
dms query "Show me all bank statements from 2024"
dms query "Find contracts related to rent"
```

**Filtered queries:**
```bash
# Filter by category
dms query "Total amount" --category "Invoice"

# Filter by directory structure
dms query "What happened in March?" --directory "2024/03"

# Filter by date range
dms query "Recent documents" --from 2024-01-01 --to 2024-03-31

# Use specific model
dms query "Summarize contracts" --model "openai/gpt-4"

# Verbose output with sources
dms query "Find important dates" --verbose
```

### Document Management

**List documents:**
```bash
dms list                           # Basic list
dms list --details                 # Detailed information
dms list --category "Invoice"      # Filter by category
dms list --directory "2024/03"     # Filter by directory
dms list --limit 10                # Limit results
```

**View categories:**
```bash
dms categories                     # Show all categories with counts
```

**Delete documents:**
```bash
dms delete --path "/path/to/file.pdf"     # Delete specific file
dms delete --category "Draft"             # Delete by category
dms delete --path "2024/01"               # Delete directory
dms delete --all --force                  # Delete everything (dangerous!)
```

### Model Management

**List available models:**
```bash
dms models-list
```

**Set default model:**
```bash
dms models-set anthropic/claude-3-sonnet
```

**Test model connectivity:**
```bash
dms models-test                    # Test all models
dms models-test --model openai/gpt-4  # Test specific model
```

## Advanced Features

### OCR Processing

DMS automatically detects when OCR is needed:

- **Text-based PDFs**: Direct text extraction (fast)
- **Image-based PDFs**: OCR with Tesseract (slower but accurate)
- **Mixed PDFs**: Hybrid approach combining both methods

Configure OCR settings:
```bash
dms config set ocr.threshold 50        # Characters per page threshold
dms config set ocr.language deu        # German language
dms config set ocr.enabled true        # Enable/disable OCR
```

### Document Categorization

DMS automatically categorizes documents:

- **Invoices**: Extracts issuer, amounts, dates
- **Bank Statements**: Identifies bank, account info
- **Contracts**: Detects contract types and parties
- **General**: Fallback category for other documents

Override automatic categorization:
```bash
dms import-file document.pdf --category "Custom Category"
```

### Directory Structure Filtering

Use directory structure for organized searching:

```bash
# Search in specific year/month
dms query "expenses" --directory "2024/03"

# Search in category subdirectory
dms query "rent payments" --directory "2024/Contracts"

# List documents by structure
dms list --directory "2024"
```

### Backup and Restore

**Backup your data:**
```bash
# Copy the entire data directory
cp -r ~/.dms ~/.dms-backup-$(date +%Y%m%d)
```

**Restore from backup:**
```bash
# Stop DMS and restore
rm -rf ~/.dms
cp -r ~/.dms-backup-20240315 ~/.dms
```

## Troubleshooting

### Common Issues

**1. "No OpenRouter API key configured"**
```bash
# Solution: Set your API key
dms config set openrouter.api_key sk-or-your-key-here
```

**2. "Tesseract not found"**
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-deu

# Verify installation
tesseract --version
```

**3. "Failed to process PDF"**
- Check if PDF is corrupted or password-protected
- Try with `--force` flag to skip validation
- Check file permissions

**4. "No relevant documents found"**
- Verify documents are imported: `dms list`
- Try broader search terms
- Check if filters are too restrictive

**5. "LLM API error"**
- Check internet connection
- Verify API key: `dms config test --openrouter`
- Try different model: `dms query "test" --model openai/gpt-3.5-turbo`

**6. "Permission denied" errors**
```bash
# Fix data directory permissions
chmod -R 755 ~/.dms
```

**7. "Database locked" errors**
```bash
# Stop any running DMS processes and try again
pkill -f dms
```

### Performance Issues

**Large document collections:**
- Increase chunk size: `dms config set chunk_size 1500`
- Use more specific queries
- Filter by date ranges or categories

**Slow OCR processing:**
- Disable OCR for text-based PDFs: `dms config set ocr.threshold 100`
- Use `--no-recursive` for directory imports when possible

**Memory issues:**
- Process documents in smaller batches
- Reduce chunk overlap: `dms config set chunk_overlap 100`

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Enable debug logging
dms config set logging.level DEBUG

# Run commands with verbose output
dms query "test" --verbose
dms import-file document.pdf --verbose
```

Check logs:
```bash
# View recent logs
tail -f ~/.dms/logs/dms.log

# Search for errors
grep ERROR ~/.dms/logs/dms.log
```

### Getting Help

**Built-in help:**
```bash
dms --help                    # General help
dms import-file --help        # Command-specific help
dms query --help              # Query options
```

**Configuration validation:**
```bash
dms config validate           # Check configuration
dms config test               # Test all connections
```

**System information:**
```bash
dms config show               # Show current config
python --version              # Check Python version
tesseract --version           # Check Tesseract version
```

## Data Storage

DMS stores all data locally in `~/.dms/`:

```
~/.dms/
├── chroma.db/              # Vector database (ChromaDB)
├── metadata.sqlite         # Document metadata (SQLite)
├── config.json            # Configuration file
├── models.json            # Model preferences
└── logs/                  # Application logs
    └── dms.log
```

**Data is fully portable** - you can copy the `~/.dms` directory to backup or transfer your data.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: Report bugs and request features on GitHub
- **Documentation**: This README and built-in help (`dms --help`)
- **Configuration**: Use `dms config validate` to check your setup