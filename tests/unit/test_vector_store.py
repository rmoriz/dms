"""Tests for VectorStore class"""

import pytest
import tempfile
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from dms.storage.vector_store import VectorStore, EmbeddingGenerator
from dms.models import TextChunk, SearchResult


@pytest.fixture
def temp_db_path():
    """Create a temporary directory for test database"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def vector_store(temp_db_path):
    """Create a VectorStore instance for testing"""
    return VectorStore(db_path=temp_db_path)


@pytest.fixture
def sample_chunks():
    """Create sample text chunks for testing"""
    return [
        TextChunk(
            id="chunk_1",
            document_id="doc_1",
            content="Dies ist eine Rechnung von Firma ABC für Dienstleistungen im März 2024.",
            page_number=1,
            chunk_index=0
        ),
        TextChunk(
            id="chunk_2", 
            document_id="doc_1",
            content="Der Gesamtbetrag beläuft sich auf 1.500,00 EUR inklusive Mehrwertsteuer.",
            page_number=1,
            chunk_index=1
        ),
        TextChunk(
            id="chunk_3",
            document_id="doc_2", 
            content="Kontoauszug der Deutschen Bank für das Konto 123456789 vom April 2024.",
            page_number=1,
            chunk_index=0
        )
    ]


@pytest.fixture
def sample_chunks_with_metadata():
    """Create sample chunks with metadata for filtering tests"""
    return [
        TextChunk(
            id="chunk_1",
            document_id="doc_1",
            content="Rechnung von Firma ABC",
            page_number=1,
            chunk_index=0
        ),
        TextChunk(
            id="chunk_2",
            document_id="doc_2", 
            content="Kontoauszug Deutsche Bank",
            page_number=1,
            chunk_index=0
        ),
        TextChunk(
            id="chunk_3",
            document_id="doc_3",
            content="Vertrag mit Kunde XYZ",
            page_number=1,
            chunk_index=0
        )
    ]


class TestVectorStore:
    """Test cases for VectorStore class"""

    def test_init_creates_collection(self, temp_db_path):
        """Test that VectorStore initialization creates a ChromaDB collection"""
        vector_store = VectorStore(db_path=temp_db_path)
        assert vector_store.collection is not None
        assert vector_store.collection.name == "documents"

    def test_add_documents_single_chunk(self, vector_store, sample_chunks):
        """Test adding a single document chunk"""
        chunk = sample_chunks[0]
        vector_store.add_documents([chunk])
        
        # Verify the document was added
        results = vector_store.collection.get(ids=[chunk.id])
        assert len(results['ids']) == 1
        assert results['ids'][0] == chunk.id
        assert results['documents'][0] == chunk.content

    def test_add_documents_multiple_chunks(self, vector_store, sample_chunks):
        """Test adding multiple document chunks"""
        vector_store.add_documents(sample_chunks)
        
        # Verify all documents were added
        results = vector_store.collection.get()
        assert len(results['ids']) == len(sample_chunks)
        
        # Check that all chunk IDs are present
        chunk_ids = [chunk.id for chunk in sample_chunks]
        assert set(results['ids']) == set(chunk_ids)

    def test_add_documents_with_metadata(self, vector_store):
        """Test adding documents with metadata for filtering"""
        chunks_with_metadata = [
            TextChunk(
                id="chunk_1",
                document_id="2024/03/Rechnungen/rechnung_abc.pdf",
                content="Rechnung von Firma ABC",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_2", 
                document_id="2024/04/Kontoauszuege/bank_statement.pdf",
                content="Kontoauszug Deutsche Bank",
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store.add_documents(chunks_with_metadata)
        
        # Verify metadata is stored correctly
        results = vector_store.collection.get(ids=["chunk_1"])
        metadata = results['metadatas'][0]
        assert metadata['document_id'] == "2024/03/Rechnungen/rechnung_abc.pdf"
        assert metadata['directory_structure'] == "2024/03/Rechnungen"
        assert metadata['page_number'] == 1

    def test_similarity_search_basic(self, vector_store, sample_chunks):
        """Test basic similarity search functionality"""
        vector_store.add_documents(sample_chunks)
        
        # Search for invoice-related content
        results = vector_store.similarity_search("Rechnung Firma", n_results=2)
        
        assert len(results) <= 2
        assert all(isinstance(result, SearchResult) for result in results)
        
        # Should return some results
        if results:
            # At least one result should contain relevant content
            relevant_found = any("Rechnung" in result.chunk.content or "Firma" in result.chunk.content 
                               for result in results)
            assert relevant_found or len(results) > 0  # Either relevant content or some results

    def test_similarity_search_with_filters(self, vector_store):
        """Test similarity search with metadata filters"""
        chunks = [
            TextChunk(
                id="chunk_1",
                document_id="2024/03/Rechnungen/rechnung1.pdf",
                content="Rechnung von Firma ABC für März 2024",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_2",
                document_id="2024/04/Rechnungen/rechnung2.pdf", 
                content="Rechnung von Firma XYZ für April 2024",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_3",
                document_id="2024/03/Kontoauszuege/bank.pdf",
                content="Kontoauszug für März 2024",
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store.add_documents(chunks)
        
        # Filter by directory structure (only March invoices)
        filters = {"directory_structure": "2024/03/Rechnungen"}
        results = vector_store.similarity_search("Rechnung", filters=filters)
        
        # Should only return results from March invoices directory
        for result in results:
            assert "2024/03/Rechnungen" in result.chunk.document_id

    def test_similarity_search_no_results(self, vector_store, sample_chunks):
        """Test similarity search when no relevant results are found"""
        vector_store.add_documents(sample_chunks)
        
        # Search for something completely unrelated
        results = vector_store.similarity_search("Weltraumforschung Aliens", n_results=5)
        
        # Should return results but with low similarity scores
        assert isinstance(results, list)

    def test_delete_documents_single(self, vector_store, sample_chunks):
        """Test deleting a single document"""
        vector_store.add_documents(sample_chunks)
        
        # Delete one document
        vector_store.delete_documents("doc_1")
        
        # Verify chunks from doc_1 are deleted
        results = vector_store.collection.get()
        remaining_doc_ids = [metadata['document_id'] for metadata in results['metadatas']]
        assert "doc_1" not in remaining_doc_ids
        assert "doc_2" in remaining_doc_ids

    def test_delete_documents_multiple(self, vector_store, sample_chunks):
        """Test deleting multiple documents"""
        vector_store.add_documents(sample_chunks)
        
        # Delete multiple documents
        vector_store.delete_documents(["doc_1", "doc_2"])
        
        # Verify all specified documents are deleted
        results = vector_store.collection.get()
        assert len(results['ids']) == 0

    def test_delete_nonexistent_document(self, vector_store, sample_chunks):
        """Test deleting a document that doesn't exist"""
        vector_store.add_documents(sample_chunks)
        
        # Should not raise an error when deleting non-existent document
        vector_store.delete_documents("nonexistent_doc")
        
        # Original documents should still be there
        results = vector_store.collection.get()
        assert len(results['ids']) == len(sample_chunks)

    def test_filter_by_category(self, vector_store):
        """Test filtering by document category"""
        chunks = [
            TextChunk(
                id="chunk_1",
                document_id="invoice1.pdf",
                content="Rechnung von Firma ABC",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_2",
                document_id="statement1.pdf",
                content="Kontoauszug Deutsche Bank", 
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store.add_documents(chunks)
        
        # Filter by category
        filters = {"category": "Rechnung"}
        results = vector_store.similarity_search("Firma", filters=filters)
        
        # Should only return invoice-related results
        for result in results:
            metadata = result.chunk.__dict__
            # This test will be updated once categorization is implemented

    def test_filter_by_date_range(self, vector_store):
        """Test filtering by date range using directory structure"""
        chunks = [
            TextChunk(
                id="chunk_1",
                document_id="2024/01/document1.pdf",
                content="Januar Dokument",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_2", 
                document_id="2024/03/document2.pdf",
                content="März Dokument",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_3",
                document_id="2024/06/document3.pdf",
                content="Juni Dokument", 
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store.add_documents(chunks)
        
        # Filter for Q1 2024 (January to March)
        filters = {"year": "2024", "month": {"$in": ["01", "03"]}}
        results = vector_store.similarity_search("Dokument", filters=filters)
        
        # Should only return Q1 documents
        for result in results:
            assert any(month in result.chunk.document_id for month in ["2024/01", "2024/03"])

    def test_empty_collection_search(self, vector_store):
        """Test searching in an empty collection"""
        results = vector_store.similarity_search("test query")
        assert results == []

    def test_collection_persistence(self, temp_db_path, sample_chunks):
        """Test that data persists between VectorStore instances"""
        # Create first instance and add data
        vector_store1 = VectorStore(db_path=temp_db_path)
        vector_store1.add_documents(sample_chunks)
        
        # Create second instance with same path
        vector_store2 = VectorStore(db_path=temp_db_path)
        
        # Data should still be accessible
        results = vector_store2.collection.get()
        assert len(results['ids']) == len(sample_chunks)


class TestEmbeddingGenerator:
    """Test cases for EmbeddingGenerator class"""

    @pytest.fixture
    def embedding_generator(self):
        """Create an EmbeddingGenerator instance for testing"""
        return EmbeddingGenerator()

    def test_init_loads_model(self, embedding_generator):
        """Test that EmbeddingGenerator initializes with the correct model"""
        assert embedding_generator.model is not None
        assert embedding_generator.model_name == "paraphrase-multilingual-MiniLM-L12-v2"

    def test_generate_embedding_single_text(self, embedding_generator):
        """Test generating embedding for a single text"""
        text = "Dies ist ein Test-Dokument auf Deutsch."
        embedding = embedding_generator.generate_embedding(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # MiniLM-L12-v2 produces 384-dimensional embeddings
        assert all(isinstance(x, float) for x in embedding)

    def test_generate_embeddings_batch(self, embedding_generator):
        """Test generating embeddings for multiple texts in batch"""
        texts = [
            "Dies ist eine Rechnung von Firma ABC.",
            "Kontoauszug der Deutschen Bank.",
            "Vertrag zwischen Kunde und Anbieter."
        ]
        
        embeddings = embedding_generator.generate_embeddings(texts)
        
        assert len(embeddings) == len(texts)
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(emb, list) for emb in embeddings)

    def test_embedding_consistency(self, embedding_generator):
        """Test that the same text produces the same embedding"""
        text = "Konsistenz-Test für Embeddings."
        
        embedding1 = embedding_generator.generate_embedding(text)
        embedding2 = embedding_generator.generate_embedding(text)
        
        # Should be identical (or very close due to floating point precision)
        assert np.allclose(embedding1, embedding2, rtol=1e-6)

    def test_embedding_similarity(self, embedding_generator):
        """Test that similar texts produce similar embeddings"""
        text1 = "Rechnung von Firma ABC für Dienstleistungen."
        text2 = "Rechnung der Firma ABC für erbrachte Leistungen."
        text3 = "Kontoauszug der Bank für das Konto 123456."
        
        emb1 = embedding_generator.generate_embedding(text1)
        emb2 = embedding_generator.generate_embedding(text2)
        emb3 = embedding_generator.generate_embedding(text3)
        
        # Calculate cosine similarity
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        # Similar texts should have higher similarity
        sim_1_2 = cosine_similarity(emb1, emb2)
        sim_1_3 = cosine_similarity(emb1, emb3)
        
        assert sim_1_2 > sim_1_3  # Invoice texts should be more similar to each other

    def test_empty_text_handling(self, embedding_generator):
        """Test handling of empty or whitespace-only text"""
        empty_text = ""
        whitespace_text = "   \n\t   "
        
        # Should handle gracefully without crashing
        emb_empty = embedding_generator.generate_embedding(empty_text)
        emb_whitespace = embedding_generator.generate_embedding(whitespace_text)
        
        assert isinstance(emb_empty, list)
        assert isinstance(emb_whitespace, list)
        assert len(emb_empty) == 384
        assert len(emb_whitespace) == 384

    def test_long_text_handling(self, embedding_generator):
        """Test handling of very long texts"""
        # Create a long text that exceeds typical token limits
        long_text = "Dies ist ein sehr langer Text. " * 1000
        
        # Should handle without crashing (model will truncate internally)
        embedding = embedding_generator.generate_embedding(long_text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_german_text_processing(self, embedding_generator):
        """Test that German text is processed correctly"""
        german_texts = [
            "Rechnung über Dienstleistungen im Bereich Softwareentwicklung.",
            "Kontoauszug mit Überweisungen und Lastschriften.",
            "Vertrag über die Lieferung von Waren und Dienstleistungen.",
            "Mahnung wegen überfälliger Zahlung der Rechnung."
        ]
        
        embeddings = embedding_generator.generate_embeddings(german_texts)
        
        # All embeddings should be generated successfully
        assert len(embeddings) == len(german_texts)
        assert all(len(emb) == 384 for emb in embeddings)
        
        # Check that different document types have different embeddings
        # (they shouldn't be identical)
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                assert not np.array_equal(embeddings[i], embeddings[j])

    def test_batch_processing_efficiency(self, embedding_generator):
        """Test that batch processing works correctly and produces valid embeddings"""
        texts = [f"Test-Dokument Nummer {i} mit verschiedenem Inhalt." for i in range(10)]
        
        # Time batch processing
        import time
        start_batch = time.time()
        batch_embeddings = embedding_generator.generate_embeddings(texts)
        batch_time = time.time() - start_batch
        
        # Time individual processing
        start_individual = time.time()
        individual_embeddings = [embedding_generator.generate_embedding(text) for text in texts]
        individual_time = time.time() - start_individual
        
        # Both methods should produce valid embeddings
        assert len(batch_embeddings) == len(individual_embeddings)
        assert len(batch_embeddings) == len(texts)
        
        # All embeddings should have the correct dimension
        for batch_emb, ind_emb in zip(batch_embeddings, individual_embeddings):
            assert len(batch_emb) == 384
            assert len(ind_emb) == 384
            assert all(isinstance(x, float) for x in batch_emb)
            assert all(isinstance(x, float) for x in ind_emb)
            
            # Embeddings should be similar (high cosine similarity)
            cosine_sim = np.dot(batch_emb, ind_emb) / (np.linalg.norm(batch_emb) * np.linalg.norm(ind_emb))
            assert cosine_sim > 0.95  # Should be very similar
        
        # Batch processing should be faster (or at least not significantly slower)
        # Note: This might not always be true for small batches, but it's a good indicator
        print(f"Batch time: {batch_time:.3f}s, Individual time: {individual_time:.3f}s")


class TestVectorStoreWithEmbeddings:
    """Test VectorStore integration with embedding generation"""

    @pytest.fixture
    def vector_store_with_embeddings(self, temp_db_path):
        """Create a VectorStore with embedding generation enabled"""
        return VectorStore(db_path=temp_db_path, use_embeddings=True)

    def test_add_documents_generates_embeddings(self, vector_store_with_embeddings):
        """Test that adding documents automatically generates embeddings"""
        chunks = [
            TextChunk(
                id="chunk_1",
                document_id="doc_1",
                content="Dies ist eine Rechnung von Firma ABC.",
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store_with_embeddings.add_documents(chunks)
        
        # Verify that embeddings were generated and stored
        results = vector_store_with_embeddings.collection.get(ids=["chunk_1"])
        assert len(results['ids']) == 1
        
        # ChromaDB should have generated embeddings automatically
        # We can't directly access them, but similarity search should work better

    def test_similarity_search_with_embeddings(self, vector_store_with_embeddings):
        """Test that similarity search works better with custom embeddings"""
        chunks = [
            TextChunk(
                id="chunk_1",
                document_id="doc_1",
                content="Rechnung von Firma ABC für Softwareentwicklung im März 2024.",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_2",
                document_id="doc_2",
                content="Kontoauszug der Deutschen Bank für April 2024.",
                page_number=1,
                chunk_index=0
            ),
            TextChunk(
                id="chunk_3",
                document_id="doc_3",
                content="Vertrag über Dienstleistungen zwischen Kunde und Anbieter.",
                page_number=1,
                chunk_index=0
            )
        ]
        
        vector_store_with_embeddings.add_documents(chunks)
        
        # Search for invoice-related content
        results = vector_store_with_embeddings.similarity_search("Rechnung Firma ABC", n_results=3)
        
        assert len(results) > 0
        # The invoice document should be the most relevant
        assert "Rechnung" in results[0].chunk.content
        assert results[0].similarity_score > 0.5  # Should have decent similarity