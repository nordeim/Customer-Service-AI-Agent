"""Sentiment analysis service for customer service AI."""

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
class SentimentResult:
    """Result of sentiment analysis."""
    sentiment: str  # positive, negative, neutral
    score: float    # -1.0 to 1.0
    confidence: float
    emotions: List[str]
    reasoning: str
    escalation_recommended: bool
    metadata: Dict[str, Any]


class SentimentAnalyzer:
    """Service for analyzing sentiment of customer text using AI models."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        prompt_manager: PromptManager
    ):
        self.orchestrator = orchestrator
        self.prompt_manager = prompt_manager
        self.sentiment_thresholds = {
            "positive": 0.1,
            "negative": -0.1,
            "neutral": 0.0
        }
    
    async def analyze_sentiment(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> SentimentResult:
        """Analyze sentiment of customer text."""
        context = context or {}
        
        # Prepare variables for prompt template
        variables = {
            "customer_message": text,
            "customer_tier": context.get("customer_tier", "basic"),
            "issue_category": context.get("issue_category", "general"),
            "previous_sentiment": context.get("previous_sentiment", "neutral"),
            "channel": context.get("channel", "web"),
        }
        
        # Render the sentiment analysis prompt
        try:
            prompt = self.prompt_manager.render_template(
                "sentiment_analysis",
                variables,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed to render sentiment analysis prompt: {e}")
            # Fallback to simple prompt
            prompt = f"""Analyze the sentiment of this customer message: "{text}"

Return JSON with sentiment, score, confidence, emotions, reasoning, and escalation recommendation."""
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.SENTIMENT_ANALYSIS,
            input_data=prompt,
            model_preference=model_preference,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Parse the response
            if isinstance(response.content, dict):
                sentiment_data = response.content
            else:
                # Try to parse JSON response
                try:
                    sentiment_data = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse sentiment analysis response: {response.content}")
                    raise AIServiceError("Invalid sentiment analysis response format")
            
            # Extract sentiment information
            sentiment = sentiment_data.get("sentiment", "neutral").lower()
            score = float(sentiment_data.get("score", 0.0))
            confidence = float(sentiment_data.get("confidence", 0.0))
            emotions = sentiment_data.get("emotions", [])
            reasoning = sentiment_data.get("reasoning", "")
            escalation_recommended = sentiment_data.get("escalation_recommended", False)
            
            # Validate sentiment
            if sentiment not in ["positive", "negative", "neutral"]:
                logger.warning(f"Invalid sentiment '{sentiment}', defaulting to 'neutral'")
                sentiment = "neutral"
            
            # Ensure score is within valid range
            score = max(-1.0, min(1.0, score))
            
            return SentimentResult(
                sentiment=sentiment,
                score=score,
                confidence=confidence,
                emotions=emotions,
                reasoning=reasoning,
                escalation_recommended=escalation_recommended,
                metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                }
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            raise AIServiceError(f"Sentiment analysis failed: {str(e)}")
    
    async def analyze_batch(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> List[SentimentResult]:
        """Analyze sentiment for multiple texts."""
        results = []
        
        for text in texts:
            try:
                result = await self.analyze_sentiment(
                    text, context, model_preference
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze sentiment for text: {text[:50]}... Error: {str(e)}")
                # Add fallback result
                results.append(SentimentResult(
                    sentiment="neutral",
                    score=0.0,
                    confidence=0.0,
                    emotions=[],
                    reasoning=f"Analysis failed: {str(e)}",
                    escalation_recommended=False,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_sentiment_label(self, score: float) -> str:
        """Get sentiment label from score."""
        if score >= self.sentiment_thresholds["positive"]:
            return "positive"
        elif score <= self.sentiment_thresholds["negative"]:
            return "negative"
        else:
            return "neutral"
    
    def should_escalate(self, result: SentimentResult) -> bool:
        """Determine if sentiment requires escalation."""
        return (
            result.escalation_recommended or
            (result.sentiment == "negative" and result.confidence > 0.7) or
            (result.score < -0.5 and result.confidence > 0.8)
        )
    
    def get_sentiment_priority(self, result: SentimentResult) -> str:
        """Get priority level based on sentiment."""
        if result.sentiment == "negative" and result.confidence > 0.8:
            return "high"
        elif result.sentiment == "negative" and result.confidence > 0.6:
            return "medium"
        elif result.sentiment == "positive" and result.confidence > 0.8:
            return "low"
        else:
            return "medium"
    
    def get_sentiment_trend(
        self,
        results: List[SentimentResult],
        window_size: int = 5
    ) -> Dict[str, Any]:
        """Analyze sentiment trend over time."""
        if len(results) < 2:
            return {"trend": "insufficient_data", "direction": "stable"}
        
        # Get recent results
        recent_results = results[-window_size:] if len(results) > window_size else results
        
        # Calculate trend
        scores = [r.score for r in recent_results]
        avg_score = sum(scores) / len(scores)
        
        # Simple trend calculation
        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg > first_avg + 0.1:
                trend = "improving"
                direction = "up"
            elif second_avg < first_avg - 0.1:
                trend = "declining"
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
            "average_score": avg_score,
            "window_size": len(recent_results),
            "recent_scores": scores,
        }
    
    def analyze_sentiment_patterns(
        self,
        results: List[SentimentResult],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze patterns in sentiment analysis results."""
        if not results:
            return {}
        
        # Count sentiments
        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        confidence_scores = []
        escalation_recommendations = 0
        
        for result in results:
            sentiment_counts[result.sentiment] += 1
            confidence_scores.append(result.confidence)
            if result.escalation_recommended:
                escalation_recommendations += 1
        
        # Calculate statistics
        total_analyses = len(results)
        avg_confidence = sum(confidence_scores) / total_analyses
        avg_score = sum(r.score for r in results) / total_analyses
        
        # Sentiment distribution
        sentiment_distribution = {
            sentiment: count / total_analyses
            for sentiment, count in sentiment_counts.items()
        }
        
        # Most common emotions
        emotion_counts = {}
        for result in results:
            for emotion in result.emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_analyses": total_analyses,
            "time_window_hours": time_window_hours,
            "average_confidence": avg_confidence,
            "average_score": avg_score,
            "sentiment_distribution": sentiment_distribution,
            "escalation_recommendations": escalation_recommendations,
            "escalation_rate": escalation_recommendations / total_analyses,
            "most_common_emotions": dict(sorted_emotions[:5]),  # Top 5 emotions
            "low_confidence_count": sum(1 for c in confidence_scores if c < 0.6),
        }
    
    def get_sentiment_insights(self, result: SentimentResult) -> List[str]:
        """Get insights and recommendations based on sentiment analysis."""
        insights = []
        
        if result.sentiment == "negative" and result.confidence > 0.8:
            insights.append("Customer is clearly dissatisfied and needs immediate attention")
            insights.append("Consider offering compensation or expedited resolution")
        
        elif result.sentiment == "negative" and result.confidence > 0.6:
            insights.append("Customer shows signs of frustration")
            insights.append("Monitor conversation closely for escalation triggers")
        
        elif result.sentiment == "positive" and result.confidence > 0.8:
            insights.append("Customer is satisfied with the service")
            insights.append("Consider asking for feedback or testimonial")
        
        if result.escalation_recommended:
            insights.append("AI recommends escalation to human agent")
        
        if "frustration" in result.emotions or "anger" in result.emotions:
            insights.append("Customer shows emotional distress")
            insights.append("Use empathetic language and acknowledge their feelings")
        
        if result.confidence < 0.6:
            insights.append("Low confidence in sentiment analysis")
            insights.append("Consider human review or additional context")
        
        return insights
