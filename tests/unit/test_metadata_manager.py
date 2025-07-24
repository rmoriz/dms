"""Tests for metadata manager"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from dms.storage.metadata_manager import MetadataManager
from dms.models import DocumentContent, CategoryResult
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
def metadata_manager(temp_config):
    """Create a metadata manager with temporary database"""
    return MetadataManager(temp_config)


@pytest.fixture
def sample_document():
    """Create a sample document for testing"""
    return DocumentContent(
        file_path="/test/documents/invoice.pdf",
        text="Sample invoice content",
        page_count=2,
        file_size=1024,
        import_date=datetime.now(),
        directory_structure="2024/03/Rechnungen",
        ocr_used=False,
        text_extraction_method="direct",
        processing_time=1.5
    )


@pytest.fixture
def sample_category():
    """Create a sample category result for testing"""
    return CategoryResult(
        primary_category="Rechnung",
        confidence=0.95,
        entities={"issuer": "Test Company", "amount": 100.50},
        suggested_categories=[("Rechnung", 0.95), ("Dokument", 0.3)]
    )


class TestMetadataManager:
    """Test metadata manager functionality"""
    
    def test_initialization(self, temp_config):
        """Test metadata manager initialization"""
        manager = MetadataManager(temp_config)
        
        assert manager.config == temp_config
        assert temp_config.metadata_db_path.exists()
    
    def test_add_document_without_category(self, metadata_manager, sample_document):
        """Test adding a document without category"""
        doc_id = metadata_manager.add_document(sample_document)
        
        assert doc_id > 0
        
        # Verify document was added
        doc = metadata_manager.get_document(doc_id)
        assert doc is not None
        assert doc['file_path'] == sample_document.file_path
        assert doc['file_name'] == "invoice.pdf"
        assert doc['file_size'] == sample_document.file_size
        assert doc['page_count'] == sample_document.page_count
        assert doc['directory_structure'] == sample_document.directory_structure
        assert doc['ocr_used'] == sample_document.ocr_used
        assert doc['text_extraction_method'] == sample_document.text_extraction_method
        assert doc['processing_time'] == sample_document.processing_time
        assert doc['status'] == 'active'
    
    def test_add_document_with_category(self, metadata_manager, sample_document, sample_category):
        """Test adding a document with category"""
        doc_id = metadata_manager.add_document(sample_document, sample_category)
        
        assert doc_id > 0
        
        # Verify document and category were added
        doc = metadata_manager.get_document(doc_id)
        assert doc is not None
        assert doc['primary_category'] == sample_category.primary_category
        assert doc['confidence'] == sample_category.confidence
        
        # Verify entities are stored as JSON
        entities = json.loads(doc['entities'])
        assert entities == sample_category.entities
    
    def test_get_document_by_path(self, metadata_manager, sample_document):
        """Test getting document by file path"""
        doc_id = metadata_manager.add_document(sample_document)
        
        doc = metadata_manager.get_document_by_path(sample_document.file_path)
        assert doc is not None
        assert doc['id'] == doc_id
        assert doc['file_path'] == sample_document.file_path
    
    def test_get_nonexistent_document(self, metadata_manager):
        """Test getting a document that doesn't exist"""
        doc = metadata_manager.get_document(999)
        assert doc is None
        
        doc = metadata_manager.get_document_by_path("/nonexistent/path.pdf")
        assert doc is None
    
    def test_update_document(self, metadata_manager, sample_document):
        """Test updating document metadata"""
        doc_id = metadata_manager.add_document(sample_document)
        
        updates = {
            'file_size': 2048,
            'processing_time': 2.5,
            'status': 'processed'
        }
        
        success = metadata_manager.update_document(doc_id, updates)
        assert success is True
        
        # Verify updates
        doc = metadata_manager.get_document(doc_id)
        assert doc['file_size'] == 2048
        assert doc['processing_time'] == 2.5
        assert doc['status'] == 'processed'
    
    def test_update_nonexistent_document(self, metadata_manager):
        """Test updating a document that doesn't exist"""
        success = metadata_manager.update_document(999, {'file_size': 2048})
        assert success is False
    
    def test_update_document_empty_updates(self, metadata_manager, sample_document):
        """Test updating document with empty updates"""
        doc_id = metadata_manager.add_document(sample_document)
        
        success = metadata_manager.update_document(doc_id, {})
        assert success is True
    
    def test_delete_document(self, metadata_manager, sample_document):
        """Test soft deleting a document"""
        doc_id = metadata_manager.add_document(sample_document)
        
        success = metadata_manager.delete_document(doc_id)
        assert success is True
        
        # Document should not appear in normal queries
        doc = metadata_manager.get_document(doc_id)
        assert doc is None
        
        # But should appear when including deleted
        docs = metadata_manager.list_documents(include_deleted=True)
        deleted_doc = next((d for d in docs if d['id'] == doc_id), None)
        assert deleted_doc is not None
        assert deleted_doc['status'] == 'deleted'
    
    def test_hard_delete_document(self, metadata_manager, sample_document, sample_category):
        """Test permanently deleting a document"""
        doc_id = metadata_manager.add_document(sample_document, sample_category)
        
        success = metadata_manager.hard_delete_document(doc_id)
        assert success is True
        
        # Document should not exist at all
        doc = metadata_manager.get_document(doc_id)
        assert doc is None
        
        docs = metadata_manager.list_documents(include_deleted=True)
        deleted_doc = next((d for d in docs if d['id'] == doc_id), None)
        assert deleted_doc is None
    
    def test_list_documents(self, metadata_manager):
        """Test listing documents with various filters"""
        # Add test documents
        doc1 = DocumentContent(
            file_path="/test/2024/03/invoice1.pdf",
            text="Invoice 1", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03/Rechnungen",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        doc2 = DocumentContent(
            file_path="/test/2024/04/contract.pdf",
            text="Contract", page_count=5, file_size=2048,
            import_date=datetime.now(), directory_structure="2024/04/Verträge",
            ocr_used=True, text_extraction_method="ocr", processing_time=3.0
        )
        
        category1 = CategoryResult("Rechnung", 0.9, {}, [])
        category2 = CategoryResult("Vertrag", 0.8, {}, [])
        
        doc1_id = metadata_manager.add_document(doc1, category1)
        doc2_id = metadata_manager.add_document(doc2, category2)
        
        # Test listing all documents
        docs = metadata_manager.list_documents()
        assert len(docs) == 2
        
        # Test directory filter
        docs = metadata_manager.list_documents(directory_filter="2024/03")
        assert len(docs) == 1
        assert docs[0]['id'] == doc1_id
        
        # Test category filter
        docs = metadata_manager.list_documents(category_filter="Vertrag")
        assert len(docs) == 1
        assert docs[0]['id'] == doc2_id
        
        # Test limit and offset
        docs = metadata_manager.list_documents(limit=1, offset=0)
        assert len(docs) == 1
        
        docs = metadata_manager.list_documents(limit=1, offset=1)
        assert len(docs) == 1
    
    def test_search_documents(self, metadata_manager):
        """Test searching documents"""
        # Add test documents
        doc1 = DocumentContent(
            file_path="/test/invoice_123.pdf",
            text="Invoice", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        doc2 = DocumentContent(
            file_path="/test/contract_456.pdf",
            text="Contract", page_count=2, file_size=2048,
            import_date=datetime.now(), directory_structure="2024/04",
            ocr_used=False, text_extraction_method="direct", processing_time=1.5
        )
        
        metadata_manager.add_document(doc1)
        metadata_manager.add_document(doc2)
        
        # Search by filename
        docs = metadata_manager.search_documents("invoice")
        assert len(docs) == 1
        assert "invoice" in docs[0]['file_name'].lower()
        
        # Search by path
        docs = metadata_manager.search_documents("contract")
        assert len(docs) == 1
        assert "contract" in docs[0]['file_path'].lower()
        
        # Search with no results
        docs = metadata_manager.search_documents("nonexistent")
        assert len(docs) == 0
    
    def test_get_categories_summary(self, metadata_manager):
        """Test getting categories summary"""
        # Add documents with categories
        doc1 = DocumentContent(
            file_path="/test/doc1.pdf", text="Doc 1", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        doc2 = DocumentContent(
            file_path="/test/doc2.pdf", text="Doc 2", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        category1 = CategoryResult("Rechnung", 0.9, {}, [])
        category2 = CategoryResult("Rechnung", 0.8, {}, [])
        
        metadata_manager.add_document(doc1, category1)
        metadata_manager.add_document(doc2, category2)
        
        summary = metadata_manager.get_categories_summary()
        assert summary["Rechnung"] == 2
    
    def test_get_directory_structure(self, metadata_manager):
        """Test getting directory structure"""
        # Add documents in different directories
        doc1 = DocumentContent(
            file_path="/test/doc1.pdf", text="Doc 1", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03/Rechnungen",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        doc2 = DocumentContent(
            file_path="/test/doc2.pdf", text="Doc 2", page_count=1, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/04/Verträge",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        metadata_manager.add_document(doc1)
        metadata_manager.add_document(doc2)
        
        structure = metadata_manager.get_directory_structure()
        assert structure["2024/03/Rechnungen"] == 1
        assert structure["2024/04/Verträge"] == 1
    
    def test_update_category(self, metadata_manager, sample_document):
        """Test updating document category"""
        doc_id = metadata_manager.add_document(sample_document)
        
        # Add initial category
        category1 = CategoryResult("Dokument", 0.5, {}, [])
        success = metadata_manager.update_category(doc_id, category1)
        assert success is True
        
        # Update category
        category2 = CategoryResult("Rechnung", 0.9, {"issuer": "Test"}, [])
        success = metadata_manager.update_category(doc_id, category2)
        assert success is True
        
        # Verify update
        doc = metadata_manager.get_document(doc_id)
        assert doc['primary_category'] == "Rechnung"
        assert doc['confidence'] == 0.9
    
    def test_get_statistics(self, metadata_manager):
        """Test getting comprehensive statistics"""
        # Add test documents
        doc1 = DocumentContent(
            file_path="/test/doc1.pdf", text="Doc 1", page_count=2, file_size=1024,
            import_date=datetime.now(), directory_structure="2024/03",
            ocr_used=False, text_extraction_method="direct", processing_time=1.0
        )
        
        doc2 = DocumentContent(
            file_path="/test/doc2.pdf", text="Doc 2", page_count=3, file_size=2048,
            import_date=datetime.now(), directory_structure="2024/04",
            ocr_used=True, text_extraction_method="ocr", processing_time=2.0
        )
        
        category1 = CategoryResult("Rechnung", 0.9, {}, [])
        
        doc1_id = metadata_manager.add_document(doc1, category1)
        metadata_manager.add_document(doc2)
        
        # Delete one document
        metadata_manager.delete_document(doc1_id)
        
        stats = metadata_manager.get_statistics()
        
        assert stats['total_documents'] == 1  # Only active documents
        assert stats['deleted_documents'] == 1
        assert stats['ocr_documents'] == 1
        # Only active documents are counted in extraction methods
        assert stats['extraction_methods']['ocr'] == 1
        assert stats['processing_time']['average'] == 2.0
        assert stats['file_sizes']['total'] == 2048
    
    def test_get_processing_logs(self, metadata_manager, sample_document):
        """Test getting processing logs"""
        doc_id = metadata_manager.add_document(sample_document)
        
        # Get all logs
        logs = metadata_manager.get_processing_logs()
        assert len(logs) >= 1
        
        # Get logs for specific document
        logs = metadata_manager.get_processing_logs(document_id=doc_id)
        assert len(logs) >= 1
        assert logs[0]['document_id'] == doc_id
        
        # Get logs for specific operation
        logs = metadata_manager.get_processing_logs(operation="import")
        assert len(logs) >= 1
        assert logs[0]['operation'] == "import"
    
    def test_backup_and_restore(self, metadata_manager, sample_document, temp_config):
        """Test backup and restore functionality"""
        # Add a document
        doc_id = metadata_manager.add_document(sample_document)
        
        # Create backup
        backup_path = temp_config.data_path / "backup.sqlite"
        success = metadata_manager.backup_metadata(backup_path)
        assert success is True
        assert backup_path.exists()
        
        # Clear database by hard deleting
        metadata_manager.hard_delete_document(doc_id)
        assert metadata_manager.get_document(doc_id) is None
        
        # Restore from backup
        success = metadata_manager.restore_metadata(backup_path)
        assert success is True
        
        # Verify data was restored
        doc = metadata_manager.get_document(doc_id)
        assert doc is not None
        assert doc['file_path'] == sample_document.file_path
    
    def test_cleanup_deleted_documents(self, metadata_manager, sample_document):
        """Test cleanup of old deleted documents"""
        doc_id = metadata_manager.add_document(sample_document)
        
        # Delete document
        metadata_manager.delete_document(doc_id)
        
        # Cleanup (should not delete recent documents)
        deleted_count = metadata_manager.cleanup_deleted_documents(older_than_days=1)
        assert deleted_count == 0
        
        # Document should still exist as deleted
        docs = metadata_manager.list_documents(include_deleted=True)
        deleted_doc = next((d for d in docs if d['id'] == doc_id), None)
        assert deleted_doc is not None
        assert deleted_doc['status'] == 'deleted'
    
    def test_duplicate_file_path_handling(self, metadata_manager, sample_document):
        """Test handling of duplicate file paths"""
        # Add document
        doc_id1 = metadata_manager.add_document(sample_document)
        assert doc_id1 > 0
        
        # Try to add same document again (should fail due to unique constraint)
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            metadata_manager.add_document(sample_document)
    
    def test_invalid_updates(self, metadata_manager, sample_document):
        """Test handling of invalid update fields"""
        doc_id = metadata_manager.add_document(sample_document)
        
        # Try to update with invalid fields
        updates = {
            'invalid_field': 'value',
            'another_invalid': 123
        }
        
        success = metadata_manager.update_document(doc_id, updates)
        assert success is False
    
    def test_error_handling(self, metadata_manager):
        """Test error handling in various scenarios"""
        # Test operations on non-existent documents
        assert metadata_manager.delete_document(999) is False
        assert metadata_manager.hard_delete_document(999) is False
        assert metadata_manager.update_category(999, CategoryResult("Test", 0.5, {}, [])) is False


class TestMetadataManagerIntegration:
    """Integration tests for metadata manager"""
    
    def test_full_document_lifecycle(self, metadata_manager):
        """Test complete document lifecycle"""
        # Create document
        document = DocumentContent(
            file_path="/test/lifecycle.pdf",
            text="Lifecycle test",
            page_count=3,
            file_size=1536,
            import_date=datetime.now(),
            directory_structure="2024/05/Tests",
            ocr_used=True,
            text_extraction_method="hybrid",
            processing_time=2.5
        )
        
        category = CategoryResult(
            primary_category="Test",
            confidence=0.8,
            entities={"type": "test_document"},
            suggested_categories=[("Test", 0.8), ("Document", 0.6)]
        )
        
        # Add document
        doc_id = metadata_manager.add_document(document, category)
        assert doc_id > 0
        
        # Verify document exists
        doc = metadata_manager.get_document(doc_id)
        assert doc is not None
        assert doc['primary_category'] == "Test"
        
        # Update document
        updates = {'file_size': 2048, 'processing_time': 3.0}
        assert metadata_manager.update_document(doc_id, updates) is True
        
        # Update category
        new_category = CategoryResult("Updated", 0.9, {"updated": True}, [])
        assert metadata_manager.update_category(doc_id, new_category) is True
        
        # Verify updates
        doc = metadata_manager.get_document(doc_id)
        assert doc['file_size'] == 2048
        assert doc['primary_category'] == "Updated"
        
        # Search for document
        results = metadata_manager.search_documents("lifecycle")
        assert len(results) == 1
        assert results[0]['id'] == doc_id
        
        # Get statistics
        stats = metadata_manager.get_statistics()
        assert stats['total_documents'] >= 1
        
        # Soft delete
        assert metadata_manager.delete_document(doc_id) is True
        assert metadata_manager.get_document(doc_id) is None
        
        # Hard delete
        assert metadata_manager.hard_delete_document(doc_id) is True
        
        # Verify complete removal
        docs = metadata_manager.list_documents(include_deleted=True)
        deleted_doc = next((d for d in docs if d['id'] == doc_id), None)
        assert deleted_doc is None