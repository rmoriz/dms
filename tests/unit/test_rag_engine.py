"""Tests for RAGEngine class"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dms.rag.engine import RAGEngine
from dms.llm.provider import LLMProvider
from dms.errors import LLMAPIError
from dms.storage.vector_store import VectorStore
from dms.models import SearchResult, TextChunk, Source, RAGResponse
from dms.config import DMSConfig, OpenRouterConfig


class TestRAGEngine:
    """Test cases for RAGEngine"""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store"""
        return Mock(spec=VectorStore)
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider"""
        return Mock(spec=LLMProvider)
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return DMSConfig.load()
    
    @pytest.fixture
    def rag_engine(self, mock_vector_store, mock_llm_provider, config):
        """Create RAGEngine instance with mocks"""
        return RAGEngine(mock_vector_store, mock_llm_provider, config)
    
    @pytest.fixture
    def sample_search_results(self):
        """Create sample search results"""
        chunk1 = TextChunk(
            id="chunk1",
            document_id="doc1",
            content="This is the first relevant passage about invoices.",
            page_number=1,
            chunk_index=0
        )
        chunk2 = TextChunk(
            id="chunk2", 
            document_id="doc2",
            content="This is the second relevant passage about payments.",
            page_number=2,
            chunk_index=1
        )
        
        return [
            SearchResult(
                chunk=chunk1,
                similarity_score=0.85,
                document_path="/path/to/doc1.pdf",
                page_number=1
            ),
            SearchResult(
                chunk=chunk2,
                similarity_score=0.75,
                document_path="/path/to/doc2.pdf", 
                page_number=2
            )
        ]
    
    def test_init(self, mock_vector_store, mock_llm_provider, config):
        """Test RAGEngine initialization"""
        engine = RAGEngine(mock_vector_store, mock_llm_provider, config)
        assert engine.vector_store == mock_vector_store
        assert engine.llm_provider == mock_llm_provider
        assert engine.config == config
    
    def test_query_success(self, rag_engine, mock_vector_store, mock_llm_provider, sample_search_results):
        """Test successful RAG query"""
        # Setup mocks
        mock_vector_store.similarity_search.return_value = sample_search_results
        mock_llm_provider.chat_completion.return_value = "Based on the documents, here is the answer."
        
        # Execute query
        question = "What are the invoice details?"
        result = rag_engine.query(question)
        
        # Verify result
        assert isinstance(result, RAGResponse)
        assert result.answer == "Based on the documents, here is the answer."
        assert len(result.sources) == 2
        assert result.search_results_count == 2
        assert 0.0 <= result.confidence <= 1.0
        
        # Verify vector store was called correctly
        mock_vector_store.similarity_search.assert_called_once_with(question, {})
        
        # Verify LLM was called with proper context
        mock_llm_provider.chat_completion.assert_called_once()
        call_args = mock_llm_provider.chat_completion.call_args[0]
        messages = call_args[0]
        assert len(messages) == 2  # system + user message
        assert "dokumente" in messages[0]["content"].lower()
    
    def test_query_with_filters(self, rag_engine, mock_vector_store, mock_llm_provider, sample_search_results):
        """Test RAG query with filters"""
        mock_vector_store.similarity_search.return_value = sample_search_results
        mock_llm_provider.chat_completion.return_value = "Filtered answer."
        
        filters = {"category": "Rechnung", "date_range": "2024-01"}
        result = rag_engine.query("Test question", filters=filters)
        
        assert result.answer == "Filtered answer."
        mock_vector_store.similarity_search.assert_called_once_with("Test question", filters)
    
    def test_query_with_specific_model(self, rag_engine, mock_vector_store, mock_llm_provider, sample_search_results):
        """Test RAG query with specific model"""
        mock_vector_store.similarity_search.return_value = sample_search_results
        mock_llm_provider.chat_completion.return_value = "Model-specific answer."
        
        result = rag_engine.query("Test question", model="openai/gpt-4")
        
        assert result.answer == "Model-specific answer."
        mock_llm_provider.chat_completion.assert_called_once()
        call_args = mock_llm_provider.chat_completion.call_args
        # Model is passed as second positional argument
        assert call_args[0][1] == "openai/gpt-4"
    
    def test_query_no_results(self, rag_engine, mock_vector_store, mock_llm_provider):
        """Test RAG query when no search results found"""
        mock_vector_store.similarity_search.return_value = []
        
        result = rag_engine.query("Question with no results")
        
        assert "keine relevanten informationen" in result.answer.lower()
        assert len(result.sources) == 0
        assert result.search_results_count == 0
        assert result.confidence == 0.0
        
        # LLM should not be called when no results
        mock_llm_provider.chat_completion.assert_not_called()
    
    def test_query_llm_error(self, rag_engine, mock_vector_store, mock_llm_provider, sample_search_results):
        """Test RAG query when LLM fails"""
        mock_vector_store.similarity_search.return_value = sample_search_results
        mock_llm_provider.chat_completion.side_effect = LLMAPIError("API error")
        
        result = rag_engine.query("Test question")
        
        assert "fehler bei der antwortgenerierung" in result.answer.lower()
        assert len(result.sources) == 2  # Sources should still be available
        assert result.confidence == 0.0
    
    def test_generate_answer(self, rag_engine, mock_llm_provider):
        """Test answer generation with context"""
        mock_llm_provider.chat_completion.return_value = "Generated answer"
        
        context_chunks = ["Context 1", "Context 2"]
        question = "Test question"
        
        answer = rag_engine.generate_answer(context_chunks, question)
        
        assert answer == "Generated answer"
        mock_llm_provider.chat_completion.assert_called_once()
        
        # Verify system prompt contains context
        call_args = mock_llm_provider.chat_completion.call_args[0]
        messages = call_args[0]
        system_message = messages[0]["content"]
        assert "Context 1" in system_message
        assert "Context 2" in system_message
    
    def test_format_sources(self, rag_engine, sample_search_results):
        """Test source formatting"""
        sources = rag_engine.format_sources(sample_search_results)
        
        assert len(sources) == 2
        
        source1 = sources[0]
        assert isinstance(source1, Source)
        assert source1.document_path == "/path/to/doc1.pdf"
        assert source1.page_number == 1
        assert source1.chunk_content == "This is the first relevant passage about invoices."
        assert source1.relevance_score == 0.85
        
        source2 = sources[1]
        assert source2.document_path == "/path/to/doc2.pdf"
        assert source2.page_number == 2
        assert source2.relevance_score == 0.75
    
    def test_calculate_confidence_high(self, rag_engine, sample_search_results):
        """Test confidence calculation with high-quality results"""
        confidence = rag_engine._calculate_confidence(sample_search_results)
        
        # Should be high confidence with good similarity scores
        assert confidence > 0.7
        assert confidence <= 1.0
    
    def test_calculate_confidence_low(self, rag_engine):
        """Test confidence calculation with low-quality results"""
        chunk = TextChunk(
            id="chunk1",
            document_id="doc1", 
            content="Low relevance content",
            page_number=1,
            chunk_index=0
        )
        
        low_quality_results = [
            SearchResult(
                chunk=chunk,
                similarity_score=0.3,
                document_path="/path/to/doc.pdf",
                page_number=1
            )
        ]
        
        confidence = rag_engine._calculate_confidence(low_quality_results)
        
        # Should be low confidence with poor similarity scores
        assert confidence < 0.5
        assert confidence >= 0.0
    
    def test_calculate_confidence_empty(self, rag_engine):
        """Test confidence calculation with no results"""
        confidence = rag_engine._calculate_confidence([])
        assert confidence == 0.0
    
    def test_aggregate_context(self, rag_engine, sample_search_results):
        """Test context aggregation from search results"""
        context = rag_engine._aggregate_context(sample_search_results)
        
        assert len(context) == 2
        assert "This is the first relevant passage about invoices." in context[0]
        assert "This is the second relevant passage about payments." in context[1]
        
        # Should include document path and page info
        assert "/path/to/doc1.pdf" in context[0]
        assert "Seite 1" in context[0]
    
    def test_create_system_prompt(self, rag_engine):
        """Test system prompt creation"""
        context_chunks = [
            "Document 1: Invoice information",
            "Document 2: Payment details"
        ]
        
        prompt = rag_engine._create_system_prompt(context_chunks)
        
        assert "Document 1: Invoice information" in prompt
        assert "Document 2: Payment details" in prompt
        assert "deutsch" in prompt.lower()  # Should specify German language
        assert "quellen" in prompt.lower()  # Should mention sources