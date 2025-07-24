"""Vector storage implementation using ChromaDB"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging
import numpy as np

from dms.models import TextChunk, SearchResult


logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for German text using sentence-transformers"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize the embedding generator
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model_name = model_name
        logger.info(f"Loading embedding model: {model_name}")
        
        # Load the model (will download if not cached)
        self.model = SentenceTransformer(model_name)
        
        logger.info(f"Embedding model loaded successfully. Dimension: {self.model.get_sentence_embedding_dimension()}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding
        """
        if not text or not text.strip():
            # Handle empty text by using a placeholder
            text = "[EMPTY]"
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Convert to list for JSON serialization
        return embedding.tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch (more efficient)
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        if not texts:
            return []
        
        # Handle empty texts
        processed_texts = []
        for text in texts:
            if not text or not text.strip():
                processed_texts.append("[EMPTY]")
            else:
                processed_texts.append(text)
        
        # Generate embeddings in batch
        embeddings = self.model.encode(processed_texts, convert_to_numpy=True)
        
        # Convert to list of lists for JSON serialization
        return [embedding.tolist() for embedding in embeddings]


class VectorStore:
    """Vector database for storing and searching document chunks using ChromaDB"""
    
    def __init__(self, db_path: str = None, use_embeddings: bool = True):
        """
        Initialize VectorStore with ChromaDB
        
        Args:
            db_path: Path to store the ChromaDB database. If None, uses default location.
            use_embeddings: Whether to use custom embeddings or ChromaDB's default
        """
        if db_path is None:
            db_path = str(Path.home() / ".dms" / "chroma.db")
        
        # Ensure the directory exists
        Path(db_path).mkdir(parents=True, exist_ok=True)
        
        self.use_embeddings = use_embeddings
        
        # Initialize embedding generator if requested
        if use_embeddings:
            self.embedding_generator = EmbeddingGenerator()
        else:
            self.embedding_generator = None
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create the documents collection
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        logger.info(f"VectorStore initialized with database at {db_path}, embeddings: {use_embeddings}")
    
    def add_documents(self, chunks: List[TextChunk]) -> None:
        """
        Add document chunks to the vector store
        
        Args:
            chunks: List of TextChunk objects to add
        """
        if not chunks:
            return
        
        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        embeddings = None
        
        for chunk in chunks:
            ids.append(chunk.id)
            documents.append(chunk.content)
            
            # Extract directory structure from document_id
            doc_path = Path(chunk.document_id)
            directory_parts = doc_path.parts[:-1]  # All parts except filename
            directory_structure = "/".join(directory_parts) if directory_parts else ""
            
            # Extract year and month from directory structure if available
            year = None
            month = None
            if len(directory_parts) >= 1:
                try:
                    year = directory_parts[0]
                    if len(directory_parts) >= 2:
                        month = directory_parts[1]
                except (IndexError, ValueError):
                    pass
            
            metadata = {
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "directory_structure": directory_structure,
            }
            
            # Add year and month if available for filtering
            if year:
                metadata["year"] = year
            if month:
                metadata["month"] = month
                
            metadatas.append(metadata)
        
        # Generate embeddings if enabled
        if self.use_embeddings and self.embedding_generator:
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embeddings = self.embedding_generator.generate_embeddings(documents)
        
        # Add to ChromaDB collection
        if embeddings:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )
        else:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
        
        logger.info(f"Added {len(chunks)} chunks to vector store")
    
    def similarity_search(
        self, 
        query: str, 
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar document chunks
        
        Args:
            query: Search query string
            n_results: Maximum number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            return []
        
        # Convert filters to ChromaDB format
        where_clause = None
        if filters:
            where_clause = self._build_where_clause(filters)
        
        try:
            # Generate query embedding if using custom embeddings
            query_embedding = None
            if self.use_embeddings and self.embedding_generator:
                query_embedding = self.embedding_generator.generate_embedding(query)
            
            # Perform similarity search
            if query_embedding:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_clause
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause
                )
            
            # Convert results to SearchResult objects
            search_results = []
            if results['ids'] and results['ids'][0]:  # Check if we have results
                for i, chunk_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    document = results['documents'][0][i]
                    distance = results['distances'][0][i] if results['distances'] else 0.0
                    
                    # Convert distance to similarity score (ChromaDB returns distances)
                    similarity_score = 1.0 - distance
                    
                    # Create TextChunk from stored data
                    chunk = TextChunk(
                        id=chunk_id,
                        document_id=metadata['document_id'],
                        content=document,
                        page_number=metadata['page_number'],
                        chunk_index=metadata['chunk_index']
                    )
                    
                    # Create SearchResult
                    search_result = SearchResult(
                        chunk=chunk,
                        similarity_score=similarity_score,
                        document_path=metadata['document_id'],
                        page_number=metadata['page_number']
                    )
                    
                    search_results.append(search_result)
            
            logger.info(f"Found {len(search_results)} results for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []
    
    def delete_documents(self, document_ids: Union[str, List[str]]) -> None:
        """
        Delete documents from the vector store
        
        Args:
            document_ids: Single document ID or list of document IDs to delete
        """
        if isinstance(document_ids, str):
            document_ids = [document_ids]
        
        if not document_ids:
            return
        
        try:
            # Find all chunks belonging to these documents
            for doc_id in document_ids:
                # Query for chunks with this document_id
                results = self.collection.get(
                    where={"document_id": doc_id}
                )
                
                if results['ids']:
                    # Delete all chunks for this document
                    self.collection.delete(ids=results['ids'])
                    logger.info(f"Deleted {len(results['ids'])} chunks for document {doc_id}")
                    
        except Exception as e:
            logger.error(f"Error deleting documents {document_ids}: {e}")
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build ChromaDB where clause from filters
        
        Args:
            filters: Filter dictionary
            
        Returns:
            ChromaDB where clause
        """
        where_clause = {}
        
        for key, value in filters.items():
            if key == "directory_structure":
                where_clause["directory_structure"] = value
            elif key == "category":
                where_clause["category"] = value
            elif key == "year":
                where_clause["year"] = value
            elif key == "month":
                if isinstance(value, dict) and "$in" in value:
                    # Handle month range queries
                    where_clause["month"] = {"$in": value["$in"]}
                else:
                    where_clause["month"] = value
            elif key == "page_number":
                where_clause["page_number"] = value
            else:
                # Pass through other filters as-is
                where_clause[key] = value
        
        return where_clause
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            results = self.collection.get()
            total_chunks = len(results['ids'])
            
            # Count unique documents
            unique_docs = set()
            directory_counts = {}
            
            for metadata in results['metadatas']:
                unique_docs.add(metadata['document_id'])
                
                dir_struct = metadata.get('directory_structure', 'unknown')
                directory_counts[dir_struct] = directory_counts.get(dir_struct, 0) + 1
            
            return {
                "total_chunks": total_chunks,
                "unique_documents": len(unique_docs),
                "directory_distribution": directory_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {
                "total_chunks": 0,
                "unique_documents": 0,
                "directory_distribution": {}
            }