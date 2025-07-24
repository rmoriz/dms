# Changelog

All notable changes to DMS (Document Management System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation
- Comprehensive documentation
- Installation scripts for system dependencies

## [0.1.0] - 2024-03-15

### Added
- **Core Features**
  - PDF text extraction with intelligent OCR fallback
  - Document categorization engine (invoices, bank statements, contracts)
  - RAG-powered natural language querying
  - Local vector database with ChromaDB
  - SQLite metadata storage
  - CLI interface with comprehensive commands

- **PDF Processing**
  - Direct text extraction using pdfplumber
  - Intelligent OCR detection and processing with Tesseract
  - Hybrid processing combining direct text and OCR
  - Configurable OCR thresholds and language support
  - Text chunking with overlap for better context

- **Search and Query**
  - Semantic search using sentence-transformers
  - Multiple LLM support via OpenRouter API
  - Context-aware answer generation with source citations
  - Filtering by category, directory structure, and date ranges
  - Confidence scoring for search results

- **Document Management**
  - Automatic document categorization
  - Entity extraction (invoice issuers, bank names, amounts)
  - Directory structure preservation (YEAR/MONTH/Category)
  - Metadata management with full CRUD operations
  - Batch import with progress tracking

- **CLI Commands**
  - `dms init` - Initialize configuration
  - `dms config` - Configuration management
  - `dms import-file` - Import single PDF
  - `dms import-directory` - Batch import from directory
  - `dms query` - Natural language querying
  - `dms list` - List imported documents
  - `dms delete` - Delete documents and data
  - `dms categories` - View document categories
  - `dms models-*` - LLM model management

- **Configuration**
  - JSON-based configuration system
  - OpenRouter API integration
  - Configurable embedding models
  - OCR settings and language support
  - Logging configuration

- **Testing**
  - Comprehensive unit test suite
  - Integration tests for end-to-end workflows
  - Test data and fixtures
  - Coverage reporting with pytest-cov

- **Documentation**
  - Complete README with installation and usage guide
  - CLI help documentation with examples
  - Configuration guide for OpenRouter setup
  - Troubleshooting guide for common issues
  - API documentation for developers

### Technical Details
- **Python Support**: 3.9, 3.10, 3.11, 3.12, 3.13
- **Dependencies**: 
  - typer for CLI framework
  - pdfplumber and pytesseract for PDF processing
  - chromadb for vector storage
  - sentence-transformers for embeddings
  - openai client for LLM integration
- **Storage**: Local SQLite + ChromaDB (no external dependencies)
- **Deployment**: pip installable package with console script entry point

### Known Issues
- OCR processing can be slow for large image-based PDFs
- Memory usage scales with document collection size
- Requires system installation of Tesseract OCR

### Breaking Changes
- None (initial release)

## Development Notes

### Version 0.1.0 Development Process
This version was developed using Test-Driven Development (TDD) methodology:

1. **Requirements Phase**: Defined user stories and acceptance criteria in EARS format
2. **Design Phase**: Created comprehensive architecture and component design
3. **Implementation Phase**: Implemented features incrementally with tests-first approach
4. **Testing Phase**: Achieved comprehensive test coverage with unit and integration tests
5. **Documentation Phase**: Created complete user and developer documentation
6. **Packaging Phase**: Prepared for distribution with proper Python packaging

### Architecture Highlights
- Modular design with clear separation of concerns
- Plugin-like architecture for LLM providers
- Local-first approach with optional cloud LLM integration
- Extensible categorization engine
- Robust error handling and recovery mechanisms

### Performance Characteristics
- **Import Speed**: ~2-5 seconds per PDF (text-based), ~10-30 seconds (OCR required)
- **Query Speed**: ~1-3 seconds for typical queries
- **Memory Usage**: ~100-500MB depending on document collection size
- **Storage**: ~1-5MB per document (metadata + embeddings)

### Future Roadmap
- Web interface for easier document management
- Advanced categorization with machine learning
- Multi-language support beyond German/English
- Cloud deployment options
- API server mode for integration with other tools
- Advanced analytics and reporting features