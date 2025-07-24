"""RAG Engine for query processing and answer generation"""

from typing import List, Dict, Any, Optional
from dms.llm.provider import LLMProvider, LLMError
from dms.storage.vector_store import VectorStore
from dms.models import SearchResult, Source, RAGResponse
from dms.config import DMSConfig


class RAGEngine:
    """RAG (Retrieval-Augmented Generation) engine for document querying"""
    
    def __init__(self, vector_store: VectorStore, llm_provider: LLMProvider, config: DMSConfig):
        """Initialize RAG engine
        
        Args:
            vector_store: Vector database for similarity search
            llm_provider: LLM provider for answer generation
            config: DMS configuration
        """
        self.vector_store = vector_store
        self.llm_provider = llm_provider
        self.config = config
    
    def query(self, question: str, filters: Optional[Dict[str, Any]] = None, 
              model: Optional[str] = None) -> RAGResponse:
        """Process a query and generate an answer with sources
        
        Args:
            question: User's question
            filters: Optional filters for search (category, date_range, etc.)
            model: Optional specific model to use for generation
            
        Returns:
            RAGResponse with answer, sources, and confidence
        """
        if filters is None:
            filters = {}
        
        # Step 1: Retrieve relevant documents
        search_results = self.vector_store.similarity_search(question, filters)
        
        # Step 2: Check if we have results
        if not search_results:
            return RAGResponse(
                answer="Es wurden keine relevanten Informationen zu Ihrer Frage gefunden. "
                       "Versuchen Sie eine andere Formulierung oder überprüfen Sie, "
                       "ob entsprechende Dokumente importiert wurden.",
                sources=[],
                confidence=0.0,
                search_results_count=0
            )
        
        # Step 3: Format sources
        sources = self.format_sources(search_results)
        
        # Step 4: Generate answer
        try:
            context_chunks = self._aggregate_context(search_results)
            answer = self.generate_answer(context_chunks, question, model)
            confidence = self._calculate_confidence(search_results)
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence=confidence,
                search_results_count=len(search_results)
            )
            
        except LLMError as e:
            # Return sources even if LLM fails
            return RAGResponse(
                answer=f"Es gab einen Fehler bei der Antwortgenerierung: {e}. "
                       f"Die gefundenen Quellen sind jedoch verfügbar.",
                sources=sources,
                confidence=0.0,
                search_results_count=len(search_results)
            )
    
    def generate_answer(self, context_chunks: List[str], question: str, 
                       model: Optional[str] = None) -> str:
        """Generate answer using LLM with provided context
        
        Args:
            context_chunks: List of relevant text chunks
            question: User's question
            model: Optional specific model to use
            
        Returns:
            Generated answer text
        """
        system_prompt = self._create_system_prompt(context_chunks)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        return self.llm_provider.chat_completion(messages, model)
    
    def format_sources(self, search_results: List[SearchResult]) -> List[Source]:
        """Format search results into source references
        
        Args:
            search_results: List of search results from vector store
            
        Returns:
            List of formatted source references
        """
        sources = []
        for result in search_results:
            source = Source(
                document_path=result.document_path,
                page_number=result.page_number,
                chunk_content=result.chunk.content,
                relevance_score=result.similarity_score
            )
            sources.append(source)
        
        return sources
    
    def _aggregate_context(self, search_results: List[SearchResult]) -> List[str]:
        """Aggregate context from search results
        
        Args:
            search_results: List of search results
            
        Returns:
            List of formatted context chunks
        """
        context_chunks = []
        for result in search_results:
            # Format context with source information
            context = (
                f"Quelle: {result.document_path} (Seite {result.page_number})\n"
                f"Inhalt: {result.chunk.content}\n"
                f"Relevanz: {result.similarity_score:.2f}"
            )
            context_chunks.append(context)
        
        return context_chunks
    
    def _create_system_prompt(self, context_chunks: List[str]) -> str:
        """Create system prompt with context for LLM
        
        Args:
            context_chunks: List of context chunks
            
        Returns:
            Formatted system prompt
        """
        context_text = "\n\n".join(context_chunks)
        
        return f"""Du bist ein hilfreicher Assistent für ein Dokumentenmanagementsystem. 
Beantworte Fragen basierend auf den bereitgestellten Dokumenteninhalten auf Deutsch.

WICHTIGE REGELN:
1. Beantworte nur Fragen, die durch die bereitgestellten Dokumente beantwortet werden können
2. Gib immer die Quellen (Dokumentpfad und Seitenzahl) für deine Antworten an
3. Wenn die Informationen nicht ausreichen, sage das ehrlich
4. Antworte präzise und strukturiert
5. Verwende die deutsche Sprache

VERFÜGBARE DOKUMENTE:
{context_text}

Beantworte die folgende Frage basierend auf diesen Dokumenten:"""
    
    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score based on search results quality
        
        Args:
            search_results: List of search results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not search_results:
            return 0.0
        
        # Calculate average similarity score
        avg_similarity = sum(result.similarity_score for result in search_results) / len(search_results)
        
        # Adjust confidence based on number of results and quality
        result_count_factor = min(len(search_results) / 3.0, 1.0)  # More results = higher confidence
        quality_factor = avg_similarity  # Higher similarity = higher confidence
        
        # Combine factors with weights
        confidence = (quality_factor * 0.7) + (result_count_factor * 0.3)
        
        return min(confidence, 1.0)