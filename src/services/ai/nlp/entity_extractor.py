"""Entity extraction service for customer service AI."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.core.exceptions import AIServiceError
from src.core.logging import get_logger
from src.services.ai.models import AIModel, ModelCapability
from src.services.ai.orchestrator import AIOrchestrator, AIRequest, AIResponse
from src.services.ai.llm.prompt_manager import PromptManager, PromptCategory

logger = get_logger(__name__)


@dataclass
class Entity:
    """An extracted entity."""
    text: str
    type: str
    start: int
    end: int
    confidence: float
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""
    entities: List[Entity]
    confidence: float
    metadata: Dict[str, Any]


class EntityExtractor:
    """Service for extracting entities from customer text using AI models."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        prompt_manager: PromptManager,
        default_entity_types: Optional[List[str]] = None
    ):
        self.orchestrator = orchestrator
        self.prompt_manager = prompt_manager
        self.default_entity_types = default_entity_types or [
            "person_name",
            "email",
            "phone_number",
            "account_id",
            "order_number",
            "product_name",
            "version_number",
            "error_code",
            "url",
            "date",
            "time",
            "currency",
            "location",
            "company_name",
            "department",
            "ticket_number",
            "case_id",
            "user_id",
            "organization",
            "other"
        ]
    
    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> EntityExtractionResult:
        """Extract entities from customer text."""
        entity_types = entity_types or self.default_entity_types
        context = context or {}
        
        # Prepare variables for prompt template
        variables = {
            "entity_types": ", ".join(entity_types),
            "text": text,
            "context": context.get("context", ""),
            "domain": context.get("domain", "customer_service"),
        }
        
        # Render the entity extraction prompt
        try:
            prompt = self.prompt_manager.render_template(
                "entity_extraction",
                variables,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed to render entity extraction prompt: {e}")
            # Fallback to simple prompt
            prompt = f"""Extract entities from this text: "{text}"

Entity types to extract: {", ".join(entity_types)}

Return JSON with entities, confidence, and reasoning."""
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.ENTITY_EXTRACTION,
            input_data=prompt,
            model_preference=model_preference,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Parse the response
            if isinstance(response.content, dict):
                entity_data = response.content
            else:
                # Try to parse JSON response
                try:
                    entity_data = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse entity extraction response: {response.content}")
                    raise AIServiceError("Invalid entity extraction response format")
            
            # Extract entities
            entities_list = entity_data.get("entities", [])
            entities = []
            
            for entity_dict in entities_list:
                entity = Entity(
                    text=entity_dict.get("text", ""),
                    type=entity_dict.get("type", "other"),
                    start=entity_dict.get("start", 0),
                    end=entity_dict.get("end", 0),
                    confidence=float(entity_dict.get("confidence", 0.0)),
                    metadata=entity_dict.get("metadata", {})
                )
                entities.append(entity)
            
            # Overall confidence
            confidence = float(entity_data.get("confidence", 0.0))
            
            return EntityExtractionResult(
                entities=entities,
                confidence=confidence,
                metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                    "total_entities": len(entities),
                }
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise AIServiceError(f"Entity extraction failed: {str(e)}")
    
    async def extract_batch(
        self,
        texts: List[str],
        entity_types: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> List[EntityExtractionResult]:
        """Extract entities from multiple texts."""
        results = []
        
        for text in texts:
            try:
                result = await self.extract_entities(
                    text, entity_types, context, model_preference
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract entities from text: {text[:50]}... Error: {str(e)}")
                # Add fallback result
                results.append(EntityExtractionResult(
                    entities=[],
                    confidence=0.0,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def filter_entities_by_type(
        self,
        result: EntityExtractionResult,
        entity_types: List[str]
    ) -> EntityExtractionResult:
        """Filter entities by type."""
        filtered_entities = [
            entity for entity in result.entities
            if entity.type in entity_types
        ]
        
        return EntityExtractionResult(
            entities=filtered_entities,
            confidence=result.confidence,
            metadata=result.metadata
        )
    
    def filter_entities_by_confidence(
        self,
        result: EntityExtractionResult,
        min_confidence: float = 0.5
    ) -> EntityExtractionResult:
        """Filter entities by confidence threshold."""
        filtered_entities = [
            entity for entity in result.entities
            if entity.confidence >= min_confidence
        ]
        
        return EntityExtractionResult(
            entities=filtered_entities,
            confidence=result.confidence,
            metadata=result.metadata
        )
    
    def get_entities_by_type(
        self,
        result: EntityExtractionResult,
        entity_type: str
    ) -> List[Entity]:
        """Get entities of a specific type."""
        return [entity for entity in result.entities if entity.type == entity_type]
    
    def validate_entities(self, result: EntityExtractionResult, original_text: str) -> EntityExtractionResult:
        """Validate extracted entities against original text."""
        validated_entities = []
        
        for entity in result.entities:
            # Check if entity text matches the substring in original text
            if entity.start < len(original_text) and entity.end <= len(original_text):
                extracted_text = original_text[entity.start:entity.end]
                if extracted_text.lower() == entity.text.lower():
                    validated_entities.append(entity)
                else:
                    logger.warning(f"Entity text mismatch: '{entity.text}' vs '{extracted_text}'")
            else:
                logger.warning(f"Entity position out of bounds: {entity.start}-{entity.end} for text length {len(original_text)}")
        
        return EntityExtractionResult(
            entities=validated_entities,
            confidence=result.confidence,
            metadata=result.metadata
        )
    
    def extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """Extract contact information using regex patterns."""
        contact_info = {
            "emails": [],
            "phone_numbers": [],
            "urls": [],
        }
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        contact_info["emails"] = list(set(emails))
        
        # Phone number pattern (various formats)
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phones = re.findall(phone_pattern, text)
        contact_info["phone_numbers"] = [''.join(phone) for phone in phones]
        
        # URL pattern
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, text)
        contact_info["urls"] = list(set(urls))
        
        return contact_info
    
    def analyze_entity_patterns(
        self,
        results: List[EntityExtractionResult],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze patterns in entity extraction results."""
        if not results:
            return {}
        
        # Count entity types
        entity_type_counts = {}
        entity_confidence_scores = {}
        total_entities = 0
        
        for result in results:
            total_entities += len(result.entities)
            
            for entity in result.entities:
                entity_type = entity.type
                entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
                
                if entity_type not in entity_confidence_scores:
                    entity_confidence_scores[entity_type] = []
                entity_confidence_scores[entity_type].append(entity.confidence)
        
        # Calculate statistics
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        # Most common entity types
        sorted_entity_types = sorted(entity_type_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Average confidence by entity type
        avg_confidence_by_type = {}
        for entity_type, scores in entity_confidence_scores.items():
            avg_confidence_by_type[entity_type] = sum(scores) / len(scores)
        
        return {
            "total_extractions": len(results),
            "total_entities": total_entities,
            "time_window_hours": time_window_hours,
            "average_confidence": avg_confidence,
            "entity_type_distribution": dict(sorted_entity_types),
            "average_confidence_by_type": avg_confidence_by_type,
            "most_common_entity_type": sorted_entity_types[0][0] if sorted_entity_types else None,
            "low_confidence_count": sum(1 for r in results if r.confidence < 0.6),
        }
