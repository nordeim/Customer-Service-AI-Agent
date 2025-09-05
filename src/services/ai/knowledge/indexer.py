"""Knowledge indexing and management for RAG system."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.knowledge.embeddings import EmbeddingService, EmbeddingResult
from src.services.ai.knowledge.vector_store import VectorStore, VectorSearchResult

logger = get_logger(__name__)


@dataclass
class KnowledgeEntry:
    """A knowledge entry with content and metadata."""
    id: str
    title: str
    content: str
    content_type: str  # text, markdown, html, pdf, etc.
    source: str
    category: str
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None


@dataclass
class IndexingResult:
    """Result of knowledge indexing."""
    entry_id: str
    success: bool
    embedding_generated: bool
    vector_stored: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class KnowledgeIndexer:
    """Service for indexing and managing knowledge entries."""
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.indexed_entries: Dict[str, KnowledgeEntry] = {}
    
    async def index_entry(
        self,
        entry: KnowledgeEntry,
        generate_embedding: bool = True,
        store_vector: bool = True
    ) -> IndexingResult:
        """Index a knowledge entry."""
        result = IndexingResult(
            entry_id=entry.id,
            success=False,
            embedding_generated=False,
            vector_stored=False
        )
        
        try:
            # Generate embedding if requested
            if generate_embedding:
                embedding_result = await self.embedding_service.generate_embedding(
                    entry.content,
                    context={
                        "title": entry.title,
                        "category": entry.category,
                        "source": entry.source,
                        "content_type": entry.content_type
                    }
                )
                
                entry.embedding = embedding_result.embedding
                entry.embedding_model = embedding_result.model_used
                result.embedding_generated = True
                
                logger.debug(f"Generated embedding for entry: {entry.id}")
            
            # Store vector if requested
            if store_vector and entry.embedding:
                vector_data = {
                    "id": entry.id,
                    "text": entry.content,
                    "embedding": entry.embedding,
                    "metadata": {
                        "title": entry.title,
                        "content_type": entry.content_type,
                        "source": entry.source,
                        "category": entry.category,
                        "tags": entry.tags,
                        "embedding_model": entry.embedding_model,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        **entry.metadata
                    }
                }
                
                await self.vector_store.upsert([vector_data])
                result.vector_stored = True
                
                logger.debug(f"Stored vector for entry: {entry.id}")
            
            # Store entry in memory
            self.indexed_entries[entry.id] = entry
            
            result.success = True
            result.metadata = {
                "embedding_dimensions": len(entry.embedding) if entry.embedding else 0,
                "content_length": len(entry.content),
                "chunk_count": 1  # Single chunk for now
            }
            
            logger.info(f"Successfully indexed entry: {entry.id}")
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Failed to index entry {entry.id}: {str(e)}")
        
        return result
    
    async def index_batch(
        self,
        entries: List[KnowledgeEntry],
        generate_embeddings: bool = True,
        store_vectors: bool = True
    ) -> List[IndexingResult]:
        """Index multiple knowledge entries."""
        results = []
        
        for entry in entries:
            result = await self.index_entry(entry, generate_embeddings, store_vectors)
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"Indexed {success_count}/{len(entries)} entries successfully")
        
        return results
    
    async def index_document(
        self,
        content: str,
        title: str,
        source: str,
        category: str = "general",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_content: bool = True
    ) -> List[IndexingResult]:
        """Index a document by chunking it into smaller pieces."""
        if chunk_content and len(content) > self.chunk_size:
            chunks = self._chunk_content(content)
            results = []
            
            for i, chunk in enumerate(chunks):
                entry = KnowledgeEntry(
                    id=f"{self._generate_id(title, source)}_{i}",
                    title=f"{title} (Part {i+1})",
                    content=chunk,
                    content_type="text",
                    source=source,
                    category=category,
                    tags=tags or [],
                    metadata=metadata or {},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                result = await self.index_entry(entry)
                results.append(result)
            
            return results
        else:
            # Index as single entry
            entry = KnowledgeEntry(
                id=self._generate_id(title, source),
                title=title,
                content=content,
                content_type="text",
                source=source,
                category=category,
                tags=tags or [],
                metadata=metadata or {},
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await self.index_entry(entry)
            return [result]
    
    def _chunk_content(self, content: str) -> List[str]:
        """Chunk content into smaller pieces."""
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + self.chunk_size
            
            if end >= len(content):
                # Last chunk
                chunks.append(content[start:])
                break
            
            # Find a good break point (sentence or paragraph)
            break_point = content.rfind('.', start, end)
            if break_point == -1:
                break_point = content.rfind('\n', start, end)
            if break_point == -1:
                break_point = content.rfind(' ', start, end)
            
            if break_point > start:
                chunks.append(content[start:break_point + 1])
                start = break_point + 1 - self.chunk_overlap
            else:
                chunks.append(content[start:end])
                start = end - self.chunk_overlap
        
        return chunks
    
    def _generate_id(self, title: str, source: str) -> str:
        """Generate a unique ID for an entry."""
        content = f"{title}:{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def search_knowledge(
        self,
        query: str,
        top_k: int = 10,
        category_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
        similarity_threshold: float = 0.7
    ) -> List[VectorSearchResult]:
        """Search knowledge base using vector similarity."""
        try:
            # Generate embedding for query
            embedding_result = await self.embedding_service.generate_embedding(query)
            query_embedding = embedding_result.embedding
            
            # Prepare filters
            filter_metadata = {}
            if category_filter:
                filter_metadata["category"] = category_filter
            if source_filter:
                filter_metadata["source"] = source_filter
            if tags_filter:
                filter_metadata["tags"] = tags_filter
            
            # Search vector store
            search_response = await self.vector_store.search(
                query_vector=query_embedding,
                top_k=top_k,
                filter_metadata=filter_metadata
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in search_response.results
                if result.score >= similarity_threshold
            ]
            
            logger.info(f"Found {len(filtered_results)} relevant knowledge entries")
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {str(e)}")
            raise AIServiceError(f"Knowledge search failed: {str(e)}")
    
    async def update_entry(
        self,
        entry_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing knowledge entry."""
        try:
            if entry_id not in self.indexed_entries:
                logger.warning(f"Entry not found: {entry_id}")
                return False
            
            entry = self.indexed_entries[entry_id]
            
            # Update fields
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            
            entry.updated_at = datetime.utcnow()
            
            # Re-index if content changed
            if "content" in updates:
                await self.index_entry(entry, generate_embedding=True, store_vector=True)
            else:
                # Just update metadata
                vector_data = {
                    "id": entry.id,
                    "text": entry.content,
                    "embedding": entry.embedding,
                    "metadata": {
                        "title": entry.title,
                        "content_type": entry.content_type,
                        "source": entry.source,
                        "category": entry.category,
                        "tags": entry.tags,
                        "embedding_model": entry.embedding_model,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                        **entry.metadata
                    }
                }
                
                await self.vector_store.upsert([vector_data])
            
            logger.info(f"Updated entry: {entry_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update entry {entry_id}: {str(e)}")
            return False
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete a knowledge entry."""
        try:
            # Delete from vector store
            await self.vector_store.delete([entry_id])
            
            # Remove from memory
            if entry_id in self.indexed_entries:
                del self.indexed_entries[entry_id]
            
            logger.info(f"Deleted entry: {entry_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete entry {entry_id}: {str(e)}")
            return False
    
    async def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a knowledge entry by ID."""
        return self.indexed_entries.get(entry_id)
    
    async def list_entries(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100
    ) -> List[KnowledgeEntry]:
        """List knowledge entries with optional filters."""
        entries = list(self.indexed_entries.values())
        
        # Apply filters
        if category:
            entries = [e for e in entries if e.category == category]
        
        if source:
            entries = [e for e in entries if e.source == source]
        
        # Sort by updated_at (newest first)
        entries.sort(key=lambda x: x.updated_at, reverse=True)
        
        return entries[:limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics."""
        try:
            vector_stats = await self.vector_store.get_stats()
            
            # Calculate entry statistics
            total_entries = len(self.indexed_entries)
            categories = set(entry.category for entry in self.indexed_entries.values())
            sources = set(entry.source for entry in self.indexed_entries.values())
            
            # Calculate content statistics
            total_content_length = sum(len(entry.content) for entry in self.indexed_entries.values())
            avg_content_length = total_content_length / total_entries if total_entries > 0 else 0
            
            return {
                "total_entries": total_entries,
                "total_categories": len(categories),
                "total_sources": len(sources),
                "total_content_length": total_content_length,
                "average_content_length": avg_content_length,
                "vector_store_stats": vector_stats,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
            }
            
        except Exception as e:
            logger.error(f"Failed to get indexing stats: {str(e)}")
            return {"error": str(e)}
    
    async def rebuild_index(self) -> Dict[str, Any]:
        """Rebuild the entire index."""
        try:
            logger.info("Starting index rebuild...")
            
            # Get all entries
            entries = list(self.indexed_entries.values())
            
            # Clear vector store
            # Note: This would need to be implemented in the vector store
            # For now, we'll re-index all entries
            
            # Re-index all entries
            results = await self.index_batch(entries, generate_embeddings=True, store_vectors=True)
            
            success_count = sum(1 for r in results if r.success)
            
            logger.info(f"Index rebuild completed: {success_count}/{len(entries)} entries")
            
            return {
                "total_entries": len(entries),
                "successful_reindexes": success_count,
                "failed_reindexes": len(entries) - success_count,
                "rebuild_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Index rebuild failed: {str(e)}")
            raise AIServiceError(f"Index rebuild failed: {str(e)}")
    
    async def optimize_index(self) -> Dict[str, Any]:
        """Optimize the index for better performance."""
        try:
            logger.info("Starting index optimization...")
            
            # Get statistics
            stats = await self.get_stats()
            
            # Remove duplicate entries
            seen_content = {}
            duplicates_removed = 0
            
            for entry_id, entry in list(self.indexed_entries.items()):
                content_hash = hashlib.md5(entry.content.encode()).hexdigest()
                
                if content_hash in seen_content:
                    # Remove duplicate
                    await self.delete_entry(entry_id)
                    duplicates_removed += 1
                else:
                    seen_content[content_hash] = entry_id
            
            logger.info(f"Index optimization completed: removed {duplicates_removed} duplicates")
            
            return {
                "duplicates_removed": duplicates_removed,
                "optimization_time": datetime.utcnow().isoformat(),
                "final_stats": await self.get_stats()
            }
            
        except Exception as e:
            logger.error(f"Index optimization failed: {str(e)}")
            raise AIServiceError(f"Index optimization failed: {str(e)}")
