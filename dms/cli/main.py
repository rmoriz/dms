"""Main CLI entry point for DMS"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from dms.config import DMSConfig


def create_parser():
    """Create the main argument parser"""
    parser = argparse.ArgumentParser(
        prog="dms",
        description="Document Management System - RAG-powered PDF search and query tool"
    )
    
    # Global options
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Override data directory path"
    )
    
    # Create subparsers
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize DMS configuration")
    init_parser.add_argument("--api-key", help="OpenRouter API key")
    init_parser.add_argument("--data-dir", help="Data directory path (default: ~/.dms)")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Manage DMS configuration")
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="Configuration actions")
    
    # Config show
    config_show_parser = config_subparsers.add_parser("show", help="Show current configuration")
    config_show_parser.add_argument("--section", choices=["openrouter", "embedding", "ocr", "logging"], help="Show specific section only")
    
    # Config set
    config_set_parser = config_subparsers.add_parser("set", help="Set configuration value")
    config_set_parser.add_argument("key", help="Configuration key (e.g., 'openrouter.api_key', 'chunk_size')")
    config_set_parser.add_argument("value", help="Configuration value")
    
    # Config get
    config_get_parser = config_subparsers.add_parser("get", help="Get configuration value")
    config_get_parser.add_argument("key", help="Configuration key")
    
    # Config validate
    config_validate_parser = config_subparsers.add_parser("validate", help="Validate current configuration")
    
    # Config test
    config_test_parser = config_subparsers.add_parser("test", help="Test configuration connectivity")
    config_test_parser.add_argument("--openrouter", action="store_true", help="Test OpenRouter API connection")
    
    # Config reset
    config_reset_parser = config_subparsers.add_parser("reset", help="Reset configuration to defaults")
    config_reset_parser.add_argument("--confirm", action="store_true", help="Confirm reset without prompt")
    
    # Legacy config options for backward compatibility
    config_parser.add_argument("--show", action="store_true", help="Show current configuration (deprecated, use 'config show')")
    config_parser.add_argument("--set-api-key", help="Set OpenRouter API key (deprecated, use 'config set openrouter.api_key VALUE')")
    config_parser.add_argument("--set-model", help="Set default LLM model (deprecated, use 'config set openrouter.default_model VALUE')")
    
    # Import commands
    import_parser = subparsers.add_parser("import-file", help="Import a single PDF file")
    import_parser.add_argument("file_path", help="Path to PDF file to import")
    import_parser.add_argument("--category", "-c", help="Override automatic category detection")
    import_parser.add_argument("--force", "-f", action="store_true", help="Force reimport if file already exists")
    
    import_dir_parser = subparsers.add_parser("import-directory", help="Import all PDF files from a directory")
    import_dir_parser.add_argument("directory_path", help="Path to directory containing PDFs")
    import_dir_parser.add_argument("--recursive", "-r", action="store_true", default=True, help="Recursively import PDFs from subdirectories")
    import_dir_parser.add_argument("--no-recursive", "-nr", dest="recursive", action="store_false", help="Don't recursively import PDFs")
    import_dir_parser.add_argument("--pattern", "-p", default="*.pdf", help="File pattern to match (default: *.pdf)")
    import_dir_parser.add_argument("--force", "-f", action="store_true", help="Force reimport of existing files")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query your documents with natural language")
    query_parser.add_argument("question", help="Natural language question to ask about your documents")
    query_parser.add_argument("--model", "-m", help="Override default LLM model for this query")
    query_parser.add_argument("--category", "-c", help="Filter by document category")
    query_parser.add_argument("--directory", "-d", help="Filter by directory structure (e.g., '2024/03')")
    query_parser.add_argument("--from", dest="date_from", help="Filter documents from date (YYYY-MM-DD)")
    query_parser.add_argument("--to", dest="date_to", help="Filter documents to date (YYYY-MM-DD)")
    query_parser.add_argument("--limit", "-l", type=int, default=5, help="Maximum number of source documents to consider")
    query_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed search results and confidence scores")
    
    # Management commands
    list_parser = subparsers.add_parser("list", help="List imported documents")
    list_parser.add_argument("--category", "-c", help="Filter by document category")
    list_parser.add_argument("--directory", "-d", help="Filter by directory structure")
    list_parser.add_argument("--limit", "-l", type=int, default=50, help="Maximum number of documents to show")
    list_parser.add_argument("--details", action="store_true", help="Show detailed document information")
    
    delete_parser = subparsers.add_parser("delete", help="Delete documents and associated data")
    delete_parser.add_argument("--path", "-p", help="Delete documents by file path or directory")
    delete_parser.add_argument("--category", "-c", help="Delete documents by category")
    delete_parser.add_argument("--all", action="store_true", help="Delete all documents (requires confirmation)")
    delete_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompts")
    
    categories_parser = subparsers.add_parser("categories", help="Show auto-detected document categories")
    categories_parser.add_argument("--count", action="store_true", default=True, help="Show document count per category")
    categories_parser.add_argument("--no-count", dest="count", action="store_false", help="Don't show document count per category")
    
    # Models commands
    models_list_parser = subparsers.add_parser("models-list", help="List available LLM models")
    
    models_set_parser = subparsers.add_parser("models-set", help="Set default LLM model")
    models_set_parser.add_argument("model", help="Model name to set as default")
    
    models_test_parser = subparsers.add_parser("models-test", help="Test LLM model connectivity")
    models_test_parser.add_argument("--model", "-m", help="Test specific model (default: test all configured models)")
    
    return parser


def handle_init(args):
    """Handle init command"""
    try:
        # Create config with provided values
        config = DMSConfig.load()
        
        if args.api_key:
            config.openrouter.api_key = args.api_key
        
        if args.data_dir:
            config.data_dir = args.data_dir
        
        # Save configuration
        config.save()
        
        # Create data directories
        config.data_path.mkdir(parents=True, exist_ok=True)
        config.logs_path.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ DMS initialized successfully!")
        print(f"📁 Data directory: {config.data_path}")
        print(f"⚙️  Configuration saved to: {config.data_path / 'config.json'}")
        
        if not config.openrouter.api_key:
            print("⚠️  Warning: No OpenRouter API key configured. Set OPENROUTER_API_KEY environment variable or run 'dms init' again.")
        
    except Exception as e:
        print(f"❌ Error initializing DMS: {e}", file=sys.stderr)
        sys.exit(1)


def handle_config(args):
    """Handle config command"""
    try:
        from dms.config import ConfigValidationError
        
        dms_config = DMSConfig.load()
        
        # Handle legacy options first
        if args.show:
            _show_config(dms_config)
            return
        
        if args.set_api_key or args.set_model:
            updated = False
            if args.set_api_key:
                dms_config.openrouter.api_key = args.set_api_key
                updated = True
                print("✅ API key updated")
            
            if args.set_model:
                dms_config.openrouter.default_model = args.set_model
                updated = True
                print(f"✅ Default model set to: {args.set_model}")
            
            if updated:
                dms_config.validate_and_raise()
                dms_config.save()
                print("💾 Configuration saved")
            return
        
        # Handle new subcommands
        if not args.config_action:
            print("ℹ️  Use 'dms config show' to view configuration or 'dms config --help' for options.")
            return
        
        if args.config_action == "show":
            _show_config(dms_config, args.section)
        
        elif args.config_action == "set":
            dms_config.update_setting(args.key, args.value)
            dms_config.validate_and_raise()
            dms_config.save()
            print(f"✅ Set {args.key} = {args.value}")
            print("💾 Configuration saved")
        
        elif args.config_action == "get":
            value = dms_config.get_setting(args.key)
            print(f"{args.key} = {value}")
        
        elif args.config_action == "validate":
            errors = dms_config.validate()
            if errors:
                print("❌ Configuration validation failed:")
                for error in errors:
                    print(f"  - {error}")
                sys.exit(1)
            else:
                print("✅ Configuration is valid")
        
        elif args.config_action == "test":
            _test_config(dms_config, args)
        
        elif args.config_action == "reset":
            _reset_config(args)
            
    except ConfigValidationError as e:
        print(f"❌ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error managing configuration: {e}", file=sys.stderr)
        sys.exit(1)


def _show_config(config: DMSConfig, section: Optional[str] = None):
    """Show configuration details"""
    if section == "openrouter" or not section:
        print("🔗 OpenRouter Configuration:")
        print(f"  API Key: {'✅ Set' if config.openrouter.api_key else '❌ Not set'}")
        print(f"  Base URL: {config.openrouter.base_url}")
        print(f"  Default Model: {config.openrouter.default_model}")
        print(f"  Fallback Models: {', '.join(config.openrouter.fallback_models)}")
        print(f"  Timeout: {config.openrouter.timeout}s")
        print(f"  Max Retries: {config.openrouter.max_retries}")
        if not section:
            print()
    
    if section == "embedding" or not section:
        print("🧠 Embedding Configuration:")
        print(f"  Model: {config.embedding.model}")
        print(f"  Device: {config.embedding.device}")
        print(f"  Cache Dir: {config.embedding.cache_dir or 'Default'}")
        if not section:
            print()
    
    if section == "ocr" or not section:
        print("👁️  OCR Configuration:")
        print(f"  Enabled: {'✅' if config.ocr.enabled else '❌'}")
        print(f"  Threshold: {config.ocr.threshold} chars/page")
        print(f"  Language: {config.ocr.language}")
        print(f"  Tesseract Config: {config.ocr.tesseract_config}")
        if not section:
            print()
    
    if section == "logging" or not section:
        print("📝 Logging Configuration:")
        print(f"  Level: {config.logging.level}")
        print(f"  File Enabled: {'✅' if config.logging.file_enabled else '❌'}")
        print(f"  Console Enabled: {'✅' if config.logging.console_enabled else '❌'}")
        print(f"  Max File Size: {config.logging.max_file_size // (1024*1024)}MB")
        print(f"  Backup Count: {config.logging.backup_count}")
        if not section:
            print()
    
    if not section:
        print("⚙️  General Configuration:")
        print(f"  Data Directory: {config.data_path}")
        print(f"  Chunk Size: {config.chunk_size}")
        print(f"  Chunk Overlap: {config.chunk_overlap}")


def _test_config(config: DMSConfig, args):
    """Test configuration connectivity"""
    if args.openrouter:
        print("🧪 Testing OpenRouter connection...")
        if config.openrouter.test_connection():
            print("✅ OpenRouter connection successful")
        else:
            print("❌ OpenRouter connection failed")
            sys.exit(1)
    else:
        print("🧪 Testing all connections...")
        
        # Test OpenRouter
        print("  OpenRouter API...", end=" ")
        if config.openrouter.test_connection():
            print("✅")
        else:
            print("❌")
        
        # Test data directory access
        print("  Data directory access...", end=" ")
        try:
            config.data_path.mkdir(parents=True, exist_ok=True)
            test_file = config.data_path / ".test"
            test_file.write_text("test")
            test_file.unlink()
            print("✅")
        except Exception:
            print("❌")


def _reset_config(args):
    """Reset configuration to defaults"""
    if not args.confirm:
        response = input("⚠️  This will reset all configuration to defaults. Continue? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Reset cancelled")
            return
    
    try:
        config = DMSConfig.create_default()
        config.save()
        print("✅ Configuration reset to defaults")
        print("💾 Configuration saved")
    except Exception as e:
        print(f"❌ Error resetting configuration: {e}", file=sys.stderr)
        sys.exit(1)


def handle_import_file(args):
    """Handle import-file command"""
    from pathlib import Path
    from dms.processing.pdf_processor import PDFProcessor
    from dms.storage.metadata_manager import MetadataManager
    from dms.storage.vector_store import VectorStore
    from dms.categorization.engine import CategorizationEngine
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        # Validate file path
        file_path = Path(args.file_path)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        
        if not file_path.suffix.lower() == '.pdf':
            print(f"❌ File is not a PDF: {file_path}", file=sys.stderr)
            sys.exit(1)
        
        print(f"🔄 Importing file: {file_path}")
        
        # Initialize components
        pdf_processor = PDFProcessor(config)
        metadata_manager = MetadataManager(config)
        vector_store = VectorStore(str(config.data_path / "chroma.db"))
        categorization_engine = CategorizationEngine()
        
        # Check if file already exists (unless force is enabled)
        if not args.force:
            existing_doc = metadata_manager.get_document_by_path(str(file_path))
            if existing_doc:
                print(f"⚠️  File already imported: {file_path}")
                print("   Use --force to reimport")
                return
        
        # Process PDF
        print("📄 Extracting text...")
        try:
            document_content = pdf_processor.extract_text_with_ocr_fallback(str(file_path))
        except Exception as e:
            print(f"❌ Failed to process PDF: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Categorize document
        print("🏷️  Categorizing document...")
        if args.category:
            category_result = categorization_engine.categorize_document_with_override(
                document_content.text, args.category
            )
            print(f"📂 Category override: {args.category}")
        else:
            category_result = categorization_engine.categorize_document(document_content.text)
        
        print(f"📂 Detected category: {category_result.primary_category} (confidence: {category_result.confidence:.2f})")
        
        # Create text chunks
        print("✂️  Creating text chunks...")
        chunks = pdf_processor.create_chunks_from_document(
            document_content, 
            chunk_size=config.chunk_size,
            overlap=config.chunk_overlap
        )
        print(f"📝 Created {len(chunks)} text chunks")
        
        # Store in metadata database
        print("💾 Storing metadata...")
        try:
            document_id = metadata_manager.add_document(document_content, category_result)
        except Exception as e:
            print(f"❌ Failed to store metadata: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Store in vector database
        print("🧠 Storing embeddings...")
        try:
            vector_store.add_documents(chunks)
        except Exception as e:
            print(f"❌ Failed to store embeddings: {e}", file=sys.stderr)
            # Try to clean up metadata if vector storage failed
            metadata_manager.delete_document(document_id)
            sys.exit(1)
        
        # Success
        print(f"✅ Successfully imported: {file_path}")
        print(f"   📊 Document ID: {document_id}")
        print(f"   📄 Pages: {document_content.page_count}")
        print(f"   📝 Chunks: {len(chunks)}")
        print(f"   🏷️  Category: {category_result.primary_category}")
        if category_result.entities:
            print(f"   🔍 Entities: {', '.join(f'{k}: {v}' for k, v in category_result.entities.items())}")
        print(f"   ⏱️  Processing time: {document_content.processing_time:.2f}s")
        
    except KeyboardInterrupt:
        print("\n❌ Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}", file=sys.stderr)
        sys.exit(1)


def handle_import_directory(args):
    """Handle import-directory command"""
    from pathlib import Path
    import glob
    import time
    from dms.processing.pdf_processor import PDFProcessor
    from dms.storage.metadata_manager import MetadataManager
    from dms.storage.vector_store import VectorStore
    from dms.categorization.engine import CategorizationEngine
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        # Validate directory path
        directory_path = Path(args.directory_path)
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory_path}", file=sys.stderr)
            sys.exit(1)
        
        if not directory_path.is_dir():
            print(f"❌ Path is not a directory: {directory_path}", file=sys.stderr)
            sys.exit(1)
        
        print(f"🔄 Importing directory: {directory_path}")
        print(f"📁 Recursive: {args.recursive}")
        print(f"🔍 Pattern: {args.pattern}")
        if args.force:
            print("🔄 Force reimport enabled")
        
        # Find PDF files
        print("🔍 Scanning for PDF files...")
        pdf_files = []
        
        if args.recursive:
            # Use recursive glob pattern
            pattern = f"**/{args.pattern}"
            pdf_files = list(directory_path.glob(pattern))
        else:
            # Use non-recursive glob pattern
            pdf_files = list(directory_path.glob(args.pattern))
        
        # Filter to only PDF files and sort
        pdf_files = [f for f in pdf_files if f.suffix.lower() == '.pdf' and f.is_file()]
        pdf_files.sort()
        
        if not pdf_files:
            print(f"📭 No PDF files found matching pattern '{args.pattern}'")
            return
        
        print(f"📄 Found {len(pdf_files)} PDF files")
        
        # Initialize components
        pdf_processor = PDFProcessor(config)
        metadata_manager = MetadataManager(config)
        vector_store = VectorStore(str(config.data_path / "chroma.db"))
        categorization_engine = CategorizationEngine()
        
        # Import statistics
        stats = {
            'total': len(pdf_files),
            'processed': 0,
            'skipped': 0,
            'failed': 0,
            'start_time': time.time()
        }
        
        # Process each file
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
                
                # Check if file already exists (unless force is enabled)
                if not args.force:
                    existing_doc = metadata_manager.get_document_by_path(str(pdf_file))
                    if existing_doc:
                        print(f"   ⏭️  Skipped (already imported)")
                        stats['skipped'] += 1
                        continue
                
                # Process PDF
                print(f"   📄 Extracting text...")
                try:
                    document_content = pdf_processor.extract_text_with_ocr_fallback(str(pdf_file))
                except Exception as e:
                    print(f"   ❌ Failed to process PDF: {e}")
                    stats['failed'] += 1
                    continue
                
                # Categorize document
                print(f"   🏷️  Categorizing...")
                category_result = categorization_engine.categorize_document(document_content.text)
                
                # Create text chunks
                print(f"   ✂️  Creating chunks...")
                chunks = pdf_processor.create_chunks_from_document(
                    document_content, 
                    chunk_size=config.chunk_size,
                    overlap=config.chunk_overlap
                )
                
                # Store in metadata database
                print(f"   💾 Storing metadata...")
                try:
                    document_id = metadata_manager.add_document(document_content, category_result)
                except Exception as e:
                    print(f"   ❌ Failed to store metadata: {e}")
                    stats['failed'] += 1
                    continue
                
                # Store in vector database
                print(f"   🧠 Storing embeddings...")
                try:
                    vector_store.add_documents(chunks)
                except Exception as e:
                    print(f"   ❌ Failed to store embeddings: {e}")
                    # Try to clean up metadata if vector storage failed
                    metadata_manager.delete_document(document_id)
                    stats['failed'] += 1
                    continue
                
                # Success
                print(f"   ✅ Success: {category_result.primary_category} ({len(chunks)} chunks, {document_content.processing_time:.1f}s)")
                stats['processed'] += 1
                
            except KeyboardInterrupt:
                print(f"\n❌ Import cancelled by user")
                break
            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
                stats['failed'] += 1
                continue
        
        # Print final statistics
        elapsed_time = time.time() - stats['start_time']
        print(f"\n📊 Import Summary:")
        print(f"   📄 Total files: {stats['total']}")
        print(f"   ✅ Processed: {stats['processed']}")
        print(f"   ⏭️  Skipped: {stats['skipped']}")
        print(f"   ❌ Failed: {stats['failed']}")
        print(f"   ⏱️  Total time: {elapsed_time:.1f}s")
        
        if stats['processed'] > 0:
            avg_time = elapsed_time / stats['processed']
            print(f"   📈 Average time per file: {avg_time:.1f}s")
        
        if stats['failed'] > 0:
            print(f"\n⚠️  {stats['failed']} files failed to import. Check the error messages above.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n❌ Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during directory import: {e}", file=sys.stderr)
        sys.exit(1)


def handle_query(args):
    """Handle query command"""
    print(f"🤔 Question: {args.question}")
    
    if args.model:
        print(f"🤖 Using model: {args.model}")
    
    if args.category:
        print(f"📂 Category: {args.category}")
    
    if args.directory:
        print(f"📁 Directory: {args.directory}")
    
    if args.date_from or args.date_to:
        date_range = f"{args.date_from or 'start'} to {args.date_to or 'end'}"
        print(f"📅 Date range: {date_range}")
    
    print(f"📊 Limit: {args.limit}")
    
    if args.verbose:
        print("🔍 Verbose mode enabled")
    
    # Implementation will be added in task 7.3
    print("⚠️  Query functionality not yet implemented")


def handle_list(args):
    """Handle list command"""
    print("📋 Listing documents...")
    
    if args.category:
        print(f"📂 Category: {args.category}")
    
    if args.directory:
        print(f"📁 Directory: {args.directory}")
    
    print(f"📊 Limit: {args.limit}")
    
    if args.details:
        print("📄 Detailed view enabled")
    
    # Implementation will be added in task 7.4
    print("⚠️  List functionality not yet implemented")


def handle_delete(args):
    """Handle delete command"""
    if not any([args.path, args.category, args.all]):
        print("❌ Must specify --path, --category, or --all", file=sys.stderr)
        sys.exit(1)
    
    if args.all:
        print("🗑️  Deleting all documents...")
    elif args.path:
        print(f"🗑️  Deleting documents at path: {args.path}")
    elif args.category:
        print(f"🗑️  Deleting documents in category: {args.category}")
    
    if args.force:
        print("⚡ Force mode enabled (skipping confirmations)")
    
    # Implementation will be added in task 7.4
    print("⚠️  Delete functionality not yet implemented")


def handle_categories(args):
    """Handle categories command"""
    print("📂 Document categories:")
    if args.count:
        print("📊 Document counts will be shown")
    # Implementation will be added in task 7.4
    print("⚠️  Categories functionality not yet implemented")


def handle_models_list(args):
    """Handle models-list command"""
    print("🤖 Available models:")
    # Implementation will be added in task 7.4
    print("⚠️  Models list functionality not yet implemented")


def handle_models_set(args):
    """Handle models-set command"""
    print(f"🤖 Setting default model to: {args.model}")
    # Implementation will be added in task 7.4
    print("⚠️  Set model functionality not yet implemented")


def handle_models_test(args):
    """Handle models-test command"""
    if args.model:
        print(f"🧪 Testing model: {args.model}")
    else:
        print("🧪 Testing all configured models...")
    
    # Implementation will be added in task 7.4
    print("⚠️  Test models functionality not yet implemented")


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging early
    from dms.logging_setup import setup_cli_logging
    logger = setup_cli_logging(verbose=getattr(args, 'verbose', False))
    
    # Handle global configuration
    if args.config or args.data_dir:
        try:
            config_file = Path(args.config) if args.config else None
            config = DMSConfig.load(config_file)
            
            # Override data directory if provided
            if args.data_dir:
                config.data_dir = args.data_dir
            
            # Ensure data directory exists
            config.data_path.mkdir(parents=True, exist_ok=True)
            config.logs_path.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Configuration loaded from {config_file or 'default location'}")
            logger.debug(f"Data directory: {config.data_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            print(f"Error loading configuration: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Handle commands
    if not args.command:
        parser.print_help()
        return
    
    logger.debug(f"Executing command: {args.command}")
    
    command_handlers = {
        "init": handle_init,
        "config": handle_config,
        "import-file": handle_import_file,
        "import-directory": handle_import_directory,
        "query": handle_query,
        "list": handle_list,
        "delete": handle_delete,
        "categories": handle_categories,
        "models-list": handle_models_list,
        "models-set": handle_models_set,
        "models-test": handle_models_test,
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            print("\n❌ Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Command {args.command} failed: {e}", exc_info=True)
            print(f"❌ Command failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        logger.error(f"Unknown command: {args.command}")
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


def cli_main():
    """Entry point for the CLI"""
    main()


if __name__ == "__main__":
    cli_main()