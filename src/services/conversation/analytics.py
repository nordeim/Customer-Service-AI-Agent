"""Conversation analytics and monitoring system."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.core.logging import get_logger
from src.services.conversation.context import ConversationContext

logger = get_logger(__name__)


@dataclass
class ConversationMetrics:
    """Core conversation metrics."""
    conversation_id: str
    organization_id: str
    user_id: str
    channel: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    message_count: int = 0
    user_message_count: int = 0
    ai_message_count: int = 0
    agent_message_count: int = 0
    
    # State metrics
    state_transitions: int = 0
    escalations: int = 0
    transfers: int = 0
    
    # AI performance metrics
    avg_intent_confidence: float = 0.0
    avg_sentiment_score: float = 0.0
    avg_emotion_intensity: float = 0.0
    ai_fallback_count: int = 0
    knowledge_used_count: int = 0
    
    # Resolution metrics
    resolved: bool = False
    resolution_time_seconds: Optional[float] = None
    resolution_type: Optional[str] = None
    satisfaction_score: Optional[float] = None
    nps_score: Optional[int] = None
    
    # Quality metrics
    first_response_time_seconds: Optional[float] = None
    avg_response_time_seconds: Optional[float] = None
    max_response_time_seconds: Optional[float] = None
    
    # Emotion metrics
    primary_emotion: Optional[str] = None
    emotion_changes: int = 0
    negative_emotion_duration: float = 0.0
    positive_emotion_duration: float = 0.0
    
    # Business metrics
    sla_breached: bool = False
    sla_breach_duration_seconds: float = 0.0
    business_rules_applied: int = 0
    workflows_triggered: int = 0


@dataclass
class MessageMetrics:
    """Individual message metrics."""
    message_id: str
    conversation_id: str
    sender_type: str
    content_length: int
    processing_time_ms: int
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    sentiment: Optional[str] = None
    sentiment_score: float = 0.0
    sentiment_confidence: float = 0.0
    emotion: Optional[str] = None
    emotion_intensity: float = 0.0
    emotion_confidence: float = 0.0
    entities_count: int = 0
    language: str = "en"
    translation_used: bool = False
    model_used: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AIPerformanceMetrics:
    """AI service performance metrics."""
    model_name: str
    capability: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_confidence: float = 0.0
    avg_tokens_used: float = 0.0
    avg_cost: float = 0.0
    cache_hit_rate: float = 0.0
    fallback_rate: float = 0.0


class ConversationAnalytics:
    """Tracks and analyzes conversation metrics."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        self.conversation_metrics: List[ConversationMetrics] = []
        self.message_metrics: List[MessageMetrics] = []
        self.ai_performance_metrics: Dict[str, AIPerformanceMetrics] = {}
    
    def start_conversation_tracking(self, conversation_id: str, organization_id: str,
                                  user_id: str, channel: str) -> None:
        """Start tracking a new conversation."""
        self.active_conversations[conversation_id] = {
            "organization_id": organization_id,
            "user_id": user_id,
            "channel": channel,
            "start_time": datetime.utcnow(),
            "message_count": 0,
            "user_message_count": 0,
            "ai_message_count": 0,
            "agent_message_count": 0,
            "state_transitions": 0,
            "escalations": 0,
            "transfers": 0,
            "ai_fallback_count": 0,
            "knowledge_used_count": 0,
            "intent_confidences": [],
            "sentiment_scores": [],
            "emotion_intensities": [],
            "response_times": [],
            "first_response_time": None,
            "emotions": [],
            "emotion_timeline": [],
            "business_rules_applied": 0,
            "workflows_triggered": 0,
            "sla_breached": False,
            "sla_breach_start": None,
            "current_state": "initialized",
            "state_history": [],
            "resolution": None
        }
        
        self.logger.info(f"Started conversation tracking: {conversation_id} for org {organization_id} on channel {channel}")
    
    def record_message_processed(self, conversation_id: str, message_id: str,
                               sender_type: str, content_length: int,
                               processing_time_ms: int, metrics: Dict[str, Any]) -> None:
        """Record message processing metrics."""
        if conversation_id not in self.active_conversations:
            self.logger.warning(
                "Attempted to record message for untracked conversation",
                conversation_id=conversation_id
            )
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["message_count"] += 1
        
        if sender_type == "user":
            conversation["user_message_count"] += 1
        elif sender_type == "ai_agent":
            conversation["ai_message_count"] += 1
        elif sender_type == "human_agent":
            conversation["agent_message_count"] += 1
        
        # Record first response time
        if conversation["first_response_time"] is None and sender_type == "ai_agent":
            first_user_time = None
            for state_record in conversation["state_history"]:
                if state_record.get("to_state") == "active":
                    first_user_time = state_record["timestamp"]
                    break
            
            if first_user_time:
                conversation["first_response_time"] = (datetime.utcnow() - first_user_time).total_seconds()
        
        # Record response times
        conversation["response_times"].append(processing_time_ms / 1000.0)
        
        # Record AI metrics
        if metrics.get("intent_confidence"):
            conversation["intent_confidences"].append(metrics["intent_confidence"])
        
        if metrics.get("sentiment_score") is not None:
            conversation["sentiment_scores"].append(metrics["sentiment_score"])
        
        if metrics.get("emotion_intensity") is not None:
            conversation["emotion_intensities"].append(metrics["emotion_intensity"])
        
        if metrics.get("emotion"):
            conversation["emotions"].append(metrics["emotion"])
            conversation["emotion_timeline"].append({
                "emotion": metrics["emotion"],
                "intensity": metrics.get("emotion_intensity", 0.0),
                "timestamp": datetime.utcnow()
            })
        
        # Record AI performance metrics
        if metrics.get("model_used"):
            self._record_ai_performance(
                metrics["model_used"],
                metrics.get("capability", "unknown"),
                processing_time_ms,
                metrics.get("confidence", 0.0),
                metrics.get("token_usage", {}),
                metrics.get("cache_hit", False),
                metrics.get("fallback_triggered", False)
            )
        
        # Create message metrics
        message_metric = MessageMetrics(
            message_id=message_id,
            conversation_id=conversation_id,
            sender_type=sender_type,
            content_length=content_length,
            processing_time_ms=processing_time_ms,
            intent=metrics.get("intent"),
            intent_confidence=metrics.get("intent_confidence", 0.0),
            sentiment=metrics.get("sentiment"),
            sentiment_score=metrics.get("sentiment_score", 0.0),
            sentiment_confidence=metrics.get("sentiment_confidence", 0.0),
            emotion=metrics.get("emotion"),
            emotion_intensity=metrics.get("emotion_intensity", 0.0),
            emotion_confidence=metrics.get("emotion_confidence", 0.0),
            entities_count=metrics.get("entities_count", 0),
            language=metrics.get("language", "en"),
            translation_used=metrics.get("translation_used", False),
            model_used=metrics.get("model_used", ""),
            token_usage=metrics.get("token_usage", {}),
            confidence=metrics.get("confidence", 0.0)
        )
        
        self.message_metrics.append(message_metric)
        
        self.logger.debug(
            "Recorded message metrics",
            conversation_id=conversation_id,
            message_id=message_id,
            sender_type=sender_type,
            processing_time_ms=processing_time_ms
        )
    
    def record_state_transition(self, conversation_id: str, from_state: str, to_state: str,
                              reason: Optional[str] = None) -> None:
        """Record conversation state transition."""
        if conversation_id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["state_transitions"] += 1
        conversation["current_state"] = to_state
        
        state_record = {
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": datetime.utcnow()
        }
        conversation["state_history"].append(state_record)
        
        # Track specific state metrics
        if to_state == "escalated":
            conversation["escalations"] += 1
        elif to_state == "transferred":
            conversation["transfers"] += 1
        
        self.logger.debug(
            "Recorded state transition",
            conversation_id=conversation_id,
            from_state=from_state,
            to_state=to_state
        )
    
    def record_resolution(self, conversation_id: str, resolved: bool, resolution_type: Optional[str] = None,
                        satisfaction_score: Optional[float] = None, nps_score: Optional[int] = None) -> None:
        """Record conversation resolution."""
        if conversation_id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["resolution"] = {
            "resolved": resolved,
            "resolution_type": resolution_type,
            "satisfaction_score": satisfaction_score,
            "nps_score": nps_score,
            "timestamp": datetime.utcnow()
        }
        
        self.logger.info(f"Recorded conversation resolution for {conversation_id}: resolved={resolved} type={resolution_type} satisfaction={satisfaction_score}")
    
    def record_sla_breach(self, conversation_id: str, breach_type: str,
                        breach_duration_seconds: float) -> None:
        """Record SLA breach."""
        if conversation_id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["sla_breached"] = True
        conversation["sla_breach_duration_seconds"] = breach_duration_seconds
        
        if conversation["sla_breach_start"] is None:
            conversation["sla_breach_start"] = datetime.utcnow()
        
        self.logger.warning(f"Recorded SLA breach for {conversation_id}: {breach_type} duration={breach_duration_seconds}s")
    
    def record_business_rule_applied(self, conversation_id: str, rule_id: str, rule_name: str,
                                   result: str) -> None:
        """Record business rule application."""
        if conversation_id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["business_rules_applied"] += 1
        
        self.logger.debug(
            "Recorded business rule application",
            conversation_id=conversation_id,
            rule_id=rule_id,
            result=result
        )
    
    def record_workflow_triggered(self, conversation_id: str, workflow_id: str, workflow_name: str,
                                status: str) -> None:
        """Record workflow trigger."""
        if conversation_id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["workflows_triggered"] += 1
        
        self.logger.debug(
            "Recorded workflow trigger",
            conversation_id=conversation_id,
            workflow_id=workflow_id,
            status=status
        )
    
    def _record_ai_performance(self, model_name: str, capability: str, latency_ms: int,
                             confidence: float, token_usage: Dict[str, int], cache_hit: bool,
                             fallback_triggered: bool) -> None:
        """Record AI performance metrics."""
        key = f"{model_name}:{capability}"
        
        if key not in self.ai_performance_metrics:
            self.ai_performance_metrics[key] = AIPerformanceMetrics(
                model_name=model_name,
                capability=capability
            )
        
        metrics = self.ai_performance_metrics[key]
        metrics.total_requests += 1
        
        if fallback_triggered:
            metrics.fallback_rate = (metrics.fallback_rate * (metrics.total_requests - 1) + 1) / metrics.total_requests
        else:
            metrics.successful_requests += 1
            
            # Update latency metrics
            metrics.avg_latency_ms = (metrics.avg_latency_ms * (metrics.successful_requests - 1) + latency_ms) / metrics.successful_requests
            
            # Simple percentile calculation (in production, use proper percentile algorithms)
            if latency_ms > metrics.p99_latency_ms:
                metrics.p99_latency_ms = latency_ms
            if latency_ms > metrics.p95_latency_ms:
                metrics.p95_latency_ms = latency_ms
            if latency_ms > metrics.p50_latency_ms:
                metrics.p50_latency_ms = latency_ms
            
            # Update confidence
            metrics.avg_confidence = (metrics.avg_confidence * (metrics.successful_requests - 1) + confidence) / metrics.successful_requests
            
            # Update token usage
            total_tokens = token_usage.get("total_tokens", 0)
            metrics.avg_tokens_used = (metrics.avg_tokens_used * (metrics.successful_requests - 1) + total_tokens) / metrics.successful_requests
            
            # Cache hit rate
            if cache_hit:
                metrics.cache_hit_rate = (metrics.cache_hit_rate * (metrics.successful_requests - 1) + 1) / metrics.successful_requests
    
    def finalize_conversation(self, conversation_id: str) -> ConversationMetrics:
        """Finalize conversation tracking and return metrics."""
        if conversation_id not in self.active_conversations:
            self.logger.warning(
                "Attempted to finalize untracked conversation",
                conversation_id=conversation_id
            )
            return None
        
        conversation = self.active_conversations[conversation_id]
        end_time = datetime.utcnow()
        
        # Calculate derived metrics
        duration_seconds = (end_time - conversation["start_time"]).total_seconds()
        
        # Calculate averages
        avg_intent_confidence = (
            sum(conversation["intent_confidences"]) / len(conversation["intent_confidences"])
            if conversation["intent_confidences"] else 0.0
        )
        
        avg_sentiment_score = (
            sum(conversation["sentiment_scores"]) / len(conversation["sentiment_scores"])
            if conversation["sentiment_scores"] else 0.0
        )
        
        avg_emotion_intensity = (
            sum(conversation["emotion_intensities"]) / len(conversation["emotion_intensities"])
            if conversation["emotion_intensities"] else 0.0
        )
        
        # Calculate response times
        avg_response_time = (
            sum(conversation["response_times"]) / len(conversation["response_times"])
            if conversation["response_times"] else None
        )
        
        max_response_time = max(conversation["response_times"]) if conversation["response_times"] else None
        
        # Determine primary emotion
        primary_emotion = None
        if conversation["emotions"]:
            emotion_counts = {}
            for emotion in conversation["emotions"]:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            primary_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        
        # Calculate emotion durations
        negative_duration = 0.0
        positive_duration = 0.0
        
        for i, emotion_record in enumerate(conversation["emotion_timeline"]):
            if i == 0:
                continue
            
            time_diff = (emotion_record["timestamp"] - conversation["emotion_timeline"][i-1]["timestamp"]).total_seconds()
            emotion = emotion_record["emotion"]
            
            if emotion in ["angry", "frustrated"]:
                negative_duration += time_diff
            elif emotion in ["happy", "excited", "satisfied"]:
                positive_duration += time_diff
        
        # Determine resolution
        resolved = False
        resolution_type = None
        satisfaction_score = None
        nps_score = None
        resolution_time_seconds = None
        
        if conversation["resolution"]:
            resolved = conversation["resolution"]["resolved"]
            resolution_type = conversation["resolution"]["resolution_type"]
            satisfaction_score = conversation["resolution"]["satisfaction_score"]
            nps_score = conversation["resolution"]["nps_score"]
            
            if conversation["resolution"]["timestamp"]:
                resolution_time_seconds = (conversation["resolution"]["timestamp"] - conversation["start_time"]).total_seconds()
        
        # Create metrics object
        metrics = ConversationMetrics(
            conversation_id=conversation_id,
            organization_id=conversation["organization_id"],
            user_id=conversation["user_id"],
            channel=conversation["channel"],
            start_time=conversation["start_time"],
            end_time=end_time,
            duration_seconds=duration_seconds,
            message_count=conversation["message_count"],
            user_message_count=conversation["user_message_count"],
            ai_message_count=conversation["ai_message_count"],
            agent_message_count=conversation["agent_message_count"],
            state_transitions=conversation["state_transitions"],
            escalations=conversation["escalations"],
            transfers=conversation["transfers"],
            avg_intent_confidence=avg_intent_confidence,
            avg_sentiment_score=avg_sentiment_score,
            avg_emotion_intensity=avg_emotion_intensity,
            ai_fallback_count=conversation["ai_fallback_count"],
            knowledge_used_count=conversation["knowledge_used_count"],
            resolved=resolved,
            resolution_time_seconds=resolution_time_seconds,
            resolution_type=resolution_type,
            satisfaction_score=satisfaction_score,
            nps_score=nps_score,
            first_response_time_seconds=conversation["first_response_time"],
            avg_response_time_seconds=avg_response_time,
            max_response_time_seconds=max_response_time,
            primary_emotion=primary_emotion,
            emotion_changes=len(conversation["emotion_timeline"]),
            negative_emotion_duration=negative_duration,
            positive_emotion_duration=positive_duration,
            sla_breached=conversation["sla_breached"],
            sla_breach_duration_seconds=conversation.get("sla_breach_duration_seconds", 0.0),
            business_rules_applied=conversation["business_rules_applied"],
            workflows_triggered=conversation["workflows_triggered"]
        )
        
        # Store metrics
        self.conversation_metrics.append(metrics)
        
        # Remove from active tracking
        del self.active_conversations[conversation_id]
        
        self.logger.info(f"Finalized conversation metrics for {conversation_id}: duration={duration_seconds}s messages={conversation['message_count']} resolved={resolved}")
        
        return metrics
    
    def get_active_conversation_metrics(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get current metrics for active conversation."""
        if conversation_id not in self.active_conversations:
            return None
        
        conversation = self.active_conversations[conversation_id]
        
        # Calculate current metrics
        current_time = datetime.utcnow()
        duration_seconds = (current_time - conversation["start_time"]).total_seconds()
        
        avg_intent_confidence = (
            sum(conversation["intent_confidences"]) / len(conversation["intent_confidences"])
            if conversation["intent_confidences"] else 0.0
        )
        
        avg_sentiment_score = (
            sum(conversation["sentiment_scores"]) / len(conversation["sentiment_scores"])
            if conversation["sentiment_scores"] else 0.0
        )
        
        avg_response_time = (
            sum(conversation["response_times"]) / len(conversation["response_times"])
            if conversation["response_times"] else None
        )
        
        return {
            "conversation_id": conversation_id,
            "duration_seconds": duration_seconds,
            "message_count": conversation["message_count"],
            "user_message_count": conversation["user_message_count"],
            "ai_message_count": conversation["ai_message_count"],
            "state_transitions": conversation["state_transitions"],
            "escalations": conversation["escalations"],
            "avg_intent_confidence": avg_intent_confidence,
            "avg_sentiment_score": avg_sentiment_score,
            "first_response_time_seconds": conversation["first_response_time"],
            "avg_response_time_seconds": avg_response_time,
            "sla_breached": conversation["sla_breached"],
            "current_state": conversation["current_state"]
        }
    
    def get_historical_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get historical metrics for specified time range."""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range_hours)
        
        recent_metrics = [
            metric for metric in self.conversation_metrics
            if metric.start_time >= cutoff_time
        ]
        
        if not recent_metrics:
            return self._get_empty_metrics()
        
        # Calculate aggregated metrics
        total_conversations = len(recent_metrics)
        resolved_conversations = sum(1 for m in recent_metrics if m.resolved)
        escalated_conversations = sum(1 for m in recent_metrics if m.escalations > 0)
        
        avg_duration = sum(m.duration_seconds for m in recent_metrics if m.duration_seconds) / total_conversations
        avg_message_count = sum(m.message_count for m in recent_metrics) / total_conversations
        avg_intent_confidence = sum(m.avg_intent_confidence for m in recent_metrics) / total_conversations
        avg_sentiment_score = sum(m.avg_sentiment_score for m in recent_metrics) / total_conversations
        
        # Calculate satisfaction metrics
        satisfaction_scores = [m.satisfaction_score for m in recent_metrics if m.satisfaction_score is not None]
        avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else None
        
        nps_scores = [m.nps_score for m in recent_metrics if m.nps_score is not None]
        avg_nps = sum(nps_scores) / len(nps_scores) if nps_scores else None
        
        # Performance metrics
        response_times = [m.avg_response_time_seconds for m in recent_metrics if m.avg_response_time_seconds]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        first_response_times = [m.first_response_time_seconds for m in recent_metrics if m.first_response_time_seconds]
        avg_first_response_time = sum(first_response_times) / len(first_response_times) if first_response_times else None
        
        # SLA metrics
        sla_breach_count = sum(1 for m in recent_metrics if m.sla_breached)
        sla_breach_rate = sla_breach_count / total_conversations if total_conversations > 0 else 0.0
        
        return {
            "time_range_hours": time_range_hours,
            "total_conversations": total_conversations,
            "resolved_conversations": resolved_conversations,
            "resolution_rate": resolved_conversations / total_conversations if total_conversations > 0 else 0.0,
            "escalated_conversations": escalated_conversations,
            "escalation_rate": escalated_conversations / total_conversations if total_conversations > 0 else 0.0,
            "avg_duration_seconds": avg_duration,
            "avg_message_count": avg_message_count,
            "avg_intent_confidence": avg_intent_confidence,
            "avg_sentiment_score": avg_sentiment_score,
            "avg_satisfaction_score": avg_satisfaction,
            "avg_nps_score": avg_nps,
            "avg_response_time_seconds": avg_response_time,
            "avg_first_response_time_seconds": avg_first_response_time,
            "sla_breach_count": sla_breach_count,
            "sla_breach_rate": sla_breach_rate
        }
    
    def _get_empty_metrics(self) -> Dict[str, Any]:
        """Get empty metrics structure."""
        return {
            "time_range_hours": 0,
            "total_conversations": 0,
            "resolved_conversations": 0,
            "resolution_rate": 0.0,
            "escalated_conversations": 0,
            "escalation_rate": 0.0,
            "avg_duration_seconds": 0.0,
            "avg_message_count": 0.0,
            "avg_intent_confidence": 0.0,
            "avg_sentiment_score": 0.0,
            "avg_satisfaction_score": None,
            "avg_nps_score": None,
            "avg_response_time_seconds": None,
            "avg_first_response_time_seconds": None,
            "sla_breach_count": 0,
            "sla_breach_rate": 0.0
        }
    
    def get_ai_performance_summary(self) -> Dict[str, Any]:
        """Get AI performance summary."""
        if not self.ai_performance_metrics:
            return {}
        
        summary = {
            "models": {},
            "overall": {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_latency_ms": 0.0,
                "avg_confidence": 0.0,
                "avg_cache_hit_rate": 0.0,
                "avg_fallback_rate": 0.0
            }
        }
        
        total_requests = 0
        total_successful = 0
        total_failed = 0
        total_latency = 0.0
        total_confidence = 0.0
        total_cache_hit_rate = 0.0
        total_fallback_rate = 0.0
        
        for key, metrics in self.ai_performance_metrics.items():
            summary["models"][key] = {
                "model_name": metrics.model_name,
                "capability": metrics.capability,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0,
                "avg_latency_ms": metrics.avg_latency_ms,
                "p50_latency_ms": metrics.p50_latency_ms,
                "p95_latency_ms": metrics.p95_latency_ms,
                "p99_latency_ms": metrics.p99_latency_ms,
                "avg_confidence": metrics.avg_confidence,
                "avg_tokens_used": metrics.avg_tokens_used,
                "avg_cost": metrics.avg_cost,
                "cache_hit_rate": metrics.cache_hit_rate,
                "fallback_rate": metrics.fallback_rate
            }
            
            total_requests += metrics.total_requests
            total_successful += metrics.successful_requests
            total_failed += metrics.failed_requests
            total_latency += metrics.avg_latency_ms
            total_confidence += metrics.avg_confidence
            total_cache_hit_rate += metrics.cache_hit_rate
            total_fallback_rate += metrics.fallback_rate
        
        # Calculate overall metrics
        model_count = len(self.ai_performance_metrics)
        if model_count > 0:
            summary["overall"] = {
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "success_rate": total_successful / total_requests if total_requests > 0 else 0.0,
                "avg_latency_ms": total_latency / model_count,
                "avg_confidence": total_confidence / model_count,
                "avg_cache_hit_rate": total_cache_hit_rate / model_count,
                "avg_fallback_rate": total_fallback_rate / model_count
            }
        
        return summary
    
    def emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit analytics event for external consumption."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # In a real implementation, this would send to event bus or analytics service
        self.logger.info(f"Analytics event emitted: {event}")
    
    def cleanup_old_metrics(self, max_age_days: int = 90) -> int:
        """Clean up metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        
        # Clean up conversation metrics
        old_conversations = [
            i for i, metric in enumerate(self.conversation_metrics)
            if metric.start_time < cutoff_date
        ]
        
        removed_conversations = len(old_conversations)
        for i in reversed(old_conversations):
            del self.conversation_metrics[i]
        
        # Clean up message metrics
        old_messages = [
            i for i, metric in enumerate(self.message_metrics)
            if metric.timestamp < cutoff_date
        ]
        
        removed_messages = len(old_messages)
        for i in reversed(old_messages):
            del self.message_metrics[i]
        
        self.logger.info(
            "Cleaned up old metrics",
            removed_conversations=removed_conversations,
            removed_messages=removed_messages,
            max_age_days=max_age_days
        )
        
        return removed_conversations + removed_messages
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "active_conversations": len(self.active_conversations),
            "total_conversations_tracked": len(self.conversation_metrics),
            "total_messages_tracked": len(self.message_metrics),
            "ai_models_tracked": len(self.ai_performance_metrics),
            "recent_metrics": self.get_historical_metrics(24),  # Last 24 hours
            "ai_performance": self.get_ai_performance_summary()
        }