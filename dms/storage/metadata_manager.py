"""Metadata management for DMS documents"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import asdict

from ..models import DocumentContent, DocumentMetadata, CategoryResult
from ..config import DMSConfig
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class MetadataManager:
    """Manages document metadata storage and retrieval"""
    
    def __init__(self, config: DMSConfig):
        self.config = config
        self.db_manager = DatabaseManager(config)
        self._ensure_initialized()
    
    def _ensure_initialized(self) -> None:
        """Ensure database is initialized"""
        if not self.config.metadata_db_path.exists():
            self.db_manager.initialize_database()
    
    def add_document(self, document: DocumentContent, category_result: Optional[CategoryResult] = None) -> int:
        """Add a new document to the metadata store"""
        logger.info(f"Adding document: {document.file_path}")
        
        try:
            with self.db_manager.get_connection() as conn:
                # Insert document
                cursor = conn.execute("""
                    INSERT INTO documents (
                        file_path, file_name, file_size, page_count,
                        directory_structure, import_date, creation_date, modification_date,
                        ocr_used, text_extraction_method, processing_time, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.file_path,
                    Path(document.file_path).name,
                    document.file_size,
                    document.page_count,
                    document.directory_structure,
                    document.import_date.isoformat(),
                    None,  # creation_date - not available in DocumentContent
                    document.import_date.isoformat(),  # Use import_date as modification_date
                    document.ocr_used,
                    document.text_extraction_method,
                    document.processing_time,
                    'active'
                ))
                
                document_id = cursor.lastrowid
                
                # Add category if provided
                if category_result:
                    self._add_category(conn, document_id, category_result)
                
                # Log successful import
                self._add_processing_log(
                    conn, document_id, "import", "success",
                    f"Document imported successfully", processing_time=document.processing_time
                )
                
                conn.commit()
                logger.info(f"Document added with ID: {document_id}")
                return document_id
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add document {document.file_path}: {e}")
            raise
    
    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT d.*, c.primary_category, c.confidence, c.entities, c.suggested_categories
                    FROM documents d
                    LEFT JOIN categories c ON d.id = c.document_id
                    WHERE d.id = ? AND d.status != 'deleted'
                """, (document_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    def get_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get document by file path"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT d.*, c.primary_category, c.confidence, c.entities, c.suggested_categories
                    FROM documents d
                    LEFT JOIN categories c ON d.id = c.document_id
                    WHERE d.file_path = ? AND d.status != 'deleted'
                """, (file_path,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get document by path {file_path}: {e}")
            return None
    
    def update_document(self, document_id: int, updates: Dict[str, Any]) -> bool:
        """Update document metadata"""
        if not updates:
            return True
        
        try:
            with self.db_manager.get_connection() as conn:
                # Build dynamic update query
                set_clauses = []
                values = []
                
                for key, value in updates.items():
                    if key in ['file_path', 'file_name', 'file_size', 'page_count',
                              'directory_structure', 'ocr_used', 'text_extraction_method',
                              'processing_time', 'content_hash', 'status']:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                
                if not set_clauses:
                    logger.warning("No valid fields to update")
                    return False
                
                values.append(document_id)
                
                query = f"""
                    UPDATE documents 
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                """
                
                cursor = conn.execute(query, values)
                
                if cursor.rowcount > 0:
                    self._add_processing_log(
                        conn, document_id, "update", "success",
                        f"Document metadata updated: {list(updates.keys())}"
                    )
                    conn.commit()
                    logger.info(f"Document {document_id} updated")
                    return True
                else:
                    logger.warning(f"No document found with ID {document_id}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            return False
    
    def delete_document(self, document_id: int) -> bool:
        """Soft delete a document (mark as inactive)"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    UPDATE documents SET status = 'deleted' WHERE id = ?
                """, (document_id,))
                
                if cursor.rowcount > 0:
                    self._add_processing_log(
                        conn, document_id, "delete", "success",
                        "Document marked as deleted"
                    )
                    conn.commit()
                    logger.info(f"Document {document_id} deleted")
                    return True
                else:
                    logger.warning(f"No document found with ID {document_id}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def hard_delete_document(self, document_id: int) -> bool:
        """Permanently delete a document and all related data"""
        try:
            with self.db_manager.get_connection() as conn:
                # Delete document (cascades to categories and processing_logs)
                cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Document {document_id} permanently deleted")
                    return True
                else:
                    logger.warning(f"No document found with ID {document_id}")
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Failed to hard delete document {document_id}: {e}")
            return False
    
    def list_documents(self, 
                      directory_filter: Optional[str] = None,
                      category_filter: Optional[str] = None,
                      limit: Optional[int] = None,
                      offset: int = 0,
                      include_deleted: bool = False) -> List[Dict[str, Any]]:
        """List documents with optional filtering"""
        try:
            with self.db_manager.get_connection() as conn:
                # Build query with filters
                where_clauses = []
                params = []
                
                if not include_deleted:
                    where_clauses.append("d.status = 'active'")
                
                if directory_filter:
                    where_clauses.append("d.directory_structure LIKE ?")
                    params.append(f"%{directory_filter}%")
                
                if category_filter:
                    where_clauses.append("c.primary_category = ?")
                    params.append(category_filter)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f"""
                    SELECT d.*, c.primary_category, c.confidence
                    FROM documents d
                    LEFT JOIN categories c ON d.id = c.document_id
                    WHERE {where_clause}
                    ORDER BY d.import_date DESC
                """
                
                if limit:
                    query += f" LIMIT {limit} OFFSET {offset}"
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    def search_documents(self, 
                        query: str,
                        directory_filter: Optional[str] = None,
                        category_filter: Optional[str] = None,
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search documents by file name or path"""
        try:
            with self.db_manager.get_connection() as conn:
                where_clauses = ["d.status = 'active'"]
                params = []
                
                # Add search query
                where_clauses.append("(d.file_name LIKE ? OR d.file_path LIKE ?)")
                search_term = f"%{query}%"
                params.extend([search_term, search_term])
                
                if directory_filter:
                    where_clauses.append("d.directory_structure LIKE ?")
                    params.append(f"%{directory_filter}%")
                
                if category_filter:
                    where_clauses.append("c.primary_category = ?")
                    params.append(category_filter)
                
                where_clause = " AND ".join(where_clauses)
                
                sql_query = f"""
                    SELECT d.*, c.primary_category, c.confidence
                    FROM documents d
                    LEFT JOIN categories c ON d.id = c.document_id
                    WHERE {where_clause}
                    ORDER BY d.import_date DESC
                """
                
                if limit:
                    sql_query += f" LIMIT {limit}"
                
                cursor = conn.execute(sql_query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to search documents: {e}")
            return []
    
    def get_categories_summary(self) -> Dict[str, int]:
        """Get summary of document categories"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT c.primary_category, COUNT(*) as count
                    FROM categories c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.status = 'active'
                    GROUP BY c.primary_category
                    ORDER BY count DESC
                """)
                
                return {row[0]: row[1] for row in cursor.fetchall()}
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get categories summary: {e}")
            return {}
    
    def get_directory_structure(self) -> Dict[str, int]:
        """Get directory structure with document counts"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT directory_structure, COUNT(*) as count
                    FROM documents
                    WHERE status = 'active'
                    GROUP BY directory_structure
                    ORDER BY directory_structure
                """)
                
                return {row[0]: row[1] for row in cursor.fetchall()}
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get directory structure: {e}")
            return {}
    
    def get_processing_logs(self, 
                           document_id: Optional[int] = None,
                           operation: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """Get processing logs with optional filtering"""
        try:
            with self.db_manager.get_connection() as conn:
                where_clauses = []
                params = []
                
                if document_id:
                    where_clauses.append("document_id = ?")
                    params.append(document_id)
                
                if operation:
                    where_clauses.append("operation = ?")
                    params.append(operation)
                
                if status:
                    where_clauses.append("status = ?")
                    params.append(status)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                query = f"""
                    SELECT * FROM processing_logs
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get processing logs: {e}")
            return []
    
    def update_category(self, document_id: int, category_result: CategoryResult) -> bool:
        """Update or add category for a document"""
        try:
            with self.db_manager.get_connection() as conn:
                # Check if category exists
                cursor = conn.execute(
                    "SELECT id FROM categories WHERE document_id = ?", 
                    (document_id,)
                )
                
                if cursor.fetchone():
                    # Update existing category
                    conn.execute("""
                        UPDATE categories 
                        SET primary_category = ?, confidence = ?, entities = ?, suggested_categories = ?
                        WHERE document_id = ?
                    """, (
                        category_result.primary_category,
                        category_result.confidence,
                        json.dumps(category_result.entities),
                        json.dumps(category_result.suggested_categories),
                        document_id
                    ))
                else:
                    # Insert new category
                    self._add_category(conn, document_id, category_result)
                
                self._add_processing_log(
                    conn, document_id, "categorize", "success",
                    f"Category updated: {category_result.primary_category}"
                )
                
                conn.commit()
                logger.info(f"Category updated for document {document_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update category for document {document_id}: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the document collection"""
        try:
            with self.db_manager.get_connection() as conn:
                stats = {}
                
                # Document counts
                cursor = conn.execute("SELECT COUNT(*) FROM documents WHERE status = 'active'")
                stats['total_documents'] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM documents WHERE status = 'deleted'")
                stats['deleted_documents'] = cursor.fetchone()[0]
                
                # OCR usage
                cursor = conn.execute("SELECT COUNT(*) FROM documents WHERE ocr_used = 1 AND status = 'active'")
                stats['ocr_documents'] = cursor.fetchone()[0]
                
                # Processing methods
                cursor = conn.execute("""
                    SELECT text_extraction_method, COUNT(*) 
                    FROM documents 
                    WHERE status = 'active'
                    GROUP BY text_extraction_method
                """)
                stats['extraction_methods'] = dict(cursor.fetchall())
                
                # Categories
                stats['categories'] = self.get_categories_summary()
                
                # Directory structure
                stats['directories'] = self.get_directory_structure()
                
                # Processing statistics
                cursor = conn.execute("""
                    SELECT AVG(processing_time), MIN(processing_time), MAX(processing_time)
                    FROM documents WHERE status = 'active'
                """)
                avg_time, min_time, max_time = cursor.fetchone()
                stats['processing_time'] = {
                    'average': avg_time or 0,
                    'minimum': min_time or 0,
                    'maximum': max_time or 0
                }
                
                # File sizes
                cursor = conn.execute("""
                    SELECT AVG(file_size), MIN(file_size), MAX(file_size), SUM(file_size)
                    FROM documents WHERE status = 'active'
                """)
                avg_size, min_size, max_size, total_size = cursor.fetchone()
                stats['file_sizes'] = {
                    'average': avg_size or 0,
                    'minimum': min_size or 0,
                    'maximum': max_size or 0,
                    'total': total_size or 0
                }
                
                return stats
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def backup_metadata(self, backup_path: Path) -> bool:
        """Create a backup of the metadata database"""
        try:
            self.db_manager.backup_database(backup_path)
            logger.info(f"Metadata backup created at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to backup metadata: {e}")
            return False
    
    def restore_metadata(self, backup_path: Path) -> bool:
        """Restore metadata from backup"""
        try:
            self.db_manager.restore_database(backup_path)
            logger.info(f"Metadata restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore metadata: {e}")
            return False
    
    def cleanup_deleted_documents(self, older_than_days: int = 30) -> int:
        """Permanently delete documents marked as deleted older than specified days"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM documents 
                    WHERE status = 'deleted' 
                    AND updated_at < datetime('now', '-{} days')
                """.format(older_than_days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_count} deleted documents")
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Failed to cleanup deleted documents: {e}")
            return 0
    
    def _add_category(self, conn: sqlite3.Connection, document_id: int, category_result: CategoryResult) -> None:
        """Add category for a document"""
        conn.execute("""
            INSERT INTO categories (
                document_id, primary_category, confidence, entities, suggested_categories
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            document_id,
            category_result.primary_category,
            category_result.confidence,
            json.dumps(category_result.entities),
            json.dumps(category_result.suggested_categories)
        ))
    
    def _add_processing_log(self, 
                           conn: sqlite3.Connection,
                           document_id: Optional[int],
                           operation: str,
                           status: str,
                           message: str,
                           details: Optional[Dict[str, Any]] = None,
                           processing_time: Optional[float] = None) -> None:
        """Add a processing log entry"""
        conn.execute("""
            INSERT INTO processing_logs (
                document_id, operation, status, message, details, processing_time
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            document_id,
            operation,
            status,
            message,
            json.dumps(details) if details else None,
            processing_time
        ))