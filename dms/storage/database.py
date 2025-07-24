"""SQLite database schema and operations for DMS metadata storage"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from ..config import DMSConfig

logger = logging.getLogger(__name__)


class DatabaseSchema:
    """Database schema definitions and migrations"""
    
    # Schema version for migrations
    SCHEMA_VERSION = 1
    
    @staticmethod
    def get_create_tables_sql() -> List[str]:
        """Get SQL statements to create all tables"""
        return [
            # Documents table - stores document metadata
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                page_count INTEGER NOT NULL,
                directory_structure TEXT NOT NULL,
                import_date TIMESTAMP NOT NULL,
                creation_date TIMESTAMP,
                modification_date TIMESTAMP NOT NULL,
                ocr_used BOOLEAN NOT NULL DEFAULT 0,
                text_extraction_method TEXT NOT NULL,
                processing_time REAL NOT NULL,
                content_hash TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Categories table - stores document categorization results
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                primary_category TEXT NOT NULL,
                confidence REAL NOT NULL,
                entities TEXT,  -- JSON string of extracted entities
                suggested_categories TEXT,  -- JSON string of suggested categories with scores
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
            )
            """,
            
            # Processing logs table - stores processing history and errors
            """
            CREATE TABLE IF NOT EXISTS processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,  -- 'success', 'error', 'warning'
                message TEXT,
                details TEXT,  -- JSON string with additional details
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE SET NULL
            )
            """
        ]
    
    @staticmethod
    def get_create_indexes_sql() -> List[str]:
        """Get SQL statements to create indexes for efficient querying"""
        return [
            # Documents table indexes
            "CREATE INDEX IF NOT EXISTS idx_documents_file_path ON documents (file_path)",
            "CREATE INDEX IF NOT EXISTS idx_documents_directory_structure ON documents (directory_structure)",
            "CREATE INDEX IF NOT EXISTS idx_documents_import_date ON documents (import_date)",
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents (status)",
            "CREATE INDEX IF NOT EXISTS idx_documents_file_name ON documents (file_name)",
            "CREATE INDEX IF NOT EXISTS idx_documents_ocr_used ON documents (ocr_used)",
            
            # Categories table indexes
            "CREATE INDEX IF NOT EXISTS idx_categories_document_id ON categories (document_id)",
            "CREATE INDEX IF NOT EXISTS idx_categories_primary_category ON categories (primary_category)",
            "CREATE INDEX IF NOT EXISTS idx_categories_confidence ON categories (confidence)",
            
            # Processing logs table indexes
            "CREATE INDEX IF NOT EXISTS idx_processing_logs_document_id ON processing_logs (document_id)",
            "CREATE INDEX IF NOT EXISTS idx_processing_logs_operation ON processing_logs (operation)",
            "CREATE INDEX IF NOT EXISTS idx_processing_logs_status ON processing_logs (status)",
            "CREATE INDEX IF NOT EXISTS idx_processing_logs_created_at ON processing_logs (created_at)"
        ]
    
    @staticmethod
    def get_create_triggers_sql() -> List[str]:
        """Get SQL statements to create triggers for data integrity"""
        return [
            # Update timestamp trigger for documents
            """
            CREATE TRIGGER IF NOT EXISTS update_documents_timestamp 
            AFTER UPDATE ON documents
            BEGIN
                UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
            """
        ]


class DatabaseManager:
    """Manages SQLite database connections and schema operations"""
    
    def __init__(self, config: DMSConfig):
        self.config = config
        self.db_path = config.metadata_db_path
        self._ensure_data_directory()
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists"""
        self.config.data_path.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with proper error handling"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys = ON")
            # Set WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode = WAL")
            # Row factory for dict-like access
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize_database(self) -> None:
        """Initialize database with schema and indexes"""
        logger.info(f"Initializing database at {self.db_path}")
        
        with self.get_connection() as conn:
            try:
                # Create tables
                for sql in DatabaseSchema.get_create_tables_sql():
                    conn.execute(sql)
                
                # Create indexes
                for sql in DatabaseSchema.get_create_indexes_sql():
                    conn.execute(sql)
                
                # Create triggers
                for sql in DatabaseSchema.get_create_triggers_sql():
                    conn.execute(sql)
                
                # Create or update schema version table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insert current schema version
                conn.execute(
                    "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                    (DatabaseSchema.SCHEMA_VERSION,)
                )
                
                conn.commit()
                logger.info("Database initialized successfully")
                
            except sqlite3.Error as e:
                logger.error(f"Failed to initialize database: {e}")
                conn.rollback()
                raise
    
    def get_schema_version(self) -> Optional[int]:
        """Get current schema version"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error:
            return None
    
    def check_database_integrity(self) -> bool:
        """Check database integrity"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                return result[0] == "ok" if result else False
        except sqlite3.Error as e:
            logger.error(f"Database integrity check failed: {e}")
            return False
    
    def vacuum_database(self) -> None:
        """Vacuum database to reclaim space and optimize"""
        logger.info("Vacuuming database")
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuumed successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to vacuum database: {e}")
            raise
    
    def backup_database(self, backup_path: Path) -> None:
        """Create a backup of the database"""
        logger.info(f"Creating database backup at {backup_path}")
        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self.get_connection() as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            logger.info("Database backup created successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to create database backup: {e}")
            raise
    
    def restore_database(self, backup_path: Path) -> None:
        """Restore database from backup"""
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        logger.info(f"Restoring database from {backup_path}")
        try:
            # Create backup of current database
            current_backup = self.db_path.with_suffix('.sqlite.backup')
            if self.db_path.exists():
                self.backup_database(current_backup)
            
            # Restore from backup
            with sqlite3.connect(backup_path) as source:
                with self.get_connection() as target:
                    source.backup(target)
            
            logger.info("Database restored successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to restore database: {e}")
            raise
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                stats = {}
                
                # Table row counts
                for table in ['documents', 'categories', 'processing_logs']:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Database size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats['database_size_bytes'] = page_count * page_size
                
                # Schema version
                stats['schema_version'] = self.get_schema_version()
                
                return stats
        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}