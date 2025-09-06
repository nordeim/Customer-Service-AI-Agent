"""
Tests for Salesforce integration functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from src.integrations.salesforce import (
    SalesforceClient,
    SalesforceServiceCloud,
    SalesforceCase,
    SalesforceContact,
    SalesforceAccount,
    SyncDirection,
    ConflictResolutionStrategy
)
from src.integrations.salesforce.sync import SalesforceSyncEngine
from src.integrations.base import RateLimitError, OAuth2Config


class TestSalesforceClient:
    """Test SalesforceClient functionality."""
    
    @pytest.fixture
    def oauth_config(self):
        return OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            authorization_url="https://login.salesforce.com/services/oauth2/authorize",
            token_url="https://login.salesforce.com/services/oauth2/token",
            redirect_uri="https://app.example.com/callback",
            scope="api refresh_token"
        )
    
    @pytest.fixture
    def sf_client(self, oauth_config):
        return SalesforceClient(
            oauth_config=oauth_config,
            instance_url="https://test.salesforce.com",
            username="test@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self, sf_client, oauth_config):
        """Test SalesforceClient initialization."""
        assert sf_client.oauth_config == oauth_config
        assert sf_client.instance_url == "https://test.salesforce.com"
        assert sf_client.username == "test@example.com"
        assert sf_client.api_version == "v58.0"
        assert sf_client._session is not None
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, sf_client):
        """Test successful authentication."""
        mock_response = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "instance_url": "https://test.salesforce.com",
            "id": "https://login.salesforce.com/id/00Dxx00000000123/005xx00000000123"
        }
        
        with patch.object(sf_client.oauth_client, 'exchange_code_for_token', return_value=mock_response):
            success = await sf_client.authenticate("test_code")
            
            assert success is True
            assert sf_client.access_token == "test_access_token"
            assert sf_client.instance_url == "https://test.salesforce.com"
    
    @pytest.mark.asyncio
    async def test_authenticate_failure(self, sf_client):
        """Test authentication failure."""
        with patch.object(sf_client.oauth_client, 'exchange_code_for_token', side_effect=Exception("Auth failed")):
            success = await sf_client.authenticate("invalid_code")
            
            assert success is False
            assert sf_client.access_token is None
    
    @pytest.mark.asyncio
    async def test_execute_soql_query(self, sf_client):
        """Test SOQL query execution."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "totalSize": 2,
            "done": True,
            "records": [
                {
                    "Id": "001xx000000001",
                    "Name": "Test Account 1",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001xx000000001"}
                },
                {
                    "Id": "001xx000000002",
                    "Name": "Test Account 2",
                    "attributes": {"type": "Account", "url": "/services/data/v58.0/sobjects/Account/001xx000000002"}
                }
            ]
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            results = await sf_client.execute_soql_query("SELECT Id, Name FROM Account LIMIT 2")
            
            assert results["totalSize"] == 2
            assert len(results["records"]) == 2
            assert results["records"][0]["Name"] == "Test Account 1"
    
    @pytest.mark.asyncio
    async def test_execute_sosl_search(self, sf_client):
        """Test SOSL search execution."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "searchRecords": [
                {
                    "Id": "001xx000000001",
                    "Name": "Test Account",
                    "attributes": {"type": "Account"}
                }
            ]
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            results = await sf_client.execute_sosl_search("FIND {Test} IN ALL FIELDS RETURNING Account(Id, Name)")
            
            assert len(results["searchRecords"]) == 1
            assert results["searchRecords"][0]["Name"] == "Test Account"
    
    @pytest.mark.asyncio
    async def test_create_record(self, sf_client):
        """Test record creation."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "id": "001xx000000003",
            "success": True,
            "errors": []
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            result = await sf_client.create_record("Account", {"Name": "New Account"})
            
            assert result["id"] == "001xx000000003"
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_update_record(self, sf_client):
        """Test record update."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "id": "001xx000000003",
            "success": True,
            "errors": []
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            result = await sf_client.update_record("Account", "001xx000000003", {"Name": "Updated Account"})
            
            assert result["id"] == "001xx000000003"
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_delete_record(self, sf_client):
        """Test record deletion."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "id": "001xx000000003",
            "success": True,
            "errors": []
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            result = await sf_client.delete_record("Account", "001xx000000003")
            
            assert result["id"] == "001xx000000003"
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_bulk_create_records(self, sf_client):
        """Test bulk record creation."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "jobInfo": {
                "id": "750xx000000001",
                "operation": "insert",
                "object": "Account",
                "state": "Open"
            }
        }
        
        records = [
            {"Name": "Account 1"},
            {"Name": "Account 2"}
        ]
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            result = await sf_client.bulk_create_records("Account", records)
            
            assert result["jobInfo"]["id"] == "750xx000000001"
            assert result["jobInfo"]["operation"] == "insert"
    
    @pytest.mark.asyncio
    async def test_get_governor_limits(self, sf_client):
        """Test governor limits retrieval."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "DailyApiRequests": {
                "Max": 100000,
                "Remaining": 95000
            },
            "DailyBulkApiRequests": {
                "Max": 10000,
                "Remaining": 9500
            }
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            limits = await sf_client.get_governor_limits()
            
            assert limits["DailyApiRequests"]["Max"] == 100000
            assert limits["DailyApiRequests"]["Remaining"] == 95000
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, sf_client):
        """Test rate limit error handling."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        # Simulate rate limit error
        rate_limit_error = RateLimitError("API rate limit exceeded")
        
        with patch.object(sf_client, '_api_request', side_effect=rate_limit_error):
            with pytest.raises(RateLimitError, match="API rate limit exceeded"):
                await sf_client.execute_soql_query("SELECT Id FROM Account")
    
    @pytest.mark.asyncio
    async def test_health_check(self, sf_client):
        """Test health check functionality."""
        sf_client.access_token = "test_token"
        sf_client.instance_url = "https://test.salesforce.com"
        
        mock_response = {
            "status": "healthy",
            "api_version": "v58.0",
            "user_info": {
                "username": "test@example.com",
                "organization_id": "00Dxx00000000123"
            }
        }
        
        with patch.object(sf_client, '_api_request', return_value=mock_response):
            health = await sf_client.health_check()
            
            assert health["status"] == "healthy"
            assert health["api_version"] == "v58.0"


class TestSalesforceServiceCloud:
    """Test SalesforceServiceCloud functionality."""
    
    @pytest.fixture
    def service_cloud(self):
        client = Mock(spec=SalesforceClient)
        return SalesforceServiceCloud(client)
    
    @pytest.mark.asyncio
    async def test_create_case(self, service_cloud):
        """Test case creation."""
        mock_case = {
            "Id": "500xx000000001",
            "CaseNumber": "00001000",
            "Subject": "Test Case",
            "Status": "New",
            "Priority": "Medium"
        }
        
        service_cloud.client.create_record = AsyncMock(return_value=mock_case)
        
        case_data = {
            "Subject": "Test Case",
            "Description": "Test description",
            "Priority": "Medium",
            "Origin": "Web"
        }
        
        result = await service_cloud.create_case(case_data)
        
        assert result["Id"] == "500xx000000001"
        assert result["CaseNumber"] == "00001000"
        assert result["Subject"] == "Test Case"
        
        service_cloud.client.create_record.assert_called_once_with("Case", case_data)
    
    @pytest.mark.asyncio
    async def test_update_case(self, service_cloud):
        """Test case update."""
        mock_result = {
            "Id": "500xx000000001",
            "success": True,
            "errors": []
        }
        
        service_cloud.client.update_record = AsyncMock(return_value=mock_result)
        
        update_data = {
            "Status": "In Progress",
            "Priority": "High"
        }
        
        result = await service_cloud.update_case("500xx000000001", update_data)
        
        assert result["success"] is True
        assert result["Id"] == "500xx000000001"
        
        service_cloud.client.update_record.assert_called_once_with("Case", "500xx000000001", update_data)
    
    @pytest.mark.asyncio
    async def test_get_case(self, service_cloud):
        """Test case retrieval."""
        mock_case = {
            "Id": "500xx000000001",
            "CaseNumber": "00001000",
            "Subject": "Test Case",
            "Status": "New",
            "Priority": "Medium",
            "ContactId": "003xx000000001",
            "AccountId": "001xx000000001"
        }
        
        service_cloud.client.get_record = AsyncMock(return_value=mock_case)
        
        result = await service_cloud.get_case("500xx000000001")
        
        assert result["Id"] == "500xx000000001"
        assert result["CaseNumber"] == "00001000"
        assert result["Subject"] == "Test Case"
        
        service_cloud.client.get_record.assert_called_once_with("Case", "500xx000000001")
    
    @pytest.mark.asyncio
    async def test_search_cases(self, service_cloud):
        """Test case search."""
        mock_results = {
            "totalSize": 2,
            "records": [
                {
                    "Id": "500xx000000001",
                    "Subject": "Test Case 1",
                    "Status": "New"
                },
                {
                    "Id": "500xx000000002",
                    "Subject": "Test Case 2",
                    "Status": "Closed"
                }
            ]
        }
        
        service_cloud.client.execute_soql_query = AsyncMock(return_value=mock_results)
        
        query = "SELECT Id, Subject, Status FROM Case WHERE Status = 'New'"
        results = await service_cloud.search_cases(query)
        
        assert results["totalSize"] == 2
        assert len(results["records"]) == 2
        assert results["records"][0]["Subject"] == "Test Case 1"
        
        service_cloud.client.execute_soql_query.assert_called_once_with(query)
    
    @pytest.mark.asyncio
    async def test_assign_case_to_agent(self, service_cloud):
        """Test case assignment to agent."""
        mock_result = {
            "Id": "500xx000000001",
            "success": True,
            "errors": []
        }
        
        service_cloud.client.update_record = AsyncMock(return_value=mock_result)
        
        result = await service_cloud.assign_case_to_agent("500xx000000001", "005xx000000001")
        
        assert result["success"] is True
        assert result["Id"] == "500xx000000001"
        
        service_cloud.client.update_record.assert_called_once_with(
            "Case", 
            "500xx000000001", 
            {"OwnerId": "005xx000000001"}
        )
    
    @pytest.mark.asyncio
    async def test_get_omni_channel_status(self, service_cloud):
        """Test Omni-Channel status retrieval."""
        mock_status = {
            "totalSize": 1,
            "records": [{
                "Id": "0FYxx000000001",
                "ServiceChannelId": "0FKxx000000001",
                "Capacity": 5,
                "IsActive": True
            }]
        }
        
        service_cloud.client.execute_soql_query = AsyncMock(return_value=mock_status)
        
        result = await service_cloud.get_omni_channel_status("005xx000000001")
        
        assert result["totalSize"] == 1
        assert result["records"][0]["Capacity"] == 5
        assert result["records"][0]["IsActive"] is True
    
    @pytest.mark.asyncio
    async def test_create_knowledge_article(self, service_cloud):
        """Test knowledge article creation."""
        mock_article = {
            "Id": "kA0xx000000001",
            "ArticleNumber": "000001000",
            "Title": "Test Article",
            "UrlName": "test-article"
        }
        
        service_cloud.client.create_record = AsyncMock(return_value=mock_article)
        
        article_data = {
            "Title": "Test Article",
            "UrlName": "test-article",
            "Summary": "Test summary",
            "KnowledgeArticleVersion": {
                "Title": "Test Article",
                "TextBody": "Article content"
            }
        }
        
        result = await service_cloud.create_knowledge_article(article_data)
        
        assert result["Id"] == "kA0xx000000001"
        assert result["Title"] == "Test Article"
        assert result["ArticleNumber"] == "000001000"
        
        service_cloud.client.create_record.assert_called_once_with("KnowledgeArticle", article_data)
    
    @pytest.mark.asyncio
    async def test_search_knowledge_base(self, service_cloud):
        """Test knowledge base search."""
        mock_results = {
            "searchRecords": [{
                "Id": "kA0xx000000001",
                "Title": "Test Article",
                "Summary": "Test summary"
            }]
        }
        
        service_cloud.client.execute_sosl_search = AsyncMock(return_value=mock_results)
        
        result = await service_cloud.search_knowledge_base("test query")
        
        assert len(result["searchRecords"]) == 1
        assert result["searchRecords"][0]["Title"] == "Test Article"
        
        service_cloud.client.execute_sosl_search.assert_called_once()


class TestSalesforceModels:
    """Test Salesforce model validation."""
    
    def test_salesforce_case_creation(self):
        """Test SalesforceCase model creation."""
        case = SalesforceCase(
            subject="Test Case",
            description="Test description",
            priority="High",
            origin="Web",
            status="New"
        )
        
        assert case.subject == "Test Case"
        assert case.description == "Test description"
        assert case.priority == "High"
        assert case.origin == "Web"
        assert case.status == "New"
    
    def test_salesforce_case_validation(self):
        """Test SalesforceCase validation."""
        # Valid case
        case = SalesforceCase(
            subject="Test Case",
            priority="High",
            status="New"
        )
        assert case.priority in ["Low", "Medium", "High", "Critical"]
        
        # Invalid priority should raise validation error
        with pytest.raises(ValueError):
            case = SalesforceCase(
                subject="Test Case",
                priority="Invalid",
                status="New"
            )
    
    def test_salesforce_contact_creation(self):
        """Test SalesforceContact model creation."""
        contact = SalesforceContact(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567"
        )
        
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.email == "john.doe@example.com"
        assert contact.phone == "+1-555-123-4567"
    
    def test_salesforce_account_creation(self):
        """Test SalesforceAccount model creation."""
        account = SalesforceAccount(
            name="Test Account",
            industry="Technology",
            type="Customer",
            annual_revenue=1000000.0
        )
        
        assert account.name == "Test Account"
        assert account.industry == "Technology"
        assert account.type == "Customer"
        assert account.annual_revenue == 1000000.0


class TestSalesforceSyncEngine:
    """Test SalesforceSyncEngine functionality."""
    
    @pytest.fixture
    def sync_engine(self):
        client = Mock(spec=SalesforceClient)
        return SalesforceSyncEngine(client)
    
    @pytest.mark.asyncio
    async def test_sync_to_salesforce_success(self, sync_engine):
        """Test successful sync to Salesforce."""
        mock_case = SalesforceCase(
            id="500xx000000001",
            subject="Test Case",
            priority="High",
            status="New"
        )
        
        sync_engine.client.create_record = AsyncMock(return_value={
            "id": "500xx000000001",
            "success": True
        })
        
        result = await sync_engine.sync_to_salesforce(mock_case)
        
        assert result.success is True
        assert result.remote_id == "500xx000000001"
        assert result.direction == SyncDirection.TO_REMOTE
        
        sync_engine.client.create_record.assert_called_once_with("Case", mock_case.to_dict())
    
    @pytest.mark.asyncio
    async def test_sync_from_salesforce_success(self, sync_engine):
        """Test successful sync from Salesforce."""
        mock_remote_data = {
            "Id": "500xx000000001",
            "Subject": "Test Case",
            "Priority": "High",
            "Status": "New",
            "CreatedDate": "2024-01-01T00:00:00Z",
            "LastModifiedDate": "2024-01-01T12:00:00Z"
        }
        
        sync_engine.client.get_record = AsyncMock(return_value=mock_remote_data)
        
        result = await sync_engine.sync_from_salesforce("Case", "500xx000000001")
        
        assert result.success is True
        assert result.remote_id == "500xx000000001"
        assert result.direction == SyncDirection.FROM_REMOTE
        assert result.data["Subject"] == "Test Case"
        
        sync_engine.client.get_record.assert_called_once_with("Case", "500xx000000001")
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_client_wins(self, sync_engine):
        """Test client-wins conflict resolution."""
        local_data = SalesforceCase(
            subject="Local Case",
            priority="High",
            status="New"
        )
        
        remote_data = {
            "Subject": "Remote Case",
            "Priority": "Low",
            "Status": "Closed"
        }
        
        result = await sync_engine._resolve_conflict(
            local_data, 
            remote_data, 
            ConflictResolutionStrategy.CLIENT_WINS
        )
        
        assert result["Subject"] == "Local Case"  # Local wins
        assert result["Priority"] == "High"       # Local wins
        assert result["Status"] == "New"          # Local wins
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_server_wins(self, sync_engine):
        """Test server-wins conflict resolution."""
        local_data = SalesforceCase(
            subject="Local Case",
            priority="High",
            status="New"
        )
        
        remote_data = {
            "Subject": "Remote Case",
            "Priority": "Low",
            "Status": "Closed"
        }
        
        result = await sync_engine._resolve_conflict(
            local_data, 
            remote_data, 
            ConflictResolutionStrategy.SERVER_WINS
        )
        
        assert result["Subject"] == "Remote Case"  # Remote wins
        assert result["Priority"] == "Low"         # Remote wins
        assert result["Status"] == "Closed"        # Remote wins
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_merge(self, sync_engine):
        """Test merge conflict resolution."""
        local_data = SalesforceCase(
            subject="Local Case",
            priority="High",
            status="New",
            description="Local description"
        )
        
        remote_data = {
            "Subject": "Remote Case",
            "Priority": "Low",
            "Status": "Closed",
            "Description": "Remote description"
        }
        
        result = await sync_engine._resolve_conflict(
            local_data, 
            remote_data, 
            ConflictResolutionStrategy.MERGE
        )
        
        # Should prefer non-empty values from both sides
        assert result["Subject"] == "Remote Case"  # Remote has newer subject
        assert result["Priority"] == "High"        # Local has higher priority
        assert result["Status"] == "Closed"        # Remote has more advanced status
        assert result["Description"] == "Remote description"  # Remote description
    
    @pytest.mark.asyncio
    async def test_delta_sync_detection(self, sync_engine):
        """Test delta sync change detection."""
        local_timestamp = datetime.utcnow() - timedelta(hours=1)
        remote_timestamp = datetime.utcnow()
        
        has_changes = await sync_engine._detect_changes(
            local_timestamp,
            remote_timestamp
        )
        
        assert has_changes is True
        
        # Test no changes
        local_timestamp = datetime.utcnow()
        remote_timestamp = datetime.utcnow() - timedelta(hours=1)
        
        has_changes = await sync_engine._detect_changes(
            local_timestamp,
            remote_timestamp
        )
        
        assert has_changes is False
    
    @pytest.mark.asyncio
    async def test_sync_with_rate_limit_handling(self, sync_engine):
        """Test sync with rate limit handling."""
        mock_case = SalesforceCase(
            subject="Test Case",
            priority="High",
            status="New"
        )
        
        # First call fails with rate limit, second succeeds
        sync_engine.client.create_record = AsyncMock(side_effect=[
            RateLimitError("Rate limit exceeded"),
            {"id": "500xx000000001", "success": True}
        ])
        
        # Should retry and succeed
        result = await sync_engine.sync_to_salesforce(mock_case)
        
        assert result.success is True
        assert sync_engine.client.create_record.call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_check(self, sync_engine):
        """Test sync engine health check."""
        sync_engine.client.health_check = AsyncMock(return_value={
            "status": "healthy",
            "api_version": "v58.0"
        })
        
        health = await sync_engine.health_check()
        
        assert health["status"] == "healthy"
        assert health["api_version"] == "v58.0"
        assert health["sync_engine"] == "operational"


# Performance tests
@pytest.mark.integration
class TestSalesforcePerformance:
    """Performance tests for Salesforce integration."""
    
    @pytest.mark.asyncio
    async def test_bulk_operations_performance(self):
        """Test bulk operations performance."""
        client = Mock(spec=SalesforceClient)
        client.bulk_create_records = AsyncMock(return_value={
            "jobInfo": {"id": "750xx000000001", "state": "Open"}
        })
        
        sf_client = SalesforceClient(
            oauth_config=Mock(),
            instance_url="https://test.salesforce.com",
            username="test@example.com"
        )
        sf_client.access_token = "test_token"
        sf_client._session = Mock()
        
        # Test 1000 record bulk creation
        records = [{"Name": f"Account {i}"} for i in range(1000)]
        
        start_time = time.time()
        result = await sf_client.bulk_create_records("Account", records)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 1 second for mock)
        assert duration < 1.0
        assert result["jobInfo"]["id"] == "750xx000000001"
    
    @pytest.mark.asyncio
    async def test_concurrent_queries_performance(self):
        """Test concurrent query performance."""
        client = Mock(spec=SalesforceClient)
        client.execute_soql_query = AsyncMock(return_value={
            "totalSize": 100,
            "records": [{"Id": f"001xx000000{i:03d}"} for i in range(100)]
        })
        
        # Test 50 concurrent queries
        queries = [f"SELECT Id FROM Account WHERE Name LIKE 'Test {i}%'" for i in range(50)]
        
        start_time = time.time()
        tasks = [client.execute_soql_query(query) for query in queries]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds for mock)
        assert duration < 2.0
        assert len(results) == 50
        assert all(result["totalSize"] == 100 for result in results)


# Error handling tests
@pytest.mark.asyncio
class TestSalesforceErrorHandling:
    """Test error handling in Salesforce integration."""
    
    async def test_oauth_error_handling(self):
        """Test OAuth error handling."""
        oauth_config = OAuth2Config(
            client_id="test_client",
            client_secret="test_secret",
            authorization_url="https://login.salesforce.com/services/oauth2/authorize",
            token_url="https://login.salesforce.com/services/oauth2/token",
            redirect_uri="https://app.example.com/callback",
            scope="api refresh_token"
        )
        
        sf_client = SalesforceClient(
            oauth_config=oauth_config,
            instance_url="https://test.salesforce.com",
            username="test@example.com"
        )
        
        # Test network error during authentication
        with patch.object(sf_client.oauth_client, 'exchange_code_for_token', side_effect=Exception("Network error")):
            success = await sf_client.authenticate("test_code")
            assert success is False
    
    async def test_api_error_handling(self):
        """Test API error handling."""
        client = Mock(spec=SalesforceClient)
        client.execute_soql_query = AsyncMock(side_effect=Exception("API Error"))
        
        service_cloud = SalesforceServiceCloud(client)
        
        with pytest.raises(Exception, match="API Error"):
            await service_cloud.search_cases("SELECT Id FROM Case")
    
    async def test_sync_error_handling(self):
        """Test sync error handling."""
        client = Mock(spec=SalesforceClient)
        client.create_record = AsyncMock(side_effect=Exception("Sync failed"))
        
        sync_engine = SalesforceSyncEngine(client)
        
        mock_case = SalesforceCase(subject="Test Case", priority="High", status="New")
        
        result = await sync_engine.sync_to_salesforce(mock_case)
        
        assert result.success is False
        assert result.error == "Sync failed"