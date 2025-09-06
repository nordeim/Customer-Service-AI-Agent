"""
Tests for external service integrations (Jira, ServiceNow, Zendesk).
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.integrations.external import (
    JiraIntegration,
    ServiceNowIntegration,
    ZendeskIntegration
)
from src.integrations.external.jira import JiraIssue, JiraIssueType, JiraPriority
from src.integrations.external.servicenow import ServiceNowIncident, ServiceNowRequest
from src.integrations.external.zendesk import ZendeskTicket, ZendeskPriority, ZendeskStatus


class TestJiraIntegration:
    """Test Jira integration functionality."""
    
    @pytest.fixture
    def jira_integration(self):
        config = {
            "server_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test-api-token",
            "project_key": "TEST",
            "rate_limit": {"requests_per_second": 50}
        }
        return JiraIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, jira_integration):
        """Test Jira integration initialization."""
        assert jira_integration.server_url == "https://test.atlassian.net"
        assert jira_integration.username == "test@example.com"
        assert jira_integration.api_token == "test-api-token"
        assert jira_integration.project_key == "TEST"
        assert jira_integration._session is not None
    
    @pytest.mark.asyncio
    async def test_create_issue_success(self, jira_integration):
        """Test successful issue creation."""
        mock_response = {
            "id": "10001",
            "key": "TEST-1",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"},
                "status": {"name": "Open"}
            }
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            issue_data = {
                "summary": "Test Issue",
                "description": "Test description",
                "issuetype": {"name": "Bug"},
                "priority": {"name": "High"}
            }
            
            result = await jira_integration.create_issue(issue_data)
            
            assert result["id"] == "10001"
            assert result["key"] == "TEST-1"
            assert result["fields"]["summary"] == "Test Issue"
            assert result["fields"]["priority"]["name"] == "High"
    
    @pytest.mark.asyncio
    async def test_get_issue(self, jira_integration):
        """Test issue retrieval."""
        mock_response = {
            "id": "10001",
            "key": "TEST-1",
            "fields": {
                "summary": "Test Issue",
                "description": "Test description",
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "John Doe"},
                "reporter": {"displayName": "Jane Smith"},
                "created": "2024-01-01T00:00:00.000Z",
                "updated": "2024-01-02T00:00:00.000Z"
            }
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            result = await jira_integration.get_issue("TEST-1")
            
            assert result["id"] == "10001"
            assert result["key"] == "TEST-1"
            assert result["fields"]["summary"] == "Test Issue"
            assert result["fields"]["status"]["name"] == "In Progress"
    
    @pytest.mark.asyncio
    async def test_update_issue(self, jira_integration):
        """Test issue update."""
        mock_response = {
            "id": "10001",
            "key": "TEST-1",
            "fields": {
                "summary": "Updated Issue",
                "status": {"name": "Resolved"}
            }
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            update_data = {
                "summary": "Updated Issue",
                "status": {"name": "Resolved"}
            }
            
            result = await jira_integration.update_issue("TEST-1", update_data)
            
            assert result["id"] == "10001"
            assert result["key"] == "TEST-1"
            assert result["fields"]["summary"] == "Updated Issue"
            assert result["fields"]["status"]["name"] == "Resolved"
    
    @pytest.mark.asyncio
    async def test_search_issues(self, jira_integration):
        """Test issue search with JQL."""
        mock_response = {
            "expand": "names,schema",
            "startAt": 0,
            "maxResults": 50,
            "total": 2,
            "issues": [
                {
                    "id": "10001",
                    "key": "TEST-1",
                    "fields": {
                        "summary": "Bug 1",
                        "status": {"name": "Open"}
                    }
                },
                {
                    "id": "10002",
                    "key": "TEST-2",
                    "fields": {
                        "summary": "Bug 2",
                        "status": {"name": "In Progress"}
                    }
                }
            ]
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            jql = "project = TEST AND issuetype = Bug ORDER BY created DESC"
            result = await jira_integration.search_issues(jql)
            
            assert result["total"] == 2
            assert len(result["issues"]) == 2
            assert result["issues"][0]["key"] == "TEST-1"
            assert result["issues"][1]["key"] == "TEST-2"
    
    @pytest.mark.asyncio
    async def test_add_comment(self, jira_integration):
        """Test comment addition."""
        mock_response = {
            "id": "10001",
            "body": "This is a test comment",
            "author": {"displayName": "Test User"},
            "created": "2024-01-01T00:00:00.000Z"
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            result = await jira_integration.add_comment("TEST-1", "This is a test comment")
            
            assert result["id"] == "10001"
            assert result["body"] == "This is a test comment"
            assert result["author"]["displayName"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_project_info(self, jira_integration):
        """Test project information retrieval."""
        mock_response = {
            "id": "10000",
            "key": "TEST",
            "name": "Test Project",
            "projectTypeKey": "software",
            "lead": {"displayName": "Project Lead"},
            "components": [
                {"id": "10000", "name": "Component 1"},
                {"id": "10001", "name": "Component 2"}
            ]
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            result = await jira_integration.get_project_info("TEST")
            
            assert result["id"] == "10000"
            assert result["key"] == "TEST"
            assert result["name"] == "Test Project"
            assert len(result["components"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_agile_boards(self, jira_integration):
        """Test agile boards retrieval."""
        mock_response = {
            "values": [
                {
                    "id": 1,
                    "name": "Test Board",
                    "type": "scrum",
                    "location": {"projectId": 10000, "displayName": "TEST"}
                }
            ]
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            result = await jira_integration.get_agile_boards()
            
            assert len(result["values"]) == 1
            assert result["values"][0]["name"] == "Test Board"
            assert result["values"][0]["type"] == "scrum"
    
    @pytest.mark.asyncio
    async def test_webhook_handling(self, jira_integration):
        """Test webhook event handling."""
        webhook_data = {
            "timestamp": 1234567890,
            "webhookEvent": "jira:issue_created",
            "issue": {
                "id": "10001",
                "key": "TEST-1",
                "fields": {
                    "summary": "New Issue",
                    "status": {"name": "Open"}
                }
            }
        }
        
        # Mock webhook handler
        jira_integration.webhook_handlers["jira:issue_created"] = AsyncMock()
        
        await jira_integration.process_webhook_event(webhook_data)
        
        # Verify handler was called
        jira_integration.webhook_handlers["jira:issue_created"].assert_called_once_with(webhook_data)
    
    @pytest.mark.asyncio
    async def test_health_check(self, jira_integration):
        """Test health check functionality."""
        mock_response = {
            "baseUrl": "https://test.atlassian.net",
            "version": "1000.0.0-SNAPSHOT",
            "versionNumbers": [1000, 0, 0],
            "deploymentType": "Cloud",
            "buildNumber": 100000,
            "buildDate": "2024-01-01T00:00:00.000+0000",
            "serverTime": "2024-01-01T12:00:00.000+0000"
        }
        
        with patch.object(jira_integration, '_make_api_request', return_value=mock_response):
            health = await jira_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["baseUrl"] == "https://test.atlassian.net"
            assert health["deploymentType"] == "Cloud"


class TestServiceNowIntegration:
    """Test ServiceNow integration functionality."""
    
    @pytest.fixture
    def servicenow_integration(self):
        config = {
            "instance_url": "https://test.service-now.com",
            "username": "test_user",
            "password": "test_password",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "rate_limit": {"requests_per_second": 30}
        }
        return ServiceNowIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, servicenow_integration):
        """Test ServiceNow integration initialization."""
        assert servicenow_integration.instance_url == "https://test.service-now.com"
        assert servicenow_integration.username == "test_user"
        assert servicenow_integration.password == "test_password"
        assert servicenow_integration.client_id == "test_client_id"
        assert servicenow_integration.client_secret == "test_client_secret"
    
    @pytest.mark.asyncio
    async def test_create_incident(self, servicenow_integration):
        """Test incident creation."""
        mock_response = {
            "result": {
                "number": "INC0010001",
                "sys_id": "1234567890abcdef",
                "short_description": "Test Incident",
                "description": "Test incident description",
                "priority": "2",
                "state": "1",
                "opened_at": "2024-01-01 00:00:00"
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            incident_data = {
                "short_description": "Test Incident",
                "description": "Test incident description",
                "priority": "2",
                "category": "Software"
            }
            
            result = await servicenow_integration.create_incident(incident_data)
            
            assert result["result"]["number"] == "INC0010001"
            assert result["result"]["sys_id"] == "1234567890abcdef"
            assert result["result"]["short_description"] == "Test Incident"
            assert result["result"]["priority"] == "2"
    
    @pytest.mark.asyncio
    async def test_get_incident(self, servicenow_integration):
        """Test incident retrieval."""
        mock_response = {
            "result": {
                "number": "INC0010001",
                "sys_id": "1234567890abcdef",
                "short_description": "Test Incident",
                "description": "Test incident description",
                "priority": "2",
                "state": "2",  # In Progress
                "assigned_to": {"display_value": "John Doe"},
                "opened_at": "2024-01-01 00:00:00",
                "updated_at": "2024-01-02 00:00:00"
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            result = await servicenow_integration.get_incident("INC0010001")
            
            assert result["result"]["number"] == "INC0010001"
            assert result["result"]["sys_id"] == "1234567890abcdef"
            assert result["result"]["short_description"] == "Test Incident"
            assert result["result"]["state"] == "2"
    
    @pytest.mark.asyncio
    async def test_update_incident(self, servicenow_integration):
        """Test incident update."""
        mock_response = {
            "result": {
                "number": "INC0010001",
                "sys_id": "1234567890abcdef",
                "short_description": "Updated Incident",
                "state": "6",  # Resolved
                "updated_at": "2024-01-03 00:00:00"
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            update_data = {
                "short_description": "Updated Incident",
                "state": "6",
                "close_notes": "Issue resolved"
            }
            
            result = await servicenow_integration.update_incident("1234567890abcdef", update_data)
            
            assert result["result"]["number"] == "INC0010001"
            assert result["result"]["short_description"] == "Updated Incident"
            assert result["result"]["state"] == "6"
    
    @pytest.mark.asyncio
    async def test_search_incidents(self, servicenow_integration):
        """Test incident search."""
        mock_response = {
            "result": [
                {
                    "number": "INC0010001",
                    "sys_id": "1234567890abcdef1",
                    "short_description": "Network Issue",
                    "priority": "1",
                    "state": "2"
                },
                {
                    "number": "INC0010002",
                    "sys_id": "1234567890abcdef2",
                    "short_description": "Software Bug",
                    "priority": "2",
                    "state": "1"
                }
            ]
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            query = "priority=1^ORpriority=2"
            result = await servicenow_integration.search_incidents(query)
            
            assert len(result["result"]) == 2
            assert result["result"][0]["number"] == "INC0010001"
            assert result["result"][1]["number"] == "INC0010002"
    
    @pytest.mark.asyncio
    async def test_create_service_request(self, servicenow_integration):
        """Test service request creation."""
        mock_response = {
            "result": {
                "number": "REQ0010001",
                "sys_id": "abcdef1234567890",
                "short_description": "New Laptop Request",
                "description": "Request for new development laptop",
                "requested_for": {"display_value": "John Doe"},
                "requested_date": "2024-01-01",
                "state": "1"  # Open
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            request_data = {
                "short_description": "New Laptop Request",
                "description": "Request for new development laptop",
                "requested_for": "john.doe",
                "category": "Hardware"
            }
            
            result = await servicenow_integration.create_service_request(request_data)
            
            assert result["result"]["number"] == "REQ0010001"
            assert result["result"]["sys_id"] == "abcdef1234567890"
            assert result["result"]["short_description"] == "New Laptop Request"
            assert result["result"]["state"] == "1"
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, servicenow_integration):
        """Test user information retrieval."""
        mock_response = {
            "result": {
                "user_name": "john.doe",
                "name": "John Doe",
                "email": "john.doe@example.com",
                "department": {"display_value": "IT Department"},
                "title": "Software Engineer",
                "active": "true"
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            result = await servicenow_integration.get_user_info("john.doe")
            
            assert result["result"]["user_name"] == "john.doe"
            assert result["result"]["name"] == "John Doe"
            assert result["result"]["email"] == "john.doe@example.com"
            assert result["result"]["active"] == "true"
    
    @pytest.mark.asyncio
    async def test_get_group_members(self, servicenow_integration):
        """Test group members retrieval."""
        mock_response = {
            "result": [
                {
                    "user": {"display_value": "John Doe"},
                    "group": {"display_value": "Support Team"}
                },
                {
                    "user": {"display_value": "Jane Smith"},
                    "group": {"display_value": "Support Team"}
                }
            ]
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            result = await servicenow_integration.get_group_members("support_team")
            
            assert len(result["result"]) == 2
            assert result["result"][0]["user"]["display_value"] == "John Doe"
            assert result["result"][1]["user"]["display_value"] == "Jane Smith"
    
    @pytest.mark.asyncio
    async def test_aggregate_data(self, servicenow_integration):
        """Test data aggregation using Aggregate API."""
        mock_response = {
            "result": {
                "stats": {
                    "count": 25,
                    "sum": 0,
                    "avg": 0,
                    "min": 0,
                    "max": 0
                },
                "data": [
                    {
                        "groupby_fields": {
                            "state": {"display_value": "New", "value": "1"}
                        },
                        "aggregate_fields": {
                            "COUNT": 10
                        }
                    },
                    {
                        "groupby_fields": {
                            "state": {"display_value": "In Progress", "value": "2"}
                        },
                        "aggregate_fields": {
                            "COUNT": 15
                        }
                    }
                ]
            }
        }
        
        with patch.object(servicenow_integration, '_make_aggregate_api_request', return_value=mock_response):
            result = await servicenow_integration.aggregate_data(
                table="incident",
                group_by="state",
                aggregate="COUNT"
            )
            
            assert result["result"]["stats"]["count"] == 25
            assert len(result["result"]["data"]) == 2
            assert result["result"]["data"][0]["groupby_fields"]["state"]["display_value"] == "New"
            assert result["result"]["data"][0]["aggregate_fields"]["COUNT"] == 10
    
    @pytest.mark.asyncio
    async def test_import_set_data(self, servicenow_integration):
        """Test data import using Import Set API."""
        mock_response = {
            "result": {
                "import_set": "ISET0010001",
                "staging_table": "u_import_incident",
                "rows_processed": 100,
                "rows_inserted": 100,
                "rows_updated": 0,
                "rows_failed": 0,
                "status": "Complete"
            }
        }
        
        with patch.object(servicenow_integration, '_make_import_set_request', return_value=mock_response):
            import_data = [
                {"short_description": "Issue 1", "priority": "2"},
                {"short_description": "Issue 2", "priority": "3"}
            ]
            
            result = await servicenow_integration.import_set_data("u_import_incident", import_data)
            
            assert result["result"]["import_set"] == "ISET0010001"
            assert result["result"]["rows_processed"] == 100
            assert result["result"]["status"] == "Complete"
    
    @pytest.mark.asyncio
    async def test_health_check(self, servicenow_integration):
        """Test health check functionality."""
        mock_response = {
            "result": {
                "name": "ServiceNow Test Instance",
                "build_date": "2024-01-01 00:00:00",
                "build_name": "release",
                "date": "2024-01-01 12:00:00",
                "db": "PostgreSQL",
                "edition": "Enterprise",
                "scope": "x_test",
                "version": "Tokyo"
            }
        }
        
        with patch.object(servicenow_integration, '_make_table_api_request', return_value=mock_response):
            health = await servicenow_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["instance_name"] == "ServiceNow Test Instance"
            assert health["version"] == "Tokyo"
            assert health["edition"] == "Enterprise"


class TestZendeskIntegration:
    """Test Zendesk integration functionality."""
    
    @pytest.fixture
    def zendesk_integration(self):
        config = {
            "subdomain": "test",
            "email": "test@example.com",
            "api_token": "test-api-token",
            "rate_limit": {"requests_per_second": 40}
        }
        return ZendeskIntegration(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, zendesk_integration):
        """Test Zendesk integration initialization."""
        assert zendesk_integration.subdomain == "test"
        assert zendesk_integration.email == "test@example.com"
        assert zendesk_integration.api_token == "test-api-token"
        assert zendesk_integration.base_url == "https://test.zendesk.com/api/v2"
    
    @pytest.mark.asyncio
    async def test_create_ticket(self, zendesk_integration):
        """Test ticket creation."""
        mock_response = {
            "ticket": {
                "id": 12345,
                "subject": "Test Ticket",
                "description": "Test ticket description",
                "priority": "high",
                "status": "open",
                "requester_id": 98765,
                "submitter_id": 98765,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z"
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            ticket_data = {
                "subject": "Test Ticket",
                "description": "Test ticket description",
                "priority": "high",
                "status": "open"
            }
            
            result = await zendesk_integration.create_ticket(ticket_data)
            
            assert result["ticket"]["id"] == 12345
            assert result["ticket"]["subject"] == "Test Ticket"
            assert result["ticket"]["priority"] == "high"
            assert result["ticket"]["status"] == "open"
    
    @pytest.mark.asyncio
    async def test_get_ticket(self, zendesk_integration):
        """Test ticket retrieval."""
        mock_response = {
            "ticket": {
                "id": 12345,
                "subject": "Test Ticket",
                "description": "Test ticket description",
                "priority": "high",
                "status": "pending",
                "requester": {"id": 98765, "name": "John Doe", "email": "john@example.com"},
                "assignee": {"id": 87654, "name": "Jane Smith", "email": "jane@example.com"},
                "organization": {"id": 123, "name": "Test Org"},
                "tags": ["bug", "urgent"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.get_ticket(12345)
            
            assert result["ticket"]["id"] == 12345
            assert result["ticket"]["subject"] == "Test Ticket"
            assert result["ticket"]["priority"] == "high"
            assert result["ticket"]["status"] == "pending"
            assert result["ticket"]["requester"]["name"] == "John Doe"
            assert result["ticket"]["assignee"]["name"] == "Jane Smith"
    
    @pytest.mark.asyncio
    async def test_update_ticket(self, zendesk_integration):
        """Test ticket update."""
        mock_response = {
            "ticket": {
                "id": 12345,
                "subject": "Updated Ticket",
                "priority": "urgent",
                "status": "solved",
                "updated_at": "2024-01-03T00:00:00Z"
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            update_data = {
                "subject": "Updated Ticket",
                "priority": "urgent",
                "status": "solved",
                "comment": {"body": "Issue resolved", "public": False}
            }
            
            result = await zendesk_integration.update_ticket(12345, update_data)
            
            assert result["ticket"]["id"] == 12345
            assert result["ticket"]["subject"] == "Updated Ticket"
            assert result["ticket"]["priority"] == "urgent"
            assert result["ticket"]["status"] == "solved"
    
    @pytest.mark.asyncio
    async def test_search_tickets(self, zendesk_integration):
        """Test ticket search."""
        mock_response = {
            "results": [
                {
                    "id": 12345,
                    "subject": "Bug Report",
                    "priority": "high",
                    "status": "open",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 12346,
                    "subject": "Feature Request",
                    "priority": "normal",
                    "status": "new",
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ],
            "facets": None,
            "next_page": None,
            "previous_page": None,
            "count": 2
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            query = "type:ticket priority:high status:open"
            result = await zendesk_integration.search_tickets(query)
            
            assert result["count"] == 2
            assert len(result["results"]) == 2
            assert result["results"][0]["subject"] == "Bug Report"
            assert result["results"][0]["priority"] == "high"
            assert result["results"][1]["subject"] == "Feature Request"
            assert result["results"][1]["priority"] == "normal"
    
    @pytest.mark.asyncio
    async def test_add_comment(self, zendesk_integration):
        """Test comment addition."""
        mock_response = {
            "audit": {
                "id": 987654321,
                "ticket_id": 12345,
                "created_at": "2024-01-03T00:00:00Z",
                "events": [
                    {
                        "id": 123456789,
                        "type": "Comment",
                        "body": "This is a test comment",
                        "public": True,
                        "author_id": 87654
                    }
                ]
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            comment_data = {
                "body": "This is a test comment",
                "public": True
            }
            
            result = await zendesk_integration.add_comment(12345, comment_data)
            
            assert result["audit"]["ticket_id"] == 12345
            assert len(result["audit"]["events"]) == 1
            assert result["audit"]["events"][0]["type"] == "Comment"
            assert result["audit"]["events"][0]["body"] == "This is a test comment"
    
    @pytest.mark.asyncio
    async def test_get_user_info(self, zendesk_integration):
        """Test user information retrieval."""
        mock_response = {
            "user": {
                "id": 98765,
                "name": "John Doe",
                "email": "john@example.com",
                "role": "end-user",
                "organization_id": 123,
                "tags": ["vip", "enterprise"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.get_user_info(98765)
            
            assert result["user"]["id"] == 98765
            assert result["user"]["name"] == "John Doe"
            assert result["user"]["email"] == "john@example.com"
            assert result["user"]["role"] == "end-user"
    
    @pytest.mark.asyncio
    async def test_get_organization_info(self, zendesk_integration):
        """Test organization information retrieval."""
        mock_response = {
            "organization": {
                "id": 123,
                "name": "Test Organization",
                "domain_names": ["test.com", "example.com"],
                "details": "Test organization details",
                "notes": "Test notes",
                "group_id": 456,
                "shared_tickets": True,
                "shared_comments": True,
                "tags": ["enterprise", "premium"],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z"
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.get_organization_info(123)
            
            assert result["organization"]["id"] == 123
            assert result["organization"]["name"] == "Test Organization"
            assert result["organization"]["domain_names"] == ["test.com", "example.com"]
    
    @pytest.mark.asyncio
    async def test_get_macros(self, zendesk_integration):
        """Test macros retrieval."""
        mock_response = {
            "macros": [
                {
                    "id": 11111,
                    "title": "Close and Notify",
                    "active": True,
                    "actions": [
                        {"field": "status", "value": "solved"},
                        {"field": "comment_value", "value": "Your request has been resolved."}
                    ]
                },
                {
                    "id": 22222,
                    "title": "Escalate to Level 2",
                    "active": True,
                    "actions": [
                        {"field": "group_id", "value": "12345"},
                        {"field": "priority", "value": "high"}
                    ]
                }
            ]
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.get_macros()
            
            assert len(result["macros"]) == 2
            assert result["macros"][0]["title"] == "Close and Notify"
            assert result["macros"][0]["active"] is True
            assert result["macros"][1]["title"] == "Escalate to Level 2"
    
    @pytest.mark.asyncio
    async def test_apply_macro(self, zendesk_integration):
        """Test macro application."""
        mock_response = {
            "ticket": {
                "id": 12345,
                "subject": "Test Ticket",
                "status": "solved",
                "comment": {"body": "Your request has been resolved.", "public": True}
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.apply_macro(12345, 11111)
            
            assert result["ticket"]["id"] == 12345
            assert result["ticket"]["status"] == "solved"
            assert result["ticket"]["comment"]["body"] == "Your request has been resolved."
    
    @pytest.mark.asyncio
    async def test_get_satisfaction_ratings(self, zendesk_integration):
        """Test satisfaction ratings retrieval."""
        mock_response = {
            "satisfaction_ratings": [
                {
                    "id": 33333,
                    "score": "good",
                    "comment": "Great service!",
                    "ticket_id": 12345,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 44444,
                    "score": "bad",
                    "comment": "Issue not resolved",
                    "ticket_id": 12346,
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ]
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            result = await zendesk_integration.get_satisfaction_ratings()
            
            assert len(result["satisfaction_ratings"]) == 2
            assert result["satisfaction_ratings"][0]["score"] == "good"
            assert result["satisfaction_ratings"][0]["comment"] == "Great service!"
            assert result["satisfaction_ratings"][1]["score"] == "bad"
            assert result["satisfaction_ratings"][1]["comment"] == "Issue not resolved"
    
    @pytest.mark.asyncio
    async def test_webhook_handling(self, zendesk_integration):
        """Test webhook event handling."""
        webhook_data = {
            "id": 12345,
            "type": "ticket.created",
            "ticket": {
                "id": 12345,
                "subject": "New Ticket",
                "priority": "high",
                "status": "new"
            },
            "timestamp": 1234567890
        }
        
        # Mock webhook handler
        zendesk_integration.webhook_handlers["ticket.created"] = AsyncMock()
        
        await zendesk_integration.process_webhook_event(webhook_data)
        
        # Verify handler was called
        zendesk_integration.webhook_handlers["ticket.created"].assert_called_once_with(webhook_data)
    
    @pytest.mark.asyncio
    async def test_health_check(self, zendesk_integration):
        """Test health check functionality."""
        mock_response = {
            "settings": {
                "subdomain": "test",
                "email": "test@example.com",
                "time_zone": "UTC",
                "has_help_center": True,
                "has_chat": False
            }
        }
        
        with patch.object(zendesk_integration, '_make_api_request', return_value=mock_response):
            health = await zendesk_integration.health_check()
            
            assert health["status"] == "healthy"
            assert health["subdomain"] == "test"
            assert health["has_help_center"] is True


# Performance tests
@pytest.mark.integration
class TestExternalIntegrationsPerformance:
    """Performance tests for external service integrations."""
    
    @pytest.mark.asyncio
    async def test_jira_issue_creation_performance(self):
        """Test Jira issue creation performance."""
        config = {
            "server_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test-api-token",
            "project_key": "TEST",
            "rate_limit": {"requests_per_second": 100}
        }
        
        jira = JiraIntegration(config)
        
        # Mock API request
        mock_response = {
            "id": "10001",
            "key": "TEST-1",
            "fields": {"summary": "Test Issue", "description": "Test description"}
        }
        jira._make_api_request = AsyncMock(return_value=mock_response)
        
        issue_data = {
            "summary": "Performance Test Issue",
            "description": "Test description",
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"}
        }
        
        start_time = time.time()
        
        # Test 50 concurrent issue creations
        tasks = []
        for i in range(50):
            issue_data["summary"] = f"Performance Test Issue {i}"
            tasks.append(jira.create_issue(issue_data))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 3 seconds)
        assert duration < 3.0
        assert len(results) == 50
        assert all(result["key"].startswith("TEST-") for result in results)
    
    @pytest.mark.asyncio
    async def test_servicenow_incident_search_performance(self):
        """Test ServiceNow incident search performance."""
        config = {
            "instance_url": "https://test.service-now.com",
            "username": "test_user",
            "password": "test_password",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "rate_limit": {"requests_per_second": 60}
        }
        
        servicenow = ServiceNowIntegration(config)
        
        # Mock API request
        mock_response = {
            "result": [
                {"number": f"INC001000{i:03d}", "priority": "2", "state": "1"}
                for i in range(100)
            ]
        }
        servicenow._make_table_api_request = AsyncMock(return_value=mock_response)
        
        start_time = time.time()
        
        # Test 30 concurrent searches
        tasks = []
        for i in range(30):
            query = f"priority=2^state=1^ORpriority=1^state=2"
            tasks.append(servicenow.search_incidents(query))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert len(results) == 30
        assert all(len(result["result"]) == 100 for result in results)
    
    @pytest.mark.asyncio
    async def test_zendesk_ticket_search_performance(self):
        """Test Zendesk ticket search performance."""
        config = {
            "subdomain": "test",
            "email": "test@example.com",
            "api_token": "test-api-token",
            "rate_limit": {"requests_per_second": 80}
        }
        
        zendesk = ZendeskIntegration(config)
        
        # Mock API request
        mock_response = {
            "results": [
                {"id": i, "subject": f"Test Ticket {i}", "priority": "high", "status": "open"}
                for i in range(50)
            ],
            "count": 50
        }
        zendesk._make_api_request = AsyncMock(return_value=mock_response)
        
        start_time = time.time()
        
        # Test 40 concurrent searches
        tasks = []
        for i in range(40):
            query = f"type:ticket priority:high status:open created>2024-01-01"
            tasks.append(zendesk.search_tickets(query))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert len(results) == 40
        assert all(result["count"] == 50 for result in results)


# Error handling tests
@pytest.mark.asyncio
class TestExternalIntegrationsErrorHandling:
    """Test error handling in external service integrations."""
    
    async def test_jira_error_handling(self):
        """Test Jira error handling."""
        config = {
            "server_url": "https://test.atlassian.net",
            "username": "test@example.com",
            "api_token": "test-api-token",
            "project_key": "TEST",
            "rate_limit": {"requests_per_second": 50}
        }
        
        jira = JiraIntegration(config)
        
        # Test API error
        with patch.object(jira, '_make_api_request', side_effect=Exception("Jira API Error")):
            with pytest.raises(Exception, match="Jira API Error"):
                await jira.create_issue({"summary": "Test Issue"})
    
    async def test_servicenow_error_handling(self):
        """Test ServiceNow error handling."""
        config = {
            "instance_url": "https://test.service-now.com",
            "username": "test_user",
            "password": "test_password",
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "rate_limit": {"requests_per_second": 30}
        }
        
        servicenow = ServiceNowIntegration(config)
        
        # Test API error
        with patch.object(servicenow, '_make_table_api_request', side_effect=Exception("ServiceNow API Error")):
            with pytest.raises(Exception, match="ServiceNow API Error"):
                await servicenow.create_incident({"short_description": "Test Incident"})
    
    async def test_zendesk_error_handling(self):
        """Test Zendesk error handling."""
        config = {
            "subdomain": "test",
            "email": "test@example.com",
            "api_token": "test-api-token",
            "rate_limit": {"requests_per_second": 40}
        }
        
        zendesk = ZendeskIntegration(config)
        
        # Test API error
        with patch.object(zendesk, '_make_api_request', side_effect=Exception("Zendesk API Error")):
            with pytest.raises(Exception, match="Zendesk API Error"):
                await zendesk.create_ticket({"subject": "Test Ticket"})


# Import time for performance tests
import time

# Export test classes
__all__ = [
    "TestJiraIntegration",
    "TestServiceNowIntegration", 
    "TestZendeskIntegration",
    "TestExternalIntegrationsPerformance",
    "TestExternalIntegrationsErrorHandling"
]


# Additional model validation tests
class TestExternalModels:
    """Test external service model validation."""
    
    def test_jira_issue_model(self):
        """Test JiraIssue model creation."""
        issue = JiraIssue(
            summary="Test Issue",
            description="Test description",
            issuetype=JiraIssueType.BUG,
            priority=JiraPriority.HIGH,
            project="TEST"
        )
        
        assert issue.summary == "Test Issue"
        assert issue.description == "Test description"
        assert issue.issuetype == JiraIssueType.BUG
        assert issue.priority == JiraPriority.HIGH
        assert issue.project == "TEST"
    
    def test_servicenow_incident_model(self):
        """Test ServiceNowIncident model creation."""
        incident = ServiceNowIncident(
            short_description="Test Incident",
            description="Test incident description",
            priority="2",
            category="Software",
            state="1"
        )
        
        assert incident.short_description == "Test Incident"
        assert incident.description == "Test incident description"
        assert incident.priority == "2"
        assert incident.category == "Software"
        assert incident.state == "1"
    
    def test_zendesk_ticket_model(self):
        """Test ZendeskTicket model creation."""
        ticket = ZendeskTicket(
            subject="Test Ticket",
            description="Test ticket description",
            priority=ZendeskPriority.HIGH,
            status=ZendeskStatus.OPEN,
            tags=["bug", "urgent"]
        )
        
        assert ticket.subject == "Test Ticket"
        assert ticket.description == "Test ticket description"
        assert ticket.priority == ZendeskPriority.HIGH
        assert ticket.status == ZendeskStatus.OPEN
        assert ticket.tags == ["bug", "urgent"]