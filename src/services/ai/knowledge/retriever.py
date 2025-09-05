"""RAG knowledge retrieval system with citations and context synthesis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.knowledge.indexer import KnowledgeIndexer
from src.services.ai.knowledge.vector_store import VectorSearchResult
from src.services.ai.orchestrator import AIOrchestrator, AIRequest, AIResponse
from src.services.ai.models import ModelCapability

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Result of knowledge retrieval."""
    query: str
    relevant_documents: List[VectorSearchResult]
    synthesized_context: str
    citations: List[Dict[str, Any]]
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class RAGResponse:
    """Response from RAG system."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    retrieval_metadata: Dict[str, Any]
    generation_metadata: Dict[str, Any]


class KnowledgeRetriever:
    """Service for retrieving and synthesizing knowledge using RAG."""
    
    def __init__(
        self,
        knowledge_indexer: KnowledgeIndexer,
        orchestrator: AIOrchestrator,
        max_context_length: int = 4000,
        max_sources: int = 5
    ):
        self.knowledge_indexer = knowledge_indexer
        self.orchestrator = orchestrator
        self.max_context_length = max_context_length
        self.max_sources = max_sources
    
    async def retrieve_knowledge(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        category_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
        similarity_threshold: float = 0.7,
        max_results: int = 10
    ) -> RetrievalResult:
        """Retrieve relevant knowledge for a query."""
        context = context or {}
        
        try:
            # Search for relevant documents
            relevant_docs = await self.knowledge_indexer.search_knowledge(
                query=query,
                top_k=max_results,
                category_filter=category_filter,
                source_filter=source_filter,
                tags_filter=tags_filter,
                similarity_threshold=similarity_threshold
            )
            
            # Synthesize context from relevant documents
            synthesized_context = await self._synthesize_context(
                query, relevant_docs, context
            )
            
            # Generate citations
            citations = self._generate_citations(relevant_docs)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(relevant_docs)
            
            return RetrievalResult(
                query=query,
                relevant_documents=relevant_docs,
                synthesized_context=synthesized_context,
                citations=citations,
                confidence=confidence,
                metadata={
                    "total_documents_found": len(relevant_docs),
                    "similarity_threshold": similarity_threshold,
                    "context_length": len(synthesized_context),
                    "filters_applied": {
                        "category": category_filter,
                        "source": source_filter,
                        "tags": tags_filter
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {str(e)}")
            raise AIServiceError(f"Knowledge retrieval failed: {str(e)}")
    
    async def _synthesize_context(
        self,
        query: str,
        documents: List[VectorSearchResult],
        context: Dict[str, Any]
    ) -> str:
        """Synthesize context from relevant documents."""
        if not documents:
            return "No relevant information found."
        
        # Prepare document content
        doc_contents = []
        for i, doc in enumerate(documents[:self.max_sources]):
            content = f"[Source {i+1}] {doc.metadata.get('title', 'Untitled')}\n{doc.text}\n"
            doc_contents.append(content)
        
        # Combine documents
        combined_content = "\n".join(doc_contents)
        
        # Truncate if too long
        if len(combined_content) > self.max_context_length:
            combined_content = combined_content[:self.max_context_length] + "..."
        
        return combined_content
    
    def _generate_citations(self, documents: List[VectorSearchResult]) -> List[Dict[str, Any]]:
        """Generate citations for retrieved documents."""
        citations = []
        
        for i, doc in enumerate(documents[:self.max_sources]):
            citation = {
                "id": doc.id,
                "title": doc.metadata.get("title", "Untitled"),
                "source": doc.metadata.get("source", "Unknown"),
                "category": doc.metadata.get("category", "general"),
                "similarity_score": doc.score,
                "reference": f"[{i+1}]",
                "metadata": doc.metadata
            }
            citations.append(citation)
        
        return citations
    
    def _calculate_confidence(self, documents: List[VectorSearchResult]) -> float:
        """Calculate overall confidence based on retrieved documents."""
        if not documents:
            return 0.0
        
        # Calculate confidence based on similarity scores
        scores = [doc.score for doc in documents]
        avg_score = sum(scores) / len(scores)
        
        # Boost confidence if we have multiple high-quality sources
        if len(documents) >= 3 and avg_score > 0.8:
            confidence = min(0.95, avg_score + 0.1)
        else:
            confidence = avg_score
        
        return confidence
    
    async def generate_answer(
        self,
        query: str,
        retrieval_result: RetrievalResult,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> RAGResponse:
        """Generate an answer using retrieved knowledge."""
        context = context or {}
        
        try:
            # Prepare variables for prompt template
            variables = {
                "customer_query": query,
                "knowledge_sources": retrieval_result.synthesized_context,
                "customer_tier": context.get("customer_tier", "basic"),
                "organization_name": context.get("organization_name", "Unknown"),
                "query_category": context.get("query_category", "general"),
            }
            
            # Create AI request for answer generation
            request = AIRequest(
                capability=ModelCapability.TEXT_GENERATION,
                input_data=variables,
                model_preference=model_preference,
                context=context
            )
            
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Extract answer
            if isinstance(response.content, dict):
                answer_data = response.content
                answer = answer_data.get("answer", str(response.content))
            else:
                answer = str(response.content)
            
            # Prepare sources
            sources = []
            for citation in retrieval_result.citations:
                source = {
                    "title": citation["title"],
                    "source": citation["source"],
                    "category": citation["category"],
                    "similarity_score": citation["similarity_score"],
                    "reference": citation["reference"]
                }
                sources.append(source)
            
            return RAGResponse(
                answer=answer,
                sources=sources,
                confidence=response.confidence,
                retrieval_metadata=retrieval_result.metadata,
                generation_metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                }
            )
            
        except Exception as e:
            logger.error(f"Answer generation failed: {str(e)}")
            raise AIServiceError(f"Answer generation failed: {str(e)}")
    
    async def ask_question(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        category_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
        model_preference: Optional[str] = None
    ) -> RAGResponse:
        """Ask a question and get an answer using RAG."""
        try:
            # Retrieve relevant knowledge
            retrieval_result = await self.retrieve_knowledge(
                query=question,
                context=context,
                category_filter=category_filter,
                source_filter=source_filter,
                tags_filter=tags_filter
            )
            
            # Generate answer
            answer = await self.generate_answer(
                query=question,
                retrieval_result=retrieval_result,
                context=context,
                model_preference=model_preference
            )
            
            logger.info(f"Generated answer for question: {question[:50]}...")
            
            return answer
            
        except Exception as e:
            logger.error(f"Question answering failed: {str(e)}")
            raise AIServiceError(f"Question answering failed: {str(e)}")
    
    async def ask_batch_questions(
        self,
        questions: List[str],
        context: Optional[Dict[str, Any]] = None,
        category_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        tags_filter: Optional[List[str]] = None,
        model_preference: Optional[str] = None
    ) -> List[RAGResponse]:
        """Ask multiple questions and get answers."""
        responses = []
        
        for question in questions:
            try:
                response = await self.ask_question(
                    question=question,
                    context=context,
                    category_filter=category_filter,
                    source_filter=source_filter,
                    tags_filter=tags_filter,
                    model_preference=model_preference
                )
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to answer question: {question[:50]}... Error: {str(e)}")
                # Add error response
                error_response = RAGResponse(
                    answer=f"Sorry, I couldn't answer that question: {str(e)}",
                    sources=[],
                    confidence=0.0,
                    retrieval_metadata={"error": str(e)},
                    generation_metadata={"error": str(e)}
                )
                responses.append(error_response)
        
        return responses
    
    def get_answer_quality_score(self, response: RAGResponse) -> float:
        """Calculate quality score for an answer."""
        score = 0.0
        
        # Base score from confidence
        score += response.confidence * 0.4
        
        # Boost score for multiple sources
        if len(response.sources) > 1:
            score += 0.2
        
        # Boost score for high-quality sources
        if response.sources:
            avg_source_score = sum(s["similarity_score"] for s in response.sources) / len(response.sources)
            score += avg_source_score * 0.3
        
        # Boost score for longer answers (more comprehensive)
        if len(response.answer) > 100:
            score += 0.1
        
        return min(1.0, score)
    
    def get_answer_insights(self, response: RAGResponse) -> List[str]:
        """Get insights about the answer quality."""
        insights = []
        
        if response.confidence < 0.7:
            insights.append("Low confidence in answer - consider human review")
        
        if len(response.sources) == 0:
            insights.append("No sources found - answer may be incomplete")
        elif len(response.sources) == 1:
            insights.append("Single source - consider additional verification")
        else:
            insights.append(f"Multiple sources ({len(response.sources)}) - good coverage")
        
        if response.sources:
            avg_source_score = sum(s["similarity_score"] for s in response.sources) / len(response.sources)
            if avg_source_score < 0.7:
                insights.append("Low source relevance - may need better search terms")
        
        if len(response.answer) < 50:
            insights.append("Short answer - may need more detail")
        elif len(response.answer) > 1000:
            insights.append("Long answer - may need summarization")
        
        return insights
    
    async def get_knowledge_summary(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        max_sources: int = 10
    ) -> Dict[str, Any]:
        """Get a summary of knowledge on a specific topic."""
        try:
            # Retrieve relevant knowledge
            retrieval_result = await self.retrieve_knowledge(
                query=topic,
                context=context,
                max_results=max_sources
            )
            
            # Group by source
            sources = {}
            for doc in retrieval_result.relevant_documents:
                source = doc.metadata.get("source", "Unknown")
                if source not in sources:
                    sources[source] = []
                sources[source].append(doc)
            
            # Calculate statistics
            total_documents = len(retrieval_result.relevant_documents)
            unique_sources = len(sources)
            avg_similarity = sum(doc.score for doc in retrieval_result.relevant_documents) / total_documents if total_documents > 0 else 0
            
            return {
                "topic": topic,
                "total_documents": total_documents,
                "unique_sources": unique_sources,
                "average_similarity": avg_similarity,
                "sources": {
                    source: {
                        "document_count": len(docs),
                        "average_similarity": sum(doc.score for doc in docs) / len(docs),
                        "categories": list(set(doc.metadata.get("category", "general") for doc in docs))
                    }
                    for source, docs in sources.items()
                },
                "citations": retrieval_result.citations,
                "confidence": retrieval_result.confidence
            }
            
        except Exception as e:
            logger.error(f"Knowledge summary failed: {str(e)}")
            raise AIServiceError(f"Knowledge summary failed: {str(e)}")
    
    async def suggest_related_questions(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        max_suggestions: int = 5
    ) -> List[str]:
        """Suggest related questions based on the current question."""
        try:
            # Retrieve relevant knowledge
            retrieval_result = await self.retrieve_knowledge(
                query=question,
                context=context,
                max_results=5
            )
            
            # Extract topics from retrieved documents
            topics = set()
            for doc in retrieval_result.relevant_documents:
                if "tags" in doc.metadata:
                    topics.update(doc.metadata["tags"])
                if "category" in doc.metadata:
                    topics.add(doc.metadata["category"])
            
            # Generate related questions (simplified)
            related_questions = []
            for topic in list(topics)[:max_suggestions]:
                related_questions.append(f"What is {topic}?")
                related_questions.append(f"How does {topic} work?")
                related_questions.append(f"What are the benefits of {topic}?")
            
            return related_questions[:max_suggestions]
            
        except Exception as e:
            logger.error(f"Related questions suggestion failed: {str(e)}")
            return []
