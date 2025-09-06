"""
Integration health monitoring and alerting system.

Provides comprehensive health monitoring including:
- Health check orchestration for all integrations
- Configurable health check intervals and timeouts
- Alert generation for health status changes
- Integration dependency tracking
- Automated recovery attempts
- Health status history and trending
- Integration with external monitoring systems
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import threading

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError
from ..base import BaseIntegrationImpl, IntegrationStatus
from .metrics import get_integration_metrics, IntegrationMetrics

logger = get_logger(__name__)


class HealthCheckStatus(str, Enum):
    """Health check execution status."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class AlertLevel(str, Enum):
    """Alert severity levels."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check execution."""
    
    integration_name: str
    integration_type: str
    status: HealthCheckStatus
    health_status: IntegrationStatus
    response_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthAlert:
    """Health alert information."""
    
    integration_name: str
    integration_type: str
    alert_level: AlertLevel
    title: str
    message: str
    previous_status: IntegrationStatus
    current_status: IntegrationStatus
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    
    enabled: bool = True
    interval_seconds: int = 60
    timeout_seconds: int = 30
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    failure_threshold: int = 3
    success_threshold: int = 2
    alert_on_status_change: bool = True
    alert_on_failure: bool = True
    auto_recovery_enabled: bool = True
    dependencies: List[str] = field(default_factory=list)
    custom_checks: List[str] = field(default_factory=list)


class HealthCheckExecutor:
    """Executes health checks for integrations."""
    
    def __init__(self, integration: BaseIntegrationImpl, config: HealthCheckConfig):
        self.integration = integration
        self.config = config
        self.logger = logger.getChild(f"health_executor.{integration.integration_type.value}")
        
        # Health check state
        self._last_check: Optional[HealthCheckResult] = None
        self._check_history: List[HealthCheckResult] = []
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._is_running = False
        self._check_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = get_integration_metrics(integration.integration_type.value)
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[HealthAlert], None]] = []
    
    async def start(self) -> None:
        """Start health check execution."""
        if not self.config.enabled:
            self.logger.info(f"Health checks disabled for {self.integration.integration_type.value}")
            return
        
        if self._is_running:
            return
        
        self._is_running = True
        self._check_task = asyncio.create_task(self._run_health_checks())
        self.logger.info(f"Started health checks for {self.integration.integration_type.value}")
    
    async def stop(self) -> None:
        """Stop health check execution."""
        if not self._is_running:
            return
        
        self._is_running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"Stopped health checks for {self.integration.integration_type.value}")
    
    async def execute_check(self, force: bool = False) -> HealthCheckResult:
        """Execute a single health check."""
        start_time = time.time()
        
        try:
            # Check dependencies first
            if not force and not await self._check_dependencies():
                return HealthCheckResult(
                    integration_name=self.integration.integration_type.value,
                    integration_type=self.integration.integration_type.value,
                    status=HealthCheckStatus.SKIPPED,
                    health_status=IntegrationStatus.DEGRADED,
                    response_time_ms=0.0,
                    timestamp=datetime.utcnow(),
                    error_message="Dependencies not healthy",
                    metadata={"skipped_reason": "dependencies"}
                )
            
            # Execute health check with timeout
            health_result = await asyncio.wait_for(
                self.integration.health_check(),
                timeout=self.config.timeout_seconds
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Map health result to our status
            if health_result.get("status") == "healthy":
                status = HealthCheckStatus.SUCCESS
                health_status = IntegrationStatus.HEALTHY
            elif health_result.get("status") == "degraded":
                status = HealthCheckStatus.SUCCESS
                health_status = IntegrationStatus.DEGRADED
            else:
                status = HealthCheckStatus.FAILURE
                health_status = IntegrationStatus.UNHEALTHY
            
            result = HealthCheckResult(
                integration_name=self.integration.integration_type.value,
                integration_type=self.integration.integration_type.value,
                status=status,
                health_status=health_status,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                metadata=health_result
            )
            
            # Record success metrics
            self.metrics.record_request(
                method="HEALTH_CHECK",
                endpoint="health",
                status="success" if status == HealthCheckStatus.SUCCESS else "failure",
                duration=response_time_ms / 1000  # Convert to seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                integration_name=self.integration.integration_type.value,
                integration_type=self.integration.integration_type.value,
                status=HealthCheckStatus.TIMEOUT,
                health_status=IntegrationStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=f"Health check timed out after {self.config.timeout_seconds} seconds"
            )
            
            # Record timeout metrics
            self.metrics.record_error("TIMEOUT", "HEALTH_CHECK_TIMEOUT")
            
            return result
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            
            result = HealthCheckResult(
                integration_name=self.integration.integration_type.value,
                integration_type=self.integration.integration_type.value,
                status=HealthCheckStatus.FAILURE,
                health_status=IntegrationStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=str(e),
                error_details={"error_type": type(e).__name__, "traceback": str(e)}
            )
            
            # Record error metrics
            self.metrics.record_error("HEALTH_CHECK", type(e).__name__)
            
            return result
    
    async def _run_health_checks(self) -> None:
        """Run health checks periodically."""
        while self._is_running:
            try:
                result = await self.execute_check()
                await self._process_result(result)
                
                await asyncio.sleep(self.config.interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check execution: {e}")
                await asyncio.sleep(self.config.retry_delay_seconds)
    
    async def _process_result(self, result: HealthCheckResult) -> None:
        """Process health check result."""
        # Update history
        self._check_history.append(result)
        if len(self._check_history) > 1000:  # Keep last 1000 results
            self._check_history.pop(0)
        
        # Update consecutive counters
        if result.status == HealthCheckStatus.SUCCESS:
            self._consecutive_successes += 1
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1
            self._consecutive_successes = 0
        
        # Check for status changes and alerts
        if self._last_check:
            await self._check_status_change(result)
        
        self._last_check = result
        
        # Attempt auto-recovery if configured
        if (result.status != HealthCheckStatus.SUCCESS and 
            self.config.auto_recovery_enabled and 
            self._consecutive_failures >= self.config.failure_threshold):
            await self._attempt_recovery()
    
    async def _check_status_change(self, current_result: HealthCheckResult) -> None:
        """Check for status changes and generate alerts."""
        if not self._last_check:
            return
        
        previous_status = self._last_check.health_status
        current_status = current_result.health_status
        
        if previous_status != current_status:
            # Status changed
            if self.config.alert_on_status_change:
                alert = self._create_status_change_alert(previous_status, current_status, current_result)
                await self._send_alert(alert)
        
        elif (current_result.status != HealthCheckStatus.SUCCESS and 
              self.config.alert_on_failure and 
              self._consecutive_failures >= self.config.failure_threshold):
            # Repeated failures
            alert = self._create_failure_alert(current_result)
            await self._send_alert(alert)
    
    def _create_status_change_alert(
        self,
        previous_status: IntegrationStatus,
        current_status: IntegrationStatus,
        result: HealthCheckResult
    ) -> HealthAlert:
        """Create status change alert."""
        if current_status == IntegrationStatus.HEALTHY:
            level = AlertLevel.INFO
            title = f"{self.integration.integration_type.value} Integration Recovered"
            message = f"Integration health status changed from {previous_status.value} to {current_status.value}"
        elif current_status == IntegrationStatus.UNHEALTHY:
            level = AlertLevel.ERROR
            title = f"{self.integration.integration_type.value} Integration Unhealthy"
            message = f"Integration health status changed from {previous_status.value} to {current_status.value}"
        else:  # DEGRADED
            level = AlertLevel.WARNING
            title = f"{self.integration.integration_type.value} Integration Degraded"
            message = f"Integration health status changed from {previous_status.value} to {current_status.value}"
        
        return HealthAlert(
            integration_name=self.integration.integration_type.value,
            integration_type=self.integration.integration_type.value,
            alert_level=level,
            title=title,
            message=message,
            previous_status=previous_status,
            current_status=current_status,
            timestamp=result.timestamp,
            metadata={
                "response_time_ms": result.response_time_ms,
                "error_message": result.error_message
            }
        )
    
    def _create_failure_alert(self, result: HealthCheckResult) -> HealthAlert:
        """Create failure alert."""
        return HealthAlert(
            integration_name=self.integration.integration_type.value,
            integration_type=self.integration.integration_type.value,
            alert_level=AlertLevel.ERROR,
            title=f"{self.integration.integration_type.value} Integration Failure",
            message=f"Integration has failed {self._consecutive_failures} consecutive times",
            previous_status=IntegrationStatus.HEALTHY,
            current_status=IntegrationStatus.UNHEALTHY,
            timestamp=result.timestamp,
            metadata={
                "consecutive_failures": self._consecutive_failures,
                "response_time_ms": result.response_time_ms,
                "error_message": result.error_message,
                "error_details": result.error_details
            }
        )
    
    async def _send_alert(self, alert: HealthAlert) -> None:
        """Send alert through configured channels."""
        self.logger.warning(f"Health alert: {alert.title} - {alert.message}")
        
        # Execute alert callbacks
        for callback in self._alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Error executing alert callback: {e}")
        
        # Record alert metrics
        self.metrics.record_error("HEALTH_ALERT", alert.alert_level.value)
    
    async def _attempt_recovery(self) -> None:
        """Attempt to recover integration."""
        self.logger.info(f"Attempting recovery for {self.integration.integration_type.value}")
        
        try:
            # Close and re-authenticate
            await self.integration.close()
            success = await self.integration.authenticate()
            
            if success:
                self.logger.info(f"Recovery successful for {self.integration.integration_type.value}")
                # Record recovery metrics
                self.metrics.record_business_metrics(success_rate=100.0, operation_type="recovery")
            else:
                self.logger.error(f"Recovery failed for {self.integration.integration_type.value}")
                
        except Exception as e:
            self.logger.error(f"Recovery attempt failed for {self.integration.integration_type.value}: {e}")
    
    async def _check_dependencies(self) -> bool:
        """Check if dependencies are healthy."""
        if not self.config.dependencies:
            return True
        
        # This would check other integration health statuses
        # For now, assume all dependencies are healthy
        return True
    
    def add_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Add alert callback."""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Remove alert callback."""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def get_current_status(self) -> Optional[HealthCheckResult]:
        """Get current health status."""
        return self._last_check
    
    def get_status_history(self, limit: int = 100) -> List[HealthCheckResult]:
        """Get health check history."""
        return self._check_history[-limit:]
    
    def get_statistics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get health check statistics."""
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_checks = [check for check in self._check_history if check.timestamp >= cutoff_time]
        
        if not recent_checks:
            return {}
        
        total_checks = len(recent_checks)
        successful_checks = sum(1 for check in recent_checks if check.status == HealthCheckStatus.SUCCESS)
        failed_checks = sum(1 for check in recent_checks if check.status == HealthCheckStatus.FAILURE)
        timeout_checks = sum(1 for check in recent_checks if check.status == HealthCheckStatus.TIMEOUT)
        
        avg_response_time = sum(check.response_time_ms for check in recent_checks) / total_checks
        
        return {
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "failed_checks": failed_checks,
            "timeout_checks": timeout_checks,
            "success_rate": (successful_checks / total_checks) * 100,
            "avg_response_time_ms": avg_response_time,
            "time_window_hours": time_window_hours
        }


class IntegrationHealthMonitor:
    """Central health monitoring for all integrations."""
    
    def __init__(self):
        self.logger = logger.getChild("health_monitor")
        self.executors: Dict[str, HealthCheckExecutor] = {}
        self.global_config = HealthCheckConfig()
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Global alert callbacks
        self._global_alert_callbacks: List[Callable[[HealthAlert], None]] = []
        
        # Health status cache
        self._status_cache: Dict[str, HealthCheckResult] = {}
        self._status_cache_lock = threading.Lock()
    
    def register_integration(self, integration: BaseIntegrationImpl, config: Optional[HealthCheckConfig] = None) -> None:
        """Register integration for health monitoring."""
        config = config or self.global_config
        
        executor = HealthCheckExecutor(integration, config)
        
        # Add global alert callback
        executor.add_alert_callback(self._handle_global_alert)
        
        self.executors[integration.integration_type.value] = executor
        
        self.logger.info(f"Registered integration for health monitoring: {integration.integration_type.value}")
    
    def unregister_integration(self, integration_type: str) -> None:
        """Unregister integration from health monitoring."""
        if integration_type in self.executors:
            executor = self.executors.pop(integration_type)
            if self._is_running:
                asyncio.create_task(executor.stop())
            
            self.logger.info(f"Unregistered integration from health monitoring: {integration_type}")
    
    async def start_monitoring(self) -> None:
        """Start health monitoring for all registered integrations."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start all executors
        start_tasks = []
        for executor in self.executors.values():
            start_tasks.append(executor.start())
        
        if start_tasks:
            await asyncio.gather(*start_tasks)
        
        # Start global monitoring task
        self._monitor_task = asyncio.create_task(self._run_global_monitoring())
        
        self.logger.info("Started integration health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring for all integrations."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Stop global monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all executors
        stop_tasks = []
        for executor in self.executors.values():
            stop_tasks.append(executor.stop())
        
        if stop_tasks:
            await asyncio.gather(*stop_tasks)
        
        self.logger.info("Stopped integration health monitoring")
    
    async def _run_global_monitoring(self) -> None:
        """Run global health monitoring tasks."""
        while self._is_running:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Update status cache
                await self._update_status_cache()
                
                # Check for overall system health
                await self._check_system_health()
                
                # Log health summary
                await self._log_health_summary()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in global monitoring: {e}")
    
    async def _update_status_cache(self) -> None:
        """Update health status cache."""
        with self._status_cache_lock:
            for name, executor in self.executors.items():
                status = executor.get_current_status()
                if status:
                    self._status_cache[name] = status
    
    async def _check_system_health(self) -> None:
        """Check overall system health."""
        unhealthy_integrations = []
        
        for name, status in self._status_cache.items():
            if status.health_status == IntegrationStatus.UNHEALTHY:
                unhealthy_integrations.append(name)
        
        if len(unhealthy_integrations) > len(self.executors) * 0.5:  # More than 50% unhealthy
            alert = HealthAlert(
                integration_name="System",
                integration_type="System",
                alert_level=AlertLevel.CRITICAL,
                title="System Health Degraded",
                message=f"More than 50% of integrations are unhealthy: {', '.join(unhealthy_integrations)}",
                previous_status=IntegrationStatus.HEALTHY,
                current_status=IntegrationStatus.UNHEALTHY,
                timestamp=datetime.utcnow()
            )
            
            await self._handle_global_alert(alert)
    
    async def _log_health_summary(self) -> None:
        """Log health summary."""
        healthy_count = 0
        degraded_count = 0
        unhealthy_count = 0
        
        for status in self._status_cache.values():
            if status.health_status == IntegrationStatus.HEALTHY:
                healthy_count += 1
            elif status.health_status == IntegrationStatus.DEGRADED:
                degraded_count += 1
            else:
                unhealthy_count += 1
        
        self.logger.info(
            f"Health summary - Total: {len(self._status_cache)}, "
            f"Healthy: {healthy_count}, Degraded: {degraded_count}, Unhealthy: {unhealthy_count}"
        )
    
    async def _handle_global_alert(self, alert: HealthAlert) -> None:
        """Handle global health alerts."""
        self.logger.warning(f"Global health alert: {alert.title} - {alert.message}")
        
        # Execute global alert callbacks
        for callback in self._global_alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                self.logger.error(f"Error executing global alert callback: {e}")
    
    def add_global_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Add global alert callback."""
        self._global_alert_callbacks.append(callback)
    
    def remove_global_alert_callback(self, callback: Callable[[HealthAlert], None]) -> None:
        """Remove global alert callback."""
        if callback in self._global_alert_callbacks:
            self._global_alert_callbacks.remove(callback)
    
    async def get_health_status(self, integration_type: Optional[str] = None) -> Dict[str, Any]:
        """Get health status for all or specific integration."""
        if integration_type:
            executor = self.executors.get(integration_type)
            if not executor:
                return {}
            
            current_status = executor.get_current_status()
            statistics = executor.get_statistics()
            
            return {
                "integration_name": integration_type,
                "current_status": current_status.to_dict() if current_status else None,
                "statistics": statistics
            }
        
        # Get all integrations health status
        all_status = {}
        for name, executor in self.executors.items():
            current_status = executor.get_current_status()
            statistics = executor.get_statistics()
            
            all_status[name] = {
                "current_status": current_status.to_dict() if current_status else None,
                "statistics": statistics
            }
        
        return {
            "system_health": {
                "total_integrations": len(self.executors),
                "monitored_integrations": len(all_status),
                "monitoring_active": self._is_running
            },
            "integrations": all_status
        }
    
    async def force_health_check(self, integration_type: str) -> HealthCheckResult:
        """Force immediate health check for specific integration."""
        executor = self.executors.get(integration_type)
        if not executor:
            raise ValueError(f"Integration not found: {integration_type}")
        
        return await executor.execute_check(force=True)


# Global health monitor instance
_global_health_monitor: Optional[IntegrationHealthMonitor] = None


def get_health_monitor() -> IntegrationHealthMonitor:
    """Get global health monitor instance."""
    global _global_health_monitor
    if _global_health_monitor is None:
        _global_health_monitor = IntegrationHealthMonitor()
    
    return _global_health_monitor


async def start_health_monitoring() -> None:
    """Start global health monitoring."""
    monitor = get_health_monitor()
    await monitor.start_monitoring()


async def stop_health_monitoring() -> None:
    """Stop global health monitoring."""
    monitor = get_health_monitor()
    await monitor.stop_monitoring()


# Export health monitoring classes
__all__ = [
    "HealthCheckStatus",
    "AlertLevel",
    "HealthCheckResult",
    "HealthAlert",
    "HealthCheckConfig",
    "HealthCheckExecutor",
    "IntegrationHealthMonitor",
    "get_health_monitor",
    "start_health_monitoring",
    "stop_health_monitoring"
]