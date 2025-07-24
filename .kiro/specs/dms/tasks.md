# Implementation Plan

**Repository:** https://github.com/rmoriz/dms.git  
**Lokales Projektverzeichnis:** /Users/rmoriz/sync/Projekte/dms  
**Python Version:** 3.13  
**Entwicklungsansatz:** Test-Driven Development (TDD)

**Hinweis:** Alle Implementierungsschritte sollen in diesem Git-Repository versioniert werden. Für jeden Task sollen zuerst Tests geschrieben werden, dann die Implementierung erfolgen.

- [x] 1. Set up project structure and core interfaces
  - Create Python 3.13 virtual environment using `python3.13 -m venv venv`
  - Create Python package structure with modules for CLI, processing, storage, and RAG
  - Set up pytest configuration and test directory structure
  - Set up requirements.txt and development dependencies (pytest, pytest-cov, etc.)
  - Define core data models and interfaces for DocumentContent, TextChunk, CategoryResult
  - Set up configuration management for OpenRouter API and local settings
  - _Requirements: 1.1, 1.2_

- [x] 2. Implement basic PDF processing without OCR
  - [x] 2.1 Create PDF text extraction using pdfplumber
    - Write unit tests for PDFProcessor class with various PDF formats (TDD)
    - Implement PDFProcessor class with extract_text method to pass tests
    - Write tests for metadata extraction (file size, page count, creation date)
    - Implement metadata extraction functionality
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Implement text chunking with overlap
    - Write tests for create_chunks method with various chunk sizes and overlaps (TDD)
    - Write tests for chunking edge cases (short documents, large documents)
    - Implement create_chunks method to pass all tests
    - Ensure chunks maintain context and page number references
    - _Requirements: 1.2_

- [x] 3. Implement intelligent OCR detection and processing
  - [x] 3.1 Create OCR necessity detection
    - Write tests for needs_ocr method with image-based and text-based PDFs (TDD)
    - Write tests for configurable threshold behavior (default: 50 chars/page)
    - Implement needs_ocr method to analyze text density per page
    - Implement configurable threshold for OCR trigger
    - _Requirements: 1.1, 1.4_

  - [x] 3.2 Implement OCR processing with Tesseract
    - Write extract_with_ocr method using pytesseract
    - Add German language support and image preprocessing
    - Implement hybrid processing combining direct text and OCR results
    - Create tests for OCR accuracy and performance
    - _Requirements: 1.1, 1.4_

- [x] 4. Set up embedded vector database with ChromaDB
  - [x] 4.1 Create VectorStore class with ChromaDB
    - Write tests for VectorStore class methods (add_documents, similarity_search, delete_documents) (TDD)
    - Write tests for metadata filtering by directory structure and categories
    - Implement VectorStore class with ChromaDB structure and categories
    - _Requirements: 2.1, 6.1, 6.2_

  - [x] 4.2 Implement embedding generation
    - Integrate sentence-transformers for German text embeddings
    - Use paraphrase-multilingual-MiniLM-L12-v2 model for local processing
    - Create batch processing for efficient embedding generation
    - Write tests for embedding consistency and similarity
    - _Requirements: 2.1, 4.1_

- [x] 5. Implement document categorization engine
  - [x] 5.1 Create rule-based categorization
    - Write CategorizationEngine class with categorize_document method
    - Implement pattern matching for invoices, bank statements, contracts
    - Extract entities like invoice issuer, bank names, amounts using regex
    - Create tests with sample documents of each category
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.2 Add confidence scoring and fallback categories
    - Implement get_confidence_score method for categorization certainty
    - Create suggested_categories with multiple options when uncertain
    - Add manual category override functionality
    - Write tests for edge cases and ambiguous documents
    - _Requirements: 7.4, 7.7_

- [x] 6. Create OpenRouter LLM integration
  - [x] 6.1 Implement LLMProvider class
    - Create OpenRouter API client with chat_completion method
    - Implement model listing and selection functionality
    - Add automatic fallback chain for API failures
    - Write tests for API connectivity and error handling
    - _Requirements: 2.1, 2.2_

  - [x] 6.2 Create RAG query engine
    - Write RAGEngine class with query method
    - Implement context aggregation from vector search results
    - Create structured response formatting with source citations
    - Add confidence scoring for generated answers
    - Write tests for query accuracy and source attribution
    - _Requirements: 2.1, 2.2, 2.4_

- [x] 7. Implement CLI interface with argparse
  - [x] 7.1 Create basic CLI structure
    - Set up argparse-based CLI with main command groups (import, query, manage)
    - Implement configuration initialization and validation
    - Add help text and command documentation
    - Create tests for CLI argument parsing
    - _Requirements: 1.1, 3.1, 5.1_

  - [x] 7.2 Implement import commands
    - Create "dms import-file" command for single PDF import
    - Create "dms import-directory" command for batch import with recursion
    - Add progress bars and status reporting during import
    - Implement error handling and skip-on-failure logic
    - Write integration tests for import workflows
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 7.3 Implement query commands
    - Replace stub in handle_query function with actual RAGEngine integration
    - Initialize RAGEngine with VectorStore and LLMProvider
    - Implement date range filtering by converting CLI args to metadata filters
    - Format RAGResponse output with source citations and confidence scores
    - Add error handling for LLM API failures and empty results
    - Write tests for query command with various filter combinations
    - _Requirements: 2.1, 2.2, 2.3, 6.1, 6.4_

  - [x] 7.4 Implement management commands
    - Replace stub in handle_list function with MetadataManager.list_documents integration
    - Replace stub in handle_delete function with MetadataManager and VectorStore deletion
    - Replace stub in handle_categories function with MetadataManager.get_categories_summary
    - Replace stubs in handle_models_* functions with LLMProvider integration
    - Add confirmation prompts for destructive operations (delete)
    - Write tests for all management command implementations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 7.5, 7.6_

- [x] 8. Create SQLite metadata storage
  - [x] 8.1 Design and create database schema
    - Create tables for documents, categories, processing_logs
    - Implement database migration and initialization
    - Add indexes for efficient querying by path, category, date
    - Write tests for database operations and constraints
    - _Requirements: 1.3, 3.3, 7.4_

  - [x] 8.2 Implement metadata management
    - Create MetadataManager class for database operations
    - Implement CRUD operations for document metadata
    - Add search and filtering capabilities
    - Create backup and restore functionality
    - Write tests for data integrity and performance
    - _Requirements: 3.1, 3.2, 3.4_

- [x] 9. Add configuration and error handling
  - [x] 9.1 Create configuration system
    - Implement config.json management with default values
    - Add validation for OpenRouter API keys and model settings
    - Create configuration update commands via CLI
    - Write tests for configuration loading and validation
    - _Requirements: 2.3, 5.1_

  - [x] 9.2 Implement comprehensive error handling
    - Add graceful handling for corrupted PDFs and API failures
    - Implement logging system with configurable levels
    - Create user-friendly error messages and recovery suggestions
    - Add retry mechanisms for transient failures
    - Write tests for error scenarios and recovery
    - _Requirements: 1.4, 1.5, 2.3_

- [x] 10. Create comprehensive test suite
  - [x] 10.1 Set up test infrastructure
    - Create test data with sample PDFs of different types
    - Set up pytest configuration with fixtures and mocks
    - Implement test database and vector store isolation
    - Create performance benchmarking tests
    - _Requirements: All requirements validation_

  - [x] 10.2 Write integration tests
    - Create end-to-end tests for complete import-to-query workflows
    - Test directory structure preservation and filtering
    - Validate categorization accuracy with known documents
    - Test OpenRouter integration with multiple models
    - Write tests for CLI command combinations and edge cases
    - _Requirements: All requirements validation_

- [x] 11. Add documentation and packaging
  - [x] 11.1 Create user documentation
    - Write README with installation and usage instructions
    - Create CLI help documentation and examples
    - Add configuration guide for OpenRouter setup
    - Document troubleshooting common issues
    - _Requirements: 5.1_

  - [x] 11.2 Package for distribution
    - Create setup.py/pyproject.toml for pip installation
    - Ensure requirements.txt is complete with all dependencies
    - Create installation script for system dependencies (Tesseract)
    - Document virtual environment setup in README
    - Test installation on clean systems with fresh venv
    - _Requirements: 5.1_