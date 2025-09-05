"""Vector store integration for RAG system (Pinecone, pgvector)."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.knowledge.embeddings import EmbeddingResult

logger = get_logger(__name__)


@dataclass
class VectorSearchResult:
    """Result of vector search."""
    id: str
    text: str
    embedding: List[float]
    score: float
    metadata: Dict[str, Any]


@dataclass
class VectorSearchResponse:
    """Response from vector search."""
    results: List[VectorSearchResult]
    total_found: int
    query_time: float
    metadata: Dict[str, Any]


class VectorStore(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    async def upsert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert vectors to the store."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> VectorSearchResponse:
        """Search for similar vectors."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete vectors by IDs."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        pass


class PineconeVectorStore(VectorStore):
    """Pinecone vector store implementation."""
    
    def __init__(
        self,
        api_key: str,
        environment: str,
        index_name: str,
        dimension: int = 1536
    ):
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension
        self._client = None
    
    async def _get_client(self):
        """Get Pinecone client."""
        if self._client is None:
            try:
                import pinecone
                pinecone.init(api_key=self.api_key, environment=self.environment)
                self._client = pinecone.Index(self.index_name)
            except ImportError:
                raise AIServiceError("Pinecone package not installed")
            except Exception as e:
                raise AIServiceError(f"Failed to initialize Pinecone: {str(e)}")
        
        return self._client
    
    async def upsert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert vectors to Pinecone."""
        try:
            client = await self._get_client()
            
            # Prepare vectors for Pinecone
            pinecone_vectors = []
            for vector in vectors:
                pinecone_vector = {
                    "id": vector["id"],
                    "values": vector["embedding"],
                    "metadata": vector.get("metadata", {})
                }
                pinecone_vectors.append(pinecone_vector)
            
            # Upsert to Pinecone
            result = client.upsert(
                vectors=pinecone_vectors,
                namespace=namespace
            )
            
            logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
            
            return {
                "upserted_count": result.upserted_count,
                "namespace": namespace,
                "index_name": self.index_name
            }
            
        except Exception as e:
            logger.error(f"Pinecone upsert failed: {str(e)}")
            raise AIServiceError(f"Pinecone upsert failed: {str(e)}")
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> VectorSearchResponse:
        """Search for similar vectors in Pinecone."""
        import time
        
        start_time = time.time()
        
        try:
            client = await self._get_client()
            
            # Prepare query
            query_params = {
                "vector": query_vector,
                "top_k": top_k,
                "include_metadata": True
            }
            
            if namespace:
                query_params["namespace"] = namespace
            
            if filter_metadata:
                query_params["filter"] = filter_metadata
            
            # Search
            result = client.query(**query_params)
            
            # Process results
            search_results = []
            for match in result.matches:
                search_result = VectorSearchResult(
                    id=match.id,
                    text=match.metadata.get("text", ""),
                    embedding=match.values,
                    score=match.score,
                    metadata=match.metadata
                )
                search_results.append(search_result)
            
            query_time = time.time() - start_time
            
            return VectorSearchResponse(
                results=search_results,
                total_found=len(search_results),
                query_time=query_time,
                metadata={
                    "index_name": self.index_name,
                    "namespace": namespace,
                    "top_k": top_k
                }
            )
            
        except Exception as e:
            logger.error(f"Pinecone search failed: {str(e)}")
            raise AIServiceError(f"Pinecone search failed: {str(e)}")
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete vectors from Pinecone."""
        try:
            client = await self._get_client()
            
            result = client.delete(
                ids=ids,
                namespace=namespace
            )
            
            logger.info(f"Deleted {len(ids)} vectors from Pinecone")
            
            return {
                "deleted_count": len(ids),
                "namespace": namespace,
                "index_name": self.index_name
            }
            
        except Exception as e:
            logger.error(f"Pinecone delete failed: {str(e)}")
            raise AIServiceError(f"Pinecone delete failed: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Pinecone index statistics."""
        try:
            client = await self._get_client()
            stats = client.describe_index_stats()
            
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
            
        except Exception as e:
            logger.error(f"Failed to get Pinecone stats: {str(e)}")
            raise AIServiceError(f"Failed to get Pinecone stats: {str(e)}")


class PgVectorStore(VectorStore):
    """PostgreSQL with pgvector implementation."""
    
    def __init__(
        self,
        connection_string: str,
        table_name: str = "knowledge_embeddings",
        dimension: int = 1536
    ):
        self.connection_string = connection_string
        self.table_name = table_name
        self.dimension = dimension
        self._connection = None
    
    async def _get_connection(self):
        """Get database connection."""
        if self._connection is None:
            try:
                import asyncpg
                self._connection = await asyncpg.connect(self.connection_string)
            except ImportError:
                raise AIServiceError("asyncpg package not installed")
            except Exception as e:
                raise AIServiceError(f"Failed to connect to PostgreSQL: {str(e)}")
        
        return self._connection
    
    async def upsert(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert vectors to PostgreSQL."""
        try:
            conn = await self._get_connection()
            
            # Prepare upsert query
            query = f"""
                INSERT INTO {self.table_name} (id, text, embedding, metadata, namespace, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE SET
                    text = EXCLUDED.text,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    namespace = EXCLUDED.namespace,
                    updated_at = NOW()
            """
            
            # Execute upsert for each vector
            upserted_count = 0
            for vector in vectors:
                await conn.execute(
                    query,
                    vector["id"],
                    vector.get("text", ""),
                    vector["embedding"],
                    json.dumps(vector.get("metadata", {})),
                    namespace
                )
                upserted_count += 1
            
            logger.info(f"Upserted {upserted_count} vectors to PostgreSQL")
            
            return {
                "upserted_count": upserted_count,
                "namespace": namespace,
                "table_name": self.table_name
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL upsert failed: {str(e)}")
            raise AIServiceError(f"PostgreSQL upsert failed: {str(e)}")
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None
    ) -> VectorSearchResponse:
        """Search for similar vectors in PostgreSQL."""
        import time
        
        start_time = time.time()
        
        try:
            conn = await self._get_connection()
            
            # Build query
            base_query = f"""
                SELECT id, text, embedding, metadata, 
                       (embedding <=> $1) as distance,
                       1 - (embedding <=> $1) as similarity
                FROM {self.table_name}
            """
            
            params = [query_vector]
            conditions = []
            
            if namespace:
                conditions.append("namespace = $" + str(len(params) + 1))
                params.append(namespace)
            
            if filter_metadata:
                for key, value in filter_metadata.items():
                    conditions.append(f"metadata->>'{key}' = $" + str(len(params) + 1))
                    params.append(str(value))
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += f" ORDER BY embedding <=> $1 LIMIT ${len(params) + 1}"
            params.append(top_k)
            
            # Execute query
            rows = await conn.fetch(base_query, *params)
            
            # Process results
            search_results = []
            for row in rows:
                search_result = VectorSearchResult(
                    id=row["id"],
                    text=row["text"],
                    embedding=row["embedding"],
                    score=row["similarity"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                search_results.append(search_result)
            
            query_time = time.time() - start_time
            
            return VectorSearchResponse(
                results=search_results,
                total_found=len(search_results),
                query_time=query_time,
                metadata={
                    "table_name": self.table_name,
                    "namespace": namespace,
                    "top_k": top_k
                }
            )
            
        except Exception as e:
            logger.error(f"PostgreSQL search failed: {str(e)}")
            raise AIServiceError(f"PostgreSQL search failed: {str(e)}")
    
    async def delete(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete vectors from PostgreSQL."""
        try:
            conn = await self._get_connection()
            
            # Build delete query
            query = f"DELETE FROM {self.table_name} WHERE id = ANY($1)"
            params = [ids]
            
            if namespace:
                query += " AND namespace = $2"
                params.append(namespace)
            
            # Execute delete
            result = await conn.execute(query, *params)
            
            # Extract deleted count from result
            deleted_count = int(result.split()[-1]) if result else 0
            
            logger.info(f"Deleted {deleted_count} vectors from PostgreSQL")
            
            return {
                "deleted_count": deleted_count,
                "namespace": namespace,
                "table_name": self.table_name
            }
            
        except Exception as e:
            logger.error(f"PostgreSQL delete failed: {str(e)}")
            raise AIServiceError(f"PostgreSQL delete failed: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get PostgreSQL table statistics."""
        try:
            conn = await self._get_connection()
            
            # Get table stats
            stats_query = f"""
                SELECT 
                    COUNT(*) as total_vectors,
                    COUNT(DISTINCT namespace) as namespace_count,
                    AVG(array_length(embedding, 1)) as avg_dimension
                FROM {self.table_name}
            """
            
            row = await conn.fetchrow(stats_query)
            
            return {
                "total_vector_count": row["total_vectors"],
                "namespace_count": row["namespace_count"],
                "avg_dimension": row["avg_dimension"],
                "table_name": self.table_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL stats: {str(e)}")
            raise AIServiceError(f"Failed to get PostgreSQL stats: {str(e)}")


class VectorStoreFactory:
    """Factory for creating vector stores."""
    
    @staticmethod
    def create_pinecone_store(
        api_key: str,
        environment: str,
        index_name: str,
        dimension: int = 1536
    ) -> PineconeVectorStore:
        """Create a Pinecone vector store."""
        return PineconeVectorStore(api_key, environment, index_name, dimension)
    
    @staticmethod
    def create_pgvector_store(
        connection_string: str,
        table_name: str = "knowledge_embeddings",
        dimension: int = 1536
    ) -> PgVectorStore:
        """Create a PostgreSQL vector store."""
        return PgVectorStore(connection_string, table_name, dimension)
    
    @staticmethod
    def create_store(
        store_type: str,
        **kwargs
    ) -> VectorStore:
        """Create a vector store by type."""
        if store_type.lower() == "pinecone":
            return VectorStoreFactory.create_pinecone_store(**kwargs)
        elif store_type.lower() == "pgvector":
            return VectorStoreFactory.create_pgvector_store(**kwargs)
        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
