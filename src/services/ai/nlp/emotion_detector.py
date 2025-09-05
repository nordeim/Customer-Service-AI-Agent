"""Emotion detection service for customer service AI."""

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
class EmotionResult:
    """Result of emotion detection."""
    primary_emotion: str
    intensity: float  # 0.0 to 1.0
    confidence: float
    all_emotions: Dict[str, float]  # emotion -> intensity
    reasoning: str
    metadata: Dict[str, Any]


class EmotionDetector:
    """Service for detecting emotions in customer text using AI models."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        prompt_manager: PromptManager
    ):
        self.orchestrator = orchestrator
        self.prompt_manager = prompt_manager
        self.emotion_categories = [
            "joy", "sadness", "anger", "fear", "surprise", "disgust", "neutral",
            "frustration", "anxiety", "excitement", "confusion", "satisfaction",
            "disappointment", "gratitude", "impatience", "relief", "concern"
        ]
    
    async def detect_emotion(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> EmotionResult:
        """Detect emotions in customer text."""
        context = context or {}
        
        # Prepare variables for prompt template
        variables = {
            "customer_message": text,
            "customer_tier": context.get("customer_tier", "basic"),
            "issue_category": context.get("issue_category", "general"),
            "previous_emotions": context.get("previous_emotions", ""),
            "channel": context.get("channel", "web"),
        }
        
        # Render the emotion detection prompt
        try:
            prompt = self.prompt_manager.render_template(
                "emotion_detection",
                variables,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed to render emotion detection prompt: {e}")
            # Fallback to simple prompt
            prompt = f"""Detect the primary emotion in this customer message: "{text}"

Return JSON with emotion, intensity, confidence, all_emotions, and reasoning."""
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.EMOTION_DETECTION,
            input_data=prompt,
            model_preference=model_preference,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Parse the response
            if isinstance(response.content, dict):
                emotion_data = response.content
            else:
                # Try to parse JSON response
                try:
                    emotion_data = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse emotion detection response: {response.content}")
                    raise AIServiceError("Invalid emotion detection response format")
            
            # Extract emotion information
            primary_emotion = emotion_data.get("emotion", "neutral").lower()
            intensity = float(emotion_data.get("intensity", 0.0))
            confidence = float(emotion_data.get("confidence", 0.0))
            all_emotions = emotion_data.get("all_emotions", {})
            reasoning = emotion_data.get("reasoning", "")
            
            # Validate primary emotion
            if primary_emotion not in self.emotion_categories:
                logger.warning(f"Invalid emotion '{primary_emotion}', defaulting to 'neutral'")
                primary_emotion = "neutral"
            
            # Ensure intensity is within valid range
            intensity = max(0.0, min(1.0, intensity))
            
            # Ensure all_emotions is a dict with float values
            if not isinstance(all_emotions, dict):
                all_emotions = {primary_emotion: intensity}
            else:
                # Validate and clean emotion intensities
                cleaned_emotions = {}
                for emotion, value in all_emotions.items():
                    try:
                        cleaned_emotions[emotion] = max(0.0, min(1.0, float(value)))
                    except (ValueError, TypeError):
                        continue
                all_emotions = cleaned_emotions
            
            return EmotionResult(
                primary_emotion=primary_emotion,
                intensity=intensity,
                confidence=confidence,
                all_emotions=all_emotions,
                reasoning=reasoning,
                metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                }
            )
            
        except Exception as e:
            logger.error(f"Emotion detection failed: {str(e)}")
            raise AIServiceError(f"Emotion detection failed: {str(e)}")
    
    async def detect_batch(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> List[EmotionResult]:
        """Detect emotions for multiple texts."""
        results = []
        
        for text in texts:
            try:
                result = await self.detect_emotion(
                    text, context, model_preference
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to detect emotion for text: {text[:50]}... Error: {str(e)}")
                # Add fallback result
                results.append(EmotionResult(
                    primary_emotion="neutral",
                    intensity=0.0,
                    confidence=0.0,
                    all_emotions={"neutral": 0.0},
                    reasoning=f"Detection failed: {str(e)}",
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_emotion_intensity_level(self, intensity: float) -> str:
        """Get intensity level description."""
        if intensity >= 0.8:
            return "very_high"
        elif intensity >= 0.6:
            return "high"
        elif intensity >= 0.4:
            return "medium"
        elif intensity >= 0.2:
            return "low"
        else:
            return "very_low"
    
    def should_escalate(self, result: EmotionResult) -> bool:
        """Determine if emotion requires escalation."""
        high_intensity_negative_emotions = ["anger", "frustration", "fear", "anxiety"]
        
        return (
            (result.primary_emotion in high_intensity_negative_emotions and result.intensity > 0.7) or
            (result.confidence > 0.8 and result.intensity > 0.8)
        )
    
    def get_emotion_priority(self, result: EmotionResult) -> str:
        """Get priority level based on emotion."""
        high_priority_emotions = ["anger", "frustration", "fear", "anxiety"]
        medium_priority_emotions = ["sadness", "disappointment", "confusion", "concern"]
        
        if result.primary_emotion in high_priority_emotions and result.intensity > 0.6:
            return "high"
        elif result.primary_emotion in medium_priority_emotions and result.intensity > 0.5:
            return "medium"
        elif result.primary_emotion in ["joy", "satisfaction", "gratitude"] and result.intensity > 0.6:
            return "low"
        else:
            return "medium"
    
    def get_emotion_trend(
        self,
        results: List[EmotionResult],
        window_size: int = 5
    ) -> Dict[str, Any]:
        """Analyze emotion trend over time."""
        if len(results) < 2:
            return {"trend": "insufficient_data", "direction": "stable"}
        
        # Get recent results
        recent_results = results[-window_size:] if len(results) > window_size else results
        
        # Calculate trend for primary emotion
        primary_emotions = [r.primary_emotion for r in recent_results]
        emotion_counts = {}
        for emotion in primary_emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Most common emotion in recent window
        most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # Calculate intensity trend
        intensities = [r.intensity for r in recent_results]
        avg_intensity = sum(intensities) / len(intensities)
        
        # Simple trend calculation
        if len(intensities) >= 2:
            first_half = intensities[:len(intensities)//2]
            second_half = intensities[len(intensities)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg > first_avg + 0.1:
                trend = "intensifying"
                direction = "up"
            elif second_avg < first_avg - 0.1:
                trend = "calming"
                direction = "down"
            else:
                trend = "stable"
                direction = "stable"
        else:
            trend = "stable"
            direction = "stable"
        
        return {
            "trend": trend,
            "direction": direction,
            "most_common_emotion": most_common_emotion,
            "average_intensity": avg_intensity,
            "window_size": len(recent_results),
            "recent_intensities": intensities,
        }
    
    def analyze_emotion_patterns(
        self,
        results: List[EmotionResult],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze patterns in emotion detection results."""
        if not results:
            return {}
        
        # Count emotions
        emotion_counts = {}
        intensity_scores = []
        confidence_scores = []
        
        for result in results:
            emotion_counts[result.primary_emotion] = emotion_counts.get(result.primary_emotion, 0) + 1
            intensity_scores.append(result.intensity)
            confidence_scores.append(result.confidence)
        
        # Calculate statistics
        total_detections = len(results)
        avg_intensity = sum(intensity_scores) / total_detections
        avg_confidence = sum(confidence_scores) / total_detections
        
        # Emotion distribution
        emotion_distribution = {
            emotion: count / total_detections
            for emotion, count in emotion_counts.items()
        }
        
        # Most common emotions
        sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
        
        # High intensity emotions
        high_intensity_count = sum(1 for intensity in intensity_scores if intensity > 0.7)
        
        return {
            "total_detections": total_detections,
            "time_window_hours": time_window_hours,
            "average_intensity": avg_intensity,
            "average_confidence": avg_confidence,
            "emotion_distribution": emotion_distribution,
            "most_common_emotions": dict(sorted_emotions[:5]),  # Top 5 emotions
            "high_intensity_count": high_intensity_count,
            "high_intensity_rate": high_intensity_count / total_detections,
            "low_confidence_count": sum(1 for c in confidence_scores if c < 0.6),
        }
    
    def get_emotion_insights(self, result: EmotionResult) -> List[str]:
        """Get insights and recommendations based on emotion detection."""
        insights = []
        
        if result.primary_emotion == "anger" and result.intensity > 0.7:
            insights.append("Customer is very angry and needs immediate de-escalation")
            insights.append("Use calming language and acknowledge their frustration")
            insights.append("Consider escalating to a senior agent")
        
        elif result.primary_emotion == "frustration" and result.intensity > 0.6:
            insights.append("Customer is frustrated with the current situation")
            insights.append("Focus on providing clear, actionable solutions")
            insights.append("Avoid technical jargon and be direct")
        
        elif result.primary_emotion == "fear" or result.primary_emotion == "anxiety":
            insights.append("Customer is experiencing fear or anxiety")
            insights.append("Provide reassurance and clear explanations")
            insights.append("Be patient and allow time for them to process information")
        
        elif result.primary_emotion == "confusion" and result.intensity > 0.5:
            insights.append("Customer is confused and needs clarification")
            insights.append("Break down complex information into simple steps")
            insights.append("Ask clarifying questions to understand their needs")
        
        elif result.primary_emotion == "joy" or result.primary_emotion == "satisfaction":
            insights.append("Customer is satisfied with the service")
            insights.append("Acknowledge their positive experience")
            insights.append("Consider asking for feedback or testimonial")
        
        if result.intensity > 0.8:
            insights.append("High emotional intensity detected")
            insights.append("Monitor conversation closely for escalation triggers")
        
        if result.confidence < 0.6:
            insights.append("Low confidence in emotion detection")
            insights.append("Consider human review or additional context")
        
        return insights
    
    def get_emotion_response_strategy(self, result: EmotionResult) -> Dict[str, Any]:
        """Get response strategy based on detected emotion."""
        strategy = {
            "tone": "professional",
            "approach": "standard",
            "urgency": "normal",
            "escalation_needed": False,
            "special_considerations": []
        }
        
        if result.primary_emotion == "anger" and result.intensity > 0.6:
            strategy.update({
                "tone": "empathetic",
                "approach": "de-escalation",
                "urgency": "high",
                "escalation_needed": True,
                "special_considerations": ["acknowledge_frustration", "offer_immediate_help"]
            })
        
        elif result.primary_emotion == "frustration" and result.intensity > 0.5:
            strategy.update({
                "tone": "understanding",
                "approach": "solution_focused",
                "urgency": "medium",
                "special_considerations": ["be_direct", "avoid_technical_jargon"]
            })
        
        elif result.primary_emotion in ["fear", "anxiety"]:
            strategy.update({
                "tone": "reassuring",
                "approach": "supportive",
                "urgency": "medium",
                "special_considerations": ["provide_reassurance", "be_patient"]
            })
        
        elif result.primary_emotion == "confusion":
            strategy.update({
                "tone": "clear",
                "approach": "educational",
                "urgency": "low",
                "special_considerations": ["simplify_language", "ask_clarifying_questions"]
            })
        
        elif result.primary_emotion in ["joy", "satisfaction"]:
            strategy.update({
                "tone": "positive",
                "approach": "appreciative",
                "urgency": "low",
                "special_considerations": ["acknowledge_satisfaction", "seek_feedback"]
            })
        
        return strategy
