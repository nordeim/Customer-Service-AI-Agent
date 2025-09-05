"""Prompt management system with templates and versioning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from src.core.logging import get_logger

logger = get_logger(__name__)


class PromptType(str, Enum):
    """Types of prompts."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TEMPLATE = "template"


class PromptCategory(str, Enum):
    """Categories of prompts."""
    CUSTOMER_SERVICE = "customer_service"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    EMOTION_DETECTION = "emotion_detection"
    LANGUAGE_DETECTION = "language_detection"
    CODE_GENERATION = "code_generation"
    SALESFORCE_ANALYSIS = "salesforce_analysis"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    ESCALATION = "escalation"


@dataclass
class PromptVariable:
    """A variable in a prompt template."""
    name: str
    description: str
    required: bool = True
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None


@dataclass
class PromptTemplate:
    """A prompt template with variables and metadata."""
    id: str
    name: str
    description: str
    category: PromptCategory
    prompt_type: PromptType
    content: str
    variables: List[PromptVariable] = field(default_factory=list)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True


class PromptManager:
    """Manages prompt templates with versioning and variable substitution."""
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._category_index: Dict[PromptCategory, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._load_default_templates()
    
    def register_template(self, template: PromptTemplate) -> None:
        """Register a new prompt template."""
        self._templates[template.id] = template
        
        # Update category index
        if template.category not in self._category_index:
            self._category_index[template.category] = []
        if template.id not in self._category_index[template.category]:
            self._category_index[template.category].append(template.id)
        
        # Update tag index
        for tag in template.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            if template.id not in self._tag_index[tag]:
                self._tag_index[tag].append(template.id)
        
        logger.info(f"Registered prompt template: {template.id}")
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a prompt template by ID."""
        return self._templates.get(template_id)
    
    def get_templates_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """Get all templates in a category."""
        template_ids = self._category_index.get(category, [])
        return [self._templates[tid] for tid in template_ids if self._templates[tid].is_active]
    
    def get_templates_by_tag(self, tag: str) -> List[PromptTemplate]:
        """Get all templates with a specific tag."""
        template_ids = self._tag_index.get(tag, [])
        return [self._templates[tid] for tid in template_ids if self._templates[tid].is_active]
    
    def render_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        strict: bool = True
    ) -> str:
        """Render a prompt template with variable substitution."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        if not template.is_active:
            raise ValueError(f"Template is inactive: {template_id}")
        
        # Validate required variables
        if strict:
            self._validate_variables(template, variables)
        
        # Substitute variables
        content = template.content
        for var in template.variables:
            value = variables.get(var.name, var.default_value)
            if value is None:
                if var.required and strict:
                    raise ValueError(f"Required variable missing: {var.name}")
                continue
            
            # Validate variable value if pattern provided
            if var.validation_pattern and not re.match(var.validation_pattern, str(value)):
                raise ValueError(f"Variable {var.name} does not match validation pattern")
            
            # Replace variable placeholder
            placeholder = f"{{{var.name}}}"
            content = content.replace(placeholder, str(value))
        
        # Check for unresolved variables
        unresolved = re.findall(r'\{(\w+)\}', content)
        if unresolved and strict:
            raise ValueError(f"Unresolved variables: {unresolved}")
        
        return content
    
    def _validate_variables(self, template: PromptTemplate, variables: Dict[str, Any]) -> None:
        """Validate that all required variables are provided."""
        for var in template.variables:
            if var.required and var.name not in variables:
                raise ValueError(f"Required variable missing: {var.name}")
    
    def _load_default_templates(self) -> None:
        """Load default prompt templates."""
        default_templates = [
            PromptTemplate(
                id="customer_service_general",
                name="General Customer Service",
                description="General customer service response template",
                category=PromptCategory.CUSTOMER_SERVICE,
                prompt_type=PromptType.SYSTEM,
                content="""You are a helpful customer service AI assistant. Your role is to:
1. Provide accurate, helpful, and friendly responses to customer inquiries
2. Escalate complex issues to human agents when necessary
3. Maintain a professional and empathetic tone
4. Follow company policies and procedures

Customer context:
- Organization: {organization_name}
- Customer tier: {customer_tier}
- Previous interactions: {interaction_history}

Current conversation:
- Channel: {channel}
- Priority: {priority}
- Issue category: {issue_category}

Please respond to the customer's inquiry while considering their context and maintaining high service quality.""",
                variables=[
                    PromptVariable("organization_name", "Name of the organization", True),
                    PromptVariable("customer_tier", "Customer tier (basic, premium, enterprise)", True),
                    PromptVariable("interaction_history", "Summary of previous interactions", False, ""),
                    PromptVariable("channel", "Communication channel (web, email, phone)", True),
                    PromptVariable("priority", "Issue priority (low, medium, high, urgent)", True),
                    PromptVariable("issue_category", "Category of the issue", True),
                ],
                tags=["customer_service", "general", "default"],
            ),
            PromptTemplate(
                id="intent_classification",
                name="Intent Classification",
                description="Classify customer intent from their message",
                category=PromptCategory.INTENT_CLASSIFICATION,
                prompt_type=PromptType.USER,
                content="""Analyze the following customer message and classify the intent. Return a JSON response with the intent and confidence score.

Available intents: {available_intents}

Customer message: "{customer_message}"

Context:
- Customer tier: {customer_tier}
- Previous intents: {previous_intents}
- Channel: {channel}

Return JSON in this format:
{{
    "intent": "most_likely_intent",
    "confidence": 0.95,
    "reasoning": "brief explanation",
    "alternative_intents": [
        {{"intent": "alternative", "confidence": 0.30}}
    ]
}}""",
                variables=[
                    PromptVariable("available_intents", "Comma-separated list of available intents", True),
                    PromptVariable("customer_message", "The customer's message to analyze", True),
                    PromptVariable("customer_tier", "Customer tier", False, "basic"),
                    PromptVariable("previous_intents", "Previous intents in conversation", False, ""),
                    PromptVariable("channel", "Communication channel", False, "web"),
                ],
                tags=["intent", "classification", "nlp"],
            ),
            PromptTemplate(
                id="sentiment_analysis",
                name="Sentiment Analysis",
                description="Analyze sentiment of customer message",
                category=PromptCategory.SENTIMENT_ANALYSIS,
                prompt_type=PromptType.USER,
                content="""Analyze the sentiment of the following customer message. Consider the context and provide a detailed analysis.

Customer message: "{customer_message}"

Context:
- Customer tier: {customer_tier}
- Issue category: {issue_category}
- Previous sentiment: {previous_sentiment}
- Channel: {channel}

Return JSON in this format:
{{
    "sentiment": "positive|negative|neutral",
    "score": 0.85,
    "confidence": 0.90,
    "emotions": ["frustration", "concern"],
    "reasoning": "brief explanation",
    "escalation_recommended": false
}}""",
                variables=[
                    PromptVariable("customer_message", "The customer's message to analyze", True),
                    PromptVariable("customer_tier", "Customer tier", False, "basic"),
                    PromptVariable("issue_category", "Category of the issue", False, "general"),
                    PromptVariable("previous_sentiment", "Previous sentiment in conversation", False, "neutral"),
                    PromptVariable("channel", "Communication channel", False, "web"),
                ],
                tags=["sentiment", "analysis", "nlp"],
            ),
            PromptTemplate(
                id="salesforce_analysis",
                name="Salesforce Code Analysis",
                description="Analyze Salesforce code and provide technical support",
                category=PromptCategory.SALESFORCE_ANALYSIS,
                prompt_type=PromptType.SYSTEM,
                content="""You are a Salesforce technical expert. Your role is to:
1. Analyze Salesforce code (Apex, SOQL, LWC, etc.)
2. Identify issues and provide solutions
3. Suggest best practices and optimizations
4. Help with Salesforce-specific technical problems

Salesforce context:
- Organization: {organization_name}
- Salesforce version: {salesforce_version}
- Code type: {code_type}
- Issue description: {issue_description}

Code to analyze:
{code_content}

Please provide:
1. Issue identification
2. Root cause analysis
3. Recommended solution
4. Best practices
5. Alternative approaches if applicable""",
                variables=[
                    PromptVariable("organization_name", "Name of the organization", True),
                    PromptVariable("salesforce_version", "Salesforce version", False, "latest"),
                    PromptVariable("code_type", "Type of code (apex, soql, lwc, etc.)", True),
                    PromptVariable("issue_description", "Description of the issue", True),
                    PromptVariable("code_content", "The code to analyze", True),
                ],
                tags=["salesforce", "technical", "code_analysis"],
            ),
            PromptTemplate(
                id="knowledge_retrieval",
                name="Knowledge Retrieval",
                description="Retrieve and synthesize knowledge for customer queries",
                category=PromptCategory.KNOWLEDGE_RETRIEVAL,
                prompt_type=PromptType.SYSTEM,
                content="""You are a knowledge retrieval assistant. Your role is to:
1. Synthesize information from multiple knowledge sources
2. Provide accurate, up-to-date information
3. Cite sources appropriately
4. Handle conflicting information gracefully

Customer query: "{customer_query}"

Relevant knowledge sources:
{knowledge_sources}

Context:
- Customer tier: {customer_tier}
- Organization: {organization_name}
- Query category: {query_category}

Please provide a comprehensive answer that:
1. Directly addresses the customer's query
2. Synthesizes information from multiple sources
3. Includes relevant citations
4. Highlights any conflicting information
5. Suggests follow-up actions if needed""",
                variables=[
                    PromptVariable("customer_query", "The customer's query", True),
                    PromptVariable("knowledge_sources", "Relevant knowledge sources", True),
                    PromptVariable("customer_tier", "Customer tier", False, "basic"),
                    PromptVariable("organization_name", "Name of the organization", True),
                    PromptVariable("query_category", "Category of the query", False, "general"),
                ],
                tags=["knowledge", "retrieval", "rag"],
            ),
        ]
        
        for template in default_templates:
            self.register_template(template)
        
        logger.info(f"Loaded {len(default_templates)} default prompt templates")
    
    def list_templates(self) -> List[PromptTemplate]:
        """List all registered templates."""
        return list(self._templates.values())
    
    def list_active_templates(self) -> List[PromptTemplate]:
        """List all active templates."""
        return [t for t in self._templates.values() if t.is_active]
    
    def search_templates(
        self,
        query: str,
        category: Optional[PromptCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[PromptTemplate]:
        """Search templates by query, category, and tags."""
        results = []
        
        for template in self._templates.values():
            if not template.is_active:
                continue
            
            # Filter by category
            if category and template.category != category:
                continue
            
            # Filter by tags
            if tags and not any(tag in template.tags for tag in tags):
                continue
            
            # Search in name, description, and content
            search_text = f"{template.name} {template.description} {template.content}".lower()
            if query.lower() in search_text:
                results.append(template)
        
        return results
    
    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: PromptCategory,
        content: str,
        variables: Optional[List[PromptVariable]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Create a new prompt template."""
        template = PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            category=category,
            prompt_type=PromptType.TEMPLATE,
            content=content,
            variables=variables or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        
        self.register_template(template)
        return template
    
    def update_template(
        self,
        template_id: str,
        **updates
    ) -> Optional[PromptTemplate]:
        """Update an existing template."""
        template = self.get_template(template_id)
        if not template:
            return None
        
        # Update fields
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        return template
    
    def deactivate_template(self, template_id: str) -> bool:
        """Deactivate a template."""
        template = self.get_template(template_id)
        if template:
            template.is_active = False
            template.updated_at = datetime.utcnow()
            return True
        return False
    
    def activate_template(self, template_id: str) -> bool:
        """Activate a template."""
        template = self.get_template(template_id)
        if template:
            template.is_active = True
            template.updated_at = datetime.utcnow()
            return True
        return False
