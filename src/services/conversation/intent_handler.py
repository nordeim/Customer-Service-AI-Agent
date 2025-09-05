"""Intent-specific handler framework for specialized conversation processing."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union
from uuid import UUID

from src.core.exceptions import IntentHandlingError
from src.core.logging import get_logger
from src.services.conversation.context import ConversationContext

logger = get_logger(__name__)


@dataclass
class IntentResult:
    """Result of intent-specific processing."""
    intent: str
    success: bool
    response_text: str = ""
    context_updates: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_escalation: bool = False
    escalation_reason: Optional[str] = None
    suggested_actions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time_ms: int = 0


@dataclass
class IntentContext:
    """Context specific to intent processing."""
    intent: str
    confidence: float
    parameters: Dict[str, Any]
    original_message: str
    conversation_id: UUID
    user_id: Optional[UUID]
    organization_id: Optional[UUID]
    channel: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    previous_intents: List[str] = field(default_factory=list)
    user_history: List[Dict[str, Any]] = field(default_factory=list)


class BaseIntentHandler(ABC):
    """Base class for all intent-specific handlers."""
    
    INTENT_NAME: str = ""
    DESCRIPTION: str = ""
    CONFIDENCE_THRESHOLD: float = 0.7
    MAX_PROCESSING_TIME_MS: int = 10000  # 10 seconds
    REQUIRES_ESCALATION: bool = False
    SUPPORTED_CHANNELS: List[str] = ["web_chat", "mobile_ios", "mobile_android", "email", "slack", "teams"]
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """Check if this handler can process the given intent context."""
        pass
    
    @abstractmethod
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process the intent and return result."""
        pass
    
    async def validate_context(self, intent_context: IntentContext) -> bool:
        """Validate that the intent context has required information."""
        if not intent_context.intent:
            self.logger.error("Intent context missing intent name")
            return False
        
        if intent_context.confidence < self.CONFIDENCE_THRESHOLD:
            self.logger.warning(
                "Intent confidence below threshold",
                intent=intent_context.intent,
                confidence=intent_context.confidence,
                threshold=self.CONFIDENCE_THRESHOLD
            )
            return False
        
        if intent_context.channel not in self.SUPPORTED_CHANNELS:
            self.logger.warning(
                "Channel not supported by handler",
                channel=intent_context.channel,
                supported_channels=self.SUPPORTED_CHANNELS
            )
            return False
        
        return True
    
    def get_required_parameters(self) -> List[str]:
        """Get list of required parameters for this handler."""
        return []
    
    def get_optional_parameters(self) -> List[str]:
        """Get list of optional parameters for this handler."""
        return []
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate intent parameters."""
        required_params = self.get_required_parameters()
        missing_params = []
        
        for param in required_params:
            if param not in parameters or not parameters[param]:
                missing_params.append(param)
        
        return len(missing_params) == 0, missing_params
    
    async def create_error_result(self, intent_context: IntentContext, error_message: str,
                                error_type: str = "processing_error") -> IntentResult:
        """Create error result for failed processing."""
        return IntentResult(
            intent=intent_context.intent,
            success=False,
            response_text="I apologize, but I'm having trouble processing your request. Could you please rephrase or provide more details?",
            metadata={
                "error_type": error_type,
                "error_message": error_message,
                "handler": self.INTENT_NAME
            },
            confidence=0.3,
            requires_escalation=True,
            escalation_reason=f"{self.INTENT_NAME}_processing_error"
        )


class TechnicalSupportHandler(BaseIntentHandler):
    """Handler for technical support intents."""
    
    INTENT_NAME = "technical_support"
    DESCRIPTION = "Handles technical issues, errors, and troubleshooting requests"
    CONFIDENCE_THRESHOLD = 0.75
    REQUIRES_ESCALATION = False
    
    # Technical keywords that indicate this handler should be used
    TECHNICAL_KEYWORDS = [
        "error", "bug", "issue", "problem", "broken", "not working",
        "failure", "crash", "exception", "timeout", "connection",
        "api", "database", "server", "deployment", "configuration"
    ]
    
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """Check if this is a technical support request."""
        if intent_context.intent != self.INTENT_NAME:
            return False
        
        # Check for technical keywords in original message
        message_lower = intent_context.original_message.lower()
        return any(keyword in message_lower for keyword in self.TECHNICAL_KEYWORDS)
    
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process technical support request."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info(
                "Processing technical support intent",
                conversation_id=intent_context.conversation_id,
                parameters=intent_context.parameters
            )
            
            # Validate parameters
            is_valid, missing_params = self.validate_parameters(intent_context.parameters)
            if not is_valid:
                return await self.create_error_result(
                    intent_context,
                    f"Missing required parameters: {', '.join(missing_params)}"
                )
            
            # Extract technical details
            error_code = intent_context.parameters.get("error_code")
            system_component = intent_context.parameters.get("system_component")
            issue_description = intent_context.parameters.get("issue_description")
            
            # Generate technical response
            response_text = await self._generate_technical_response(
                error_code, system_component, issue_description, conversation_context
            )
            
            # Check if escalation is needed
            requires_escalation, escalation_reason = self._should_escalate_technical_issue(
                error_code, system_component, issue_description, conversation_context
            )
            
            # Calculate confidence based on available information
            confidence = self._calculate_confidence(intent_context, conversation_context)
            
            processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            return IntentResult(
                intent=self.INTENT_NAME,
                success=True,
                response_text=response_text,
                context_updates={
                    "last_technical_issue": {
                        "error_code": error_code,
                        "system_component": system_component,
                        "resolved": not requires_escalation
                    }
                },
                metadata={
                    "error_code": error_code,
                    "system_component": system_component,
                    "issue_complexity": self._assess_issue_complexity(error_code, system_component)
                },
                requires_escalation=requires_escalation,
                escalation_reason=escalation_reason,
                suggested_actions=["technical_diagnosis", "knowledge_base_lookup"],
                confidence=confidence,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            self.logger.error(
                "Technical support processing failed",
                conversation_id=intent_context.conversation_id,
                error=str(e)
            )
            return await self.create_error_result(intent_context, str(e))
    
    async def _generate_technical_response(self, error_code: Optional[str], system_component: Optional[str],
                                         issue_description: Optional[str], context: ConversationContext) -> str:
        """Generate technical support response."""
        response_parts = []
        
        # Acknowledge the issue
        if error_code:
            response_parts.append(f"I see you're encountering error code {error_code}.")
        elif system_component:
            response_parts.append(f"I understand you're having issues with {system_component}.")
        else:
            response_parts.append("I understand you're experiencing a technical issue.")
        
        # Add specific guidance based on component
        if system_component:
            component_guidance = self._get_component_guidance(system_component, error_code)
            if component_guidance:
                response_parts.append(component_guidance)
        
        # Add general troubleshooting steps
        response_parts.append(self._get_troubleshooting_steps(error_code, system_component))
        
        # Offer further assistance
        response_parts.append("If these steps don't resolve the issue, I can escalate this to our technical team for further assistance.")
        
        return " ".join(response_parts)
    
    def _get_component_guidance(self, system_component: str, error_code: Optional[str]) -> Optional[str]:
        """Get specific guidance for system component."""
        component_guidance = {
            "api": "Let me check our API documentation for this specific error.",
            "database": "This could be related to connection settings or query optimization.",
            "deployment": "Deployment issues often relate to configuration or environment settings.",
            "authentication": "Authentication issues typically involve token validation or user permissions.",
            "integration": "Integration issues may require checking external service connectivity."
        }
        
        return component_guidance.get(system_component.lower())
    
    def _get_troubleshooting_steps(self, error_code: Optional[str], system_component: Optional[str]) -> str:
        """Get general troubleshooting steps."""
        steps = [
            "Here are some steps we can try:",
            "1. Verify your connection and authentication settings",
            "2. Check if there are any recent changes to your configuration",
            "3. Review the error logs for more detailed information"
        ]
        
        if error_code:
            steps.append(f"4. Look up error code {error_code} in our documentation")
        
        return " ".join(steps)
    
    def _should_escalate_technical_issue(self, error_code: Optional[str], system_component: Optional[str],
                                       issue_description: Optional[str], context: ConversationContext) -> tuple[bool, Optional[str]]:
        """Determine if technical issue should be escalated."""
        
        # Escalate based on error code severity
        if error_code:
            # Simple heuristic - escalate specific error code patterns
            if any(pattern in error_code.upper() for pattern in ["CRITICAL", "FATAL", "SYSTEM"]):
                return True, "critical_error_code"
            
            # Escalate if same error code appeared multiple times
            if self._is_repeated_error(error_code, context):
                return True, "repeated_error"
        
        # Escalate based on component criticality
        if system_component and system_component.lower() in ["database", "authentication", "core_api"]:
            return True, "critical_system_component"
        
        # Check conversation history for repeated technical issues
        if self._has_repeated_technical_issues(context):
            return True, "repeated_technical_issues"
        
        return False, None
    
    def _is_repeated_error(self, error_code: str, context: ConversationContext) -> bool:
        """Check if this error code has appeared multiple times."""
        # This would check conversation history - simplified for now
        return False
    
    def _has_repeated_technical_issues(self, context: ConversationContext) -> bool:
        """Check if conversation has repeated technical issues."""
        # Check AI context for repeated technical intents
        recent_intents = [record["intent"] for record in context.ai_context.intent_history[-5:]]
        technical_intent_count = sum(1 for intent in recent_intents if intent == self.INTENT_NAME)
        return technical_intent_count >= 3
    
    def _assess_issue_complexity(self, error_code: Optional[str], system_component: Optional[str]) -> str:
        """Assess the complexity of the technical issue."""
        if error_code and system_component:
            return "high"
        elif error_code or system_component:
            return "medium"
        else:
            return "low"
    
    def _calculate_confidence(self, intent_context: IntentContext, conversation_context: ConversationContext) -> float:
        """Calculate confidence score for technical support processing."""
        base_confidence = intent_context.confidence
        
        # Boost confidence if we have specific technical details
        if intent_context.parameters.get("error_code") or intent_context.parameters.get("system_component"):
            base_confidence += 0.1
        
        # Reduce confidence if this is a repeated issue
        if self._has_repeated_technical_issues(conversation_context):
            base_confidence -= 0.2
        
        return max(0.3, min(1.0, base_confidence))
    
    def get_required_parameters(self) -> List[str]:
        """Get required parameters for technical support."""
        return []
    
    def get_optional_parameters(self) -> List[str]:
        """Get optional parameters for technical support."""
        return ["error_code", "system_component", "issue_description", "steps_taken", "environment"]


class AccountManagementHandler(BaseIntentHandler):
    """Handler for account management intents."""
    
    INTENT_NAME = "account_management"
    DESCRIPTION = "Handles account-related requests like password reset, profile updates, billing"
    CONFIDENCE_THRESHOLD = 0.7
    REQUIRES_ESCALATION = False
    
    ACCOUNT_KEYWORDS = [
        "account", "profile", "password", "login", "sign in", "billing", "subscription",
        "payment", "invoice", "plan", "upgrade", "downgrade", "cancel"
    ]
    
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """Check if this is an account management request."""
        if intent_context.intent != self.INTENT_NAME:
            return False
        
        message_lower = intent_context.original_message.lower()
        return any(keyword in message_lower for keyword in self.ACCOUNT_KEYWORDS)
    
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process account management request."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info(
                "Processing account management intent",
                conversation_id=intent_context.conversation_id,
                parameters=intent_context.parameters
            )
            
            # Extract account action
            action = intent_context.parameters.get("action", "general_inquiry")
            
            # Route to specific account action handler
            if action == "password_reset":
                return await self._handle_password_reset(intent_context, conversation_context)
            elif action == "billing_inquiry":
                return await self._handle_billing_inquiry(intent_context, conversation_context)
            elif action == "plan_change":
                return await self._handle_plan_change(intent_context, conversation_context)
            elif action == "profile_update":
                return await self._handle_profile_update(intent_context, conversation_context)
            else:
                return await self._handle_general_account_inquiry(intent_context, conversation_context)
                
        except Exception as e:
            self.logger.error(
                "Account management processing failed",
                conversation_id=intent_context.conversation_id,
                error=str(e)
            )
            return await self.create_error_result(intent_context, str(e))
    
    async def _handle_password_reset(self, intent_context: IntentContext, context: ConversationContext) -> IntentResult:
        """Handle password reset requests."""
        return IntentResult(
            intent=self.INTENT_NAME,
            success=True,
            response_text="I can help you reset your password. I'll send a password reset link to your registered email address. Please check your email and follow the instructions to create a new password.",
            context_updates={"password_reset_requested": True},
            metadata={"action": "password_reset"},
            suggested_actions=["email_verification", "security_check"],
            confidence=0.9
        )
    
    async def _handle_billing_inquiry(self, intent_context: IntentContext, context: ConversationContext) -> IntentResult:
        """Handle billing-related inquiries."""
        billing_type = intent_context.parameters.get("billing_type", "general")
        
        if billing_type == "invoice":
            response = "I can help you with invoice inquiries. Let me check your recent invoices and payment history."
        elif billing_type == "payment_method":
            response = "I can help you update your payment method. Would you like to add a new credit card or bank account?"
        elif billing_type == "refund":
            response = "I understand you're requesting a refund. Let me review your account to see what options are available."
        else:
            response = "I can help you with your billing questions. What specific billing issue would you like me to address?"
        
        return IntentResult(
            intent=self.INTENT_NAME,
            success=True,
            response_text=response,
            metadata={"billing_type": billing_type},
            suggested_actions=["account_verification", "billing_history_review"],
            confidence=0.8
        )
    
    async def _handle_plan_change(self, intent_context: IntentContext, context: ConversationContext) -> IntentResult:
        """Handle plan upgrade/downgrade requests."""
        change_type = intent_context.parameters.get("change_type", "inquiry")
        
        if change_type == "upgrade":
            response = "I'd be happy to help you upgrade your plan! Let me show you the available upgrade options and their benefits."
        elif change_type == "downgrade":
            response = "I can help you explore downgrade options. Let me review your current plan usage to ensure a downgrade won't impact your service."
        else:
            response = "I can help you with plan changes. Would you like to upgrade, downgrade, or just explore your options?"
        
        return IntentResult(
            intent=self.INTENT_NAME,
            success=True,
            response_text=response,
            metadata={"change_type": change_type},
            suggested_actions=["plan_comparison", "usage_analysis"],
            confidence=0.8
        )
    
    async def _handle_profile_update(self, intent_context: IntentContext, context: ConversationContext) -> IntentResult:
        """Handle profile update requests."""
        update_type = intent_context.parameters.get("update_type", "general")
        
        response = "I can help you update your profile information. What specific details would you like to change?"
        
        return IntentResult(
            intent=self.INTENT_NAME,
            success=True,
            response_text=response,
            metadata={"update_type": update_type},
            suggested_actions=["profile_verification", "update_form"],
            confidence=0.8
        )
    
    async def _handle_general_account_inquiry(self, intent_context: IntentContext, context: ConversationContext) -> IntentResult:
        """Handle general account inquiries."""
        return IntentResult(
            intent=self.INTENT_NAME,
            success=True,
            response_text="I can help you with various account-related tasks. What would you like to do with your account today?",
            metadata={"action": "general_inquiry"},
            suggested_actions=["account_overview", "help_menu"],
            confidence=0.7
        )


class BillingInquiryHandler(BaseIntentHandler):
    """Handler for billing-specific inquiries."""
    
    INTENT_NAME = "billing_inquiry"
    DESCRIPTION = "Handles billing, payment, and subscription-related questions"
    CONFIDENCE_THRESHOLD = 0.8
    REQUIRES_ESCALATION = False
    
    BILLING_KEYWORDS = [
        "billing", "payment", "invoice", "charge", "refund", "subscription",
        "plan", "price", "cost", "amount", "credit card", "bank", "transaction"
    ]
    
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """Check if this is a billing inquiry."""
        if intent_context.intent != self.INTENT_NAME:
            return False
        
        message_lower = intent_context.original_message.lower()
        return any(keyword in message_lower for keyword in self.BILLING_KEYWORDS)
    
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process billing inquiry."""
        try:
            billing_type = intent_context.parameters.get("billing_type", "general")
            amount = intent_context.parameters.get("amount")
            date_range = intent_context.parameters.get("date_range")
            
            if billing_type == "refund_request":
                response_text = "I understand you're requesting a refund. Let me review your account and recent transactions to see what options are available to you."
            elif billing_type == "payment_issue":
                response_text = "I can help you resolve payment issues. Let me check your payment methods and recent payment history."
            elif billing_type == "invoice_question":
                response_text = "I can help you understand your invoice. Let me pull up your recent billing details."
            elif amount:
                response_text = f"I see you're asking about a charge of {amount}. Let me review this transaction for you."
            else:
                response_text = "I can help you with billing questions. What specific billing matter would you like me to address?"
            
            return IntentResult(
                intent=self.INTENT_NAME,
                success=True,
                response_text=response_text,
                metadata={"billing_type": billing_type, "amount": amount, "date_range": date_range},
                suggested_actions=["billing_history", "payment_method_review", "refund_eligibility"],
                confidence=0.85
            )
            
        except Exception as e:
            self.logger.error(f"Billing inquiry processing failed: {str(e)}")
            return await self.create_error_result(intent_context, str(e))


class GeneralQuestionHandler(BaseIntentHandler):
    """Handler for general questions and information requests."""
    
    INTENT_NAME = "general_question"
    DESCRIPTION = "Handles general questions, FAQs, and information requests"
    CONFIDENCE_THRESHOLD = 0.6
    REQUIRES_ESCALATION = False
    
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """General handler can handle any general question."""
        return intent_context.intent == self.INTENT_NAME
    
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process general question."""
        try:
            question_type = intent_context.parameters.get("question_type", "general")
            topic = intent_context.parameters.get("topic", "general")
            
            # Use knowledge retrieval to answer general questions
            response_text = await self._generate_general_response(
                intent_context.original_message, question_type, topic, conversation_context
            )
            
            return IntentResult(
                intent=self.INTENT_NAME,
                success=True,
                response_text=response_text,
                metadata={"question_type": question_type, "topic": topic},
                suggested_actions=["related_topics", "further_assistance"],
                confidence=0.7
            )
            
        except Exception as e:
            self.logger.error(f"General question processing failed: {str(e)}")
            return await self.create_error_result(intent_context, str(e))
    
    async def _generate_general_response(self, message: str, question_type: str, topic: str,
                                       context: ConversationContext) -> str:
        """Generate response for general question."""
        # This would typically use knowledge retrieval - simplified for now
        return f"I can help answer your question about {topic}. Let me provide you with the most relevant information."


class EscalationRequestHandler(BaseIntentHandler):
    """Handler for explicit escalation requests."""
    
    INTENT_NAME = "escalation_request"
    DESCRIPTION = "Handles explicit requests to speak with human agent"
    CONFIDENCE_THRESHOLD = 0.9
    REQUIRES_ESCALATION = True
    
    ESCALATION_KEYWORDS = [
        "speak to human", "talk to agent", "escalate", "supervisor", "manager",
        "human help", "real person", "live agent", "transfer to human"
    ]
    
    async def can_handle(self, intent_context: IntentContext) -> bool:
        """Check if this is an escalation request."""
        if intent_context.intent != self.INTENT_NAME:
            return False
        
        message_lower = intent_context.original_message.lower()
        return any(keyword in message_lower for keyword in self.ESCALATION_KEYWORDS)
    
    async def process(self, intent_context: IntentContext, conversation_context: ConversationContext) -> IntentResult:
        """Process escalation request."""
        try:
            escalation_reason = intent_context.parameters.get("reason", "user_requested")
            urgency_level = intent_context.parameters.get("urgency", "normal")
            
            response_text = "I understand you'd like to speak with a human agent. I'm transferring you to one of our customer service representatives who will be able to assist you further. Please hold while I connect you."
            
            return IntentResult(
                intent=self.INTENT_NAME,
                success=True,
                response_text=response_text,
                context_updates={
                    "escalation_requested": True,
                    "escalation_reason": escalation_reason,
                    "urgency_level": urgency_level
                },
                metadata={
                    "escalation_reason": escalation_reason,
                    "urgency_level": urgency_level,
                    "user_requested": True
                },
                requires_escalation=True,
                escalation_reason=escalation_reason,
                suggested_actions=["immediate_agent_transfer", "priority_queue"],
                confidence=0.95
            )
            
        except Exception as e:
            self.logger.error(f"Escalation request processing failed: {str(e)}")
            return await self.create_error_result(intent_context, str(e))


class IntentHandlerRegistry:
    """Registry for managing intent handlers."""
    
    def __init__(self):
        self.handlers: Dict[str, Type[BaseIntentHandler]] = {}
        self.logger = get_logger(__name__)
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default intent handlers."""
        default_handlers = [
            TechnicalSupportHandler,
            AccountManagementHandler,
            BillingInquiryHandler,
            GeneralQuestionHandler,
            EscalationRequestHandler
        ]
        
        for handler_class in default_handlers:
            self.register_handler(handler_class)
    
    def register_handler(self, handler_class: Type[BaseIntentHandler]):
        """Register an intent handler."""
        if not handler_class.INTENT_NAME:
            raise ValueError(f"Handler {handler_class.__name__} must have INTENT_NAME")
        
        self.handlers[handler_class.INTENT_NAME] = handler_class
        self.logger.info(f"Registered intent handler: {handler_class.INTENT_NAME}")
    
    def get_handler(self, intent_name: str) -> Optional[Type[BaseIntentHandler]]:
        """Get handler for specific intent."""
        return self.handlers.get(intent_name)
    
    def get_all_handlers(self) -> List[Type[BaseIntentHandler]]:
        """Get all registered handlers."""
        return list(self.handlers.values())
    
    def unregister_handler(self, intent_name: str):
        """Unregister an intent handler."""
        if intent_name in self.handlers:
            del self.handlers[intent_name]
            self.logger.info(f"Unregistered intent handler: {intent_name}")
    
    async def find_suitable_handler(self, intent_context: IntentContext) -> Optional[BaseIntentHandler]:
        """Find the most suitable handler for the intent context."""
        handler_class = self.get_handler(intent_context.intent)
        if not handler_class:
            return None
        
        handler = handler_class()
        
        # Check if handler can process this specific context
        if await handler.can_handle(intent_context):
            # Validate context
            if await handler.validate_context(intent_context):
                return handler
        
        return None
    
    def get_handler_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered handlers."""
        info = {}
        for intent_name, handler_class in self.handlers.items():
            handler_instance = handler_class()
            info[intent_name] = {
                "name": handler_class.INTENT_NAME,
                "description": handler_class.DESCRIPTION,
                "confidence_threshold": handler_class.CONFIDENCE_THRESHOLD,
                "requires_escalation": handler_class.REQUIRES_ESCALATION,
                "supported_channels": handler_class.SUPPORTED_CHANNELS,
                "required_parameters": handler_instance.get_required_parameters(),
                "optional_parameters": handler_instance.get_optional_parameters()
            }
        
        return info


class IntentHandler:
    """Main intent handler that coordinates intent processing."""
    
    def __init__(self, registry: Optional[IntentHandlerRegistry] = None):
        self.registry = registry or IntentHandlerRegistry()
        self.logger = get_logger(__name__)
    
    async def process_intent(self, intent_context: IntentContext,
                           conversation_context: ConversationContext) -> IntentResult:
        """Process intent using appropriate handler."""
        
        self.logger.info(
            "Processing intent",
            intent=intent_context.intent,
            conversation_id=intent_context.conversation_id,
            confidence=intent_context.confidence
        )
        
        # Find suitable handler
        handler = await self.registry.find_suitable_handler(intent_context)
        
        if not handler:
            self.logger.warning(
                "No suitable handler found for intent",
                intent=intent_context.intent
            )
            return await self._create_fallback_result(intent_context)
        
        # Process with handler
        try:
            result = await handler.process(intent_context, conversation_context)
            
            self.logger.info(
                "Intent processed successfully",
                intent=intent_context.intent,
                success=result.success,
                requires_escalation=result.requires_escalation
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Intent processing failed",
                intent=intent_context.intent,
                error=str(e)
            )
            return await handler.create_error_result(intent_context, str(e))
    
    async def _create_fallback_result(self, intent_context: IntentContext) -> IntentResult:
        """Create fallback result when no suitable handler is found."""
        return IntentResult(
            intent=intent_context.intent,
            success=False,
            response_text="I'm not sure how to help with that specific request. Could you please rephrase or provide more details about what you're looking for?",
            metadata={"fallback": True, "reason": "no_suitable_handler"},
            confidence=0.3,
            requires_escalation=False
        )
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return list(self.registry.handlers.keys())
    
    def get_handler_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about registered handlers."""
        return self.registry.get_handler_info()