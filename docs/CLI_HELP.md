# DMS CLI Help Documentation

Complete reference for all DMS command-line interface commands.

## Global Options

Available for all commands:

```bash
--config, -c PATH     Path to configuration file
--verbose, -v         Enable verbose output
--data-dir PATH       Override data directory path
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `init` | Initialize DMS configuration |
| `config` | Manage DMS configuration |
| `import-file` | Import a single PDF file |
| `import-directory` | Import all PDF files from a directory |
| `query` | Query documents with natural language |
| `list` | List imported documents |
| `delete` | Delete documents and associated data |
| `categories` | Show auto-detected document categories |
| `models-list` | List available LLM models |
| `models-set` | Set default LLM model |
| `models-test` | Test LLM model connectivity |

---

## init

Initialize DMS configuration and create data directories.

### Usage
```bash
dms init [OPTIONS]
```

### Options
- `--api-key TEXT`: OpenRouter API key
- `--data-dir PATH`: Data directory path (default: ~/.dms)

### Examples
```bash
# Basic initialization
dms init --api-key sk-or-your-api-key-here

# Initialize with custom data directory
dms init --api-key sk-or-your-key --data-dir /custom/path

# Initialize without API key (set later)
dms init
```

---

## config

Manage DMS configuration settings.

### Usage
```bash
dms config [ACTION] [OPTIONS]
```

### Actions

#### show
Display current configuration.

```bash
dms config show [--section SECTION]
```

**Options:**
- `--section`: Show specific section only (openrouter, embedding, ocr, logging)

**Examples:**
```bash
# Show all configuration
dms config show

# Show only OpenRouter settings
dms config show --section openrouter

# Show OCR settings
dms config show --section ocr
```

#### set
Set a configuration value.

```bash
dms config set KEY VALUE
```

**Examples:**
```bash
# Set API key
dms config set openrouter.api_key sk-or-your-new-key

# Set default model
dms config set openrouter.default_model anthropic/claude-3-sonnet

# Set chunk size
dms config set chunk_size 1500

# Set OCR threshold
dms config set ocr.threshold 100

# Enable/disable OCR
dms config set ocr.enabled true
```

#### get
Get a configuration value.

```bash
dms config get KEY
```

**Examples:**
```bash
# Get current model
dms config get openrouter.default_model

# Get chunk size
dms config get chunk_size

# Get data directory
dms config get data_dir
```

#### validate
Validate current configuration.

```bash
dms config validate
```

#### test
Test configuration connectivity.

```bash
dms config test [--openrouter]
```

**Options:**
- `--openrouter`: Test only OpenRouter API connection

#### reset
Reset configuration to defaults.

```bash
dms config reset [--confirm]
```

**Options:**
- `--confirm`: Skip confirmation prompt

---

## import-file

Import a single PDF file into the DMS.

### Usage
```bash
dms import-file FILE_PATH [OPTIONS]
```

### Options
- `--category, -c TEXT`: Override automatic category detection
- `--force, -f`: Force reimport if file already exists

### Examples
```bash
# Basic file import
dms import-file ~/Documents/invoice.pdf

# Import with category override
dms import-file contract.pdf --category "Legal Contract"

# Force reimport existing file
dms import-file document.pdf --force

# Import with verbose output
dms import-file document.pdf --verbose
```

---

## import-directory

Import all PDF files from a directory.

### Usage
```bash
dms import-directory DIRECTORY_PATH [OPTIONS]
```

### Options
- `--recursive, -r`: Recursively import PDFs from subdirectories (default: true)
- `--no-recursive, -nr`: Don't recursively import PDFs
- `--pattern, -p TEXT`: File pattern to match (default: *.pdf)
- `--force, -f`: Force reimport of existing files

### Examples
```bash
# Import directory recursively (default)
dms import-directory ~/Documents/2024

# Import only current directory
dms import-directory ~/Documents/Invoices --no-recursive

# Import with custom pattern
dms import-directory ~/Scans --pattern "scan_*.pdf"

# Force reimport all files
dms import-directory ~/Documents --force

# Import with verbose output
dms import-directory ~/Documents --verbose
```

---

## query

Query your documents using natural language.

### Usage
```bash
dms query "QUESTION" [OPTIONS]
```

### Options
- `--model, -m TEXT`: Override default LLM model for this query
- `--category, -c TEXT`: Filter by document category
- `--directory, -d TEXT`: Filter by directory structure (e.g., '2024/03')
- `--from DATE`: Filter documents from date (YYYY-MM-DD)
- `--to DATE`: Filter documents to date (YYYY-MM-DD)
- `--limit, -l INTEGER`: Maximum number of source documents to consider (default: 5)
- `--verbose, -v`: Show detailed search results and confidence scores

### Examples
```bash
# Basic query
dms query "What invoices did I receive last month?"

# Query with category filter
dms query "Show me bank statements" --category "Bank Statement"

# Query with directory filter
dms query "What happened in March?" --directory "2024/03"

# Query with date range
dms query "Recent contracts" --from 2024-01-01 --to 2024-03-31

# Query with specific model
dms query "Summarize expenses" --model "openai/gpt-4"

# Verbose query with detailed output
dms query "Find important dates" --verbose --limit 10

# Complex filtered query
dms query "Total invoice amounts" \
  --category "Invoice" \
  --directory "2024/03" \
  --from 2024-03-01 \
  --to 2024-03-31 \
  --verbose
```

### Query Tips
- Use natural language: "What", "Show me", "Find", "How much"
- Be specific about time periods: "last month", "in 2024", "recent"
- Mention document types: "invoices", "contracts", "statements"
- Ask for summaries: "summarize", "total", "overview"

---

## list

List imported documents with optional filtering.

### Usage
```bash
dms list [OPTIONS]
```

### Options
- `--category, -c TEXT`: Filter by document category
- `--directory, -d TEXT`: Filter by directory structure
- `--limit, -l INTEGER`: Maximum number of documents to show (default: 50)
- `--details`: Show detailed document information

### Examples
```bash
# Basic list
dms list

# List with details
dms list --details

# Filter by category
dms list --category "Invoice"

# Filter by directory
dms list --directory "2024/03"

# Limit results
dms list --limit 10

# Combined filters
dms list --category "Contract" --directory "2024" --details
```

---

## delete

Delete documents and associated data from DMS.

### Usage
```bash
dms delete [OPTIONS]
```

### Options
- `--path, -p TEXT`: Delete documents by file path or directory
- `--category, -c TEXT`: Delete documents by category
- `--all`: Delete all documents (requires confirmation)
- `--force, -f`: Skip confirmation prompts

### Examples
```bash
# Delete specific file
dms delete --path "/path/to/document.pdf"

# Delete by category
dms delete --category "Draft"

# Delete entire directory
dms delete --path "2024/01"

# Delete all documents (dangerous!)
dms delete --all

# Force delete without confirmation
dms delete --category "Temp" --force
```

**⚠️ Warning:** Deletion is permanent and removes both metadata and vector embeddings.

---

## categories

Show auto-detected document categories and their counts.

### Usage
```bash
dms categories [OPTIONS]
```

### Options
- `--count`: Show document count per category (default: true)
- `--no-count`: Don't show document count per category

### Examples
```bash
# Show categories with counts
dms categories

# Show categories without counts
dms categories --no-count
```

---

## models-list

List available LLM models from OpenRouter.

### Usage
```bash
dms models-list
```

### Examples
```bash
# List all available models
dms models-list
```

---

## models-set

Set the default LLM model for queries.

### Usage
```bash
dms models-set MODEL_NAME
```

### Examples
```bash
# Set Claude as default
dms models-set anthropic/claude-3-sonnet

# Set GPT-4 as default
dms models-set openai/gpt-4

# Set Llama as default
dms models-set meta-llama/llama-2-70b-chat
```

---

## models-test

Test LLM model connectivity.

### Usage
```bash
dms models-test [OPTIONS]
```

### Options
- `--model, -m TEXT`: Test specific model (default: test all configured models)

### Examples
```bash
# Test all models
dms models-test

# Test specific model
dms models-test --model anthropic/claude-3-sonnet
```

---

## Common Workflows

### Initial Setup
```bash
# 1. Initialize DMS
dms init --api-key sk-or-your-api-key

# 2. Test configuration
dms config test

# 3. Import your documents
dms import-directory ~/Documents/PDFs --recursive

# 4. Start querying
dms query "What documents do I have?"
```

### Daily Usage
```bash
# Import new document
dms import-file new-invoice.pdf

# Quick query
dms query "Recent invoices"

# Check what's imported
dms list --limit 10

# Detailed search
dms query "Contracts from last month" --verbose
```

### Maintenance
```bash
# Check configuration
dms config show

# Validate setup
dms config validate

# View categories
dms categories

# Clean up old documents
dms delete --directory "2023" --force
```

### Troubleshooting
```bash
# Test API connection
dms config test --openrouter

# Verbose import for debugging
dms import-file problem.pdf --verbose

# Check available models
dms models-list

# Reset configuration if needed
dms config reset --confirm
```

---

## Exit Codes

- `0`: Success
- `1`: General error (file not found, API error, etc.)
- `2`: Configuration error
- `130`: Interrupted by user (Ctrl+C)

---

## Environment Variables

DMS respects these environment variables:

- `OPENROUTER_API_KEY`: OpenRouter API key (alternative to config)
- `DMS_DATA_DIR`: Override default data directory
- `DMS_CONFIG_FILE`: Override default config file location
- `TESSERACT_CMD`: Path to tesseract executable (if not in PATH)

### Examples
```bash
# Use environment variable for API key
export OPENROUTER_API_KEY=sk-or-your-key
dms query "test"

# Use custom data directory
export DMS_DATA_DIR=/custom/dms/data
dms init

# Use custom tesseract path
export TESSERACT_CMD=/usr/local/bin/tesseract
dms import-file scanned.pdf
```