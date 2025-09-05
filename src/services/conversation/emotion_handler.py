"""Emotion-aware response system with tone adaptation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from src.core.logging import get_logger
from src.services.conversation.context import ConversationContext

logger = get_logger(__name__)


class EmotionType(str, Enum):
    """Supported emotion types."""
    ANGRY = "angry"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    NEUTRAL = "neutral"
    SATISFIED = "satisfied"
    HAPPY = "happy"
    EXCITED = "excited"


class ToneType(str, Enum):
    """Response tone types."""
    EMPATHETIC = "empathetic"
    SUPPORTIVE = "supportive"
    CLEAR_GUIDANCE = "clear_guidance"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    ENTHUSIASTIC = "enthusiastic"
    PROFESSIONAL = "professional"
    APOLOGETIC = "apologetic"


@dataclass
class EmotionResponseStrategy:
    """Strategy for responding to specific emotions."""
    primary_emotion: EmotionType
    intensity_threshold: float
    response_tone: ToneType
    escalation_threshold: float
    empathy_markers: List[str] = field(default_factory=list)
    de_escalation_phrases: List[str] = field(default_factory=list)
    avoid_phrases: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    timeout_seconds: Optional[int] = None
    requires_human_review: bool = False


@dataclass
class ToneAdaptation:
    """Tone adaptation configuration."""
    original_text: str
    adapted_text: str
    tone_used: ToneType
    emotion_detected: EmotionType
    intensity: float
    confidence: float
    modifications_made: List[str] = field(default_factory=list)
    escalation_recommended: bool = False
    escalation_reason: Optional[str] = None


class EmotionResponseHandler:
    """Handles emotion-aware response adaptation."""
    
    # Emotion response strategies based on PRD v4 requirements
    EMOTION_STRATEGIES = {
        EmotionType.ANGRY: EmotionResponseStrategy(
            primary_emotion=EmotionType.ANGRY,
            intensity_threshold=0.6,
            response_tone=ToneType.EMPATHETIC,
            escalation_threshold=0.8,
            empathy_markers=[
                "I understand your frustration",
                "I can see why you're upset",
                "I apologize for the inconvenience",
                "Let me help resolve this for you"
            ],
            de_escalation_phrases=[
                "I completely understand your concern",
                "Let me take care of this right away",
                "I want to make sure we get this resolved",
                "Your satisfaction is our priority"
            ],
            avoid_phrases=[
                "Calm down",
                "That's not our fault",
                "You should have",
                "That's policy",
                "There's nothing I can do"
            ],
            recommended_actions=[
                "immediate_escalation",
                "senior_agent_review",
                "priority_handling"
            ],
            requires_human_review=True
        ),
        EmotionType.FRUSTRATED: EmotionResponseStrategy(
            primary_emotion=EmotionType.FRUSTRATED,
            intensity_threshold=0.5,
            response_tone=ToneType.SUPPORTIVE,
            escalation_threshold=0.7,
            empathy_markers=[
                "I understand this is frustrating",
                "Let me help clarify this for you",
                "I can see why this is confusing",
                "Let's work through this together"
            ],
            de_escalation_phrases=[
                "I understand how frustrating this must be",
                "Let me walk you through this step by step",
                "I'll make sure we get this sorted out",
                "I'm here to help make this easier"
            ],
            avoid_phrases=[
                "It's simple",
                "Just follow the instructions",
                "You don't understand",
                "That's obvious"
            ],
            recommended_actions=[
                "detailed_explanation",
                "step_by_step_guidance",
                "follow_up_confirmation"
            ]
        ),
        EmotionType.CONFUSED: EmotionResponseStrategy(
            primary_emotion=EmotionType.CONFUSED,
            intensity_threshold=0.5,
            response_tone=ToneType.CLEAR_GUIDANCE,
            escalation_threshold=0.6,
            empathy_markers=[
                "Let me clarify that for you",
                "I can help explain this better",
                "Let me break this down",
                "I'll make this clearer"
            ],
            de_escalation_phrases=[
                "Let me explain this in simpler terms",
                "I'll walk you through this step by step",
                "Here's what this means",
                "Let me provide a clear example"
            ],
            avoid_phrases=[
                "It's obvious",
                "As I said before",
                "You should know this",
                "It's straightforward"
            ],
            recommended_actions=[
                "simplified_explanation",
                "visual_aids",
                "examples_provided",
                "confirmation_questions"
            ]
        ),
        EmotionType.SATISFIED: EmotionResponseStrategy(
            primary_emotion=EmotionType.SATISFIED,
            intensity_threshold=0.6,
            response_tone=ToneType.FRIENDLY,
            escalation_threshold=0.9,
            empathy_markers=[
                "I'm glad I could help",
                "That's wonderful to hear",
                "I'm happy this worked out",
                "Thank you for your patience"
            ],
            de_escalation_phrases=[
                "I'm so glad we could resolve this for you",
                "It's great that everything is working now",
                "Thank you for giving us the opportunity to help",
                "We appreciate your feedback"
            ],
            avoid_phrases=[
                "Whatever",
                "Fine",
                "Good enough",
                "At least it works"
            ],
            recommended_actions=[
                "positive_reinforcement",
                "feedback_collection",
                "future_assistance_offer"
            ]
        ),
        EmotionType.HAPPY: EmotionResponseStrategy(
            primary_emotion=EmotionType.HAPPY,
            intensity_threshold=0.7,
            response_tone=ToneType.ENTHUSIASTIC,
            escalation_threshold=0.95,
            empathy_markers=[
                "That's fantastic!",
                "I'm thrilled to hear that",
                "That's wonderful news!",
                "I'm so glad everything worked out"
            ],
            de_escalation_phrases=[
                "That's absolutely wonderful!",
                "I'm delighted that we could exceed your expectations",
                "Your satisfaction makes our day!",
                "We're thrilled to have you as a satisfied customer"
            ],
            avoid_phrases=[
                "Okay",
                "Sure",
                "Whatever you say",
                "If you say so"
            ],
            recommended_actions=[
                "celebratory_tone",
                "positive_feedback_request",
                "loyalty_program_mention"
            ]
        ),
        EmotionType.EXCITED: EmotionResponseStrategy(
            primary_emotion=EmotionType.EXCITED,
            intensity_threshold=0.7,
            response_tone=ToneType.ENTHUSIASTIC,
            escalation_threshold=0.95,
            empathy_markers=[
                "That's exciting!",
                "How wonderful!",
                "That's amazing!",
                "I'm excited for you!"
            ],
            de_escalation_phrases=[
                "That's incredibly exciting!",
                "I'm so excited to help you with this!",
                "This is fantastic news!",
                "Let's make this even more amazing!"
            ],
            avoid_phrases=[
                "Calm down",
                "Settle down",
                "Don't get too excited",
                "It's not that big of a deal"
            ],
            recommended_actions=[
                "match_enthusiasm",
                "amplify_positive",
                "future_optimism"
            ]
        ),
        EmotionType.NEUTRAL: EmotionResponseStrategy(
            primary_emotion=EmotionType.NEUTRAL,
            intensity_threshold=0.0,
            response_tone=ToneType.NEUTRAL,
            escalation_threshold=0.9,
            empathy_markers=[
                "I understand",
                "I see",
                "Thank you for the information",
                "Let me help you with that"
            ],
            de_escalation_phrases=[
                "I understand your request",
                "Let me assist you with that",
                "I'll help you resolve this",
                "Let's work through this together"
            ],
            avoid_phrases=[],
            recommended_actions=[
                "professional_assistance",
                "clear_communication",
                "efficient_resolution"
            ]
        )
    }
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def get_strategy(self, emotion: str, intensity: float) -> Optional[EmotionResponseStrategy]:
        """Get response strategy for detected emotion."""
        try:
            emotion_type = EmotionType(emotion.lower())
        except ValueError:
            self.logger.warning(f"Unknown emotion type: {emotion}")
            return self.EMOTION_STRATEGIES.get(EmotionType.NEUTRAL)
        
        strategy = self.EMOTION_STRATEGIES.get(emotion_type)
        if strategy and intensity >= strategy.intensity_threshold:
            return strategy
        
        # Return neutral strategy if emotion doesn't meet threshold
        return self.EMOTION_STRATEGIES.get(EmotionType.NEUTRAL)
    
    def adapt_response_tone(self, response_text: str, emotion: str, intensity: float,
                          confidence: float, context: ConversationContext) -> ToneAdaptation:
        """Adapt response tone based on detected emotion."""
        strategy = self.get_strategy(emotion, intensity)
        if not strategy:
            return ToneAdaptation(
                original_text=response_text,
                adapted_text=response_text,
                tone_used=ToneType.NEUTRAL,
                emotion_detected=EmotionType.NEUTRAL,
                intensity=intensity,
                confidence=confidence,
                modifications_made=[],
                escalation_recommended=False
            )
        
        # Apply tone adaptation based on strategy
        adapted_text = response_text
        modifications_made = []
        escalation_recommended = False
        escalation_reason = None
        
        # Apply empathy markers
        if strategy.empathy_markers and intensity >= strategy.intensity_threshold:
            empathy_marker = self._select_empathy_marker(strategy.empathy_markers, intensity)
            if not self._already_has_empathy(response_text, strategy.empathy_markers):
                adapted_text = f"{empathy_marker}. {adapted_text}"
                modifications_made.append("added_empathy_marker")
        
        # Apply de-escalation phrases
        if strategy.de_escalation_phrases and intensity >= strategy.intensity_threshold:
            de_escalation = self._select_de_escalation_phrase(
                strategy.de_escalation_phrases, intensity, context
            )
            if not self._already_has_de_escalation(response_text, strategy.de_escalation_phrases):
                adapted_text = f"{adapted_text} {de_escalation}"
                modifications_made.append("added_de_escalation")
        
        # Remove avoid phrases
        if strategy.avoid_phrases:
            original_text = adapted_text
            adapted_text = self._remove_avoid_phrases(adapted_text, strategy.avoid_phrases)
            if adapted_text != original_text:
                modifications_made.append("removed_avoid_phrases")
        
        # Apply tone-specific modifications
        tone_modifications = self._apply_tone_modifications(
            adapted_text, strategy.response_tone, intensity, context
        )
        if tone_modifications["text"] != adapted_text:
            adapted_text = tone_modifications["text"]
            modifications_made.extend(tone_modifications["modifications"])
        
        # Determine if escalation is needed
        if intensity >= strategy.escalation_threshold:
            escalation_recommended = True
            escalation_reason = f"high_{emotion}_intensity"
        elif strategy.requires_human_review:
            escalation_recommended = True
            escalation_reason = "requires_human_review"
        
        return ToneAdaptation(
            original_text=response_text,
            adapted_text=adapted_text,
            tone_used=strategy.response_tone,
            emotion_detected=EmotionType(emotion.lower()),
            intensity=intensity,
            confidence=confidence,
            modifications_made=modifications_made,
            escalation_recommended=escalation_recommended,
            escalation_reason=escalation_reason
        )
    
    def _select_empathy_marker(self, empathy_markers: List[str], intensity: float) -> str:
        """Select appropriate empathy marker based on intensity."""
        if intensity >= 0.8:
            # High intensity - use stronger empathy
            return empathy_markers[0] if empathy_markers else "I understand"
        elif intensity >= 0.6:
            # Medium intensity - use moderate empathy
            return empathy_markers[1] if len(empathy_markers) > 1 else "I understand"
        else:
            # Low intensity - use gentle empathy
            return empathy_markers[-1] if empathy_markers else "I understand"
    
    def _select_de_escalation_phrase(self, de_escalation_phrases: List[str], intensity: float,
                                   context: ConversationContext) -> str:
        """Select appropriate de-escalation phrase based on intensity and context."""
        # Consider conversation history and user context
        user_history = context.user_context.history
        sentiment_trend = context.user_context.get_sentiment_trend()
        
        if intensity >= 0.8 or sentiment_trend["trend"] == "negative":
            # High intensity or negative trend - use stronger de-escalation
            return de_escalation_phrases[0] if de_escalation_phrases else "Let me help resolve this"
        elif intensity >= 0.6:
            # Medium intensity - use moderate de-escalation
            return de_escalation_phrases[1] if len(de_escalation_phrases) > 1 else "Let me help"
        else:
            # Low intensity - use gentle de-escalation
            return de_escalation_phrases[-1] if de_escalation_phrases else "Let me assist you"
    
    def _already_has_empathy(self, text: str, empathy_markers: List[str]) -> bool:
        """Check if text already contains empathy markers."""
        text_lower = text.lower()
        return any(marker.lower() in text_lower for marker in empathy_markers)
    
    def _already_has_de_escalation(self, text: str, de_escalation_phrases: List[str]) -> bool:
        """Check if text already contains de-escalation phrases."""
        text_lower = text.lower()
        return any(phrase.lower() in text_lower for phrase in de_escalation_phrases)
    
    def _remove_avoid_phrases(self, text: str, avoid_phrases: List[str]) -> str:
        """Remove or replace avoid phrases."""
        result = text
        for phrase in avoid_phrases:
            # Replace with more appropriate alternatives
            if phrase.lower() in result.lower():
                # This is a simplified replacement - in production, use more sophisticated NLP
                result = result.replace(phrase, self._get_alternative_phrase(phrase))
        return result
    
    def _get_alternative_phrase(self, avoid_phrase: str) -> str:
        """Get alternative phrase for avoid phrase."""
        alternatives = {
            "calm down": "let's work through this together",
            "that's not our fault": "let's see how we can resolve this",
            "you should have": "going forward, we can",
            "that's policy": "here's what we can do",
            "there's nothing I can do": "let me see what options we have",
            "it's simple": "let me walk you through this",
            "just follow the instructions": "here are the steps we can take",
            "you don't understand": "let me clarify this",
            "that's obvious": "let me explain this clearly",
            "whatever you say": "I understand your perspective",
            "if you say so": "I appreciate your input"
        }
        return alternatives.get(avoid_phrase.lower(), "let me help you with this")
    
    def _apply_tone_modifications(self, text: str, tone: ToneType, intensity: float,
                                context: ConversationContext) -> Dict[str, Any]:
        """Apply tone-specific modifications to text."""
        modifications = []
        adapted_text = text
        
        if tone == ToneType.EMPATHETIC:
            # Add empathetic language
            if intensity >= 0.7 and not self._has_empathetic_language(adapted_text):
                adapted_text = f"I truly understand how you feel. {adapted_text}"
                modifications.append("added_empathetic_language")
        
        elif tone == ToneType.SUPPORTIVE:
            # Add supportive phrases
            if not self._has_supportive_language(adapted_text):
                adapted_text = f"I'm here to support you. {adapted_text}"
                modifications.append("added_supportive_language")
        
        elif tone == ToneType.CLEAR_GUIDANCE:
            # Ensure clarity and structure
            if intensity >= 0.6:
                adapted_text = self._add_guidance_structure(adapted_text)
                modifications.append("added_guidance_structure")
        
        elif tone == ToneType.FRIENDLY:
            # Add friendly elements
            if not self._has_friendly_language(adapted_text):
                adapted_text = f"I'd be happy to help! {adapted_text}"
                modifications.append("added_friendly_language")
        
        elif tone == ToneType.ENTHUSIASTIC:
            # Add enthusiastic elements
            adapted_text = self._add_enthusiastic_elements(adapted_text, intensity)
            modifications.append("added_enthusiastic_elements")
        
        elif tone == ToneType.APOLOGETIC:
            # Add apologetic elements for angry/frustrated users
            if not self._has_apologetic_language(adapted_text):
                adapted_text = f"I sincerely apologize for the inconvenience. {adapted_text}"
                modifications.append("added_apologetic_language")
        
        return {
            "text": adapted_text,
            "modifications": modifications
        }
    
    def _has_empathetic_language(self, text: str) -> bool:
        """Check if text has empathetic language."""
        empathetic_indicators = [
            "i understand", "i truly", "i can see", "i appreciate", "i realize",
            "that must be", "how difficult", "i'm sorry"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in empathetic_indicators)
    
    def _has_supportive_language(self, text: str) -> bool:
        """Check if text has supportive language."""
        supportive_indicators = [
            "i'm here", "let me help", "we'll work", "together", "support",
            "assist", "guide", "help you"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in supportive_indicators)
    
    def _has_friendly_language(self, text: str) -> bool:
        """Check if text has friendly language."""
        friendly_indicators = [
            "happy to", "glad to", "excited", "wonderful", "great", "fantastic",
            "amazing", "awesome", "perfect"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in friendly_indicators)
    
    def _has_apologetic_language(self, text: str) -> bool:
        """Check if text has apologetic language."""
        apologetic_indicators = [
            "apologize", "sorry", "regret", "unfortunate", "inconvenience"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in apologetic_indicators)
    
    def _add_guidance_structure(self, text: str) -> str:
        """Add clear structure for guidance tone."""
        # Simple structure addition - in production, use more sophisticated structuring
        if "step" not in text.lower() and "first" not in text.lower():
            return f"Here's what we need to do: {text}"
        return text
    
    def _add_enthusiastic_elements(self, text: str, intensity: float) -> str:
        """Add enthusiastic elements based on intensity."""
        if intensity >= 0.8:
            # High enthusiasm
            if not text.startswith(("That's", "This is", "How")):
                return f"That's absolutely fantastic! {text}"
        elif intensity >= 0.6:
            # Medium enthusiasm
            if not self._has_enthusiastic_language(text):
                return f"That's wonderful! {text}"
        
        return text
    
    def _has_enthusiastic_language(self, text: str) -> bool:
        """Check if text has enthusiastic language."""
        enthusiastic_indicators = [
            "fantastic", "wonderful", "amazing", "exciting", "thrilled",
            "delighted", "excellent", "perfect", "awesome"
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in enthusiastic_indicators)
    
    def get_recommended_actions(self, emotion: str, intensity: float) -> List[str]:
        """Get recommended actions based on emotion and intensity."""
        strategy = self.get_strategy(emotion, intensity)
        return strategy.recommended_actions if strategy else []
    
    def should_escalate(self, emotion: str, intensity: float, confidence: float) -> tuple[bool, Optional[str]]:
        """Determine if conversation should be escalated based on emotion."""
        strategy = self.get_strategy(emotion, intensity)
        if not strategy:
            return False, None
        
        # Check if intensity exceeds escalation threshold
        if intensity >= strategy.escalation_threshold:
            return True, f"high_{emotion}_intensity"
        
        # Check if emotion requires human review
        if strategy.requires_human_review and confidence >= 0.8:
            return True, "requires_human_review"
        
        return False, None
    
    def get_emotion_specific_greeting(self, emotion: str, intensity: float) -> str:
        """Get emotion-appropriate greeting."""
        strategy = self.get_strategy(emotion, intensity)
        if not strategy:
            return "Hello! How can I help you today?"
        
        if emotion == EmotionType.ANGRY.value and intensity >= 0.7:
            return "I understand you're frustrated. Let me help resolve this for you."
        elif emotion == EmotionType.FRUSTRATED.value and intensity >= 0.6:
            return "I can see this is frustrating. Let me help make this easier."
        elif emotion == EmotionType.CONFUSED.value and intensity >= 0.6:
            return "I can help clarify this for you. Let me explain step by step."
        elif emotion == EmotionType.HAPPY.value and intensity >= 0.7:
            return "That's wonderful to hear! How can I assist you today?"
        elif emotion == EmotionType.EXCITED.value and intensity >= 0.7:
            return "That's exciting! How can I help make this even better?"
        else:
            return "Hello! How can I help you today?"
    
    def track_emotion_trend(self, emotion_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Track emotion trend over time."""
        if not emotion_history:
            return {"trend": "stable", "primary_emotion": "neutral", "confidence": 0.0}
        
        # Analyze last 5 emotions
        recent_emotions = emotion_history[-5:] if len(emotion_history) >= 5 else emotion_history
        
        emotion_counts = {}
        total_intensity = 0.0
        
        for record in recent_emotions:
            emotion = record.get("emotion", "neutral")
            intensity = record.get("intensity", 0.0)
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_intensity += intensity
        
        primary_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
        avg_intensity = total_intensity / len(recent_emotions)
        
        # Determine trend
        if len(emotion_history) >= 2:
            first_emotion = emotion_history[0].get("emotion", "neutral")
            last_emotion = emotion_history[-1].get("emotion", "neutral")
            
            if first_emotion != last_emotion:
                if self._is_positive_change(first_emotion, last_emotion):
                    trend = "improving"
                elif self._is_negative_change(first_emotion, last_emotion):
                    trend = "worsening"
                else:
                    trend = "changing"
            else:
                first_intensity = emotion_history[0].get("intensity", 0.0)
                last_intensity = emotion_history[-1].get("intensity", 0.0)
                
                if last_intensity > first_intensity + 0.2:
                    trend = "intensifying"
                elif last_intensity < first_intensity - 0.2:
                    trend = "diminishing"
                else:
                    trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "primary_emotion": primary_emotion,
            "average_intensity": avg_intensity,
            "confidence": min(1.0, len(recent_emotions) / 5.0)
        }
    
    def _is_positive_change(self, from_emotion: str, to_emotion: str) -> bool:
        """Determine if emotion change is positive."""
        positive_emotions = {"happy", "excited", "satisfied"}
        negative_emotions = {"angry", "frustrated"}
        
        if from_emotion in negative_emotions and to_emotion not in negative_emotions:
            return True
        if from_emotion == "confused" and to_emotion in {"satisfied", "neutral"}:
            return True
        
        return False
    
    def _is_negative_change(self, from_emotion: str, to_emotion: str) -> bool:
        """Determine if emotion change is negative."""
        negative_emotions = {"angry", "frustrated", "confused"}
        positive_emotions = {"happy", "excited", "satisfied"}
        
        if from_emotion not in negative_emotions and to_emotion in negative_emotions:
            return True
        if from_emotion in positive_emotions and to_emotion not in positive_emotions:
            return True
        
        return False


class EmotionContext:
    """Tracks emotion context over conversation lifetime."""
    
    def __init__(self):
        self.emotion_history: List[Dict[str, Any]] = []
        self.current_emotion: Optional[str] = None
        self.current_intensity: float = 0.0
        self.emotion_transitions: List[Dict[str, Any]] = []
        self.escalation_triggers: List[Dict[str, Any]] = []
    
    def record_emotion(self, emotion: str, intensity: float, confidence: float,
                      reason: str = None, metadata: Dict[str, Any] = None):
        """Record emotion detection in conversation."""
        previous_emotion = self.current_emotion
        
        emotion_record = {
            "emotion": emotion,
            "intensity": intensity,
            "confidence": confidence,
            "timestamp": time.time(),
            "reason": reason,
            "metadata": metadata or {}
        }
        
        self.emotion_history.append(emotion_record)
        self.current_emotion = emotion
        self.current_intensity = intensity
        
        # Record transition if emotion changed
        if previous_emotion and previous_emotion != emotion:
            self.emotion_transitions.append({
                "from": previous_emotion,
                "to": emotion,
                "intensity_change": intensity - self.current_intensity,
                "timestamp": emotion_record["timestamp"]
            })
        
        # Keep only last 50 emotion records
        if len(self.emotion_history) > 50:
            self.emotion_history = self.emotion_history[-50:]
    
    def record_escalation_trigger(self, reason: str, emotion: str, intensity: float):
        """Record escalation trigger due to emotion."""
        self.escalation_triggers.append({
            "reason": reason,
            "emotion": emotion,
            "intensity": intensity,
            "timestamp": time.time()
        })
    
    def get_emotion_summary(self) -> Dict[str, Any]:
        """Get summary of emotion context."""
        if not self.emotion_history:
            return {
                "current_emotion": "neutral",
                "current_intensity": 0.0,
                "emotion_history_count": 0,
                "escalation_triggers": 0
            }
        
        # Calculate emotion distribution
        emotion_counts = {}
        total_intensity = 0.0
        
        for record in self.emotion_history:
            emotion = record["emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_intensity += record["intensity"]
        
        most_common_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
        avg_intensity = total_intensity / len(self.emotion_history)
        
        return {
            "current_emotion": self.current_emotion or "neutral",
            "current_intensity": self.current_intensity,
            "most_common_emotion": most_common_emotion,
            "average_intensity": avg_intensity,
            "emotion_history_count": len(self.emotion_history),
            "emotion_transitions": len(self.emotion_transitions),
            "escalation_triggers": len(self.escalation_triggers),
            "emotion_distribution": emotion_counts
        }