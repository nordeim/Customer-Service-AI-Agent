"""
Integration monitoring and observability module.

Provides comprehensive monitoring capabilities for all integrations including:
- Real-time metrics collection and aggregation
- Health monitoring with configurable checks
- Performance monitoring and alerting
- Error tracking and analysis
- Resource utilization monitoring
- Business metrics and KPIs
- Integration with external monitoring systems (Prometheus, Datadog)
"""

from __future__ import annotations

# Import metrics monitoring
from .metrics import (
    MetricType,
    MetricUnit,
    MetricSample,
    MetricMetadata,
    MetricCollector,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    IntegrationMetrics,
    get_integration_metrics,
    get_all_metrics,
    export_all_prometheus_metrics,
    start_all_metrics_collection,
    stop_all_metrics_collection
)

# Import health monitoring
from .health import (
    HealthCheckStatus,
    AlertLevel,
    HealthCheckResult,
    HealthAlert,
    HealthCheckConfig,
    HealthCheckExecutor,
    IntegrationHealthMonitor,
    get_health_monitor,
    start_health_monitoring,
    stop_health_monitoring
)

# Monitoring configuration
DEFAULT_MONITORING_CONFIG = {
    "metrics": {
        "enabled": True,
        "collection_interval_seconds": 60,
        "retention_hours": 24,
        "export_prometheus": True,
        "export_datadog": False
    },
    "health_checks": {
        "enabled": True,
        "default_interval_seconds": 60,
        "default_timeout_seconds": 30,
        "failure_threshold": 3,
        "success_threshold": 2,
        "auto_recovery_enabled": True
    },
    "alerts": {
        "enabled": True,
        "channels": ["email", "slack", "webhook"],
        "escalation_enabled": True,
        "escalation_delay_minutes": 15
    }
}


class IntegrationMonitoring:
    """Central integration monitoring coordinator."""
    
    def __init__(self):
        self.logger = logger.getChild("integration_monitoring")
        self.config = DEFAULT_MONITORING_CONFIG
        self._is_running = False
    
    async def start(self) -> None:
        """Start all monitoring services."""
        if self._is_running:
            return
        
        self._is_running = True
        
        # Start metrics collection
        if self.config["metrics"]["enabled"]:
            await start_all_metrics_collection()
            self.logger.info("Started metrics collection")
        
        # Start health monitoring
        if self.config["health_checks"]["enabled"]:
            await start_health_monitoring()
            self.logger.info("Started health monitoring")
        
        self.logger.info("Integration monitoring started")
    
    async def stop(self) -> None:
        """Stop all monitoring services."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Stop metrics collection
        if self.config["metrics"]["enabled"]:
            await stop_all_metrics_collection()
            self.logger.info("Stopped metrics collection")
        
        # Stop health monitoring
        if self.config["health_checks"]["enabled"]:
            await stop_health_monitoring()
            self.logger.info("Stopped health monitoring")
        
        self.logger.info("Integration monitoring stopped")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get monitoring system status."""
        return {
            "running": self._is_running,
            "config": self.config,
            "metrics_enabled": self.config["metrics"]["enabled"],
            "health_checks_enabled": self.config["health_checks"]["enabled"],
            "alerts_enabled": self.config["alerts"]["enabled"]
        }


# Global monitoring instance
_integration_monitoring: Optional[IntegrationMonitoring] = None


def get_integration_monitoring() -> IntegrationMonitoring:
    """Get global integration monitoring instance."""
    global _integration_monitoring
    if _integration_monitoring is None:
        _integration_monitoring = IntegrationMonitoring()
    
    return _integration_monitoring


async def start_integration_monitoring() -> None:
    """Start global integration monitoring."""
    monitoring = get_integration_monitoring()
    await monitoring.start()


async def stop_integration_monitoring() -> None:
    """Stop global integration monitoring."""
    monitoring = get_integration_monitoring()
    await monitoring.stop()


# Export monitoring functionality
__all__ = [
    # Metrics monitoring
    "MetricType",
    "MetricUnit",
    "MetricSample",
    "MetricMetadata",
    "MetricCollector",
    "CounterMetric",
    "GaugeMetric",
    "HistogramMetric",
    "IntegrationMetrics",
    "get_integration_metrics",
    "get_all_metrics",
    "export_all_prometheus_metrics",
    "start_all_metrics_collection",
    "stop_all_metrics_collection",
    
    # Health monitoring
    "HealthCheckStatus",
    "AlertLevel",
    "HealthCheckResult",
    "HealthAlert",
    "HealthCheckConfig",
    "HealthCheckExecutor",
    "IntegrationHealthMonitor",
    "get_health_monitor",
    "start_health_monitoring",
    "stop_health_monitoring",
    
    # Central monitoring
    "IntegrationMonitoring",
    "DEFAULT_MONITORING_CONFIG",
    "get_integration_monitoring",
    "start_integration_monitoring",
    "stop_integration_monitoring"
]