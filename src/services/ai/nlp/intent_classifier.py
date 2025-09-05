"""Intent classification service for customer service AI."""

from __future__ import annotations

import json
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
class IntentResult:
    """Result of intent classification."""
    intent: str
    confidence: float
    reasoning: str
    alternative_intents: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class IntentClassifier:
    """Service for classifying customer intents using AI models."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        prompt_manager: PromptManager,
        default_intents: Optional[List[str]] = None
    ):
        self.orchestrator = orchestrator
        self.prompt_manager = prompt_manager
        self.default_intents = default_intents or [
            "general_inquiry",
            "technical_support",
            "billing_inquiry",
            "feature_request",
            "bug_report",
            "account_management",
            "product_information",
            "complaint",
            "compliment",
            "escalation_request",
            "sales_inquiry",
            "integration_help",
            "training_request",
            "documentation_request",
            "other"
        ]
    
    async def classify_intent(
        self,
        text: str,
        available_intents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> IntentResult:
        """Classify the intent of customer text."""
        intents = available_intents or self.default_intents
        context = context or {}
        
        # Prepare variables for prompt template
        variables = {
            "available_intents": ", ".join(intents),
            "customer_message": text,
            "customer_tier": context.get("customer_tier", "basic"),
            "previous_intents": context.get("previous_intents", ""),
            "channel": context.get("channel", "web"),
        }
        
        # Render the intent classification prompt
        try:
            prompt = self.prompt_manager.render_template(
                "intent_classification",
                variables,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed to render intent classification prompt: {e}")
            # Fallback to simple prompt
            prompt = f"""Classify the intent of this customer message: "{text}"

Available intents: {", ".join(intents)}

Return JSON with intent, confidence, and reasoning."""
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.INTENT_CLASSIFICATION,
            input_data=prompt,
            model_preference=model_preference,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Parse the response
            if isinstance(response.content, dict):
                intent_data = response.content
            else:
                # Try to parse JSON response
                try:
                    intent_data = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse intent classification response: {response.content}")
                    raise AIServiceError("Invalid intent classification response format")
            
            # Extract intent information
            intent = intent_data.get("intent", "other")
            confidence = float(intent_data.get("confidence", 0.0))
            reasoning = intent_data.get("reasoning", "")
            alternative_intents = intent_data.get("alternative_intents", [])
            
            # Validate intent is in available list
            if intent not in intents:
                logger.warning(f"Classified intent '{intent}' not in available intents, using 'other'")
                intent = "other"
                confidence = min(confidence, 0.5)  # Reduce confidence for fallback
            
            return IntentResult(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                alternative_intents=alternative_intents,
                metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                }
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            raise AIServiceError(f"Intent classification failed: {str(e)}")
    
    async def classify_batch(
        self,
        texts: List[str],
        available_intents: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> List[IntentResult]:
        """Classify intents for multiple texts."""
        results = []
        
        for text in texts:
            try:
                result = await self.classify_intent(
                    text, available_intents, context, model_preference
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to classify intent for text: {text[:50]}... Error: {str(e)}")
                # Add fallback result
                results.append(IntentResult(
                    intent="other",
                    confidence=0.0,
                    reasoning=f"Classification failed: {str(e)}",
                    alternative_intents=[],
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_intent_confidence_threshold(self, intent: str) -> float:
        """Get confidence threshold for specific intent."""
        # Different intents may require different confidence thresholds
        thresholds = {
            "escalation_request": 0.8,  # High confidence required for escalations
            "complaint": 0.7,           # Medium-high for complaints
            "billing_inquiry": 0.6,     # Medium for billing
            "technical_support": 0.6,   # Medium for technical support
            "general_inquiry": 0.5,     # Lower for general inquiries
            "other": 0.3,               # Very low for catch-all
        }
        return thresholds.get(intent, 0.6)  # Default threshold
    
    def should_escalate(self, intent_result: IntentResult) -> bool:
        """Determine if intent requires escalation."""
        high_priority_intents = [
            "escalation_request",
            "complaint",
            "billing_inquiry",
            "bug_report"
        ]
        
        return (
            intent_result.intent in high_priority_intents and
            intent_result.confidence >= self.get_intent_confidence_threshold(intent_result.intent)
        )
    
    def get_intent_priority(self, intent: str) -> str:
        """Get priority level for intent."""
        priority_map = {
            "escalation_request": "urgent",
            "complaint": "high",
            "billing_inquiry": "high",
            "bug_report": "high",
            "technical_support": "medium",
            "feature_request": "medium",
            "account_management": "medium",
            "sales_inquiry": "medium",
            "general_inquiry": "low",
            "product_information": "low",
            "documentation_request": "low",
            "training_request": "low",
            "compliment": "low",
            "other": "low",
        }
        return priority_map.get(intent, "medium")
    
    def get_suggested_actions(self, intent_result: IntentResult) -> List[str]:
        """Get suggested actions based on classified intent."""
        action_map = {
            "escalation_request": ["escalate_to_human", "create_case", "notify_manager"],
            "complaint": ["acknowledge_concern", "investigate_issue", "escalate_to_manager"],
            "billing_inquiry": ["check_account", "provide_billing_info", "escalate_to_billing"],
            "technical_support": ["gather_technical_details", "search_knowledge_base", "escalate_to_technical"],
            "bug_report": ["gather_bug_details", "create_bug_ticket", "escalate_to_development"],
            "feature_request": ["acknowledge_request", "log_feature_request", "escalate_to_product"],
            "account_management": ["verify_identity", "check_permissions", "provide_account_info"],
            "sales_inquiry": ["gather_requirements", "schedule_demo", "escalate_to_sales"],
            "general_inquiry": ["provide_general_info", "search_knowledge_base"],
            "product_information": ["provide_product_info", "share_documentation"],
            "documentation_request": ["share_documentation", "provide_links"],
            "training_request": ["schedule_training", "provide_training_materials"],
            "compliment": ["acknowledge_compliment", "share_with_team"],
            "other": ["ask_for_clarification", "escalate_to_human"],
        }
        return action_map.get(intent_result.intent, ["ask_for_clarification"])
    
    def analyze_intent_patterns(
        self,
        intent_results: List[IntentResult],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze patterns in intent classification results."""
        if not intent_results:
            return {}
        
        # Count intents
        intent_counts = {}
        confidence_scores = {}
        
        for result in intent_results:
            intent = result.intent
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            if intent not in confidence_scores:
                confidence_scores[intent] = []
            confidence_scores[intent].append(result.confidence)
        
        # Calculate statistics
        total_classifications = len(intent_results)
        avg_confidence = sum(r.confidence for r in intent_results) / total_classifications
        
        # Most common intents
        sorted_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Average confidence by intent
        avg_confidence_by_intent = {}
        for intent, scores in confidence_scores.items():
            avg_confidence_by_intent[intent] = sum(scores) / len(scores)
        
        return {
            "total_classifications": total_classifications,
            "time_window_hours": time_window_hours,
            "average_confidence": avg_confidence,
            "intent_distribution": dict(sorted_intents),
            "average_confidence_by_intent": avg_confidence_by_intent,
            "most_common_intent": sorted_intents[0][0] if sorted_intents else None,
            "low_confidence_count": sum(1 for r in intent_results if r.confidence < 0.6),
        }
