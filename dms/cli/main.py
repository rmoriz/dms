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
        
        # Filter to only PDF files and sort - use case-insensitive matching
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
    from dms.storage.vector_store import VectorStore
    from dms.storage.metadata_manager import MetadataManager
    from dms.llm.provider import LLMProvider
    from dms.rag.engine import RAGEngine
    from dms.errors import LLMAPIError
    from datetime import datetime
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        print(f"🤔 Question: {args.question}")
        
        if args.model:
            print(f"🤖 Using model: {args.model}")
        
        if args.category:
            print(f"📂 Category filter: {args.category}")
        
        if args.directory:
            print(f"📁 Directory filter: {args.directory}")
        
        if args.date_from or args.date_to:
            date_range = f"{args.date_from or 'start'} to {args.date_to or 'end'}"
            print(f"📅 Date range: {date_range}")
        
        print(f"📊 Result limit: {args.limit}")
        
        if args.verbose:
            print("🔍 Verbose mode enabled")
        
        # Initialize components
        print("🔄 Initializing search components...")
        vector_store = VectorStore(str(config.data_path / "chroma.db"))
        metadata_manager = MetadataManager(config)
        llm_provider = LLMProvider(config.openrouter)
        rag_engine = RAGEngine(vector_store, llm_provider, config)
        
        # Build filters from CLI arguments
        filters = {}
        
        if args.category:
            filters["category"] = args.category
        
        if args.directory:
            filters["directory_structure"] = args.directory
        
        # Handle date filtering
        if args.date_from or args.date_to:
            # Convert date strings to metadata filters
            if args.date_from:
                try:
                    from_date = datetime.strptime(args.date_from, "%Y-%m-%d")
                    filters["date_from"] = from_date
                except ValueError:
                    print(f"❌ Invalid date format for --from: {args.date_from}. Use YYYY-MM-DD format.", file=sys.stderr)
                    sys.exit(1)
            
            if args.date_to:
                try:
                    to_date = datetime.strptime(args.date_to, "%Y-%m-%d")
                    filters["date_to"] = to_date
                except ValueError:
                    print(f"❌ Invalid date format for --to: {args.date_to}. Use YYYY-MM-DD format.", file=sys.stderr)
                    sys.exit(1)
        
        # Perform RAG query
        print("🔍 Searching documents...")
        try:
            rag_response = rag_engine.query(
                question=args.question,
                filters=filters,
                model=args.model
            )
        except LLMAPIError as e:
            print(f"❌ LLM API error: {e}", file=sys.stderr)
            print("💡 Try again later or check your API configuration.", file=sys.stderr)
            sys.exit(1)
        
        # Display results
        if rag_response.search_results_count == 0:
            print("📭 No relevant documents found for your question.")
            print("💡 Try rephrasing your question or check if relevant documents have been imported.")
            return
        
        print(f"\n✅ Found {rag_response.search_results_count} relevant document(s)")
        print(f"🎯 Confidence: {rag_response.confidence:.2f}")
        
        print(f"\n💬 Answer:")
        print(f"{rag_response.answer}")
        
        # Show sources
        if rag_response.sources:
            print(f"\n📚 Sources:")
            for i, source in enumerate(rag_response.sources[:args.limit], 1):
                print(f"  {i}. {source.document_path} (Page {source.page_number})")
                if args.verbose:
                    print(f"     Relevance: {source.relevance_score:.3f}")
                    print(f"     Content preview: {source.chunk_content[:100]}...")
                    print()
        
        if args.verbose:
            print(f"\n🔍 Search Details:")
            print(f"   Total sources found: {len(rag_response.sources)}")
            print(f"   Answer confidence: {rag_response.confidence:.3f}")
            if filters:
                print(f"   Applied filters: {filters}")
        
    except KeyboardInterrupt:
        print("\n❌ Query cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error during query: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def handle_list(args):
    """Handle list command"""
    from dms.storage.metadata_manager import MetadataManager
    from datetime import datetime
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        print("📋 Listing documents...")
        
        if args.category:
            print(f"📂 Category filter: {args.category}")
        
        if args.directory:
            print(f"📁 Directory filter: {args.directory}")
        
        print(f"📊 Limit: {args.limit}")
        
        if args.details:
            print("📄 Detailed view enabled")
        
        # Initialize metadata manager
        metadata_manager = MetadataManager(config)
        
        # Build filters
        filters = {}
        if args.category:
            filters['category'] = args.category
        if args.directory:
            filters['directory_structure'] = args.directory
        
        # Get documents
        documents = metadata_manager.list_documents(
            filters=filters,
            limit=args.limit,
            include_deleted=False
        )
        
        if not documents:
            print("📭 No documents found matching the criteria.")
            return
        
        print(f"\n📄 Found {len(documents)} document(s):")
        print("=" * 80)
        
        for i, doc in enumerate(documents, 1):
            # Basic info
            file_name = doc['file_name']
            category = doc.get('category', 'Unknown')
            pages = doc['page_count']
            size_mb = doc['file_size'] / (1024 * 1024)
            
            print(f"{i:3d}. {file_name}")
            print(f"     📂 Category: {category}")
            print(f"     📁 Path: {doc['directory_structure']}")
            print(f"     📄 Pages: {pages} | 💾 Size: {size_mb:.1f} MB")
            
            if args.details:
                # Additional details
                import_date = datetime.fromisoformat(doc['import_date']).strftime("%Y-%m-%d %H:%M")
                processing_time = doc.get('processing_time', 0)
                ocr_used = doc.get('ocr_used', False)
                confidence = doc.get('confidence', 0)
                
                print(f"     📅 Imported: {import_date}")
                print(f"     ⏱️  Processing: {processing_time:.2f}s")
                print(f"     👁️  OCR: {'Yes' if ocr_used else 'No'}")
                print(f"     🎯 Confidence: {confidence:.2f}")
                
                # Show entities if available
                entities = doc.get('entities')
                if entities:
                    entities_str = ', '.join(f"{k}: {v}" for k, v in entities.items())
                    print(f"     🔍 Entities: {entities_str}")
            
            print()
        
        # Summary statistics
        total_size = sum(doc['file_size'] for doc in documents) / (1024 * 1024)
        total_pages = sum(doc['page_count'] for doc in documents)
        
        print("=" * 80)
        print(f"📊 Summary: {len(documents)} documents, {total_pages} pages, {total_size:.1f} MB total")
        
        # Category breakdown
        categories = {}
        for doc in documents:
            cat = doc.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        if len(categories) > 1:
            print("📂 Categories:", ', '.join(f"{cat}: {count}" for cat, count in categories.items()))
        
    except KeyboardInterrupt:
        print("\n❌ List operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error listing documents: {e}", file=sys.stderr)
        sys.exit(1)


def handle_delete(args):
    """Handle delete command"""
    from dms.storage.metadata_manager import MetadataManager
    from dms.storage.vector_store import VectorStore
    
    if not any([args.path, args.category, args.all]):
        print("❌ Must specify --path, --category, or --all", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        # Initialize components
        metadata_manager = MetadataManager(config)
        vector_store = VectorStore(str(config.data_path / "chroma.db"))
        
        # Determine what to delete
        documents_to_delete = []
        
        if args.all:
            print("🗑️  Preparing to delete ALL documents...")
            documents_to_delete = metadata_manager.list_documents(include_deleted=False)
            
        elif args.path:
            print(f"🗑️  Preparing to delete documents at path: {args.path}")
            # Find documents matching the path (can be file or directory)
            all_docs = metadata_manager.list_documents(include_deleted=False)
            for doc in all_docs:
                if args.path in doc['file_path'] or args.path in doc['directory_structure']:
                    documents_to_delete.append(doc)
                    
        elif args.category:
            print(f"🗑️  Preparing to delete documents in category: {args.category}")
            documents_to_delete = metadata_manager.list_documents(
                filters={'category': args.category},
                include_deleted=False
            )
        
        if not documents_to_delete:
            print("📭 No documents found matching the deletion criteria.")
            return
        
        # Show what will be deleted
        print(f"\n⚠️  Found {len(documents_to_delete)} document(s) to delete:")
        for i, doc in enumerate(documents_to_delete[:10], 1):  # Show first 10
            print(f"  {i}. {doc['file_name']} ({doc.get('category', 'Unknown')})")
        
        if len(documents_to_delete) > 10:
            print(f"  ... and {len(documents_to_delete) - 10} more documents")
        
        # Confirmation (unless force mode)
        if not args.force:
            print(f"\n🚨 This will permanently delete {len(documents_to_delete)} document(s) and all associated data!")
            response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
            if response.lower() != 'yes':
                print("❌ Deletion cancelled")
                return
        else:
            print("⚡ Force mode enabled - skipping confirmation")
        
        # Perform deletion
        print(f"\n🗑️  Deleting {len(documents_to_delete)} document(s)...")
        
        deleted_count = 0
        failed_count = 0
        
        for doc in documents_to_delete:
            try:
                doc_id = doc['id']
                file_path = doc['file_path']
                
                # Delete from vector store first
                vector_store.delete_documents(file_path)
                
                # Delete from metadata database (hard delete)
                success = metadata_manager.delete_document(doc_id, hard_delete=True)
                
                if success:
                    deleted_count += 1
                    print(f"  ✅ Deleted: {doc['file_name']}")
                else:
                    failed_count += 1
                    print(f"  ❌ Failed to delete: {doc['file_name']}")
                    
            except Exception as e:
                failed_count += 1
                print(f"  ❌ Error deleting {doc['file_name']}: {e}")
        
        # Summary
        print(f"\n📊 Deletion Summary:")
        print(f"  ✅ Successfully deleted: {deleted_count}")
        if failed_count > 0:
            print(f"  ❌ Failed to delete: {failed_count}")
        
        if failed_count > 0:
            print(f"\n⚠️  Some deletions failed. Check the error messages above.")
            sys.exit(1)
        else:
            print(f"\n🎉 All documents deleted successfully!")
        
    except KeyboardInterrupt:
        print("\n❌ Delete operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during deletion: {e}", file=sys.stderr)
        sys.exit(1)


def handle_categories(args):
    """Handle categories command"""
    from dms.storage.metadata_manager import MetadataManager
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        print("📂 Document categories:")
        
        # Initialize metadata manager
        metadata_manager = MetadataManager(config)
        
        # Get categories summary
        categories_summary = metadata_manager.get_categories_summary()
        
        if not categories_summary:
            print("📭 No categories found. Import some documents first.")
            return
        
        # Sort categories by count (descending) then by name
        sorted_categories = sorted(
            categories_summary.items(),
            key=lambda x: (-x[1], x[0])
        )
        
        print()
        total_docs = 0
        
        for category, count in sorted_categories:
            total_docs += count
            if args.count:
                print(f"  📁 {category}: {count} document(s)")
            else:
                print(f"  📁 {category}")
        
        if args.count:
            print(f"\n📊 Total: {len(sorted_categories)} categories, {total_docs} documents")
        
        # Show directory structure breakdown if available
        directory_structure = metadata_manager.get_directory_structure()
        if directory_structure and len(directory_structure) > 1:
            print(f"\n📁 Directory Structure:")
            sorted_dirs = sorted(directory_structure.items())
            for directory, count in sorted_dirs:
                if directory:  # Skip empty directory names
                    print(f"  📂 {directory}: {count} document(s)")
        
    except KeyboardInterrupt:
        print("\n❌ Categories operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error retrieving categories: {e}", file=sys.stderr)
        sys.exit(1)


def handle_models_list(args):
    """Handle models-list command"""
    from dms.llm.provider import LLMProvider
    from dms.errors import LLMAPIError
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        print("🤖 Available models:")
        
        # Initialize LLM provider
        llm_provider = LLMProvider(config.openrouter)
        
        # Get available models
        try:
            models = llm_provider.list_available_models()
        except LLMAPIError as e:
            print(f"❌ Failed to fetch models: {e}", file=sys.stderr)
            print("💡 Check your API key and internet connection.", file=sys.stderr)
            sys.exit(1)
        
        if not models:
            print("📭 No models available.")
            return
        
        # Show current configuration
        print(f"\n⚙️  Current Configuration:")
        print(f"  Default model: {config.openrouter.default_model}")
        print(f"  Fallback models: {', '.join(config.openrouter.fallback_models)}")
        
        # Group models by provider
        model_groups = {}
        for model in models:
            if '/' in model:
                provider = model.split('/')[0]
                model_name = model.split('/', 1)[1]
            else:
                provider = 'Other'
                model_name = model
            
            if provider not in model_groups:
                model_groups[provider] = []
            model_groups[provider].append((model, model_name))
        
        print(f"\n📋 Available Models ({len(models)} total):")
        
        # Sort providers
        for provider in sorted(model_groups.keys()):
            print(f"\n  🏢 {provider.title()}:")
            
            # Sort models within provider
            for full_model, display_name in sorted(model_groups[provider], key=lambda x: x[1]):
                # Mark current default
                marker = " ⭐" if full_model == config.openrouter.default_model else ""
                # Mark fallback models
                if full_model in config.openrouter.fallback_models:
                    marker += " 🔄"
                
                print(f"    • {display_name}{marker}")
        
        print(f"\n💡 Legend:")
        print(f"  ⭐ Current default model")
        print(f"  🔄 Configured fallback model")
        
    except KeyboardInterrupt:
        print("\n❌ Models list operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error listing models: {e}", file=sys.stderr)
        sys.exit(1)


def handle_models_set(args):
    """Handle models-set command"""
    from dms.llm.provider import LLMProvider
    from dms.errors import LLMAPIError
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        print(f"🤖 Setting default model to: {args.model}")
        
        # Initialize LLM provider to validate model
        llm_provider = LLMProvider(config.openrouter)
        
        # Validate that the model exists
        try:
            available_models = llm_provider.list_available_models()
            if args.model not in available_models:
                print(f"❌ Model '{args.model}' is not available.", file=sys.stderr)
                print(f"💡 Use 'dms models-list' to see available models.", file=sys.stderr)
                sys.exit(1)
        except LLMAPIError as e:
            print(f"⚠️  Warning: Could not validate model availability: {e}")
            print(f"🔄 Proceeding anyway...")
        
        # Update configuration
        old_model = config.openrouter.default_model
        config.openrouter.default_model = args.model
        
        # Validate and save configuration
        try:
            config.validate_and_raise()
            config.save()
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}", file=sys.stderr)
            sys.exit(1)
        
        print(f"✅ Default model updated successfully!")
        print(f"   Previous: {old_model}")
        print(f"   New: {args.model}")
        print(f"💾 Configuration saved")
        
        # Test the new model
        print(f"\n🧪 Testing new model...")
        try:
            test_messages = [{"role": "user", "content": "Hello, this is a test."}]
            response = llm_provider.chat_completion(test_messages, args.model)
            print(f"✅ Model test successful!")
            if len(response) > 100:
                print(f"📝 Response preview: {response[:100]}...")
            else:
                print(f"📝 Response: {response}")
        except LLMAPIError as e:
            print(f"⚠️  Warning: Model test failed: {e}")
            print(f"💡 The model was set but may not be working correctly.")
        
    except KeyboardInterrupt:
        print("\n❌ Set model operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error setting model: {e}", file=sys.stderr)
        sys.exit(1)


def handle_models_test(args):
    """Handle models-test command"""
    from dms.llm.provider import LLMProvider
    from dms.errors import LLMAPIError
    
    try:
        # Load configuration
        config = DMSConfig.load()
        
        # Initialize LLM provider
        llm_provider = LLMProvider(config.openrouter)
        
        # Determine which models to test
        models_to_test = []
        if args.model:
            print(f"🧪 Testing specific model: {args.model}")
            models_to_test = [args.model]
        else:
            print("🧪 Testing all configured models...")
            models_to_test = [config.openrouter.default_model] + config.openrouter.fallback_models
            # Remove duplicates while preserving order
            seen = set()
            models_to_test = [m for m in models_to_test if not (m in seen or seen.add(m))]
        
        print(f"📋 Models to test: {', '.join(models_to_test)}")
        
        # Test each model
        test_message = [{"role": "user", "content": "Hello! Please respond with 'Test successful' to confirm you're working."}]
        
        results = {}
        
        for i, model in enumerate(models_to_test, 1):
            print(f"\n[{i}/{len(models_to_test)}] Testing {model}...")
            
            try:
                response = llm_provider.chat_completion(test_message, model)
                results[model] = {
                    'status': 'success',
                    'response': response,
                    'error': None
                }
                print(f"  ✅ Success!")
                if len(response) > 80:
                    print(f"  📝 Response: {response[:80]}...")
                else:
                    print(f"  📝 Response: {response}")
                    
            except LLMAPIError as e:
                results[model] = {
                    'status': 'failed',
                    'response': None,
                    'error': str(e)
                }
                print(f"  ❌ Failed: {e}")
            except Exception as e:
                results[model] = {
                    'status': 'error',
                    'response': None,
                    'error': str(e)
                }
                print(f"  💥 Error: {e}")
        
        # Summary
        print(f"\n📊 Test Summary:")
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        failed = len(results) - successful
        
        print(f"  ✅ Successful: {successful}/{len(results)}")
        if failed > 0:
            print(f"  ❌ Failed: {failed}/{len(results)}")
        
        # Show failed models
        failed_models = [model for model, result in results.items() if result['status'] != 'success']
        if failed_models:
            print(f"\n❌ Failed Models:")
            for model in failed_models:
                error = results[model]['error']
                print(f"  • {model}: {error}")
            
            print(f"\n💡 Suggestions:")
            print(f"  - Check your OpenRouter API key")
            print(f"  - Verify your internet connection")
            print(f"  - Some models may be temporarily unavailable")
            print(f"  - Use 'dms models-list' to see currently available models")
        
        if failed > 0:
            sys.exit(1)
        else:
            print(f"\n🎉 All models are working correctly!")
        
    except KeyboardInterrupt:
        print("\n❌ Model test operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error testing models: {e}", file=sys.stderr)
        sys.exit(1)


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