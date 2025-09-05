"""Response generation for conversation system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ResponseTemplate:
    """Template for generating responses."""
    name: str
    template_text: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    variables: List[str] = field(default_factory=list)
    tone_requirements: List[str] = field(default_factory=list)
    fallback_template: Optional[str] = None


@dataclass
class ResponseContext:
    """Context for response generation."""
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    sentiment: Optional[str] = None
    sentiment_score: float = 0.0
    emotion: Optional[str] = None
    emotion_intensity: float = 0.0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    user_context: Dict[str, Any] = field(default_factory=dict)
    knowledge_used: List[Dict[str, Any]] = field(default_factory=list)
    language: str = "en"


class ResponseGenerator:
    """Generates contextually appropriate responses."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, ResponseTemplate]:
        """Load default response templates."""
        return {
            "greeting": ResponseTemplate(
                name="greeting",
                template_text="Hello! How can I help you today?",
                conditions={"intent": "greeting", "sentiment": "positive"}
            ),
            "help": ResponseTemplate(
                name="help",
                template_text="I'm here to help! What would you like to know?",
                conditions={"intent": "help_request"}
            ),
            "goodbye": ResponseTemplate(
                name="goodbye",
                template_text="Thank you for contacting us. Have a great day!",
                conditions={"intent": "goodbye"}
            ),
            "unknown": ResponseTemplate(
                name="unknown",
                template_text="I'm not sure I understand. Could you please rephrase or provide more details?",
                conditions={"intent_confidence": {"max": 0.5}},
                fallback_template="I apologize, but I'm having trouble understanding your request. Could you try rephrasing it?"
            ),
            "escalation": ResponseTemplate(
                name="escalation",
                template_text="I'm transferring you to one of our specialists who can better assist you with this issue.",
                conditions={"requires_escalation": True}
            ),
            "technical_support": ResponseTemplate(
                name="technical_support",
                template_text="I understand you're experiencing {issue_description}. Let me help you resolve this.",
                variables=["issue_description"],
                conditions={"intent": "technical_support"}
            ),
            "account_management": ResponseTemplate(
                name="account_management",
                template_text="I can help you with your account. What would you like to do?",
                conditions={"intent": "account_management"}
            ),
            "billing_inquiry": ResponseTemplate(
                name="billing_inquiry",
                template_text="I can help you with billing questions. What specific billing matter would you like me to address?",
                conditions={"intent": "billing_inquiry"}
            ),
            "positive_sentiment": ResponseTemplate(
                name="positive_sentiment",
                template_text="I'm glad I could help! Is there anything else I can assist you with?",
                conditions={"sentiment": "positive", "sentiment_score": {"min": 0.7}}
            ),
            "negative_sentiment": ResponseTemplate(
                name="negative_sentiment",
                template_text="I understand your frustration. Let me see what I can do to help resolve this.",
                conditions={"sentiment": "negative", "sentiment_score": {"max": -0.5}}
            ),
            "angry_emotion": ResponseTemplate(
                name="angry_emotion",
                template_text="I can see you're upset about this. I want to make sure we get this resolved for you.",
                conditions={"emotion": "angry", "emotion_intensity": {"min": 0.6}},
                tone_requirements=["empathetic", "apologetic"]
            ),
            "frustrated_emotion": ResponseTemplate(
                name="frustrated_emotion",
                template_text="I understand how frustrating this must be. Let me work with you to find a solution.",
                conditions={"emotion": "frustrated", "emotion_intensity": {"min": 0.5}},
                tone_requirements=["supportive"]
            ),
            "confused_emotion": ResponseTemplate(
                name="confused_emotion",
                template_text="Let me clarify this for you. I'll explain it step by step.",
                conditions={"emotion": "confused", "emotion_intensity": {"min": 0.5}},
                tone_requirements=["clear", "patient"]
            ),
            "happy_emotion": ResponseTemplate(
                name="happy_emotion",
                template_text="That's wonderful to hear! I'm so glad everything worked out.",
                conditions={"emotion": "happy", "emotion_intensity": {"min": 0.7}},
                tone_requirements=["enthusiastic"]
            ),
            "knowledge_based": ResponseTemplate(
                name="knowledge_based",
                template_text="Based on the information I found: {knowledge_summary}",
                variables=["knowledge_summary"],
                conditions={"knowledge_used": {"min_count": 1}}
            ),
            "low_confidence": ResponseTemplate(
                name="low_confidence",
                template_text="I'm not entirely sure about this. Let me get more information or connect you with someone who can help.",
                conditions={"intent_confidence": {"max": 0.6}},
                fallback_template="I apologize, but I'm not confident about this answer. Let me escalate this to get you the right assistance."
            ),
            "vip_customer": ResponseTemplate(
                name="vip_customer",
                template_text="As one of our valued customers, I'll make sure to prioritize your request.",
                conditions={"user_context": {"vip_status": True}},
                tone_requirements=["professional", "priority"]
            ),
            "complex_issue": ResponseTemplate(
                name="complex_issue",
                template_text="This appears to be a complex issue that may require additional attention. Let me gather more information and see how we can best assist you.",
                conditions={"entities_count": {"min": 5}},
                tone_requirements=["thorough", "professional"]
            )
        }
    
    def generate_response(self, base_response: str, context: ResponseContext,
                         emotion_adaptation: Optional[Any] = None,
                         intent_result: Optional[Any] = None) -> str:
        """Generate contextually appropriate response."""
        
        # Start with base response or template-based response
        if not base_response or base_response.strip() == "":
            base_response = self._select_template(context)
        
        # Apply emotion adaptation if available
        if emotion_adaptation and emotion_adaptation.adapted_text:
            response = emotion_adaptation.adapted_text
        else:
            response = base_response
        
        # Apply intent-specific modifications
        if intent_result and intent_result.response_text:
            response = intent_result.response_text
        
        # Apply variable substitution
        response = self._substitute_variables(response, context)
        
        # Apply tone and style adjustments
        response = self._apply_tone_adjustments(response, context, emotion_adaptation)
        
        # Ensure response is appropriate length
        response = self._optimize_response_length(response)
        
        self.logger.debug(
            "Generated response",
            original_length=len(base_response),
            final_length=len(response),
            intent=context.intent,
            emotion=context.emotion
        )
        
        return response
    
    def _select_template(self, context: ResponseContext) -> str:
        """Select appropriate template based on context."""
        # Score templates based on context match
        scored_templates = []
        
        for template_name, template in self.templates.items():
            score = self._score_template_match(template, context)
            if score > 0:
                scored_templates.append((score, template))
        
        # Sort by score (descending)
        scored_templates.sort(key=lambda x: x[0], reverse=True)
        
        if scored_templates:
            best_template = scored_templates[0][1]
            return best_template.template_text
        
        # Fallback to unknown template
        return self.templates["unknown"].template_text
    
    def _score_template_match(self, template: ResponseTemplate, context: ResponseContext) -> float:
        """Score how well a template matches the context."""
        score = 0.0
        conditions = template.conditions
        
        # Intent matching
        if "intent" in conditions:
            if context.intent == conditions["intent"]:
                score += 1.0
            else:
                return 0.0  # Intent is required
        
        # Sentiment matching
        if "sentiment" in conditions:
            if context.sentiment == conditions["sentiment"]:
                score += 0.8
                
                # Check sentiment score range
                if "sentiment_score" in conditions:
                    score_range = conditions["sentiment_score"]
                    if self._is_in_range(context.sentiment_score, score_range):
                        score += 0.2
            else:
                return 0.0
        
        # Emotion matching
        if "emotion" in conditions:
            if context.emotion == conditions["emotion"]:
                score += 0.8
                
                # Check emotion intensity range
                if "emotion_intensity" in conditions:
                    intensity_range = conditions["emotion_intensity"]
                    if self._is_in_range(context.emotion_intensity, intensity_range):
                        score += 0.2
            else:
                return 0.0
        
        # Confidence matching
        if "intent_confidence" in conditions:
            confidence_range = conditions["intent_confidence"]
            if self._is_in_range(context.intent_confidence, confidence_range):
                score += 0.5
        
        # Knowledge usage matching
        if "knowledge_used" in conditions:
            knowledge_conditions = conditions["knowledge_used"]
            if "min_count" in knowledge_conditions:
                if len(context.knowledge_used) >= knowledge_conditions["min_count"]:
                    score += 0.3
        
        # Entity count matching
        if "entities_count" in conditions:
            entity_conditions = conditions["entities_count"]
            if "min" in entity_conditions:
                if len(context.entities) >= entity_conditions["min"]:
                    score += 0.2
        
        # User context matching
        if "user_context" in conditions:
            user_conditions = conditions["user_context"]
            for key, value in user_conditions.items():
                if context.user_context.get(key) == value:
                    score += 0.3
        
        return score
    
    def _is_in_range(self, value: float, range_def: Dict[str, Any]) -> bool:
        """Check if value is within defined range."""
        if "min" in range_def and value < range_def["min"]:
            return False
        if "max" in range_def and value > range_def["max"]:
            return False
        return True
    
    def _substitute_variables(self, template_text: str, context: ResponseContext) -> str:
        """Substitute variables in template text."""
        response = template_text
        
        # Common variable substitutions
        variable_mappings = {
            "{intent}": context.intent or "",
            "{sentiment}": context.sentiment or "",
            "{emotion}": context.emotion or "",
            "{emotion_intensity}": str(context.emotion_intensity),
            "{sentiment_score}": str(context.sentiment_score),
            "{entities_count}": str(len(context.entities)),
            "{language}": context.language,
            "{user_name}": context.user_context.get("name", ""),
            "{customer_tier}": context.user_context.get("customer_tier", ""),
        }
        
        # Add knowledge summary if available
        if context.knowledge_used:
            knowledge_summary = self._summarize_knowledge(context.knowledge_used)
            variable_mappings["{knowledge_summary}"] = knowledge_summary
        
        # Add entity information if specific entities are referenced
        if context.entities:
            entity_info = self._format_entity_info(context.entities)
            variable_mappings["{entity_info}"] = entity_info
        
        # Add issue description for technical support
        if context.intent == "technical_support" and context.entities:
            issue_description = self._extract_issue_description(context.entities)
            variable_mappings["{issue_description}"] = issue_description
        
        # Apply substitutions
        for placeholder, value in variable_mappings.items():
            if placeholder in response:
                response = response.replace(placeholder, str(value))
        
        return response
    
    def _summarize_knowledge(self, knowledge_used: List[Dict[str, Any]]) -> str:
        """Summarize knowledge used in response."""
        if not knowledge_used:
            return ""
        
        # Simple summary - in production, use more sophisticated summarization
        if len(knowledge_used) == 1:
            return knowledge_used[0].get("summary", "relevant information")
        else:
            return f"{len(knowledge_used)} pieces of relevant information"
    
    def _format_entity_info(self, entities: List[Dict[str, Any]]) -> str:
        """Format entity information for response."""
        if not entities:
            return ""
        
        # Extract key entities
        key_entities = []
        for entity in entities[:3]:  # Limit to first 3 entities
            entity_text = entity.get("text", "")
            entity_type = entity.get("type", "")
            if entity_text:
                key_entities.append(f"{entity_text} ({entity_type})")
        
        return ", ".join(key_entities) if key_entities else ""
    
    def _extract_issue_description(self, entities: List[Dict[str, Any]]) -> str:
        """Extract issue description from entities."""
        # Look for error codes, system names, etc.
        error_codes = [e["text"] for e in entities if e.get("type") == "error_code"]
        system_names = [e["text"] for e in entities if e.get("type") == "system"]
        
        parts = []
        if error_codes:
            parts.append(f"error code {error_codes[0]}")
        if system_names:
            parts.append(f"in {system_names[0]}")
        
        return " ".join(parts) if parts else "this issue"
    
    def _apply_tone_adjustments(self, response: str, context: ResponseContext,
                               emotion_adaptation: Optional[Any]) -> str:
        """Apply tone adjustments based on context and emotion adaptation."""
        # If we have emotion adaptation, use the already adapted text
        if emotion_adaptation:
            return emotion_adaptation.adapted_text
        
        # Apply basic tone adjustments based on sentiment and emotion
        if context.sentiment == "negative" and context.sentiment_score < -0.5:
            if not self._has_empathetic_language(response):
                response = f"I understand your concern. {response}"
        
        if context.emotion == "confused" and context.emotion_intensity > 0.6:
            if not self._has_clear_language(response):
                response = f"Let me clarify this for you. {response}"
        
        return response
    
    def _has_empathetic_language(self, text: str) -> bool:
        """Check if text has empathetic language."""
        empathetic_words = ["understand", "concern", "appreciate", "sorry", "apologize"]
        text_lower = text.lower()
        return any(word in text_lower for word in empathetic_words)
    
    def _has_clear_language(self, text: str) -> bool:
        """Check if text has clear/explanatory language."""
        clear_words = ["clarify", "explain", "step", "guide", "help"]
        text_lower = text.lower()
        return any(word in text_lower for word in clear_words)
    
    def _optimize_response_length(self, response: str, max_length: int = 500) -> str:
        """Optimize response length."""
        if len(response) <= max_length:
            return response
        
        # Try to truncate at sentence boundary
        sentences = response.split('. ')
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence + ". ") <= max_length:
                truncated += sentence + ". "
            else:
                break
        
        if truncated:
            return truncated.strip() + "..." if len(sentences) > 1 else response[:max_length] + "..."
        else:
            return response[:max_length] + "..."
    
    def add_template(self, name: str, template: ResponseTemplate) -> None:
        """Add a custom response template."""
        self.templates[name] = template
        self.logger.info(f"Added response template: {name}")
    
    def remove_template(self, name: str) -> bool:
        """Remove a response template."""
        if name in self.templates and name not in ["unknown", "greeting", "help", "goodbye"]:
            del self.templates[name]
            self.logger.info(f"Removed response template: {name}")
            return True
        return False
    
    def get_template(self, name: str) -> Optional[ResponseTemplate]:
        """Get a specific template."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())
    
    def validate_template(self, template: ResponseTemplate) -> tuple[bool, List[str]]:
        """Validate a response template."""
        errors = []
        
        if not template.name:
            errors.append("Template name is required")
        
        if not template.template_text:
            errors.append("Template text is required")
        
        # Check for valid variable syntax
        import re
        variables = re.findall(r'\{(\w+)\}', template.template_text)
        for var in variables:
            if var not in ["intent", "sentiment", "emotion", "emotion_intensity", 
                          "sentiment_score", "entities_count", "language", "user_name",
                          "customer_tier", "knowledge_summary", "entity_info", "issue_description"]:
                errors.append(f"Unknown variable: {var}")
        
        return len(errors) == 0, errors
    
    def get_response_suggestions(self, context: ResponseContext, max_suggestions: int = 3) -> List[str]:
        """Get suggested responses based on context."""
        suggestions = []
        
        # Score all templates
        scored_templates = []
        for template_name, template in self.templates.items():
            score = self._score_template_match(template, context)
            if score > 0.3:  # Minimum threshold for suggestions
                scored_templates.append((score, template))
        
        # Sort by score and take top suggestions
        scored_templates.sort(key=lambda x: x[0], reverse=True)
        
        for score, template in scored_templates[:max_suggestions]:
            suggestion = self._substitute_variables(template.template_text, context)
            suggestions.append(suggestion)
        
        return suggestions
    
    def generate_quick_replies(self, context: ResponseContext, max_replies: int = 3) -> List[str]:
        """Generate quick reply suggestions."""
        quick_replies = []
        
        # Base quick replies for common scenarios
        base_replies = {
            "technical_support": ["Yes, I'm still having issues", "No, that resolved it", "Let me try that"],
            "account_management": ["Reset my password", "Update billing", "Change plan", "View account"],
            "billing_inquiry": ["View invoice", "Update payment method", "Request refund", "Dispute charge"],
            "general_question": ["Tell me more", "That helps", "I have another question", "Thank you"],
            "greeting": ["Hello", "Hi there", "Good morning", "Good afternoon"],
            "help": ["Technical support", "Account help", "Billing question", "General inquiry"],
            "goodbye": ["Thank you", "Goodbye", "Have a great day", "Talk to you later"]
        }
        
        # Get intent-specific quick replies
        if context.intent and context.intent in base_replies:
            quick_replies.extend(base_replies[context.intent][:max_replies])
        
        # Add emotion-aware quick replies
        if context.emotion:
            emotion_replies = self._get_emotion_quick_replies(context.emotion, context.emotion_intensity)
            quick_replies.extend(emotion_replies)
        
        # Remove duplicates and limit
        unique_replies = list(dict.fromkeys(quick_replies))
        return unique_replies[:max_replies]
    
    def _get_emotion_quick_replies(self, emotion: str, intensity: float) -> List[str]:
        """Get quick replies based on detected emotion."""
        emotion_replies = {
            "angry": ["I understand your frustration", "Let me help resolve this", "Please escalate this"],
            "frustrated": ["I can help with that", "Let me clarify", "Let's work through this"],
            "confused": ["Please explain more", "Can you give an example?", "What specifically?"],
            "happy": ["That's great!", "I'm glad to help", "Anything else?"],
            "excited": ["That's exciting!", "Tell me more", "How can I help?"]
        }
        
        if emotion in emotion_replies and intensity >= 0.5:
            return emotion_replies[emotion]
        
        return []
    
    def format_response_for_channel(self, response: str, channel: str) -> str:
        """Format response for specific channel."""
        if channel in ["web_chat", "mobile_ios", "mobile_android"]:
            # Web and mobile channels - support rich formatting
            return response
        elif channel in ["email", "slack", "teams"]:
            # Email and chat channels - plain text with some formatting
            return response
        elif channel == "sms":
            # SMS - plain text, limited length
            if len(response) > 160:
                return response[:157] + "..."
            return response
        else:
            # Default - plain text
            return response