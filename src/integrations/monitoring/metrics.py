"""
Integration metrics collection and monitoring for observability.

Provides comprehensive metrics collection including:
- Request/response latency and throughput
- Error rates and types
- Rate limiting and throttling metrics
- Authentication and authorization metrics
- Connection pool and resource utilization
- Business metrics (sync success rates, data quality)
- Custom metrics for specific integrations
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Deque
from dataclasses import dataclass, field
from enum import Enum
import threading

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.exceptions import ExternalServiceError

logger = get_logger(__name__)


class MetricType(str, Enum):
    """Supported metric types."""
    
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(str, Enum):
    """Metric units."""
    
    # Time units
    NANOSECONDS = "nanoseconds"
    MICROSECONDS = "microseconds"
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    
    # Data units
    BYTES = "bytes"
    KILOBYTES = "kilobytes"
    MEGABYTES = "megabytes"
    GIGABYTES = "gigabytes"
    
    # Count units
    COUNT = "count"
    PERCENT = "percent"
    RATE = "rate"


@dataclass
class MetricSample:
    """Single metric sample."""
    
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricMetadata:
    """Metric metadata and configuration."""
    
    name: str
    metric_type: MetricType
    description: str
    unit: MetricUnit
    labels: List[str]
    buckets: Optional[List[float]] = None  # For histograms
    quantiles: Optional[List[float]] = None  # For summaries
    retention_seconds: int = 3600  # 1 hour default
    max_samples: int = 10000


class MetricCollector:
    """Base class for metric collectors."""
    
    def __init__(self, metadata: MetricMetadata):
        self.metadata = metadata
        self.samples: Dict[str, Deque[MetricSample]] = defaultdict(lambda: deque(maxlen=metadata.max_samples))
        self._lock = threading.Lock()
        
    def record(self, value: float, labels: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric sample."""
        labels = labels or {}
        metadata = metadata or {}
        
        # Validate labels
        if not all(label in self.metadata.labels for label in labels.keys()):
            raise ValueError(f"Invalid labels for metric {self.metadata.name}")
        
        # Create sample key from labels
        label_key = self._create_label_key(labels)
        
        sample = MetricSample(
            value=value,
            timestamp=datetime.utcnow(),
            labels=labels,
            metadata=metadata
        )
        
        with self._lock:
            self.samples[label_key].append(sample)
            
            # Clean up old samples
            self._cleanup_old_samples(label_key)
    
    def get_value(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Get current metric value."""
        labels = labels or {}
        label_key = self._create_label_key(labels)
        
        with self._lock:
            samples = self.samples.get(label_key, deque())
            if not samples:
                return 0.0
            
            if self.metadata.metric_type == MetricType.COUNTER:
                return sum(sample.value for sample in samples)
            elif self.metadata.metric_type == MetricType.GAUGE:
                return samples[-1].value if samples else 0.0
            else:
                return samples[-1].value if samples else 0.0
    
    def get_samples(self, labels: Optional[Dict[str, str]] = None, since: Optional[datetime] = None) -> List[MetricSample]:
        """Get metric samples."""
        labels = labels or {}
        label_key = self._create_label_key(labels)
        since = since or (datetime.utcnow() - timedelta(seconds=self.metadata.retention_seconds))
        
        with self._lock:
            all_samples = self.samples.get(label_key, deque())
            return [sample for sample in all_samples if sample.timestamp >= since]
    
    def get_statistics(self, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get metric statistics."""
        samples = self.get_samples(labels)
        if not samples:
            return {}
        
        values = [sample.value for sample in samples]
        
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": self._percentile(values, 0.5),
            "p90": self._percentile(values, 0.9),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99)
        }
    
    def clear(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Clear metric samples."""
        labels = labels or {}
        label_key = self._create_label_key(labels)
        
        with self._lock:
            if label_key in self.samples:
                self.samples[label_key].clear()
    
    def _create_label_key(self, labels: Dict[str, str]) -> str:
        """Create label key from labels dictionary."""
        # Sort labels to ensure consistent key generation
        sorted_labels = sorted(labels.items())
        return ",".join(f"{k}={v}" for k, v in sorted_labels)
    
    def _cleanup_old_samples(self, label_key: str) -> None:
        """Clean up samples older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.metadata.retention_seconds)
        
        if label_key in self.samples:
            # Remove old samples
            while (self.samples[label_key] and 
                   self.samples[label_key][0].timestamp < cutoff_time):
                self.samples[label_key].popleft()
    
    def _percentile(self, values: List[float], p: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * p)
        return sorted_values[min(index, len(sorted_values) - 1)]


class CounterMetric(MetricCollector):
    """Counter metric that only increases."""
    
    def __init__(self, name: str, description: str, unit: MetricUnit = MetricUnit.COUNT, labels: Optional[List[str]] = None):
        metadata = MetricMetadata(
            name=name,
            metric_type=MetricType.COUNTER,
            description=description,
            unit=unit,
            labels=labels or []
        )
        super().__init__(metadata)
    
    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Increment counter by amount."""
        self.record(amount, labels, metadata)


class GaugeMetric(MetricCollector):
    """Gauge metric that can go up and down."""
    
    def __init__(self, name: str, description: str, unit: MetricUnit = MetricUnit.COUNT, labels: Optional[List[str]] = None):
        metadata = MetricMetadata(
            name=name,
            metric_type=MetricType.GAUGE,
            description=description,
            unit=unit,
            labels=labels or []
        )
        super().__init__(metadata)
    
    def set(self, value: float, labels: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Set gauge value."""
        self.record(value, labels, metadata)


class HistogramMetric(MetricCollector):
    """Histogram metric for measuring distributions."""
    
    def __init__(
        self,
        name: str,
        description: str,
        buckets: Optional[List[float]] = None,
        unit: MetricUnit = MetricUnit.MILLISECONDS,
        labels: Optional[List[str]] = None
    ):
        # Default buckets for latency measurements
        if buckets is None:
            buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]
        
        metadata = MetricMetadata(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            description=description,
            unit=unit,
            labels=labels or [],
            buckets=buckets
        )
        super().__init__(metadata)
        
        # Track bucket counts
        self._bucket_counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
    
    def observe(self, value: float, labels: Optional[Dict[str, str]] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Observe a value in the histogram."""
        self.record(value, labels, metadata)
        
        # Update bucket counts
        label_key = self._create_label_key(labels or {})
        for bucket in self.metadata.buckets:
            if value <= bucket:
                self._bucket_counts[label_key][bucket] += 1
    
    def get_bucket_counts(self, labels: Optional[Dict[str, str]] = None) -> Dict[float, int]:
        """Get bucket counts for histogram."""
        label_key = self._create_label_key(labels or {})
        return dict(self._bucket_counts.get(label_key, {}))
    
    def clear(self, labels: Optional[Dict[str, str]] = None) -> None:
        """Clear histogram samples and bucket counts."""
        super().clear(labels)
        
        label_key = self._create_label_key(labels or {})
        if label_key in self._bucket_counts:
            self._bucket_counts[label_key].clear()


class IntegrationMetrics:
    """Comprehensive metrics for integration monitoring."""
    
    def __init__(self, integration_name: str):
        self.integration_name = integration_name
        self.logger = logger.getChild(f"metrics.{integration_name}")
        
        # Request/Response Metrics
        self.request_count = CounterMetric(
            name=f"{integration_name}_requests_total",
            description=f"Total number of requests to {integration_name}",
            labels=["method", "endpoint", "status"]
        )
        
        self.request_duration = HistogramMetric(
            name=f"{integration_name}_request_duration_seconds",
            description=f"Request duration for {integration_name}",
            unit=MetricUnit.SECONDS,
            labels=["method", "endpoint"]
        )
        
        self.response_size = HistogramMetric(
            name=f"{integration_name}_response_size_bytes",
            description=f"Response size for {integration_name}",
            unit=MetricUnit.BYTES,
            buckets=[100, 1000, 10000, 100000, 1000000, 10000000],
            labels=["method", "endpoint"]
        )
        
        # Error Metrics
        self.error_count = CounterMetric(
            name=f"{integration_name}_errors_total",
            description=f"Total number of errors for {integration_name}",
            labels=["error_type", "error_code", "endpoint"]
        )
        
        self.error_rate = GaugeMetric(
            name=f"{integration_name}_error_rate",
            description=f"Error rate for {integration_name}",
            unit=MetricUnit.PERCENT,
            labels=["time_window"]
        )
        
        # Rate Limiting Metrics
        self.rate_limit_remaining = GaugeMetric(
            name=f"{integration_name}_rate_limit_remaining",
            description=f"Remaining rate limit for {integration_name}",
            labels=["limit_type"]
        )
        
        self.rate_limit_reset = GaugeMetric(
            name=f"{integration_name}_rate_limit_reset_timestamp",
            description=f"Rate limit reset timestamp for {integration_name}",
            labels=["limit_type"]
        )
        
        # Authentication Metrics
        self.auth_attempts = CounterMetric(
            name=f"{integration_name}_auth_attempts_total",
            description=f"Total authentication attempts for {integration_name}",
            labels=["auth_method", "status"]
        )
        
        self.auth_duration = HistogramMetric(
            name=f"{integration_name}_auth_duration_seconds",
            description=f"Authentication duration for {integration_name}",
            unit=MetricUnit.SECONDS,
            labels=["auth_method"]
        )
        
        # Connection Metrics
        self.connection_pool_size = GaugeMetric(
            name=f"{integration_name}_connection_pool_size",
            description=f"Connection pool size for {integration_name}",
            labels=["pool_type"]
        )
        
        self.connection_pool_usage = GaugeMetric(
            name=f"{integration_name}_connection_pool_usage",
            description=f"Connection pool usage for {integration_name}",
            unit=MetricUnit.PERCENT,
            labels=["pool_type"]
        )
        
        # Sync Metrics (for data synchronization)
        self.sync_operations = CounterMetric(
            name=f"{integration_name}_sync_operations_total",
            description=f"Total sync operations for {integration_name}",
            labels=["operation_type", "status", "object_type"]
        )
        
        self.sync_duration = HistogramMetric(
            name=f"{integration_name}_sync_duration_seconds",
            description=f"Sync operation duration for {integration_name}",
            unit=MetricUnit.SECONDS,
            labels=["operation_type", "object_type"]
        )
        
        self.sync_lag = GaugeMetric(
            name=f"{integration_name}_sync_lag_seconds",
            description=f"Data synchronization lag for {integration_name}",
            unit=MetricUnit.SECONDS,
            labels=["object_type"]
        )
        
        # Business Metrics
        self.data_quality_score = GaugeMetric(
            name=f"{integration_name}_data_quality_score",
            description=f"Data quality score for {integration_name}",
            unit=MetricUnit.PERCENT,
            labels=["data_type"]
        )
        
        self.success_rate = GaugeMetric(
            name=f"{integration_name}_success_rate",
            description=f"Success rate for {integration_name}",
            unit=MetricUnit.PERCENT,
            labels=["operation_type", "time_window"]
        )
        
        # Custom metrics storage
        self._custom_metrics: Dict[str, MetricCollector] = {}
        
        # Metrics collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._collection_interval = 60  # Collect metrics every 60 seconds
        self._running = False
    
    def record_request(
        self,
        method: str,
        endpoint: str,
        status: str,
        duration: float,
        response_size: Optional[int] = None
    ) -> None:
        """Record request metrics."""
        labels = {"method": method, "endpoint": endpoint, "status": status}
        
        self.request_count.increment(labels=labels)
        self.request_duration.observe(duration, labels={"method": method, "endpoint": endpoint})
        
        if response_size is not None:
            self.response_size.observe(response_size, labels={"method": method, "endpoint": endpoint})
    
    def record_error(self, error_type: str, error_code: str, endpoint: Optional[str] = None) -> None:
        """Record error metrics."""
        labels = {"error_type": error_type, "error_code": error_code}
        if endpoint:
            labels["endpoint"] = endpoint
        
        self.error_count.increment(labels=labels)
    
    def record_rate_limit(self, limit_type: str, remaining: int, reset_timestamp: Optional[float] = None) -> None:
        """Record rate limiting metrics."""
        labels = {"limit_type": limit_type}
        
        self.rate_limit_remaining.set(remaining, labels=labels)
        
        if reset_timestamp:
            self.rate_limit_reset.set(reset_timestamp, labels=labels)
    
    def record_auth_attempt(self, auth_method: str, status: str, duration: Optional[float] = None) -> None:
        """Record authentication metrics."""
        labels = {"auth_method": auth_method, "status": status}
        
        self.auth_attempts.increment(labels=labels)
        
        if duration is not None:
            self.auth_duration.observe(duration, labels={"auth_method": auth_method})
    
    def record_sync_operation(
        self,
        operation_type: str,
        status: str,
        object_type: str,
        duration: Optional[float] = None,
        lag_seconds: Optional[float] = None
    ) -> None:
        """Record synchronization metrics."""
        labels = {"operation_type": operation_type, "status": status, "object_type": object_type}
        
        self.sync_operations.increment(labels=labels)
        
        if duration is not None:
            self.sync_duration.observe(duration, labels={"operation_type": operation_type, "object_type": object_type})
        
        if lag_seconds is not None:
            self.sync_lag.set(lag_seconds, labels={"object_type": object_type})
    
    def record_connection_pool_metrics(self, pool_type: str, size: int, usage_percent: float) -> None:
        """Record connection pool metrics."""
        labels = {"pool_type": pool_type}
        
        self.connection_pool_size.set(size, labels=labels)
        self.connection_pool_usage.set(usage_percent, labels=labels)
    
    def record_business_metrics(
        self,
        data_quality_score: Optional[float] = None,
        success_rate: Optional[float] = None,
        operation_type: str = "general",
        time_window: str = "1h"
    ) -> None:
        """Record business metrics."""
        if data_quality_score is not None:
            self.data_quality_score.set(data_quality_score, labels={"data_type": operation_type})
        
        if success_rate is not None:
            self.success_rate.set(success_rate, labels={"operation_type": operation_type, "time_window": time_window})
    
    def create_custom_counter(self, name: str, description: str, labels: Optional[List[str]] = None) -> CounterMetric:
        """Create custom counter metric."""
        full_name = f"{self.integration_name}_{name}"
        counter = CounterMetric(full_name, description, labels=labels)
        self._custom_metrics[full_name] = counter
        return counter
    
    def create_custom_gauge(self, name: str, description: str, unit: MetricUnit = MetricUnit.COUNT, labels: Optional[List[str]] = None) -> GaugeMetric:
        """Create custom gauge metric."""
        full_name = f"{self.integration_name}_{name}"
        gauge = GaugeMetric(full_name, description, unit=unit, labels=labels)
        self._custom_metrics[full_name] = gauge
        return gauge
    
    def create_custom_histogram(self, name: str, description: str, buckets: Optional[List[float]] = None, unit: MetricUnit = MetricUnit.MILLISECONDS, labels: Optional[List[str]] = None) -> HistogramMetric:
        """Create custom histogram metric."""
        full_name = f"{self.integration_name}_{name}"
        histogram = HistogramMetric(full_name, description, buckets=buckets, unit=unit, labels=labels)
        self._custom_metrics[full_name] = histogram
        return histogram
    
    async def start_collection(self) -> None:
        """Start automatic metrics collection."""
        if self._running:
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics())
        self.logger.info(f"Started metrics collection for {self.integration_name}")
    
    async def stop_collection(self) -> None:
        """Stop automatic metrics collection."""
        if not self._running:
            return
        
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"Stopped metrics collection for {self.integration_name}")
    
    async def _collect_metrics(self) -> None:
        """Periodically collect and process metrics."""
        while self._running:
            try:
                await asyncio.sleep(self._collection_interval)
                
                # Calculate and update derived metrics
                await self._update_derived_metrics()
                
                # Log periodic metrics summary
                await self._log_metrics_summary()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
    
    async def _update_derived_metrics(self) -> None:
        """Update derived metrics like error rates and success rates."""
        # Calculate error rate for last hour
        error_samples = self.error_count.get_samples(since=datetime.utcnow() - timedelta(hours=1))
        total_errors = sum(sample.value for sample in error_samples)
        
        request_samples = self.request_count.get_samples(since=datetime.utcnow() - timedelta(hours=1))
        total_requests = sum(sample.value for sample in request_samples)
        
        if total_requests > 0:
            error_rate = (total_errors / total_requests) * 100
            self.error_rate.set(error_rate, labels={"time_window": "1h"})
    
    async def _log_metrics_summary(self) -> None:
        """Log periodic metrics summary."""
        stats = {
            "total_requests": self.request_count.get_value(),
            "total_errors": self.error_count.get_value(),
            "error_rate": self.error_rate.get_value(labels={"time_window": "1h"}),
            "active_custom_metrics": len(self._custom_metrics)
        }
        
        self.logger.info(f"Metrics summary for {self.integration_name}: {stats}")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics data."""
        return {
            "integration_name": self.integration_name,
            "timestamp": datetime.utcnow().isoformat(),
            "request_metrics": {
                "total_requests": self.request_count.get_value(),
                "request_duration_stats": self.request_duration.get_statistics(),
                "response_size_stats": self.response_size.get_statistics()
            },
            "error_metrics": {
                "total_errors": self.error_count.get_value(),
                "error_rate": self.error_rate.get_value(labels={"time_window": "1h"})
            },
            "auth_metrics": {
                "total_attempts": self.auth_attempts.get_value(),
                "auth_duration_stats": self.auth_duration.get_statistics()
            },
            "sync_metrics": {
                "total_operations": self.sync_operations.get_value(),
                "sync_duration_stats": self.sync_duration.get_statistics()
            },
            "custom_metrics": {
                name: {
                    "type": metric.metadata.metric_type.value,
                    "value": metric.get_value()
                }
                for name, metric in self._custom_metrics.items()
            }
        }
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Add metric descriptions and values
        all_metrics = [
            self.request_count,
            self.request_duration,
            self.response_size,
            self.error_count,
            self.error_rate,
            self.rate_limit_remaining,
            self.auth_attempts,
            self.auth_duration,
            self.sync_operations,
            self.sync_duration,
            self.sync_lag,
            self.data_quality_score,
            self.success_rate
        ] + list(self._custom_metrics.values())
        
        for metric in all_metrics:
            # Add HELP line
            lines.append(f"# HELP {metric.metadata.name} {metric.metadata.description}")
            
            # Add TYPE line
            lines.append(f"# TYPE {metric.metadata.name} {metric.metadata.metric_type.value}")
            
            # Add metric values
            if metric.metadata.metric_type == MetricType.HISTOGRAM:
                # Special handling for histograms
                stats = metric.get_statistics()
                if stats:
                    lines.append(f"{metric.metadata.name}_count {stats['count']}")
                    lines.append(f"{metric.metadata.name}_sum {stats['sum']}")
            else:
                # Simple metric value
                value = metric.get_value()
                lines.append(f"{metric.metadata.name} {value}")
            
            lines.append("")  # Empty line between metrics
        
        return "\n".join(lines)


# Global metrics registry
_integration_metrics: Dict[str, IntegrationMetrics] = {}


def get_integration_metrics(integration_name: str) -> IntegrationMetrics:
    """Get or create integration metrics collector."""
    if integration_name not in _integration_metrics:
        _integration_metrics[integration_name] = IntegrationMetrics(integration_name)
    
    return _integration_metrics[integration_name]


def get_all_metrics() -> Dict[str, Any]:
    """Get metrics for all integrations."""
    return {
        name: metrics.get_all_metrics()
        for name, metrics in _integration_metrics.items()
    }


def export_all_prometheus_metrics() -> str:
    """Export all metrics in Prometheus format."""
    all_lines = []
    
    for name, metrics in _integration_metrics.items():
        all_lines.append(f"# Integration: {name}")
        all_lines.append(metrics.export_prometheus_format())
        all_lines.append("")
    
    return "\n".join(all_lines)


async def start_all_metrics_collection() -> None:
    """Start metrics collection for all integrations."""
    tasks = []
    for metrics in _integration_metrics.values():
        tasks.append(metrics.start_collection())
    
    if tasks:
        await asyncio.gather(*tasks)


async def stop_all_metrics_collection() -> None:
    """Stop metrics collection for all integrations."""
    tasks = []
    for metrics in _integration_metrics.values():
        tasks.append(metrics.stop_collection())
    
    if tasks:
        await asyncio.gather(*tasks)


# Export metrics classes
__all__ = [
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
    "stop_all_metrics_collection"
]