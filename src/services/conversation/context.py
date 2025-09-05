"""Multi-layered conversation context management system."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from uuid import UUID

from src.core.exceptions import ConversationError
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UserContext:
    """User-specific context information."""
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    sentiment_history: List[Dict[str, Any]] = field(default_factory=list)
    emotion_history: List[Dict[str, Any]] = field(default_factory=list)
    language_preference: str = "en"
    timezone: str = "UTC"
    customer_tier: str = "standard"
    vip_status: bool = False
    
    def add_sentiment_record(self, sentiment: str, score: float, confidence: float):
        """Add sentiment record to user history."""
        self.sentiment_history.append({
            "sentiment": sentiment,
            "score": score,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 100 records
        if len(self.sentiment_history) > 100:
            self.sentiment_history = self.sentiment_history[-100:]
    
    def add_emotion_record(self, emotion: str, intensity: float, confidence: float):
        """Add emotion record to user history."""
        self.emotion_history.append({
            "emotion": emotion,
            "intensity": intensity,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 100 records
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]
    
    def get_sentiment_trend(self) -> Dict[str, Any]:
        """Get sentiment trend analysis."""
        if not self.sentiment_history:
            return {"trend": "neutral", "confidence": 0.0}
        
        recent = self.sentiment_history[-10:]  # Last 10 records
        scores = [record["score"] for record in recent]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        if avg_score > 0.5:
            trend = "positive"
        elif avg_score < -0.5:
            trend = "negative"
        else:
            trend = "neutral"
        
        return {
            "trend": trend,
            "average_score": avg_score,
            "confidence": min(1.0, len(recent) / 10.0)
        }


@dataclass
class SessionContext:
    """Session-specific context for current conversation."""
    conversation_id: Optional[UUID] = None
    channel: str = "web_chat"
    current_state: str = "initialized"
    previous_state: str = "initialized"
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    message_count: int = 0
    user_message_count: int = 0
    ai_message_count: int = 0
    start_time: Optional[datetime] = None
    last_activity_time: Optional[datetime] = None
    context_variables: Dict[str, Any] = field(default_factory=dict)
    temporary_data: Dict[str, Any] = field(default_factory=dict)
    
    def record_state_change(self, new_state: str, reason: str = None, metadata: Dict[str, Any] = None):
        """Record a state change in the session."""
        self.previous_state = self.current_state
        self.current_state = new_state
        
        state_record = {
            "from_state": self.previous_state,
            "to_state": new_state,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "metadata": metadata or {}
        }
        
        self.state_history.append(state_record)
        
        # Keep only last 50 state changes
        if len(self.state_history) > 50:
            self.state_history = self.state_history[-50:]
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity_time = datetime.utcnow()
    
    def is_timed_out(self, timeout_seconds: int) -> bool:
        """Check if session has timed out."""
        if not self.last_activity_time:
            return False
        
        elapsed = (datetime.utcnow() - self.last_activity_time).total_seconds()
        return elapsed > timeout_seconds
    
    def get_session_duration(self) -> float:
        """Get session duration in seconds."""
        if not self.start_time:
            return 0.0
        return (datetime.utcnow() - self.start_time).total_seconds()


@dataclass
class AIContext:
    """AI processing context and metadata."""
    last_intent: Optional[str] = None
    intent_confidence: float = 0.0
    intent_history: List[Dict[str, Any]] = field(default_factory=list)
    last_sentiment: Optional[str] = None
    sentiment_score: float = 0.0
    sentiment_history: List[Dict[str, Any]] = field(default_factory=list)
    last_emotion: Optional[str] = None
    emotion_intensity: float = 0.0
    emotion_history: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_used: List[Dict[str, Any]] = field(default_factory=list)
    model_used: Optional[str] = None
    model_version: Optional[str] = None
    processing_time_ms: int = 0
    token_usage: Dict[str, int] = field(default_factory=dict)
    confidence_threshold: float = 0.7
    fallback_triggered: bool = False
    
    def record_intent(self, intent: str, confidence: float, parameters: Dict[str, Any] = None):
        """Record intent detection result."""
        self.last_intent = intent
        self.intent_confidence = confidence
        
        intent_record = {
            "intent": intent,
            "confidence": confidence,
            "parameters": parameters or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.intent_history.append(intent_record)
        
        # Keep only last 20 intents
        if len(self.intent_history) > 20:
            self.intent_history = self.intent_history[-20:]
    
    def record_sentiment(self, sentiment: str, score: float, confidence: float):
        """Record sentiment analysis result."""
        self.last_sentiment = sentiment
        self.sentiment_score = score
        
        sentiment_record = {
            "sentiment": sentiment,
            "score": score,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.sentiment_history.append(sentiment_record)
        
        # Keep only last 20 sentiments
        if len(self.sentiment_history) > 20:
            self.sentiment_history = self.sentiment_history[-20:]
    
    def record_emotion(self, emotion: str, intensity: float, confidence: float):
        """Record emotion detection result."""
        self.last_emotion = emotion
        self.emotion_intensity = intensity
        
        emotion_record = {
            "emotion": emotion,
            "intensity": intensity,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.emotion_history.append(emotion_record)
        
        # Keep only last 20 emotions
        if len(self.emotion_history) > 20:
            self.emotion_history = self.emotion_history[-20:]
    
    def get_emotion_trend(self) -> Dict[str, Any]:
        """Get emotion trend analysis."""
        if not self.emotion_history:
            return {"primary_emotion": "neutral", "intensity": 0.0, "confidence": 0.0}
        
        # Simple emotion aggregation
        emotion_counts = {}
        total_intensity = 0.0
        
        for record in self.emotion_history[-10:]:  # Last 10 emotions
            emotion = record["emotion"]
            intensity = record["intensity"]
            
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            total_intensity += intensity
        
        primary_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
        avg_intensity = total_intensity / len(self.emotion_history[-10:]) if self.emotion_history[-10:] else 0.0
        
        return {
            "primary_emotion": primary_emotion,
            "intensity": avg_intensity,
            "confidence": min(1.0, len(self.emotion_history[-10:]) / 10.0)
        }


@dataclass
class BusinessContext:
    """Business logic context for rules and workflows."""
    sla_breached: bool = False
    sla_deadline: Optional[datetime] = None
    escalation_triggered: bool = False
    escalation_reason: Optional[str] = None
    escalation_level: int = 0
    rules_applied: List[Dict[str, Any]] = field(default_factory=list)
    workflows_triggered: List[Dict[str, Any]] = field(default_factory=list)
    compliance_flags: List[str] = field(default_factory=list)
    priority_override: Optional[str] = None
    queue_assignment: Optional[str] = None
    agent_assignment: Optional[str] = None
    business_hours_active: bool = True
    
    def record_rule_application(self, rule_id: str, rule_name: str, result: str, metadata: Dict[str, Any] = None):
        """Record rule application in conversation."""
        rule_record = {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "result": result,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.rules_applied.append(rule_record)
    
    def record_workflow_trigger(self, workflow_id: str, workflow_name: str, status: str, metadata: Dict[str, Any] = None):
        """Record workflow trigger in conversation."""
        workflow_record = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "status": status,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.workflows_triggered.append(workflow_record)
    
    def add_compliance_flag(self, flag: str, reason: str = None):
        """Add compliance flag to conversation."""
        flag_record = f"{flag}:{reason}" if reason else flag
        if flag_record not in self.compliance_flags:
            self.compliance_flags.append(flag_record)


class ConversationContext:
    """Multi-layered conversation context management system."""
    
    def __init__(self, organization_id: Optional[UUID] = None):
        self.organization_id = organization_id
        self.user_context = UserContext()
        self.session_context = SessionContext()
        self.ai_context = AIContext()
        self.business_context = BusinessContext()
        self.logger = get_logger(__name__)
    
    def initialize_for_conversation(self, conversation_id: UUID, user_id: Optional[UUID] = None,
                                  organization_id: Optional[UUID] = None, channel: str = "web_chat"):
        """Initialize context for a new conversation."""
        self.session_context.conversation_id = conversation_id
        self.session_context.channel = channel
        self.session_context.start_time = datetime.utcnow()
        self.session_context.last_activity_time = datetime.utcnow()
        
        if user_id:
            self.user_context.user_id = user_id
        
        if organization_id:
            self.user_context.organization_id = organization_id
            self.organization_id = organization_id
        
        self.logger.info(f"Context initialized for conversation: {conversation_id} user={user_id} org={organization_id} channel={channel}")
    
    def record_message_processed(self, message_content: str, sender_type: str, sentiment_result: Dict[str, Any] = None,
                               emotion_result: Dict[str, Any] = None, intent_result: Dict[str, Any] = None):
        """Record message processing results in context."""
        # Update session metrics
        self.session_context.message_count += 1
        self.session_context.update_activity()
        
        if sender_type == "user":
            self.session_context.user_message_count += 1
        elif sender_type == "ai_agent":
            self.session_context.ai_message_count += 1
        
        # Record AI results if available
        if sentiment_result:
            self.ai_context.record_sentiment(
                sentiment_result["sentiment"],
                sentiment_result["score"],
                sentiment_result["confidence"]
            )
            self.user_context.add_sentiment_record(
                sentiment_result["sentiment"],
                sentiment_result["score"],
                sentiment_result["confidence"]
            )
        
        if emotion_result:
            self.ai_context.record_emotion(
                emotion_result["emotion"],
                emotion_result["intensity"],
                emotion_result["confidence"]
            )
            self.user_context.add_emotion_record(
                emotion_result["emotion"],
                emotion_result["intensity"],
                emotion_result["confidence"]
            )
        
        if intent_result:
            self.ai_context.record_intent(
                intent_result["intent"],
                intent_result["confidence"],
                intent_result.get("parameters", {})
            )
    
    def record_state_change(self, new_state: str, reason: str = None, metadata: Dict[str, Any] = None):
        """Record conversation state change."""
        self.session_context.record_state_change(new_state, reason, metadata)
        
        self.logger.info(f"Conversation state changed: {self.session_context.conversation_id} from {self.session_context.previous_state} to {new_state} reason={reason}")
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get comprehensive context summary."""
        emotion_trend = self.ai_context.get_emotion_trend()
        sentiment_trend = self.user_context.get_sentiment_trend()
        
        return {
            "user_context": {
                "user_id": str(self.user_context.user_id) if self.user_context.user_id else None,
                "organization_id": str(self.user_context.organization_id) if self.user_context.organization_id else None,
                "customer_tier": self.user_context.customer_tier,
                "vip_status": self.user_context.vip_status,
                "sentiment_trend": sentiment_trend,
                "emotion_trend": emotion_trend,
                "language_preference": self.user_context.language_preference,
                "timezone": self.user_context.timezone
            },
            "session_context": {
                "conversation_id": str(self.session_context.conversation_id) if self.session_context.conversation_id else None,
                "channel": self.session_context.channel,
                "current_state": self.session_context.current_state,
                "message_count": self.session_context.message_count,
                "session_duration": self.session_context.get_session_duration(),
                "is_timed_out": self.session_context.is_timed_out(1800)  # 30 minutes
            },
            "ai_context": {
                "last_intent": self.ai_context.last_intent,
                "intent_confidence": self.ai_context.intent_confidence,
                "last_sentiment": self.ai_context.last_sentiment,
                "sentiment_score": self.ai_context.sentiment_score,
                "last_emotion": self.ai_context.last_emotion,
                "emotion_intensity": self.ai_context.emotion_intensity,
                "confidence_threshold": self.ai_context.confidence_threshold,
                "fallback_triggered": self.ai_context.fallback_triggered
            },
            "business_context": {
                "sla_breached": self.business_context.sla_breached,
                "escalation_triggered": self.business_context.escalation_triggered,
                "escalation_level": self.business_context.escalation_level,
                "rules_applied_count": len(self.business_context.rules_applied),
                "workflows_triggered_count": len(self.business_context.workflows_triggered),
                "compliance_flags": self.business_context.compliance_flags
            }
        }
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entire context for storage."""
        return {
            "user_context": asdict(self.user_context),
            "session_context": asdict(self.session_context),
            "ai_context": asdict(self.ai_context),
            "business_context": asdict(self.business_context),
            "version": "1.0",
            "serialized_at": datetime.utcnow().isoformat()
        }
    
    def deserialize(self, data: Dict[str, Any]):
        """Deserialize context from storage."""
        if "user_context" in data:
            user_data = data["user_context"]
            if "user_id" in user_data and user_data["user_id"]:
                self.user_context.user_id = UUID(user_data["user_id"])
            if "organization_id" in user_data and user_data["organization_id"]:
                self.user_context.organization_id = UUID(user_data["organization_id"])
            self.user_context.preferences = user_data.get("preferences", {})
            self.user_context.profile = user_data.get("profile", {})
            self.user_context.history = user_data.get("history", [])
            self.user_context.sentiment_history = user_data.get("sentiment_history", [])
            self.user_context.emotion_history = user_data.get("emotion_history", [])
            self.user_context.language_preference = user_data.get("language_preference", "en")
            self.user_context.timezone = user_data.get("timezone", "UTC")
            self.user_context.customer_tier = user_data.get("customer_tier", "standard")
            self.user_context.vip_status = user_data.get("vip_status", False)
        
        if "session_context" in data:
            session_data = data["session_context"]
            if "conversation_id" in session_data and session_data["conversation_id"]:
                self.session_context.conversation_id = UUID(session_data["conversation_id"])
            self.session_context.channel = session_data.get("channel", "web_chat")
            self.session_context.current_state = session_data.get("current_state", "initialized")
            self.session_context.previous_state = session_data.get("previous_state", "initialized")
            self.session_context.state_history = session_data.get("state_history", [])
            self.session_context.message_count = session_data.get("message_count", 0)
            self.session_context.user_message_count = session_data.get("user_message_count", 0)
            self.session_context.ai_message_count = session_data.get("ai_message_count", 0)
            if session_data.get("start_time"):
                self.session_context.start_time = datetime.fromisoformat(session_data["start_time"])
            if session_data.get("last_activity_time"):
                self.session_context.last_activity_time = datetime.fromisoformat(session_data["last_activity_time"])
            self.session_context.context_variables = session_data.get("context_variables", {})
            self.session_context.temporary_data = session_data.get("temporary_data", {})
        
        if "ai_context" in data:
            ai_data = data["ai_context"]
            self.ai_context.last_intent = ai_data.get("last_intent")
            self.ai_context.intent_confidence = ai_data.get("intent_confidence", 0.0)
            self.ai_context.intent_history = ai_data.get("intent_history", [])
            self.ai_context.last_sentiment = ai_data.get("last_sentiment")
            self.ai_context.sentiment_score = ai_data.get("sentiment_score", 0.0)
            self.ai_context.sentiment_history = ai_data.get("sentiment_history", [])
            self.ai_context.last_emotion = ai_data.get("last_emotion")
            self.ai_context.emotion_intensity = ai_data.get("emotion_intensity", 0.0)
            self.ai_context.emotion_history = ai_data.get("emotion_history", [])
            self.ai_context.entities = ai_data.get("entities", [])
            self.ai_context.knowledge_used = ai_data.get("knowledge_used", [])
            self.ai_context.model_used = ai_data.get("model_used")
            self.ai_context.model_version = ai_data.get("model_version")
            self.ai_context.processing_time_ms = ai_data.get("processing_time_ms", 0)
            self.ai_context.token_usage = ai_data.get("token_usage", {})
            self.ai_context.confidence_threshold = ai_data.get("confidence_threshold", 0.7)
            self.ai_context.fallback_triggered = ai_data.get("fallback_triggered", False)
        
        if "business_context" in data:
            business_data = data["business_context"]
            self.business_context.sla_breached = business_data.get("sla_breached", False)
            if business_data.get("sla_deadline"):
                self.business_context.sla_deadline = datetime.fromisoformat(business_data["sla_deadline"])
            self.business_context.escalation_triggered = business_data.get("escalation_triggered", False)
            self.business_context.escalation_reason = business_data.get("escalation_reason")
            self.business_context.escalation_level = business_data.get("escalation_level", 0)
            self.business_context.rules_applied = business_data.get("rules_applied", [])
            self.business_context.workflows_triggered = business_data.get("workflows_triggered", [])
            self.business_context.compliance_flags = business_data.get("compliance_flags", [])
            self.business_context.priority_override = business_data.get("priority_override")
            self.business_context.queue_assignment = business_data.get("queue_assignment")
            self.business_context.agent_assignment = business_data.get("agent_assignment")
            self.business_context.business_hours_active = business_data.get("business_hours_active", True)


class ContextManager:
    """Manager for conversation context lifecycle."""
    
    def __init__(self):
        self.contexts: Dict[str, ConversationContext] = {}
        self.logger = get_logger(__name__)
    
    def get_or_create_context(self, conversation_id: str, organization_id: Optional[UUID] = None) -> ConversationContext:
        """Get existing context or create new one."""
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = ConversationContext(organization_id)
            self.logger.info(f"Created new conversation context: {conversation_id}")
        
        return self.contexts[conversation_id]
    
    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get existing context."""
        return self.contexts.get(conversation_id)
    
    def remove_context(self, conversation_id: str):
        """Remove context from memory."""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
            self.logger.info(f"Removed conversation context: {conversation_id}")
    
    def cleanup_expired_contexts(self, max_age_hours: int = 24):
        """Clean up contexts older than specified hours."""
        current_time = datetime.utcnow()
        expired_conversations = []
        
        for conversation_id, context in self.contexts.items():
            if context.session_context.last_activity_time:
                age_hours = (current_time - context.session_context.last_activity_time).total_seconds() / 3600
                if age_hours > max_age_hours:
                    expired_conversations.append(conversation_id)
        
        for conversation_id in expired_conversations:
            self.remove_context(conversation_id)
        
        self.logger.info(
            "Cleaned up expired contexts",
            expired_count=len(expired_conversations),
            remaining_count=len(self.contexts)
        )