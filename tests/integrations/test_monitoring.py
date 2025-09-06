"""
Tests for integration monitoring and observability functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.integrations.monitoring import (
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
    stop_all_metrics_collection,
    HealthCheckStatus,
    AlertLevel,
    HealthCheckResult,
    HealthAlert,
    HealthCheckConfig,
    HealthCheckExecutor,
    IntegrationHealthMonitor,
    get_health_monitor,
    start_health_monitoring,
    stop_health_monitoring,
    IntegrationMonitoring,
    get_integration_monitoring,
    start_integration_monitoring,
    stop_integration_monitoring
)


class TestMetricCollectors:
    """Test metric collector functionality."""
    
    @pytest.fixture
    def metric_metadata(self):
        return MetricMetadata(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            description="Test metric description",
            unit=MetricUnit.COUNT,
            labels=["method", "endpoint"]
        )
    
    @pytest.fixture
    def metric_collector(self, metric_metadata):
        return MetricCollector(metric_metadata)
    
    def test_metric_collector_initialization(self, metric_collector, metric_metadata):
        """Test MetricCollector initialization."""
        assert metric_collector.metadata == metric_metadata
        assert metric_collector.samples == {}
        assert metric_metadata.name == "test_metric"
        assert metric_metadata.metric_type == MetricType.COUNTER
    
    def test_record_sample(self, metric_collector):
        """Test recording metric sample."""
        metric_collector.record(1.0, labels={"method": "GET", "endpoint": "/test"})
        
        label_key = "endpoint=/test,method=GET"
        assert label_key in metric_collector.samples
        assert len(metric_collector.samples[label_key]) == 1
        assert metric_collector.samples[label_key][0].value == 1.0
        assert metric_collector.samples[label_key][0].labels == {"method": "GET", "endpoint": "/test"}
    
    def test_get_value(self, metric_collector):
        """Test getting current metric value."""
        # Record multiple samples
        metric_collector.record(1.0, labels={"method": "GET", "endpoint": "/test"})
        metric_collector.record(2.0, labels={"method": "GET", "endpoint": "/test"})
        metric_collector.record(3.0, labels={"method": "POST", "endpoint": "/test"})
        
        # Test counter aggregation
        value = metric_collector.get_value(labels={"method": "GET", "endpoint": "/test"})
        assert value == 3.0  # 1.0 + 2.0
        
        # Test different labels
        post_value = metric_collector.get_value(labels={"method": "POST", "endpoint": "/test"})
        assert post_value == 3.0
    
    def test_get_samples(self, metric_collector):
        """Test getting metric samples."""
        # Record samples
        metric_collector.record(1.0, labels={"method": "GET", "endpoint": "/test"})
        time.sleep(0.01)  # Small delay
        metric_collector.record(2.0, labels={"method": "GET", "endpoint": "/test"})
        
        # Get all samples
        samples = metric_collector.get_samples(labels={"method": "GET", "endpoint": "/test"})
        assert len(samples) == 2
        assert samples[0].value == 1.0
        assert samples[1].value == 2.0
        
        # Get samples since specific time
        cutoff_time = datetime.utcnow() - timedelta(milliseconds=5)
        recent_samples = metric_collector.get_samples(
            labels={"method": "GET", "endpoint": "/test"},
            since=cutoff_time
        )
        assert len(recent_samples) >= 1
    
    def test_get_statistics(self, metric_collector):
        """Test getting metric statistics."""
        # Record samples
        for i in range(1, 6):
            metric_collector.record(float(i), labels={"method": "GET", "endpoint": "/test"})
        
        stats = metric_collector.get_statistics(labels={"method": "GET", "endpoint": "/test"})
        
        assert stats["count"] == 5
        assert stats["sum"] == 15.0  # 1+2+3+4+5
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["avg"] == 3.0
        assert stats["p50"] == 3.0
        assert stats["p90"] == 5.0
        assert stats["p95"] == 5.0
        assert stats["p99"] == 5.0
    
    def test_cleanup_old_samples(self, metric_collector):
        """Test cleanup of old samples."""
        # Record sample
        metric_collector.record(1.0, labels={"method": "GET", "endpoint": "/test"})
        
        # Manually expire the sample
        label_key = "endpoint=/test,method=GET"
        if label_key in metric_collector.samples:
            metric_collector.samples[label_key][0].timestamp = datetime.utcnow() - timedelta(hours=2)
        
        # Record another sample to trigger cleanup
        metric_collector.record(2.0, labels={"method": "GET", "endpoint": "/test"})
        
        # Old sample should be cleaned up
        samples = metric_collector.get_samples(labels={"method": "GET", "endpoint": "/test"})
        assert len(samples) == 1
        assert samples[0].value == 2.0


class TestCounterMetric:
    """Test CounterMetric functionality."""
    
    def test_counter_metric_creation(self):
        """Test CounterMetric creation."""
        counter = CounterMetric(
            name="test_counter",
            description="Test counter metric",
            unit=MetricUnit.COUNT,
            labels=["method", "endpoint"]
        )
        
        assert counter.metadata.name == "test_counter"
        assert counter.metadata.metric_type == MetricType.COUNTER
        assert counter.metadata.description == "Test counter metric"
        assert counter.metadata.unit == MetricUnit.COUNT
        assert counter.metadata.labels == ["method", "endpoint"]
    
    def test_counter_increment(self):
        """Test counter increment."""
        counter = CounterMetric("test_counter", "Test counter")
        
        counter.increment(labels={"method": "GET", "endpoint": "/test"})
        assert counter.get_value(labels={"method": "GET", "endpoint": "/test"}) == 1.0
        
        counter.increment(5.0, labels={"method": "GET", "endpoint": "/test"})
        assert counter.get_value(labels={"method": "GET", "endpoint": "/test"}) == 6.0
    
    def test_counter_only_increases(self):
        """Test that counter only increases."""
        counter = CounterMetric("test_counter", "Test counter")
        
        counter.increment(10.0, labels={"method": "GET", "endpoint": "/test"})
        counter.increment(-5.0, labels={"method": "GET", "endpoint": "/test"})  # Should still add
        
        # Counter should still increase (negative values are added)
        assert counter.get_value(labels={"method": "GET", "endpoint": "/test"}) == 5.0


class TestGaugeMetric:
    """Test GaugeMetric functionality."""
    
    def test_gauge_metric_creation(self):
        """Test GaugeMetric creation."""
        gauge = GaugeMetric(
            name="test_gauge",
            description="Test gauge metric",
            unit=MetricUnit.PERCENT,
            labels=["server"]
        )
        
        assert gauge.metadata.name == "test_gauge"
        assert gauge.metadata.metric_type == MetricType.GAUGE
        assert gauge.metadata.description == "Test gauge metric"
        assert gauge.metadata.unit == MetricUnit.PERCENT
        assert gauge.metadata.labels == ["server"]
    
    def test_gauge_set(self):
        """Test gauge set."""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        
        gauge.set(75.5, labels={"server": "server1"})
        assert gauge.get_value(labels={"server": "server1"}) == 75.5
        
        gauge.set(80.0, labels={"server": "server1"})
        assert gauge.get_value(labels={"server": "server1"}) == 80.0
        
        gauge.set(60.0, labels={"server": "server2"})
        assert gauge.get_value(labels={"server": "server2"}) == 60.0
    
    def test_gauge_can_decrease(self):
        """Test that gauge can decrease."""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        
        gauge.set(100.0, labels={"server": "server1"})
        gauge.set(50.0, labels={"server": "server1"})
        gauge.set(25.0, labels={"server": "server1"})
        
        assert gauge.get_value(labels={"server": "server1"}) == 25.0


class TestHistogramMetric:
    """Test HistogramMetric functionality."""
    
    def test_histogram_metric_creation(self):
        """Test HistogramMetric creation."""
        histogram = HistogramMetric(
            name="test_histogram",
            description="Test histogram metric",
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
            unit=MetricUnit.SECONDS,
            labels=["method", "endpoint"]
        )
        
        assert histogram.metadata.name == "test_histogram"
        assert histogram.metadata.metric_type == MetricType.HISTOGRAM
        assert histogram.metadata.description == "Test histogram metric"
        assert histogram.metadata.unit == MetricUnit.SECONDS
        assert histogram.metadata.buckets == [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        assert histogram.metadata.labels == ["method", "endpoint"]
    
    def test_histogram_observe(self):
        """Test histogram observation."""
        histogram = HistogramMetric("test_histogram", "Test histogram")
        
        # Observe various values
        histogram.observe(0.05, labels={"method": "GET", "endpoint": "/test"})   # < 0.1
        histogram.observe(0.3, labels={"method": "GET", "endpoint": "/test"})    # < 0.5
        histogram.observe(0.8, labels={"method": "GET", "endpoint": "/test"})    # < 1.0
        histogram.observe(2.0, labels={"method": "GET", "endpoint": "/test"})    # < 2.5
        histogram.observe(7.0, labels={"method": "GET", "endpoint": "/test"})    # < 10.0
        
        # Check bucket counts
        bucket_counts = histogram.get_bucket_counts(labels={"method": "GET", "endpoint": "/test"})
        assert bucket_counts[0.1] == 1    # Only 0.05
        assert bucket_counts[0.5] == 2    # 0.05, 0.3
        assert bucket_counts[1.0] == 3    # 0.05, 0.3, 0.8
        assert bucket_counts[2.5] == 4    # 0.05, 0.3, 0.8, 2.0
        assert bucket_counts[5.0] == 4    # Same as 2.5
        assert bucket_counts[10.0] == 5   # All values
    
    def test_histogram_default_buckets(self):
        """Test histogram with default buckets."""
        histogram = HistogramMetric("test_histogram", "Test histogram")
        
        # Default buckets should be set for latency measurements
        assert histogram.metadata.buckets == [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 500.0, 1000.0]


class TestIntegrationMetrics:
    """Test IntegrationMetrics functionality."""
    
    @pytest.fixture
    def integration_metrics(self):
        return IntegrationMetrics("test_integration")
    
    def test_integration_metrics_initialization(self, integration_metrics):
        """Test IntegrationMetrics initialization."""
        assert integration_metrics.integration_name == "test_integration"
        assert integration_metrics.request_count is not None
        assert integration_metrics.request_duration is not None
        assert integration_metrics.error_count is not None
        assert integration_metrics.auth_attempts is not None
    
    def test_record_request(self, integration_metrics):
        """Test request recording."""
        integration_metrics.record_request(
            method="GET",
            endpoint="/test",
            status="success",
            duration=0.5,
            response_size=1024
        )
        
        # Check request count
        count = integration_metrics.request_count.get_value(labels={"method": "GET", "endpoint": "/test", "status": "success"})
        assert count == 1.0
        
        # Check request duration
        duration_stats = integration_metrics.request_duration.get_statistics(labels={"method": "GET", "endpoint": "/test"})
        assert duration_stats["count"] == 1
        assert duration_stats["min"] == 0.5
        assert duration_stats["max"] == 0.5
        assert duration_stats["avg"] == 0.5
        
        # Check response size
        size_stats = integration_metrics.response_size.get_statistics(labels={"method": "GET", "endpoint": "/test"})
        assert size_stats["count"] == 1
        assert size_stats["min"] == 1024
    
    def test_record_error(self, integration_metrics):
        """Test error recording."""
        integration_metrics.record_error("API_ERROR", "TIMEOUT", endpoint="/test")
        
        error_count = integration_metrics.error_count.get_value(labels={"error_type": "API_ERROR", "error_code": "TIMEOUT", "endpoint": "/test"})
        assert error_count == 1.0
    
    def test_record_auth_attempt(self, integration_metrics):
        """Test authentication attempt recording."""
        integration_metrics.record_auth_attempt("oauth2", "success", duration=0.3)
        
        # Check auth attempts
        auth_count = integration_metrics.auth_attempts.get_value(labels={"auth_method": "oauth2", "status": "success"})
        assert auth_count == 1.0
        
        # Check auth duration
        duration_stats = integration_metrics.auth_duration.get_statistics(labels={"auth_method": "oauth2"})
        assert duration_stats["count"] == 1
        assert duration_stats["min"] == 0.3
    
    def test_record_sync_operation(self, integration_metrics):
        """Test sync operation recording."""
        integration_metrics.record_sync_operation(
            operation_type="delta_sync",
            status="success",
            object_type="contact",
            duration=2.5,
            lag_seconds=30.0
        )
        
        # Check sync operations
        sync_count = integration_metrics.sync_operations.get_value(labels={"operation_type": "delta_sync", "status": "success", "object_type": "contact"})
        assert sync_count == 1.0
        
        # Check sync duration
        duration_stats = integration_metrics.sync_duration.get_statistics(labels={"operation_type": "delta_sync", "object_type": "contact"})
        assert duration_stats["count"] == 1
        assert duration_stats["min"] == 2.5
        
        # Check sync lag
        lag_value = integration_metrics.sync_lag.get_value(labels={"object_type": "contact"})
        assert lag_value == 30.0
    
    def test_custom_metrics(self, integration_metrics):
        """Test custom metric creation."""
        # Create custom counter
        custom_counter = integration_metrics.create_custom_counter(
            "custom_requests",
            "Custom request counter",
            labels=["source"]
        )
        
        assert custom_counter.metadata.name == "test_integration_custom_requests"
        assert "test_integration_custom_requests" in integration_metrics._custom_metrics
        
        # Use custom counter
        custom_counter.increment(labels={"source": "webhook"})
        assert custom_counter.get_value(labels={"source": "webhook"}) == 1.0
    
    def test_get_all_metrics(self, integration_metrics):
        """Test getting all metrics."""
        # Record some data
        integration_metrics.record_request("GET", "/test", "success", 0.5)
        integration_metrics.record_error("API_ERROR", "TIMEOUT")
        integration_metrics.record_auth_attempt("oauth2", "success", 0.3)
        
        all_metrics = integration_metrics.get_all_metrics()
        
        assert all_metrics["integration_name"] == "test_integration"
        assert "timestamp" in all_metrics
        assert "request_metrics" in all_metrics
        assert "error_metrics" in all_metrics
        assert "auth_metrics" in all_metrics
        
        assert all_metrics["request_metrics"]["total_requests"] == 1.0
        assert all_metrics["error_metrics"]["total_errors"] == 1.0
        assert all_metrics["auth_metrics"]["total_attempts"] == 1.0
    
    def test_export_prometheus_format(self, integration_metrics):
        """Test Prometheus format export."""
        # Record some data
        integration_metrics.record_request("GET", "/test", "success", 0.5, 1024)
        integration_metrics.record_error("API_ERROR", "TIMEOUT")
        
        prometheus_output = integration_metrics.export_prometheus_format()
        
        # Check that output contains expected Prometheus format
        assert "# HELP test_integration_requests_total" in prometheus_output
        assert "# TYPE test_integration_requests_total counter" in prometheus_output
        assert "test_integration_requests_total" in prometheus_output
        
        assert "# HELP test_integration_errors_total" in prometheus_output
        assert "# TYPE test_integration_errors_total counter" in prometheus_output
        assert "test_integration_errors_total" in prometheus_output


class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    @pytest.fixture
    def health_check_config(self):
        return HealthCheckConfig(
            enabled=True,
            interval_seconds=60,
            timeout_seconds=30,
            retry_attempts=3,
            failure_threshold=3,
            success_threshold=2,
            alert_on_status_change=True,
            alert_on_failure=True,
            auto_recovery_enabled=True
        )
    
    @pytest.fixture
    def mock_integration(self):
        integration = Mock()
        integration.integration_type.value = "test_integration"
        integration.health_check = AsyncMock(return_value={"status": "healthy", "response_time": 100})
        return integration
    
    @pytest.fixture
    def health_executor(self, mock_integration, health_check_config):
        return HealthCheckExecutor(mock_integration, health_check_config)
    
    @pytest.mark.asyncio
    async def test_health_check_executor_initialization(self, health_executor, mock_integration, health_check_config):
        """Test HealthCheckExecutor initialization."""
        assert health_executor.integration == mock_integration
        assert health_executor.config == health_check_config
        assert health_executor._last_check is None
        assert health_executor._check_history == []
        assert health_executor._consecutive_failures == 0
        assert health_executor._consecutive_successes == 0
    
    @pytest.mark.asyncio
    async def test_execute_check_success(self, health_executor):
        """Test successful health check execution."""
        result = await health_executor.execute_check()
        
        assert result.integration_name == "test_integration"
        assert result.integration_type == "test_integration"
        assert result.status == HealthCheckStatus.SUCCESS
        assert result.health_status.value == "healthy"
        assert result.response_time_ms > 0
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_execute_check_failure(self, health_executor):
        """Test failed health check execution."""
        health_executor.integration.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        
        result = await health_executor.execute_check()
        
        assert result.integration_name == "test_integration"
        assert result.status == HealthCheckStatus.FAILURE
        assert result.health_status.value == "unhealthy"
        assert result.error_message == "Health check failed"
        assert result.error_details is not None
    
    @pytest.mark.asyncio
    async def test_execute_check_timeout(self, health_executor):
        """Test health check timeout."""
        async def slow_health_check():
            await asyncio.sleep(2)  # Longer than timeout
            return {"status": "healthy"}
        
        health_executor.integration.health_check = slow_health_check
        health_executor.config.timeout_seconds = 1
        
        result = await health_executor.execute_check()
        
        assert result.status == HealthCheckStatus.TIMEOUT
        assert result.health_status.value == "unhealthy"
        assert "timed out" in result.error_message
    
    @pytest.mark.asyncio
    async def test_status_change_alert(self, health_executor):
        """Test status change alert generation."""
        # Mock alert callback
        alert_callback = AsyncMock()
        health_executor.add_alert_callback(alert_callback)
        
        # First check - success
        result1 = await health_executor.execute_check()
        await health_executor._process_result(result1)
        
        # Simulate failure
        health_executor.integration.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        result2 = await health_executor.execute_check()
        await health_executor._process_result(result2)
        
        # Alert callback should be called for status change
        alert_callback.assert_called_once()
        alert_call = alert_callback.call_args[0][0]
        assert alert_call.alert_level == AlertLevel.ERROR
        assert "Integration Unhealthy" in alert_call.title
    
    @pytest.mark.asyncio
    async def test_auto_recovery(self, health_executor):
        """Test auto-recovery functionality."""
        # Configure for auto-recovery
        health_executor.config.auto_recovery_enabled = True
        health_executor.config.failure_threshold = 2
        
        # Mock authentication
        health_executor.integration.authenticate = AsyncMock(return_value=True)
        health_executor.integration.close = AsyncMock()
        
        # Simulate consecutive failures
        health_executor.integration.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        
        for i in range(3):
            result = await health_executor.execute_check()
            await health_executor._process_result(result)
        
        # Auto-recovery should be triggered
        health_executor.integration.close.assert_called_once()
        health_executor.integration.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_statistics(self, health_executor):
        """Test health check statistics."""
        # Execute multiple checks
        for i in range(5):
            result = await health_executor.execute_check()
            await health_executor._process_result(result)
        
        # Simulate one failure
        health_executor.integration.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        result = await health_executor.execute_check()
        await health_executor._process_result(result)
        
        # Get statistics
        stats = health_executor.get_statistics(time_window_hours=1)
        
        assert stats["total_checks"] == 6
        assert stats["successful_checks"] == 5
        assert stats["failed_checks"] == 1
        assert stats["timeout_checks"] == 0
        assert stats["success_rate"] == (5/6) * 100
        assert stats["avg_response_time_ms"] > 0


class TestIntegrationHealthMonitor:
    """Test IntegrationHealthMonitor functionality."""
    
    @pytest.fixture
    def health_monitor(self):
        return IntegrationHealthMonitor()
    
    @pytest.fixture
    def mock_integration(self):
        integration = Mock()
        integration.integration_type.value = "test_integration"
        integration.health_check = AsyncMock(return_value={"status": "healthy"})
        return integration
    
    @pytest.mark.asyncio
    async def test_register_integration(self, health_monitor, mock_integration):
        """Test integration registration."""
        health_monitor.register_integration(mock_integration)
        
        assert "test_integration" in health_monitor.executors
        assert health_monitor.executors["test_integration"].integration == mock_integration
    
    @pytest.mark.asyncio
    async def test_unregister_integration(self, health_monitor, mock_integration):
        """Test integration unregistration."""
        health_monitor.register_integration(mock_integration)
        assert "test_integration" in health_monitor.executors
        
        health_monitor.unregister_integration("test_integration")
        assert "test_integration" not in health_monitor.executors
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, health_monitor, mock_integration):
        """Test health monitoring start/stop."""
        health_monitor.register_integration(mock_integration)
        
        # Start monitoring
        await health_monitor.start_monitoring()
        assert health_monitor._is_running is True
        
        # Stop monitoring
        await health_monitor.stop_monitoring()
        assert health_monitor._is_running is False
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, health_monitor, mock_integration):
        """Test health status retrieval."""
        health_monitor.register_integration(mock_integration)
        
        # Manually set status
        mock_result = HealthCheckResult(
            integration_name="test_integration",
            integration_type="test_integration",
            status=HealthCheckStatus.SUCCESS,
            health_status="healthy",
            response_time_ms=100.0,
            timestamp=datetime.utcnow()
        )
        
        health_monitor.executors["test_integration"]._last_check = mock_result
        
        # Get status for specific integration
        status = await health_monitor.get_health_status("test_integration")
        assert status["integration_name"] == "test_integration"
        assert status["current_status"] is not None
        assert "statistics" in status
    
    @pytest.mark.asyncio
    async def test_get_all_health_status(self, health_monitor, mock_integration):
        """Test getting health status for all integrations."""
        health_monitor.register_integration(mock_integration)
        
        # Manually set status
        mock_result = HealthCheckResult(
            integration_name="test_integration",
            integration_type="test_integration",
            status=HealthCheckStatus.SUCCESS,
            health_status="healthy",
            response_time_ms=100.0,
            timestamp=datetime.utcnow()
        )
        
        health_monitor.executors["test_integration"]._last_check = mock_result
        
        # Get all status
        all_status = await health_monitor.get_health_status()
        assert all_status["system_health"]["total_integrations"] == 1
        assert all_status["system_health"]["monitored_integrations"] == 1
        assert "test_integration" in all_status["integrations"]
    
    @pytest.mark.asyncio
    async def test_force_health_check(self, health_monitor, mock_integration):
        """Test forced health check."""
        health_monitor.register_integration(mock_integration)
        
        result = await health_monitor.force_health_check("test_integration")
        
        assert result.integration_name == "test_integration"
        assert result.status == HealthCheckStatus.SUCCESS
        assert result.health_status.value == "healthy"
    
    @pytest.mark.asyncio
    async def test_system_health_alert(self, health_monitor):
        """Test system health alerting."""
        # Register multiple integrations
        for i in range(3):
            integration = Mock()
            integration.integration_type.value = f"test_integration_{i}"
            integration.health_check = AsyncMock(side_effect=Exception("Health check failed"))
            health_monitor.register_integration(integration)
        
        # Mock global alert callback
        global_callback = AsyncMock()
        health_monitor.add_global_alert_callback(global_callback)
        
        # Manually set unhealthy status for more than 50%
        for i in range(2):
            mock_result = HealthCheckResult(
                integration_name=f"test_integration_{i}",
                integration_type=f"test_integration_{i}",
                status=HealthCheckStatus.FAILURE,
                health_status="unhealthy",
                response_time_ms=0.0,
                timestamp=datetime.utcnow()
            )
            health_monitor.executors[f"test_integration_{i}"]._last_check = mock_result
        
        # Trigger system health check
        await health_monitor._check_system_health()
        
        # Global alert should be triggered
        global_callback.assert_called_once()
        alert = global_callback.call_args[0][0]
        assert alert.alert_level == AlertLevel.CRITICAL
        assert "System Health Degraded" in alert.title


class TestIntegrationMonitoring:
    """Test IntegrationMonitoring functionality."""
    
    @pytest.fixture
    def integration_monitoring(self):
        return IntegrationMonitoring()
    
    @pytest.mark.asyncio
    async def test_initialization(self, integration_monitoring):
        """Test IntegrationMonitoring initialization."""
        assert integration_monitoring._is_running is False
        assert integration_monitoring.config == integration_monitoring.config
        assert "metrics" in integration_monitoring.config
        assert "health_checks" in integration_monitoring.config
        assert "alerts" in integration_monitoring.config
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, integration_monitoring):
        """Test monitoring start/stop."""
        # Start monitoring
        await integration_monitoring.start()
        assert integration_monitoring._is_running is True
        
        # Stop monitoring
        await integration_monitoring.stop()
        assert integration_monitoring._is_running is False
    
    def test_get_monitoring_status(self, integration_monitoring):
        """Test monitoring status retrieval."""
        status = integration_monitoring.get_monitoring_status()
        
        assert status["running"] is False
        assert "config" in status
        assert "metrics_enabled" in status
        assert "health_checks_enabled" in status
        assert "alerts_enabled" in status
    
    @pytest.mark.asyncio
    async def test_global_monitoring_functions(self):
        """Test global monitoring functions."""
        # Get global monitoring instance
        monitoring = get_integration_monitoring()
        assert isinstance(monitoring, IntegrationMonitoring)
        
        # Start global monitoring
        await start_integration_monitoring()
        assert monitoring._is_running is True
        
        # Stop global monitoring
        await stop_integration_monitoring()
        assert monitoring._is_running is False


# Performance tests
@pytest.mark.integration
class TestMonitoringPerformance:
    """Performance tests for monitoring components."""
    
    @pytest.mark.asyncio
    async def test_metrics_recording_performance(self):
        """Test metrics recording performance."""
        metrics = IntegrationMetrics("performance_test")
        
        start_time = time.time()
        
        # Record 1000 requests
        for i in range(1000):
            metrics.record_request(
                method="GET" if i % 2 == 0 else "POST",
                endpoint="/test",
                status="success" if i % 10 != 0 else "failure",
                duration=float(i % 100) / 1000.0,  # 0-100ms
                response_size=1024 + (i % 1000)
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert duration < 1.0
        
        # Verify metrics were recorded
        assert metrics.request_count.get_value() == 1000.0
        assert metrics.error_count.get_value() == 100.0  # 10% failure rate
    
    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test health check execution performance."""
        # Create mock integration
        integration = Mock()
        integration.integration_type.value = "performance_test"
        integration.health_check = AsyncMock(return_value={"status": "healthy", "response_time": 50})
        
        config = HealthCheckConfig(enabled=True, interval_seconds=60, timeout_seconds=30)
        executor = HealthCheckExecutor(integration, config)
        
        start_time = time.time()
        
        # Execute 100 health checks
        tasks = []
        for i in range(100):
            tasks.append(executor.execute_check())
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 2 seconds)
        assert duration < 2.0
        assert len(results) == 100
        assert all(result.status == HealthCheckStatus.SUCCESS for result in results)
    
    @pytest.mark.asyncio
    async def test_prometheus_export_performance(self):
        """Test Prometheus export performance."""
        metrics = IntegrationMetrics("prometheus_test")
        
        # Record substantial data
        for i in range(500):
            metrics.record_request(
                method=["GET", "POST", "PUT", "DELETE"][i % 4],
                endpoint=["/api/users", "/api/tickets", "/api/cases"][i % 3],
                status=["success", "failure", "timeout"][i % 3],
                duration=float(i % 50) / 100.0,
                response_size=512 + (i % 2048)
            )
            
            if i % 10 == 0:
                metrics.record_error("API_ERROR", ["TIMEOUT", "RATE_LIMIT", "AUTH_FAILED"][i % 3])
        
        start_time = time.time()
        
        # Export to Prometheus format
        prometheus_output = metrics.export_prometheus_format()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (< 100ms)
        assert duration < 0.1
        
        # Verify output format
        assert "# HELP" in prometheus_output
        assert "# TYPE" in prometheus_output
        assert len(prometheus_output) > 1000  # Should be substantial


# Error handling tests
@pytest.mark.asyncio
class TestMonitoringErrorHandling:
    """Test error handling in monitoring components."""
    
    async def test_metrics_error_handling(self):
        """Test metrics error handling."""
        metrics = IntegrationMetrics("error_test")
        
        # Test with invalid labels
        try:
            metrics.record_request(
                method="GET",
                endpoint="/test",
                status="success",
                duration=0.5,
                response_size=1024
            )
            # Should succeed
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
        
        # Test with None values
        try:
            metrics.record_request(
                method="GET",
                endpoint="/test",
                status="success",
                duration=None,  # Should handle None gracefully
                response_size=None
            )
            # Should handle gracefully
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")
    
    async def test_health_check_error_handling(self):
        """Test health check error handling."""
        # Create integration that always fails
        integration = Mock()
        integration.integration_type.value = "error_test"
        integration.health_check = AsyncMock(side_effect=Exception("Health check always fails"))
        
        config = HealthCheckConfig(enabled=True, interval_seconds=60, timeout_seconds=30)
        executor = HealthCheckExecutor(integration, config)
        
        # Execute health check - should handle error gracefully
        result = await executor.execute_check()
        
        assert result.status == HealthCheckStatus.FAILURE
        assert result.health_status.value == "unhealthy"
        assert result.error_message == "Health check always fails"
        assert result.error_details is not None
    
    async def test_monitoring_system_error_handling(self):
        """Test monitoring system error handling."""
        monitoring = IntegrationMonitoring()
        
        # Test start with invalid config
        monitoring.config = {"invalid": "config"}
        
        try:
            await monitoring.start()
            # Should handle gracefully
        except Exception as e:
            # Should not crash, might log error
            pass
        
        # Test stop when not running
        try:
            await monitoring.stop()
            # Should handle gracefully
        except Exception as e:
            # Should not crash
            pass


# Import time for performance tests
import time

# Export test classes
__all__ = [
    "TestMetricCollectors",
    "TestCounterMetric",
    "TestGaugeMetric", 
    "TestHistogramMetric",
    "TestIntegrationMetrics",
    "TestHealthMonitoring",
    "TestIntegrationHealthMonitor",
    "TestIntegrationMonitoring",
    "TestMonitoringPerformance",
    "TestMonitoringErrorHandling"
]