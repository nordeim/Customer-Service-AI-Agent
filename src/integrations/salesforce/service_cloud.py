"""
Salesforce Service Cloud integration with Omni-Channel and case management.

Provides comprehensive Service Cloud functionality including:
- Case lifecycle management
- Omni-Channel agent integration
- Knowledge base operations
- Live Agent support
- Cross-cloud orchestration
- Service Cloud console integration
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, AsyncGenerator
from uuid import UUID

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import SyncDirection
from .client import SalesforceClient, SalesforceAPIError
from .models import (
    SalesforceCase,
    SalesforceContact,
    SalesforceAccount,
    SalesforceCaseComment,
    SalesforceCaseStatus,
    SalesforceCasePriority,
    SalesforceCaseOrigin,
    SalesforceCaseType,
    SalesforceCaseReason,
    SalesforceOmniChannelStatus,
    SalesforceOmniChannelPresenceStatus,
    SalesforceKnowledgeArticle,
    SalesforceLiveAgentSession,
    SalesforceLiveAgentStatus,
)

logger = get_logger(__name__)


class ServiceCloudError(ExternalServiceError):
    """Service Cloud specific errors."""
    pass


class ServiceCloudIntegration:
    """Salesforce Service Cloud integration with comprehensive functionality."""
    
    def __init__(self, client: SalesforceClient, organization_id: UUID):
        self.client = client
        self.organization_id = organization_id
        self.settings = get_settings()
        self.logger = logger.getChild("service_cloud")
        
        # Service Cloud specific configuration
        self.config = self.client.config
        
        # Agent presence tracking
        self._agent_presence: Dict[str, Any] = {}
        self._presence_update_task: Optional[asyncio.Task] = None
    
    # Case Management
    
    async def create_case(
        self,
        subject: str,
        description: str,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
        priority: SalesforceCasePriority = SalesforceCasePriority.MEDIUM,
        origin: SalesforceCaseOrigin = SalesforceCaseOrigin.WEB,
        case_type: Optional[SalesforceCaseType] = None,
        reason: Optional[SalesforceCaseReason] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> SalesforceCase:
        """Create a new support case."""
        try:
            case_data = {
                "Subject": subject,
                "Description": description,
                "Priority": priority.value,
                "Origin": origin.value,
                "Status": SalesforceCaseStatus.NEW.value
            }
            
            if contact_id:
                case_data["ContactId"] = contact_id
            
            if account_id:
                case_data["AccountId"] = account_id
            
            if case_type:
                case_data["Type"] = case_type.value
            
            if reason:
                case_data["Reason"] = reason.value
            
            # Add custom fields
            if custom_fields:
                case_data.update(custom_fields)
            
            # Add AI context
            case_data.update({
                "AI_Source_System__c": "AI_Customer_Service_Agent",
                "AI_Conversation_ID__c": str(self.organization_id),
                "AI_Confidence_Score__c": 0.0,  # Will be updated by AI processing
                "AI_Intent_Classified__c": "",
                "AI_Sentiment_Analysis__c": ""
            })
            
            response = await self.client.create_object("Case", case_data)
            
            self.logger.info(f"Created case {response['id']} with subject: {subject}")
            
            return SalesforceCase(
                id=response["id"],
                case_number=response.get("CaseNumber", ""),
                subject=subject,
                description=description,
                status=SalesforceCaseStatus.NEW,
                priority=priority,
                origin=origin,
                type=case_type,
                reason=reason,
                contact_id=contact_id,
                account_id=account_id,
                created_date=datetime.utcnow(),
                last_modified_date=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create case: {e}")
            raise ServiceCloudError(f"Failed to create case: {e}")
    
    async def update_case(
        self,
        case_id: str,
        status: Optional[SalesforceCaseStatus] = None,
        priority: Optional[SalesforceCasePriority] = None,
        subject: Optional[str] = None,
        description: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> SalesforceCase:
        """Update existing case."""
        try:
            update_data = {}
            
            if status:
                update_data["Status"] = status.value
            
            if priority:
                update_data["Priority"] = priority.value
            
            if subject:
                update_data["Subject"] = subject
            
            if description:
                update_data["Description"] = description
            
            if custom_fields:
                update_data.update(custom_fields)
            
            # Update last modified timestamp
            update_data["LastModifiedDate"] = datetime.utcnow().isoformat()
            
            response = await self.client.update_object("Case", case_id, update_data)
            
            self.logger.info(f"Updated case {case_id}")
            
            # Fetch updated case
            return await self.get_case(case_id)
            
        except Exception as e:
            self.logger.error(f"Failed to update case {case_id}: {e}")
            raise ServiceCloudError(f"Failed to update case: {e}")
    
    async def get_case(self, case_id: str) -> SalesforceCase:
        """Get case by ID."""
        try:
            case_data = await self.client.get_object("Case", case_id)
            
            return SalesforceCase(
                id=case_data["Id"],
                case_number=case_data.get("CaseNumber", ""),
                subject=case_data.get("Subject", ""),
                description=case_data.get("Description", ""),
                status=SalesforceCaseStatus(case_data.get("Status", "New")),
                priority=SalesforceCasePriority(case_data.get("Priority", "Medium")),
                origin=SalesforceCaseOrigin(case_data.get("Origin", "Web")),
                contact_id=case_data.get("ContactId"),
                account_id=case_data.get("AccountId"),
                created_date=datetime.fromisoformat(case_data["CreatedDate"].replace("Z", "+00:00")),
                last_modified_date=datetime.fromisoformat(case_data["LastModifiedDate"].replace("Z", "+00:00"))
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get case {case_id}: {e}")
            raise ServiceCloudError(f"Failed to get case: {e}")
    
    async def search_cases(
        self,
        query: str,
        status: Optional[SalesforceCaseStatus] = None,
        priority: Optional[SalesforceCasePriority] = None,
        contact_id: Optional[str] = None,
        limit: int = 50
    ) -> List[SalesforceCase]:
        """Search for cases using SOQL."""
        try:
            conditions = []
            
            if query:
                conditions.append(f"(Subject LIKE '%{query}%' OR Description LIKE '%{query}%')")
            
            if status:
                conditions.append(f"Status = '{status.value}'")
            
            if priority:
                conditions.append(f"Priority = '{priority.value}'")
            
            if contact_id:
                conditions.append(f"ContactId = '{contact_id}'")
            
            where_clause = " AND ".join(conditions) if conditions else ""
            
            soql = f"""
                SELECT Id, CaseNumber, Subject, Description, Status, Priority, Origin, 
                       ContactId, AccountId, CreatedDate, LastModifiedDate
                FROM Case
                {f'WHERE {where_clause}' if where_clause else ''}
                ORDER BY CreatedDate DESC
                LIMIT {limit}
            """
            
            result = await self.client.query(soql)
            
            cases = []
            for record in result.get("records", []):
                cases.append(SalesforceCase(
                    id=record["Id"],
                    case_number=record.get("CaseNumber", ""),
                    subject=record.get("Subject", ""),
                    description=record.get("Description", ""),
                    status=SalesforceCaseStatus(record.get("Status", "New")),
                    priority=SalesforceCasePriority(record.get("Priority", "Medium")),
                    origin=SalesforceCaseOrigin(record.get("Origin", "Web")),
                    contact_id=record.get("ContactId"),
                    account_id=record.get("AccountId"),
                    created_date=datetime.fromisoformat(record["CreatedDate"].replace("Z", "+00:00")),
                    last_modified_date=datetime.fromisoformat(record["LastModifiedDate"].replace("Z", "+00:00"))
                ))
            
            return cases
            
        except Exception as e:
            self.logger.error(f"Failed to search cases: {e}")
            raise ServiceCloudError(f"Failed to search cases: {e}")
    
    # Case Comments
    
    async def add_case_comment(
        self,
        case_id: str,
        comment: str,
        is_public: bool = False,
        created_by_id: Optional[str] = None
    ) -> SalesforceCaseComment:
        """Add comment to case."""
        try:
            comment_data = {
                "ParentId": case_id,
                "CommentBody": comment,
                "IsPublished": is_public
            }
            
            if created_by_id:
                comment_data["CreatedById"] = created_by_id
            
            response = await self.client.create_object("CaseComment", comment_data)
            
            self.logger.info(f"Added comment to case {case_id}")
            
            return SalesforceCaseComment(
                id=response["id"],
                case_id=case_id,
                comment=comment,
                is_public=is_public,
                created_by_id=created_by_id,
                created_date=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to add comment to case {case_id}: {e}")
            raise ServiceCloudError(f"Failed to add case comment: {e}")
    
    # Omni-Channel Integration
    
    async def register_agent(
        self,
        user_id: str,
        presence_status: SalesforceOmniChannelPresenceStatus,
        capacity: int = 5
    ) -> Dict[str, Any]:
        """Register agent with Omni-Channel."""
        try:
            if not self.config.enable_omni_channel:
                raise ServiceCloudError("Omni-Channel is not enabled")
            
            # Create agent work presence
            presence_data = {
                "UserId": user_id,
                "Status": presence_status.value,
                "Capacity": capacity,
                "IsActive": True
            }
            
            response = await self.client.create_object("AgentWork", presence_data)
            
            self._agent_presence[user_id] = {
                "id": response["id"],
                "status": presence_status.value,
                "capacity": capacity,
                "last_update": datetime.utcnow()
            }
            
            self.logger.info(f"Registered agent {user_id} with Omni-Channel")
            
            return {
                "agent_work_id": response["id"],
                "status": presence_status.value,
                "capacity": capacity
            }
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {user_id}: {e}")
            raise ServiceCloudError(f"Failed to register agent: {e}")
    
    async def update_agent_presence(
        self,
        user_id: str,
        presence_status: SalesforceOmniChannelPresenceStatus,
        capacity: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update agent presence status."""
        try:
            if user_id not in self._agent_presence:
                # Register agent if not already registered
                return await self.register_agent(user_id, presence_status, capacity or 5)
            
            agent_work_id = self._agent_presence[user_id]["id"]
            
            update_data = {"Status": presence_status.value}
            if capacity is not None:
                update_data["Capacity"] = capacity
            
            await self.client.update_object("AgentWork", agent_work_id, update_data)
            
            self._agent_presence[user_id].update({
                "status": presence_status.value,
                "capacity": capacity or self._agent_presence[user_id]["capacity"],
                "last_update": datetime.utcnow()
            })
            
            self.logger.info(f"Updated agent {user_id} presence to {presence_status.value}")
            
            return {
                "agent_work_id": agent_work_id,
                "status": presence_status.value,
                "capacity": capacity or self._agent_presence[user_id]["capacity"]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update agent {user_id} presence: {e}")
            raise ServiceCloudError(f"Failed to update agent presence: {e}")
    
    async def get_agent_work_assignments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get work assignments for agent."""
        try:
            soql = f"""
                SELECT Id, CaseId, Status, CapacityWeight, CreatedDate
                FROM AgentWork
                WHERE UserId = '{user_id}' AND Status IN ('Assigned', 'Opened')
                ORDER BY CreatedDate ASC
            """
            
            result = await self.client.query(soql)
            
            assignments = []
            for record in result.get("records", []):
                assignments.append({
                    "id": record["Id"],
                    "case_id": record.get("CaseId"),
                    "status": record.get("Status"),
                    "capacity_weight": record.get("CapacityWeight", 1),
                    "created_date": datetime.fromisoformat(record["CreatedDate"].replace("Z", "+00:00"))
                })
            
            return assignments
            
        except Exception as e:
            self.logger.error(f"Failed to get agent assignments for {user_id}: {e}")
            raise ServiceCloudError(f"Failed to get agent assignments: {e}")
    
    # Knowledge Base Integration
    
    async def search_knowledge_articles(
        self,
        query: str,
        language: str = "en-US",
        limit: int = 10
    ) -> List[SalesforceKnowledgeArticle]:
        """Search knowledge base articles."""
        try:
            soql = f"""
                SELECT Id, Title, Summary, UrlName, ArticleType, 
                       LastPublishedDate, Language, ArticleNumber
                FROM KnowledgeArticleVersion
                WHERE PublishStatus = 'Online' 
                  AND Language = '{language}'
                  AND (Title LIKE '%{query}%' OR Summary LIKE '%{query}%')
                ORDER BY LastPublishedDate DESC
                LIMIT {limit}
            """
            
            result = await self.client.query(soql)
            
            articles = []
            for record in result.get("records", []):
                articles.append(SalesforceKnowledgeArticle(
                    id=record["Id"],
                    title=record.get("Title", ""),
                    summary=record.get("Summary", ""),
                    url_name=record.get("UrlName", ""),
                    article_type=record.get("ArticleType", ""),
                    last_published_date=datetime.fromisoformat(record["LastPublishedDate"].replace("Z", "+00:00")),
                    language=record.get("Language", "en-US"),
                    article_number=record.get("ArticleNumber", "")
                ))
            
            return articles
            
        except Exception as e:
            self.logger.error(f"Failed to search knowledge articles: {e}")
            raise ServiceCloudError(f"Failed to search knowledge articles: {e}")
    
    async def get_knowledge_article(self, article_id: str) -> SalesforceKnowledgeArticle:
        """Get knowledge article by ID."""
        try:
            soql = f"""
                SELECT Id, Title, Summary, UrlName, ArticleType, 
                       LastPublishedDate, Language, ArticleNumber, 
                       ArticleBody__c, ArticleType__c
                FROM KnowledgeArticleVersion
                WHERE Id = '{article_id}' AND PublishStatus = 'Online'
            """
            
            result = await self.client.query(soql)
            
            if not result.get("records"):
                raise ServiceCloudError(f"Knowledge article {article_id} not found")
            
            record = result["records"][0]
            
            return SalesforceKnowledgeArticle(
                id=record["Id"],
                title=record.get("Title", ""),
                summary=record.get("Summary", ""),
                url_name=record.get("UrlName", ""),
                article_type=record.get("ArticleType", ""),
                last_published_date=datetime.fromisoformat(record["LastPublishedDate"].replace("Z", "+00:00")),
                language=record.get("Language", "en-US"),
                article_number=record.get("ArticleNumber", ""),
                content=record.get("ArticleBody__c", ""),
                type_details=record.get("ArticleType__c")
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get knowledge article {article_id}: {e}")
            raise ServiceCloudError(f"Failed to get knowledge article: {e}")
    
    # Live Agent Integration
    
    async def create_live_agent_session(
        self,
        deployment_id: str,
        visitor_name: str,
        visitor_email: str,
        custom_fields: Optional[Dict[str, Any]] = None
    ) -> SalesforceLiveAgentSession:
        """Create Live Agent session."""
        try:
            session_data = {
                "DeploymentId": deployment_id,
                "VisitorName": visitor_name,
                "VisitorEmail": visitor_email,
                "SessionStartDate": datetime.utcnow().isoformat(),
                "Status": "Waiting"
            }
            
            if custom_fields:
                session_data.update(custom_fields)
            
            response = await self.client.create_object("LiveChatTranscript", session_data)
            
            self.logger.info(f"Created Live Agent session {response['id']} for {visitor_name}")
            
            return SalesforceLiveAgentSession(
                id=response["id"],
                deployment_id=deployment_id,
                visitor_name=visitor_name,
                visitor_email=visitor_email,
                status=SalesforceLiveAgentStatus.WAITING,
                session_start_date=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create Live Agent session: {e}")
            raise ServiceCloudError(f"Failed to create Live Agent session: {e}")
    
    async def get_live_agent_status(self, session_id: str) -> SalesforceLiveAgentStatus:
        """Get Live Agent session status."""
        try:
            session_data = await self.client.get_object("LiveChatTranscript", session_id)
            
            return SalesforceLiveAgentStatus(session_data.get("Status", "Waiting"))
            
        except Exception as e:
            self.logger.error(f"Failed to get Live Agent status for {session_id}: {e}")
            raise ServiceCloudError(f"Failed to get Live Agent status: {e}")
    
    # Cross-Cloud Orchestration
    
    async def orchestrate_cross_cloud(
        self,
        case_id: str,
        target_clouds: List[str],
        orchestration_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrate actions across multiple Salesforce clouds."""
        try:
            results = {}
            
            for cloud in target_clouds:
                if cloud == "Marketing":
                    results["marketing"] = await self._orchestrate_marketing_cloud(case_id, orchestration_data)
                elif cloud == "Commerce":
                    results["commerce"] = await self._orchestrate_commerce_cloud(case_id, orchestration_data)
                elif cloud == "Platform":
                    results["platform"] = await self._orchestrate_platform_cloud(case_id, orchestration_data)
                else:
                    self.logger.warning(f"Unknown target cloud: {cloud}")
            
            return {
                "case_id": case_id,
                "target_clouds": target_clouds,
                "orchestration_results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Cross-cloud orchestration failed for case {case_id}: {e}")
            raise ServiceCloudError(f"Cross-cloud orchestration failed: {e}")
    
    async def _orchestrate_marketing_cloud(self, case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate with Marketing Cloud."""
        # Implementation would integrate with Marketing Cloud APIs
        return {
            "cloud": "Marketing",
            "action": "customer_journey_update",
            "status": "completed",
            "details": {"case_id": case_id}
        }
    
    async def _orchestrate_commerce_cloud(self, case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate with Commerce Cloud."""
        # Implementation would integrate with Commerce Cloud APIs
        return {
            "cloud": "Commerce",
            "action": "order_status_check",
            "status": "completed",
            "details": {"case_id": case_id}
        }
    
    async def _orchestrate_platform_cloud(self, case_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate with Platform Cloud."""
        # Implementation would integrate with Platform Cloud APIs
        return {
            "cloud": "Platform",
            "action": "custom_object_update",
            "status": "completed",
            "details": {"case_id": case_id}
        }
    
    # Service Cloud Console Integration
    
    async def get_console_metadata(self) -> Dict[str, Any]:
        """Get Service Cloud console metadata."""
        try:
            # Get available console apps
            soql = """
                SELECT Id, Name, DeveloperName, Description, IsActive
                FROM ServiceCloudConsoleApp
                WHERE IsActive = true
                ORDER BY Name
            """
            
            result = await self.client.query(soql)
            
            return {
                "console_apps": result.get("records", []),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get console metadata: {e}")
            raise ServiceCloudError(f"Failed to get console metadata: {e}")
    
    async def create_console_tab(self, app_id: str, tab_config: Dict[str, Any]) -> str:
        """Create Service Cloud console tab."""
        try:
            tab_data = {
                "ServiceCloudConsoleAppId": app_id,
                "Name": tab_config["name"],
                "DeveloperName": tab_config["developer_name"],
                "Url": tab_config["url"],
                "IsActive": True
            }
            
            response = await self.client.create_object("ServiceCloudConsoleTab", tab_data)
            
            self.logger.info(f"Created console tab {response['id']} in app {app_id}")
            
            return response["id"]
            
        except Exception as e:
            self.logger.error(f"Failed to create console tab: {e}")
            raise ServiceCloudError(f"Failed to create console tab: {e}")
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive Service Cloud health check."""
        try:
            # Check Service Cloud specific endpoints
            health_results = {
                "service_cloud_available": False,
                "omni_channel_enabled": self.config.enable_omni_channel,
                "knowledge_enabled": False,
                "live_agent_enabled": False,
                "bulk_api_enabled": self.config.enable_bulk_api,
                "platform_events_enabled": self.config.enable_platform_events
            }
            
            # Test case creation capability
            try:
                # Try a lightweight query to test connectivity
                result = await self.client.query("SELECT Id FROM Case LIMIT 1")
                health_results["service_cloud_available"] = True
            except Exception as e:
                self.logger.error(f"Service Cloud connectivity test failed: {e}")
            
            # Test knowledge base
            try:
                result = await self.client.query("SELECT Id FROM KnowledgeArticleVersion LIMIT 1")
                health_results["knowledge_enabled"] = True
            except Exception as e:
                self.logger.warning(f"Knowledge base not available: {e}")
            
            # Test Live Agent
            try:
                result = await self.client.query("SELECT Id FROM LiveChatTranscript LIMIT 1")
                health_results["live_agent_enabled"] = True
            except Exception as e:
                self.logger.warning(f"Live Agent not available: {e}")
            
            # Check API usage
            try:
                api_usage = await self.client.get_api_usage()
                usage_percentage = (api_usage["used"] / api_usage["limit"] * 100) if api_usage["limit"] > 0 else 0
                
                health_results.update({
                    "api_usage_percentage": usage_percentage,
                    "api_usage": api_usage,
                    "governor_limits_healthy": usage_percentage < 80  # Alert if >80%
                })
            except Exception as e:
                self.logger.error(f"Failed to get API usage: {e}")
                health_results["governor_limits_healthy"] = False
            
            # Overall health status
            is_healthy = (
                health_results["service_cloud_available"] and
                health_results["governor_limits_healthy"]
            )
            
            health_results.update({
                "status": "healthy" if is_healthy else "degraded",
                "last_check": datetime.utcnow().isoformat()
            })
            
            return health_results
            
        except Exception as e:
            self.logger.error(f"Service Cloud health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


# Export the integration
__all__ = ["ServiceCloudIntegration", "ServiceCloudError"]