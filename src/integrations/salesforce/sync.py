"""
Bi-directional synchronization engine for Salesforce integration.

Provides comprehensive sync capabilities including:
- Real-time and scheduled synchronization
- Change detection and conflict resolution
- Delta sync for efficiency
- Error recovery and retry logic
- Sync status monitoring and reporting
- Dead letter queue management
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator
from uuid import UUID, uuid4

from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from redis import Redis

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from src.database.connection import get_session
from src.database.models import SalesforceSyncRecord
from ..base import SyncDirection, ConflictResolutionStrategy
from .client import SalesforceClient, SalesforceAPIError
from .models import (
    SalesforceCase,
    SalesforceContact,
    SalesforceAccount,
    SalesforceSyncState,
    SalesforceObjectMapping,
    SalesforceFieldMapping,
)

logger = get_logger(__name__)


class SyncError(ExternalServiceError):
    """Synchronization specific errors."""
    pass


class SalesforceSyncEngine:
    """Bi-directional synchronization engine for Salesforce."""
    
    def __init__(
        self,
        client: SalesforceClient,
        organization_id: UUID,
        redis_client: Redis,
        conflict_resolution: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS
    ):
        self.client = client
        self.organization_id = organization_id
        self.redis = redis_client
        self.settings = get_settings()
        self.logger = logger.getChild("sync_engine")
        self.conflict_resolution = conflict_resolution
        
        # Sync configuration
        self.sync_config = self.client.config.sync
        self.lag_threshold = timedelta(seconds=self.sync_config.lag_threshold_seconds)
        self.batch_size = self.sync_config.batch_size
        
        # Sync state tracking
        self._sync_in_progress = False
        self._last_sync_time: Optional[datetime] = None
        self._sync_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "conflicts": 0,
            "start_time": None,
            "end_time": None
        }
    
    # Core Sync Methods
    
    async def sync_bidirectional(
        self,
        object_type: str,
        sync_mode: str = "incremental",
        force_full_sync: bool = False
    ) -> Dict[str, Any]:
        """Perform bi-directional synchronization for specified object type."""
        if self._sync_in_progress:
            raise SyncError("Sync already in progress")
        
        self._sync_in_progress = True
        self._sync_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "conflicts": 0,
            "start_time": datetime.utcnow(),
            "end_time": None
        }
        
        try:
            self.logger.info(f"Starting bi-directional sync for {object_type}")
            
            # Determine sync strategy
            if sync_mode == "full" or force_full_sync:
                result = await self._perform_full_sync(object_type)
            else:
                result = await self._perform_incremental_sync(object_type)
            
            self._last_sync_time = datetime.utcnow()
            self._sync_stats["end_time"] = self._last_sync_time
            
            self.logger.info(
                f"Bi-directional sync completed for {object_type}: "
                f"{self._sync_stats['successful']} successful, "
                f"{self._sync_stats['failed']} failed, "
                f"{self._sync_stats['conflicts']} conflicts"
            )
            
            return {
                "object_type": object_type,
                "sync_mode": sync_mode,
                "status": "completed",
                "stats": self._sync_stats.copy(),
                "timestamp": self._last_sync_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Bi-directional sync failed for {object_type}: {e}")
            self._sync_stats["end_time"] = datetime.utcnow()
            
            return {
                "object_type": object_type,
                "sync_mode": sync_mode,
                "status": "failed",
                "error": str(e),
                "stats": self._sync_stats.copy(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        finally:
            self._sync_in_progress = False
    
    async def _perform_full_sync(self, object_type: str) -> Dict[str, Any]:
        """Perform full synchronization (all records)."""
        self.logger.info(f"Performing full sync for {object_type}")
        
        # Get all records from both systems
        local_records = await self._get_all_local_records(object_type)
        remote_records = await self._get_all_remote_records(object_type)
        
        # Sync each record
        for local_record in local_records:
            await self._sync_single_record(object_type, local_record, remote_records)
        
        # Handle remote-only records
        for remote_record in remote_records:
            if not any(r["salesforce_id"] == remote_record["Id"] for r in local_records):
                await self._sync_remote_only_record(object_type, remote_record)
        
        return {"status": "completed", "records_processed": len(local_records) + len(remote_records)}
    
    async def _perform_incremental_sync(self, object_type: str) -> Dict[str, Any]:
        """Perform incremental synchronization (changed records only)."""
        self.logger.info(f"Performing incremental sync for {object_type}")
        
        # Get last sync timestamp
        last_sync = await self._get_last_sync_timestamp(object_type)
        
        # Get changed records from both systems
        local_changes = await self._get_local_changes(object_type, last_sync)
        remote_changes = await self._get_remote_changes(object_type, last_sync)
        
        # Sync changed records
        for local_change in local_changes:
            await self._sync_single_record(object_type, local_change, remote_changes)
        
        # Handle remote-only changes
        for remote_change in remote_changes:
            if not any(r["salesforce_id"] == remote_change["Id"] for r in local_changes):
                await self._sync_remote_only_record(object_type, remote_change)
        
        return {"status": "completed", "records_processed": len(local_changes) + len(remote_changes)}
    
    async def _sync_single_record(
        self,
        object_type: str,
        local_record: Dict[str, Any],
        remote_records: List[Dict[str, Any]]
    ) -> None:
        """Synchronize a single record."""
        try:
            self._sync_stats["total_processed"] += 1
            
            # Find corresponding remote record
            remote_record = None
            for record in remote_records:
                if record["Id"] == local_record.get("salesforce_id"):
                    remote_record = record
                    break
            
            if remote_record:
                # Both records exist, check for conflicts
                await self._resolve_conflict(object_type, local_record, remote_record)
            else:
                # Local record only, push to Salesforce
                await self._push_to_salesforce(object_type, local_record)
            
            self._sync_stats["successful"] += 1
            
        except Exception as e:
            self.logger.error(f"Failed to sync record {local_record.get('id')}: {e}")
            self._sync_stats["failed"] += 1
            
            # Add to dead letter queue
            await self._add_to_dead_letter_queue(object_type, local_record, str(e))
    
    async def _resolve_conflict(
        self,
        object_type: str,
        local_record: Dict[str, Any],
        remote_record: Dict[str, Any]
    ) -> None:
        """Resolve conflict between local and remote records."""
        # Check if there's an actual conflict (both modified since last sync)
        local_modified = local_record.get("last_modified_date")
        remote_modified = remote_record.get("LastModifiedDate")
        last_sync = await self._get_last_sync_time(object_type, local_record["id"])
        
        if self._has_conflict(local_modified, remote_modified, last_sync):
            self._sync_stats["conflicts"] += 1
            self.logger.warning(f"Conflict detected for {object_type} record {local_record['id']}")
            
            # Resolve based on configured strategy
            if self.conflict_resolution == ConflictResolutionStrategy.LAST_WRITE_WINS:
                await self._resolve_last_write_wins(object_type, local_record, remote_record)
            elif self.conflict_resolution == ConflictResolutionStrategy.MERGE:
                await self._resolve_merge(object_type, local_record, remote_record)
            else:
                # Manual resolution required
                await self._flag_manual_resolution(object_type, local_record, remote_record)
        else:
            # No conflict, just update sync state
            await self._update_sync_state(object_type, local_record["id"], remote_record["Id"])
    
    def _has_conflict(
        self,
        local_modified: Optional[str],
        remote_modified: Optional[str],
        last_sync: Optional[datetime]
    ) -> bool:
        """Determine if there's a conflict between local and remote changes."""
        if not last_sync:
            return False
        
        if not local_modified or not remote_modified:
            return False
        
        # Parse timestamps
        try:
            local_dt = datetime.fromisoformat(local_modified.replace("Z", "+00:00"))
            remote_dt = datetime.fromisoformat(remote_modified.replace("Z", "+00:00"))
            
            # Conflict if both modified after last sync
            return local_dt > last_sync and remote_dt > last_sync
            
        except Exception:
            return False
    
    async def _resolve_last_write_wins(
        self,
        object_type: str,
        local_record: Dict[str, Any],
        remote_record: Dict[str, Any]
    ) -> None:
        """Resolve conflict using last-write-wins strategy."""
        local_modified = datetime.fromisoformat(local_record["last_modified_date"].replace("Z", "+00:00"))
        remote_modified = datetime.fromisoformat(remote_record["LastModifiedDate"].replace("Z", "+00:00"))
        
        if local_modified >= remote_modified:
            # Local is newer, push to Salesforce
            await self._push_to_salesforce(object_type, local_record)
        else:
            # Remote is newer, pull from Salesforce
            await self._pull_from_salesforce(object_type, remote_record)
    
    async def _resolve_merge(
        self,
        object_type: str,
        local_record: Dict[str, Any],
        remote_record: Dict[str, Any]
    ) -> None:
        """Resolve conflict by merging data."""
        # Merge logic would be implemented here
        # For now, use last-write-wins as fallback
        await self._resolve_last_write_wins(object_type, local_record, remote_record)
    
    async def _flag_manual_resolution(
        self,
        object_type: str,
        local_record: Dict[str, Any],
        remote_record: Dict[str, Any]
    ) -> None:
        """Flag record for manual conflict resolution."""
        self.logger.warning(f"Manual conflict resolution required for {object_type} record {local_record['id']}")
        
        # Store conflict details for manual review
        conflict_data = {
            "object_type": object_type,
            "local_record": local_record,
            "remote_record": remote_record,
            "conflict_type": "manual_resolution_required",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self._store_conflict(conflict_data)
    
    async def _push_to_salesforce(self, object_type: str, local_record: Dict[str, Any]) -> None:
        """Push local record to Salesforce."""
        try:
            # Transform local data to Salesforce format
            salesforce_data = await self._transform_to_salesforce(object_type, local_record)
            
            # Determine if this is a new or existing record
            if local_record.get("salesforce_id"):
                # Update existing record
                result = await self.client.update_object(object_type, local_record["salesforce_id"], salesforce_data)
                salesforce_id = local_record["salesforce_id"]
            else:
                # Create new record
                result = await self.client.create_object(object_type, salesforce_data)
                salesforce_id = result["id"]
            
            # Update sync state
            await self._update_sync_state(object_type, local_record["id"], salesforce_id)
            
            self.logger.info(f"Pushed {object_type} record {local_record['id']} to Salesforce as {salesforce_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to push {object_type} record to Salesforce: {e}")
            raise SyncError(f"Failed to push record to Salesforce: {e}")
    
    async def _pull_from_salesforce(self, object_type: str, remote_record: Dict[str, Any]) -> None:
        """Pull remote record from Salesforce to local system."""
        try:
            # Transform Salesforce data to local format
            local_data = await self._transform_from_salesforce(object_type, remote_record)
            
            # Update local record
            await self._update_local_record(object_type, local_data)
            
            # Update sync state
            local_id = await self._get_local_id_by_salesforce_id(object_type, remote_record["Id"])
            if local_id:
                await self._update_sync_state(object_type, local_id, remote_record["Id"])
            
            self.logger.info(f"Pulled {object_type} record {remote_record['Id']} from Salesforce")
            
        except Exception as e:
            self.logger.error(f"Failed to pull {object_type} record from Salesforce: {e}")
            raise SyncError(f"Failed to pull record from Salesforce: {e}")
    
    async def _sync_remote_only_record(self, object_type: str, remote_record: Dict[str, Any]) -> None:
        """Sync remote-only record to local system."""
        await self._pull_from_salesforce(object_type, remote_record)
    
    # Data Transformation Methods
    
    async def _transform_to_salesforce(self, object_type: str, local_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform local record to Salesforce format."""
        # Get field mapping for this object type
        field_mapping = await self._get_field_mapping(object_type)
        
        salesforce_data = {}
        
        # Apply field mappings
        for local_field, salesforce_field in field_mapping.items():
            if local_field in local_record:
                # Apply transformation if specified
                if salesforce_field.transformation_rule:
                    transformed_value = await self._apply_transformation(
                        local_record[local_field],
                        salesforce_field.transformation_rule
                    )
                    salesforce_data[salesforce_field.salesforce_field] = transformed_value
                else:
                    salesforce_data[salesforce_field.salesforce_field] = local_record[local_field]
        
        # Add AI-specific fields
        salesforce_data.update({
            "AI_Source_System__c": "AI_Customer_Service_Agent",
            "AI_Conversation_ID__c": str(self.organization_id),
            "AI_Last_Sync_Date__c": datetime.utcnow().isoformat()
        })
        
        return salesforce_data
    
    async def _transform_from_salesforce(self, object_type: str, remote_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Salesforce record to local format."""
        # Get field mapping for this object type
        field_mapping = await self._get_field_mapping(object_type)
        
        local_data = {
            "id": await self._get_local_id_by_salesforce_id(object_type, remote_record["Id"]),
            "salesforce_id": remote_record["Id"],
            "organization_id": self.organization_id,
            "last_synced_at": datetime.utcnow().isoformat()
        }
        
        # Apply field mappings
        for local_field, salesforce_field in field_mapping.items():
            sf_field_name = salesforce_field.salesforce_field
            if sf_field_name in remote_record:
                local_data[local_field] = remote_record[sf_field_name]
        
        return local_data
    
    # Sync State Management
    
    async def _update_sync_state(
        self,
        object_type: str,
        local_id: str,
        salesforce_id: str,
        status: str = "synced"
    ) -> None:
        """Update sync state for a record."""
        async with get_session() as session:
            # Update or create sync record
            stmt = select(SalesforceSyncRecord).where(
                SalesforceSyncRecord.organization_id == self.organization_id,
                SalesforceSyncRecord.local_id == local_id,
                SalesforceSyncRecord.object_type == object_type
            )
            
            result = await session.execute(stmt)
            sync_record = result.scalar_one_or_none()
            
            if sync_record:
                # Update existing record
                sync_record.salesforce_id = salesforce_id
                sync_record.sync_status = status
                sync_record.last_sync_date = datetime.utcnow()
            else:
                # Create new record
                sync_record = SalesforceSyncRecord(
                    id=uuid4(),
                    organization_id=self.organization_id,
                    local_id=local_id,
                    salesforce_id=salesforce_id,
                    object_type=object_type,
                    sync_direction=SyncDirection.BIDIRECTIONAL.value,
                    sync_status=status,
                    last_sync_date=datetime.utcnow(),
                    conflict_resolution=self.conflict_resolution.value
                )
                session.add(sync_record)
            
            await session.commit()
    
    async def _get_last_sync_time(self, object_type: str, record_id: str) -> Optional[datetime]:
        """Get last sync time for a record."""
        async with get_session() as session:
            stmt = select(SalesforceSyncRecord.last_sync_date).where(
                SalesforceSyncRecord.organization_id == self.organization_id,
                SalesforceSyncRecord.local_id == record_id,
                SalesforceSyncRecord.object_type == object_type
            )
            
            result = await session.execute(stmt)
            last_sync = result.scalar_one_or_none()
            
            return last_sync
    
    async def _get_local_id_by_salesforce_id(self, object_type: str, salesforce_id: str) -> Optional[str]:
        """Get local ID by Salesforce ID."""
        async with get_session() as session:
            stmt = select(SalesforceSyncRecord.local_id).where(
                SalesforceSyncRecord.organization_id == self.organization_id,
                SalesforceSyncRecord.salesforce_id == salesforce_id,
                SalesforceSyncRecord.object_type == object_type
            )
            
            result = await session.execute(stmt)
            local_id = result.scalar_one_or_none()
            
            return local_id
    
    # Data Retrieval Methods
    
    async def _get_all_local_records(self, object_type: str) -> List[Dict[str, Any]]:
        """Get all local records of specified type."""
        # This would query the local database
        # Implementation depends on the specific object type
        return []
    
    async def _get_all_remote_records(self, object_type: str) -> List[Dict[str, Any]]:
        """Get all remote records of specified type."""
        try:
            soql = f"SELECT Id, LastModifiedDate FROM {object_type} ORDER BY LastModifiedDate DESC"
            result = await self.client.query(soql)
            return result.get("records", [])
        except Exception as e:
            self.logger.error(f"Failed to get remote {object_type} records: {e}")
            return []
    
    async def _get_local_changes(self, object_type: str, since: Optional[datetime]) -> List[Dict[str, Any]]:
        """Get local records changed since specified time."""
        # Implementation depends on the specific object type
        return []
    
    async def _get_remote_changes(self, object_type: str, since: Optional[datetime]) -> List[Dict[str, Any]]:
        """Get remote records changed since specified time."""
        try:
            where_clause = ""
            if since:
                where_clause = f"WHERE LastModifiedDate > {since.isoformat()}"
            
            soql = f"SELECT Id, LastModifiedDate FROM {object_type} {where_clause} ORDER BY LastModifiedDate DESC"
            result = await self.client.query(soql)
            return result.get("records", [])
        except Exception as e:
            self.logger.error(f"Failed to get remote {object_type} changes: {e}")
            return []
    
    async def _get_last_sync_timestamp(self, object_type: str) -> Optional[datetime]:
        """Get last successful sync timestamp for object type."""
        async with get_session() as session:
            stmt = select(SalesforceSyncRecord.last_sync_date).where(
                SalesforceSyncRecord.organization_id == self.organization_id,
                SalesforceSyncRecord.object_type == object_type,
                SalesforceSyncRecord.sync_status == "synced"
            ).order_by(SalesforceSyncRecord.last_sync_date.desc())
            
            result = await session.execute(stmt)
            last_sync = result.scalar_one_or_none()
            
            return last_sync
    
    # Helper Methods
    
    async def _get_field_mapping(self, object_type: str) -> Dict[str, SalesforceFieldMapping]:
        """Get field mapping configuration for object type."""
        # This would load from configuration
        # Return default mappings for now
        return {}
    
    async def _apply_transformation(self, value: Any, rule: str) -> Any:
        """Apply data transformation rule."""
        # Implementation of transformation rules
        return value
    
    async def _add_to_dead_letter_queue(
        self,
        object_type: str,
        record: Dict[str, Any],
        error_message: str
    ) -> None:
        """Add failed record to dead letter queue."""
        dlq_data = {
            "object_type": object_type,
            "record_data": record,
            "error_message": error_message,
            "retry_count": record.get("retry_count", 0),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in Redis with TTL
        dlq_key = f"salesforce_dlq:{self.organization_id}:{object_type}:{record['id']}"
        await self.redis.setex(
            dlq_key,
            timedelta(days=7),  # 7 day retention
            json.dumps(dlq_data)
        )
        
        self.logger.error(f"Added {object_type} record {record['id']} to dead letter queue: {error_message}")
    
    async def _store_conflict(self, conflict_data: Dict[str, Any]) -> None:
        """Store conflict data for manual resolution."""
        conflict_key = f"salesforce_conflicts:{self.organization_id}:{conflict_data['object_type']}:{conflict_data['local_record']['id']}"
        await self.redis.setex(
            conflict_key,
            timedelta(days=30),  # 30 day retention
            json.dumps(conflict_data)
        )
    
    # Real-time Sync Methods
    
    async def enable_real_time_sync(self, object_type: str) -> None:
        """Enable real-time synchronization for object type."""
        if not self.sync_config.enable_real_time:
            self.logger.warning(f"Real-time sync not enabled for {object_type}")
            return
        
        # Subscribe to Platform Events
        channel = f"/event/{object_type}ChangeEvent"
        
        async for event in self.client.subscribe_platform_events(channel):
            await self._handle_real_time_change(event)
    
    async def _handle_real_time_change(self, event: Dict[str, Any]) -> None:
        """Handle real-time change event."""
        try:
            event_data = event.get("data", {}).get("payload", {})
            object_type = event_data.get("ChangeEventHeader", {}).get("entityName", "")
            
            if not object_type:
                return
            
            # Process the change
            self.logger.info(f"Processing real-time change for {object_type}")
            
            # Trigger incremental sync for the changed record
            await self.sync_bidirectional(object_type, sync_mode="incremental")
            
        except Exception as e:
            self.logger.error(f"Failed to handle real-time change: {e}")
    
    # Monitoring and Reporting
    
    async def get_sync_status(self, object_type: Optional[str] = None) -> Dict[str, Any]:
        """Get synchronization status and statistics."""
        async with get_session() as session:
            # Get overall sync statistics
            if object_type:
                stmt = select(SalesforceSyncRecord).where(
                    SalesforceSyncRecord.organization_id == self.organization_id,
                    SalesforceSyncRecord.object_type == object_type
                )
            else:
                stmt = select(SalesforceSyncRecord).where(
                    SalesforceSyncRecord.organization_id == self.organization_id
                )
            
            result = await session.execute(stmt)
            sync_records = result.scalars().all()
            
            # Calculate statistics
            total_records = len(sync_records)
            synced_records = len([r for r in sync_records if r.sync_status == "synced"])
            failed_records = len([r for r in sync_records if r.sync_status == "failed"])
            conflict_records = len([r for r in sync_records if r.sync_status == "conflict"])
            
            # Get dead letter queue size
            dlq_pattern = f"salesforce_dlq:{self.organization_id}:*"
            dlq_keys = await self.redis.keys(dlq_pattern)
            dlq_size = len(dlq_keys)
            
            # Get conflict queue size
            conflict_pattern = f"salesforce_conflicts:{self.organization_id}:*"
            conflict_keys = await self.redis.keys(conflict_pattern)
            conflict_size = len(conflict_keys)
            
            return {
                "organization_id": str(self.organization_id),
                "object_type": object_type,
                "total_synced_records": total_records,
                "synced_records": synced_records,
                "failed_records": failed_records,
                "conflict_records": conflict_records,
                "sync_success_rate": (synced_records / total_records * 100) if total_records > 0 else 0,
                "dead_letter_queue_size": dlq_size,
                "conflict_queue_size": conflict_size,
                "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_sync_lag(self, object_type: str) -> float:
        """Get current sync lag in seconds for object type."""
        try:
            # Get most recent remote change
            soql = f"SELECT Id, LastModifiedDate FROM {object_type} ORDER BY LastModifiedDate DESC LIMIT 1"
            result = await self.client.query(soql)
            
            if not result.get("records"):
                return 0.0
            
            remote_modified = datetime.fromisoformat(result["records"][0]["LastModifiedDate"].replace("Z", "+00:00"))
            
            # Get last sync time
            last_sync = await self._get_last_sync_timestamp(object_type)
            if not last_sync:
                return 0.0
            
            lag = (datetime.utcnow() - remote_modified).total_seconds()
            return max(lag, 0.0)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate sync lag for {object_type}: {e}")
            return 0.0
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check of sync engine."""
        try:
            # Check client health
            client_health = await self.client.health_check()
            
            # Check sync lag for configured objects
            sync_lags = {}
            for obj_type in self.client.config.sync_objects:
                try:
                    lag = await self.get_sync_lag(obj_type)
                    sync_lags[obj_type] = lag
                except Exception as e:
                    self.logger.warning(f"Failed to get sync lag for {obj_type}: {e}")
                    sync_lags[obj_type] = -1.0
            
            # Check for excessive lag
            excessive_lag = any(lag > self.sync_config.lag_threshold_seconds for lag in sync_lags.values() if lag >= 0)
            
            # Overall health status
            is_healthy = (
                client_health.get("status") == "healthy" and
                not excessive_lag and
                not self._sync_in_progress
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "client_health": client_health,
                "sync_lags": sync_lags,
                "excessive_lag": excessive_lag,
                "sync_in_progress": self._sync_in_progress,
                "last_sync_time": self._last_sync_time.isoformat() if self._last_sync_time else None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Sync engine health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Export the sync engine
__all__ = ["SalesforceSyncEngine", "SyncError"]