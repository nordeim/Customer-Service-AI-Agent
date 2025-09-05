"""Language detection service for customer service AI."""

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
class LanguageResult:
    """Result of language detection."""
    language: str
    language_code: str
    confidence: float
    reasoning: str
    alternative_languages: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class LanguageDetector:
    """Service for detecting language of customer text using AI models."""
    
    def __init__(
        self,
        orchestrator: AIOrchestrator,
        prompt_manager: PromptManager
    ):
        self.orchestrator = orchestrator
        self.prompt_manager = prompt_manager
        self.supported_languages = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "nl": "Dutch",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "pl": "Polish",
            "tr": "Turkish",
            "th": "Thai",
            "vi": "Vietnamese",
            "id": "Indonesian",
            "ms": "Malay",
            "tl": "Filipino",
            "he": "Hebrew",
            "uk": "Ukrainian",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "mt": "Maltese",
            "ga": "Irish",
            "cy": "Welsh",
            "eu": "Basque",
            "ca": "Catalan",
            "gl": "Galician",
        }
    
    async def detect_language(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> LanguageResult:
        """Detect language of customer text."""
        context = context or {}
        
        # Prepare variables for prompt template
        variables = {
            "customer_message": text,
            "customer_tier": context.get("customer_tier", "basic"),
            "organization": context.get("organization", "unknown"),
            "channel": context.get("channel", "web"),
        }
        
        # Render the language detection prompt
        try:
            prompt = self.prompt_manager.render_template(
                "language_detection",
                variables,
                strict=False
            )
        except Exception as e:
            logger.warning(f"Failed to render language detection prompt: {e}")
            # Fallback to simple prompt
            prompt = f"""Detect the language of this customer message: "{text}"

Return JSON with language, language_code, confidence, reasoning, and alternative languages."""
        
        # Create AI request
        request = AIRequest(
            capability=ModelCapability.LANGUAGE_DETECTION,
            input_data=prompt,
            model_preference=model_preference,
            context=context
        )
        
        try:
            # Get AI response
            response = await self.orchestrator.process_request(request)
            
            # Parse the response
            if isinstance(response.content, dict):
                language_data = response.content
            else:
                # Try to parse JSON response
                try:
                    language_data = json.loads(response.content)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse language detection response: {response.content}")
                    raise AIServiceError("Invalid language detection response format")
            
            # Extract language information
            language_code = language_data.get("language", "en").lower()
            confidence = float(language_data.get("confidence", 0.0))
            reasoning = language_data.get("reasoning", "")
            alternative_languages = language_data.get("alternative_languages", [])
            
            # Validate language code
            if language_code not in self.supported_languages:
                logger.warning(f"Unsupported language code '{language_code}', defaulting to 'en'")
                language_code = "en"
            
            language = self.supported_languages[language_code]
            
            return LanguageResult(
                language=language,
                language_code=language_code,
                confidence=confidence,
                reasoning=reasoning,
                alternative_languages=alternative_languages,
                metadata={
                    "model_used": response.model_used,
                    "processing_time": response.processing_time,
                    "token_usage": response.token_usage.total_tokens,
                    "fallback_used": response.fallback_used,
                }
            )
            
        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            raise AIServiceError(f"Language detection failed: {str(e)}")
    
    async def detect_batch(
        self,
        texts: List[str],
        context: Optional[Dict[str, Any]] = None,
        model_preference: Optional[str] = None
    ) -> List[LanguageResult]:
        """Detect language for multiple texts."""
        results = []
        
        for text in texts:
            try:
                result = await self.detect_language(
                    text, context, model_preference
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to detect language for text: {text[:50]}... Error: {str(e)}")
                # Add fallback result
                results.append(LanguageResult(
                    language="English",
                    language_code="en",
                    confidence=0.0,
                    reasoning=f"Detection failed: {str(e)}",
                    alternative_languages=[],
                    metadata={"error": str(e)}
                ))
        
        return results
    
    def get_language_name(self, language_code: str) -> str:
        """Get full language name from code."""
        return self.supported_languages.get(language_code.lower(), "Unknown")
    
    def get_language_code(self, language_name: str) -> Optional[str]:
        """Get language code from name."""
        for code, name in self.supported_languages.items():
            if name.lower() == language_name.lower():
                return code
        return None
    
    def is_supported_language(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code.lower() in self.supported_languages
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get all supported languages."""
        return self.supported_languages.copy()
    
    def should_escalate(self, result: LanguageResult) -> bool:
        """Determine if language detection requires escalation."""
        # Escalate if confidence is low or if it's a non-English language
        return (
            result.confidence < 0.7 or
            (result.language_code != "en" and result.confidence < 0.8)
        )
    
    def get_language_priority(self, result: LanguageResult) -> str:
        """Get priority level based on language detection."""
        if result.language_code != "en" and result.confidence > 0.8:
            return "high"  # Non-English languages need special handling
        elif result.confidence < 0.6:
            return "medium"  # Low confidence needs review
        else:
            return "low"  # Standard English, high confidence
    
    def get_language_insights(self, result: LanguageResult) -> List[str]:
        """Get insights and recommendations based on language detection."""
        insights = []
        
        if result.language_code != "en":
            insights.append(f"Customer is communicating in {result.language}")
            insights.append("Consider providing multilingual support")
            insights.append("May need translation services")
        
        if result.confidence < 0.7:
            insights.append("Low confidence in language detection")
            insights.append("Consider human review or additional context")
        
        if result.confidence < 0.5:
            insights.append("Very low confidence - language may be mixed or unclear")
            insights.append("Ask customer to clarify their preferred language")
        
        if result.alternative_languages:
            insights.append("Multiple language possibilities detected")
            insights.append("Consider asking customer to specify their language")
        
        return insights
    
    def get_language_response_strategy(self, result: LanguageResult) -> Dict[str, Any]:
        """Get response strategy based on detected language."""
        strategy = {
            "language": result.language_code,
            "use_translation": False,
            "escalation_needed": False,
            "special_considerations": []
        }
        
        if result.language_code != "en":
            strategy.update({
                "use_translation": True,
                "escalation_needed": result.confidence < 0.8,
                "special_considerations": [
                    "provide_multilingual_support",
                    "use_simple_english_if_no_translation",
                    "acknowledge_language_preference"
                ]
            })
        
        if result.confidence < 0.7:
            strategy.update({
                "escalation_needed": True,
                "special_considerations": [
                    "ask_for_language_clarification",
                    "use_simple_english",
                    "offer_translation_services"
                ]
            })
        
        return strategy
    
    def analyze_language_patterns(
        self,
        results: List[LanguageResult],
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze patterns in language detection results."""
        if not results:
            return {}
        
        # Count languages
        language_counts = {}
        confidence_scores = []
        non_english_count = 0
        
        for result in results:
            language_counts[result.language_code] = language_counts.get(result.language_code, 0) + 1
            confidence_scores.append(result.confidence)
            if result.language_code != "en":
                non_english_count += 1
        
        # Calculate statistics
        total_detections = len(results)
        avg_confidence = sum(confidence_scores) / total_detections
        
        # Language distribution
        language_distribution = {
            language: count / total_detections
            for language, count in language_counts.items()
        }
        
        # Most common languages
        sorted_languages = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Low confidence detections
        low_confidence_count = sum(1 for c in confidence_scores if c < 0.7)
        
        return {
            "total_detections": total_detections,
            "time_window_hours": time_window_hours,
            "average_confidence": avg_confidence,
            "language_distribution": language_distribution,
            "most_common_languages": dict(sorted_languages[:5]),  # Top 5 languages
            "non_english_count": non_english_count,
            "non_english_rate": non_english_count / total_detections,
            "low_confidence_count": low_confidence_count,
            "low_confidence_rate": low_confidence_count / total_detections,
        }
    
    def get_multilingual_support_recommendations(
        self,
        results: List[LanguageResult]
    ) -> Dict[str, Any]:
        """Get recommendations for multilingual support based on language patterns."""
        if not results:
            return {"recommendations": [], "priority_languages": []}
        
        # Analyze language distribution
        language_counts = {}
        for result in results:
            language_counts[result.language_code] = language_counts.get(result.language_code, 0) + 1
        
        total_detections = len(results)
        non_english_languages = {
            lang: count for lang, count in language_counts.items()
            if lang != "en" and count > 0
        }
        
        # Calculate percentages
        language_percentages = {
            lang: (count / total_detections) * 100
            for lang, count in language_counts.items()
        }
        
        # Generate recommendations
        recommendations = []
        priority_languages = []
        
        for lang, percentage in language_percentages.items():
            if lang != "en" and percentage >= 5:  # 5% threshold
                priority_languages.append(lang)
                recommendations.append(f"Add support for {self.get_language_name(lang)} ({percentage:.1f}% of interactions)")
        
        if non_english_languages:
            recommendations.append("Consider implementing translation services")
            recommendations.append("Train support agents in multiple languages")
            recommendations.append("Create multilingual knowledge base")
        
        return {
            "recommendations": recommendations,
            "priority_languages": priority_languages,
            "language_percentages": language_percentages,
            "total_non_english": sum(non_english_languages.values()),
            "non_english_percentage": (sum(non_english_languages.values()) / total_detections) * 100,
        }
