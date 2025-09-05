"""Embeddings generation and management for RAG system."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelCapability
from src.services.ai.orchestrator import AIOrchestrator, AIRequest, AIResponse

logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    model_used: str
    token_usage: int
    metadata: Dict[str, Any]


@dataclass
class EmbeddingBatch:
    """Batch of embeddings with metadata."""
    embeddings: List[EmbeddingResult]
    batch_id: str
    total_tokens: int
    processing_time: float
    metadata: Dict[str, Any]


class EmbeddingService:
    """Service for generating and managing embeddings for RAG system."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        default_model: str = "text-embedding-3-small"
    ):
        self.orchestrator = orchestrator
        self.default_model = default_model
        self.embedding_cache: Dict[str, EmbeddingResult] = {}
        self.batch_cache: Dict[str, EmbeddingBatch] = {}
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EmbeddingResult:
        """Generate embedding for a single text."""
        model_name = model or self.default_model
        
        # Check cache first
        cache_key = self._get_cache_key(text, model_name)
        if cache_key in self.embedding_cache:
            logger.debug(f"Using cached embedding for text: {text[:50]}...")
            return self.embedding_cache[cache_key]
        
        # Prepare context
        context = context or {}
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.EMBEDDINGS,
            input_data=text,
            model_preference=model_name,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Extract embedding
            if isinstance(response.content, list):
                embedding = response.content
            else:
                raise AIServiceError("Invalid embedding response format")
            
            # Create result
            result = EmbeddingResult(
                text=text,
                embedding=embedding,
                model_used=response.model_used,
                token_usage=response.token_usage.total_tokens,
                metadata={
                    "processing_time": response.processing_time,
                    "fallback_used": response.fallback_used,
                    "confidence": response.confidence,
                }
            )
            
            # Cache the result
            self.embedding_cache[cache_key] = result
            
            logger.debug(f"Generated embedding for text: {text[:50]}... (dimensions: {len(embedding)})")
            
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise AIServiceError(f"Embedding generation failed: {str(e)}")
    
    async def generate_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        batch_size: int = 100
    ) -> EmbeddingBatch:
        """Generate embeddings for multiple texts in batches."""
        import time
        import uuid
        
        model_name = model or self.default_model
        batch_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Check cache for existing embeddings
        cached_results = []
        texts_to_process = []
        
        for text in texts:
            cache_key = self._get_cache_key(text, model_name)
            if cache_key in self.embedding_cache:
                cached_results.append(self.embedding_cache[cache_key])
            else:
                texts_to_process.append(text)
        
        # Process texts in batches
        all_results = cached_results.copy()
        
        if texts_to_process:
            for i in range(0, len(texts_to_process), batch_size):
                batch_texts = texts_to_process[i:i + batch_size]
                
                # Process batch
                batch_results = await self._process_batch(batch_texts, model_name, context)
                all_results.extend(batch_results)
                
                # Cache results
                for result in batch_results:
                    cache_key = self._get_cache_key(result.text, model_name)
                    self.embedding_cache[cache_key] = result
        
        # Calculate statistics
        total_tokens = sum(result.token_usage for result in all_results)
        processing_time = time.time() - start_time
        
        # Create batch result
        batch = EmbeddingBatch(
            embeddings=all_results,
            batch_id=batch_id,
            total_tokens=total_tokens,
            processing_time=processing_time,
            metadata={
                "model_used": model_name,
                "total_texts": len(texts),
                "cached_count": len(cached_results),
                "processed_count": len(texts_to_process),
                "batch_size": batch_size,
            }
        )
        
        # Cache the batch
        self.batch_cache[batch_id] = batch
        
        logger.info(f"Generated {len(all_results)} embeddings in {processing_time:.2f}s (batch: {batch_id})")
        
        return batch
    
    async def _process_batch(
        self,
        texts: List[str],
        model: str,
        context: Optional[Dict[str, Any]]
    ) -> List[EmbeddingResult]:
        """Process a batch of texts for embedding generation."""
        results = []
        
        # Process texts concurrently (with rate limiting)
        import asyncio
        semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
        
        async def process_single(text: str) -> EmbeddingResult:
            async with semaphore:
                return await self.generate_embedding(text, model, context)
        
        tasks = [process_single(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate embedding for text {i}: {str(result)}")
                # Create fallback result
                fallback_result = EmbeddingResult(
                    text=texts[i],
                    embedding=[0.0] * 1536,  # Default dimension
                    model_used=model,
                    token_usage=0,
                    metadata={"error": str(result)}
                )
                valid_results.append(fallback_result)
            else:
                valid_results.append(result)
        
        return valid_results
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model."""
        content = f"{text}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get_embedding_dimensions(self, model: str) -> int:
        """Get embedding dimensions for a model."""
        dimension_map = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536,
        }
        return dimension_map.get(model, 1536)  # Default to 1536
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
        method: str = "cosine"
    ) -> float:
        """Calculate similarity between two embeddings."""
        import numpy as np
        
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        if method == "cosine":
            # Cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        
        elif method == "euclidean":
            # Euclidean distance (inverted for similarity)
            distance = np.linalg.norm(vec1 - vec2)
            return 1.0 / (1.0 + distance)
        
        elif method == "dot_product":
            # Dot product
            return np.dot(vec1, vec2)
        
        else:
            raise ValueError(f"Unsupported similarity method: {method}")
    
    def find_similar_embeddings(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[EmbeddingResult],
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        method: str = "cosine"
    ) -> List[Dict[str, Any]]:
        """Find similar embeddings using various similarity methods."""
        similarities = []
        
        for candidate in candidate_embeddings:
            similarity = self.calculate_similarity(
                query_embedding,
                candidate.embedding,
                method
            )
            
            if similarity >= similarity_threshold:
                similarities.append({
                    "text": candidate.text,
                    "similarity": similarity,
                    "model_used": candidate.model_used,
                    "metadata": candidate.metadata,
                })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:top_k]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        total_embeddings = len(self.embedding_cache)
        total_batches = len(self.batch_cache)
        
        # Calculate total tokens cached
        total_tokens = sum(result.token_usage for result in self.embedding_cache.values())
        
        # Calculate total batch tokens
        total_batch_tokens = sum(batch.total_tokens for batch in self.batch_cache.values())
        
        return {
            "total_embeddings": total_embeddings,
            "total_batches": total_batches,
            "total_tokens": total_tokens,
            "total_batch_tokens": total_batch_tokens,
            "cache_hit_rate": "N/A",  # Would need hit/miss tracking
        }
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self.embedding_cache.clear()
        self.batch_cache.clear()
        logger.info("Embedding cache cleared")
    
    def get_cached_embedding(self, text: str, model: str) -> Optional[EmbeddingResult]:
        """Get cached embedding if available."""
        cache_key = self._get_cache_key(text, model)
        return self.embedding_cache.get(cache_key)
    
    def get_cached_batch(self, batch_id: str) -> Optional[EmbeddingBatch]:
        """Get cached batch if available."""
        return self.batch_cache.get(batch_id)
    
    def precompute_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Precompute embeddings for common texts (async operation)."""
        import asyncio
        
        async def precompute():
            try:
                await self.generate_batch(texts, model, context)
                logger.info(f"Precomputed embeddings for {len(texts)} texts")
            except Exception as e:
                logger.error(f"Failed to precompute embeddings: {str(e)}")
        
        # Run in background
        asyncio.create_task(precompute())
    
    def validate_embedding(self, embedding: List[float], model: str) -> bool:
        """Validate embedding format and dimensions."""
        expected_dim = self.get_embedding_dimensions(model)
        
        if len(embedding) != expected_dim:
            logger.warning(f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}")
            return False
        
        if not all(isinstance(x, (int, float)) for x in embedding):
            logger.warning("Embedding contains non-numeric values")
            return False
        
        return True
    
    def normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to unit vector."""
        import numpy as np
        
        vec = np.array(embedding)
        norm = np.linalg.norm(vec)
        
        if norm == 0:
            return embedding
        
        return (vec / norm).tolist()
    
    def analyze_embedding_quality(
        self,
        embeddings: List[EmbeddingResult]
    ) -> Dict[str, Any]:
        """Analyze quality of generated embeddings."""
        if not embeddings:
            return {}
        
        import numpy as np
        
        # Extract embedding vectors
        vectors = [np.array(emb.embedding) for emb in embeddings]
        
        # Calculate statistics
        dimensions = len(vectors[0]) if vectors else 0
        total_tokens = sum(emb.token_usage for emb in embeddings)
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                sim = self.calculate_similarity(vectors[i].tolist(), vectors[j].tolist())
                similarities.append(sim)
        
        # Calculate quality metrics
        avg_similarity = np.mean(similarities) if similarities else 0.0
        std_similarity = np.std(similarities) if similarities else 0.0
        
        # Check for duplicate embeddings
        unique_embeddings = len(set(tuple(emb.embedding) for emb in embeddings))
        duplicate_rate = 1.0 - (unique_embeddings / len(embeddings))
        
        return {
            "total_embeddings": len(embeddings),
            "dimensions": dimensions,
            "total_tokens": total_tokens,
            "average_similarity": avg_similarity,
            "similarity_std": std_similarity,
            "unique_embeddings": unique_embeddings,
            "duplicate_rate": duplicate_rate,
            "quality_score": 1.0 - duplicate_rate,  # Simple quality metric
        }
