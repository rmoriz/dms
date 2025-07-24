"""Tests for database schema and operations"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

from dms.storage.database import DatabaseManager, DatabaseSchema
from dms.config import DMSConfig, OpenRouterConfig, EmbeddingConfig, OCRConfig, LoggingConfig


@pytest.fixture
def temp_config():
    """Create a temporary config for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = DMSConfig(
            openrouter=OpenRouterConfig(api_key="test-key"),
            embedding=EmbeddingConfig(),
            ocr=OCRConfig(),
            logging=LoggingConfig(),
            data_dir=temp_dir
        )
        yield config


@pytest.fixture
def db_manager(temp_config):
    """Create a database manager with temporary database"""
    return DatabaseManager(temp_config)


class TestDatabaseSchema:
    """Test database schema definitions"""
    
    def test_create_tables_sql_structure(self):
        """Test that create tables SQL is properly structured"""
        sql_statements = DatabaseSchema.get_create_tables_sql()
        
        assert len(sql_statements) == 3
        assert all("CREATE TABLE IF NOT EXISTS" in sql for sql in sql_statements)
        
        # Check table names by looking for them in the SQL
        sql_text = " ".join(sql_statements)
        assert "documents" in sql_text
        assert "categories" in sql_text
        assert "processing_logs" in sql_text
    
    def test_create_indexes_sql_structure(self):
        """Test that create indexes SQL is properly structured"""
        sql_statements = DatabaseSchema.get_create_indexes_sql()
        
        assert len(sql_statements) > 0
        assert all("CREATE INDEX IF NOT EXISTS" in sql for sql in sql_statements)
        
        # Check that indexes cover important columns
        indexes_sql = " ".join(sql_statements)
        assert "file_path" in indexes_sql
        assert "directory_structure" in indexes_sql
        assert "import_date" in indexes_sql
        assert "primary_category" in indexes_sql
    
    def test_create_triggers_sql_structure(self):
        """Test that create triggers SQL is properly structured"""
        sql_statements = DatabaseSchema.get_create_triggers_sql()
        
        assert len(sql_statements) > 0
        assert all("CREATE TRIGGER IF NOT EXISTS" in sql for sql in sql_statements)


class TestDatabaseManager:
    """Test database manager functionality"""
    
    def test_initialization(self, temp_config):
        """Test database manager initialization"""
        db_manager = DatabaseManager(temp_config)
        
        assert db_manager.config == temp_config
        assert db_manager.db_path == temp_config.metadata_db_path
        assert temp_config.data_path.exists()
    
    def test_database_initialization(self, db_manager):
        """Test database initialization creates all tables and indexes"""
        db_manager.initialize_database()
        
        # Check that database file was created
        assert db_manager.db_path.exists()
        
        # Check that tables were created
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            assert "documents" in tables
            assert "categories" in tables
            assert "processing_logs" in tables
            assert "schema_version" in tables
    
    def test_database_indexes_created(self, db_manager):
        """Test that database indexes are created"""
        db_manager.initialize_database()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Check some key indexes exist
            assert any("documents_file_path" in idx for idx in indexes)
            assert any("documents_directory_structure" in idx for idx in indexes)
            assert any("categories_document_id" in idx for idx in indexes)
    
    def test_foreign_key_constraints(self, db_manager):
        """Test that foreign key constraints are enabled"""
        db_manager.initialize_database()
        
        with db_manager.get_connection() as conn:
            cursor = conn.execute("PRAGMA foreign_keys")
            result = cursor.fetchone()
            assert result[0] == 1  # Foreign keys enabled
    
    def test_schema_version_tracking(self, db_manager):
        """Test schema version is tracked correctly"""
        db_manager.initialize_database()
        
        version = db_manager.get_schema_version()
        assert version == DatabaseSchema.SCHEMA_VERSION
    
    def test_database_integrity_check(self, db_manager):
        """Test database integrity check"""
        db_manager.initialize_database()
        
        # Fresh database should pass integrity check
        assert db_manager.check_database_integrity() is True
    
    def test_database_stats(self, db_manager):
        """Test database statistics collection"""
        db_manager.initialize_database()
        
        stats = db_manager.get_database_stats()
        
        assert "documents_count" in stats
        assert "categories_count" in stats
        assert "processing_logs_count" in stats
        assert "database_size_bytes" in stats
        assert "schema_version" in stats
        
        # Fresh database should have zero records
        assert stats["documents_count"] == 0
        assert stats["categories_count"] == 0
        assert stats["processing_logs_count"] == 0
        assert stats["schema_version"] == DatabaseSchema.SCHEMA_VERSION
    
    def test_vacuum_database(self, db_manager):
        """Test database vacuum operation"""
        db_manager.initialize_database()
        
        # Should not raise any exceptions
        db_manager.vacuum_database()
    
    def test_backup_and_restore(self, db_manager, temp_config):
        """Test database backup and restore functionality"""
        db_manager.initialize_database()
        
        # Insert some test data
        with db_manager.get_connection() as conn:
            conn.execute("""
                INSERT INTO documents (
                    file_path, file_name, file_size, page_count, 
                    directory_structure, import_date, modification_date,
                    text_extraction_method, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "/test/doc.pdf", "doc.pdf", 1024, 5,
                "2024/03", datetime.now().isoformat(), datetime.now().isoformat(),
                "direct", 1.5
            ))
            conn.commit()
        
        # Create backup
        backup_path = temp_config.data_path / "backup.sqlite"
        db_manager.backup_database(backup_path)
        
        assert backup_path.exists()
        
        # Verify backup contains data
        with sqlite3.connect(backup_path) as backup_conn:
            cursor = backup_conn.execute("SELECT COUNT(*) FROM documents")
            assert cursor.fetchone()[0] == 1
        
        # Clear original database
        with db_manager.get_connection() as conn:
            conn.execute("DELETE FROM documents")
            conn.commit()
        
        # Restore from backup
        db_manager.restore_database(backup_path)
        
        # Verify data was restored
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            assert cursor.fetchone()[0] == 1
    
    def test_connection_context_manager(self, db_manager):
        """Test database connection context manager"""
        db_manager.initialize_database()
        
        # Test successful connection
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        
        # Test connection is closed after context
        # Connection should be closed, so this should work without issues
        with db_manager.get_connection() as conn:
            cursor = conn.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
    
    def test_connection_error_handling(self, db_manager):
        """Test database connection error handling"""
        db_manager.initialize_database()
        
        # Test that errors are properly handled
        with pytest.raises(sqlite3.Error):
            with db_manager.get_connection() as conn:
                conn.execute("INVALID SQL STATEMENT")
    
    def test_database_constraints(self, db_manager):
        """Test database constraints are enforced"""
        db_manager.initialize_database()
        
        with db_manager.get_connection() as conn:
            # Insert a document
            cursor = conn.execute("""
                INSERT INTO documents (
                    file_path, file_name, file_size, page_count,
                    directory_structure, import_date, modification_date,
                    text_extraction_method, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "/test/doc.pdf", "doc.pdf", 1024, 5,
                "2024/03", datetime.now().isoformat(), datetime.now().isoformat(),
                "direct", 1.5
            ))
            
            doc_id = cursor.lastrowid
            
            # Test unique constraint on file_path
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO documents (
                        file_path, file_name, file_size, page_count,
                        directory_structure, import_date, modification_date,
                        text_extraction_method, processing_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "/test/doc.pdf", "doc2.pdf", 2048, 3,
                    "2024/04", datetime.now().isoformat(), datetime.now().isoformat(),
                    "ocr", 2.5
                ))
            
            # Test foreign key constraint
            conn.execute("""
                INSERT INTO categories (
                    document_id, primary_category, confidence, entities
                ) VALUES (?, ?, ?, ?)
            """, (doc_id, "Rechnung", 0.95, "{}"))
            
            # Test cascade delete
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            
            cursor = conn.execute("SELECT COUNT(*) FROM categories WHERE document_id = ?", (doc_id,))
            assert cursor.fetchone()[0] == 0  # Category should be deleted
    
    def test_timestamp_triggers(self, db_manager):
        """Test that timestamp triggers work correctly"""
        db_manager.initialize_database()
        
        with db_manager.get_connection() as conn:
            # Insert a document
            cursor = conn.execute("""
                INSERT INTO documents (
                    file_path, file_name, file_size, page_count,
                    directory_structure, import_date, modification_date,
                    text_extraction_method, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "/test/doc.pdf", "doc.pdf", 1024, 5,
                "2024/03", datetime.now().isoformat(), datetime.now().isoformat(),
                "direct", 1.5
            ))
            
            doc_id = cursor.lastrowid
            
            # Get initial timestamps
            cursor = conn.execute("SELECT created_at, updated_at FROM documents WHERE id = ?", (doc_id,))
            initial_created, initial_updated = cursor.fetchone()
            
            # Update the document
            import time
            time.sleep(1.1)  # Ensure timestamp difference (SQLite CURRENT_TIMESTAMP has second precision)
            
            conn.execute("UPDATE documents SET file_size = ? WHERE id = ?", (2048, doc_id))
            
            # Check that updated_at changed but created_at didn't
            cursor = conn.execute("SELECT created_at, updated_at FROM documents WHERE id = ?", (doc_id,))
            final_created, final_updated = cursor.fetchone()
            
            assert initial_created == final_created
            assert final_updated > initial_updated


class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    def test_full_document_lifecycle(self, db_manager):
        """Test complete document lifecycle in database"""
        db_manager.initialize_database()
        
        with db_manager.get_connection() as conn:
            # Insert document
            cursor = conn.execute("""
                INSERT INTO documents (
                    file_path, file_name, file_size, page_count,
                    directory_structure, import_date, modification_date,
                    text_extraction_method, processing_time, content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "/test/invoice.pdf", "invoice.pdf", 1024, 2,
                "2024/03/Rechnungen", datetime.now().isoformat(), datetime.now().isoformat(),
                "direct", 1.2, "abc123"
            ))
            
            doc_id = cursor.lastrowid
            
            # Add categorization
            entities = json.dumps({"issuer": "Test Company", "amount": 100.50})
            suggested = json.dumps([("Rechnung", 0.95), ("Dokument", 0.3)])
            
            conn.execute("""
                INSERT INTO categories (
                    document_id, primary_category, confidence, entities, suggested_categories
                ) VALUES (?, ?, ?, ?, ?)
            """, (doc_id, "Rechnung", 0.95, entities, suggested))
            
            # Add processing log
            conn.execute("""
                INSERT INTO processing_logs (
                    document_id, operation, status, message, processing_time
                ) VALUES (?, ?, ?, ?, ?)
            """, (doc_id, "import", "success", "Document imported successfully", 1.2))
            
            conn.commit()
            
            # Verify all data was inserted correctly
            cursor = conn.execute("""
                SELECT d.file_path, c.primary_category, p.status
                FROM documents d
                LEFT JOIN categories c ON d.id = c.document_id
                LEFT JOIN processing_logs p ON d.id = p.document_id
                WHERE d.id = ?
            """, (doc_id,))
            
            result = cursor.fetchone()
            assert result[0] == "/test/invoice.pdf"
            assert result[1] == "Rechnung"
            assert result[2] == "success"