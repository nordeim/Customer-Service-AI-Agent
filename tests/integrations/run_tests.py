"""
Comprehensive test runner for Phase 7 integration tests.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import pytest
from unittest.mock import Mock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.logging import get_logger

logger = get_logger(__name__)


class IntegrationTestRunner:
    """Comprehensive test runner for Phase 7 integrations."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        logger.info("Starting Phase 7 Integration Test Suite")
        self.start_time = time.time()
        
        test_suites = [
            ("Base Integration Tests", self.run_base_tests),
            ("Salesforce Integration Tests", self.run_salesforce_tests),
            ("Channel Integration Tests", self.run_channel_tests),
            ("External Service Tests", self.run_external_tests),
            ("OAuth Provider Tests", self.run_oauth_tests),
            ("Monitoring Tests", self.run_monitoring_tests),
            ("Performance Tests", self.run_performance_tests),
            ("Integration Tests", self.run_integration_tests),
        ]
        
        results = {}
        
        for suite_name, test_func in test_suites:
            try:
                logger.info(f"Running {suite_name}...")
                suite_results = await test_func()
                results[suite_name] = suite_results
                logger.info(f"✅ {suite_name} completed successfully")
            except Exception as e:
                logger.error(f"❌ {suite_name} failed: {e}")
                results[suite_name] = {"status": "failed", "error": str(e)}
        
        self.end_time = time.time()
        
        # Generate summary report
        summary = self.generate_summary_report(results)
        
        logger.info("Phase 7 Integration Test Suite completed")
        return summary
    
    async def run_base_tests(self) -> Dict[str, Any]:
        """Run base integration tests."""
        logger.info("Running base integration tests...")
        
        # Import test modules
        from tests.integrations.test_base import (
            TestOAuth2Client, TestRateLimiter, TestRetryHandler, 
            TestCircuitBreaker, TestBaseIntegrationImpl, TestIntegrationWithResilience,
            TestIntegrationPerformance, TestIntegrationErrorHandling
        )
        
        test_classes = [
            TestOAuth2Client, TestRateLimiter, TestRetryHandler, TestCircuitBreaker,
            TestBaseIntegrationImpl, TestIntegrationWithResilience,
            TestIntegrationPerformance, TestIntegrationErrorHandling
        ]
        
        return await self.run_test_classes(test_classes, "base")
    
    async def run_salesforce_tests(self) -> Dict[str, Any]:
        """Run Salesforce integration tests."""
        logger.info("Running Salesforce integration tests...")
        
        from tests.integrations.test_salesforce import (
            TestSalesforceClient, TestSalesforceServiceCloud, TestSalesforceModels,
            TestSalesforceSyncEngine, TestSalesforcePerformance, TestSalesforceErrorHandling
        )
        
        test_classes = [
            TestSalesforceClient, TestSalesforceServiceCloud, TestSalesforceModels,
            TestSalesforceSyncEngine, TestSalesforcePerformance, TestSalesforceErrorHandling
        ]
        
        return await self.run_test_classes(test_classes, "salesforce")
    
    async def run_channel_tests(self) -> Dict[str, Any]:
        """Run channel integration tests."""
        logger.info("Running channel integration tests...")
        
        from tests.integrations.test_channels import (
            TestSlackIntegration, TestTeamsIntegration, TestEmailIntegration,
            TestWhatsAppIntegration, TestWebhookIntegration, TestChannelsPerformance,
            TestChannelsErrorHandling
        )
        
        test_classes = [
            TestSlackIntegration, TestTeamsIntegration, TestEmailIntegration,
            TestWhatsAppIntegration, TestWebhookIntegration, TestChannelsPerformance,
            TestChannelsErrorHandling
        ]
        
        return await self.run_test_classes(test_classes, "channels")
    
    async def run_external_tests(self) -> Dict[str, Any]:
        """Run external service tests."""
        logger.info("Running external service tests...")
        
        from tests.integrations.test_external import (
            TestJiraIntegration, TestServiceNowIntegration, TestZendeskIntegration,
            TestExternalIntegrationsPerformance, TestExternalIntegrationsErrorHandling,
            TestExternalModels
        )
        
        test_classes = [
            TestJiraIntegration, TestServiceNowIntegration, TestZendeskIntegration,
            TestExternalIntegrationsPerformance, TestExternalIntegrationsErrorHandling,
            TestExternalModels
        ]
        
        return await self.run_test_classes(test_classes, "external")
    
    async def run_oauth_tests(self) -> Dict[str, Any]:
        """Run OAuth provider tests."""
        logger.info("Running OAuth provider tests...")
        
        from tests.integrations.test_auth import (
            TestOAuth2Provider, TestOAuth2TokenManagement, TestOAuth2AuthorizationCode,
            TestAuthenticationRequest, TestTokenValidationResult, TestOAuth2Performance,
            TestOAuth2ErrorHandling
        )
        
        test_classes = [
            TestOAuth2Provider, TestOAuth2TokenManagement, TestOAuth2AuthorizationCode,
            TestAuthenticationRequest, TestTokenValidationResult, TestOAuth2Performance,
            TestOAuth2ErrorHandling
        ]
        
        return await self.run_test_classes(test_classes, "oauth")
    
    async def run_monitoring_tests(self) -> Dict[str, Any]:
        """Run monitoring tests."""
        logger.info("Running monitoring tests...")
        
        from tests.integrations.test_monitoring import (
            TestMetricCollectors, TestCounterMetric, TestGaugeMetric, TestHistogramMetric,
            TestIntegrationMetrics, TestHealthMonitoring, TestIntegrationHealthMonitor,
            TestIntegrationMonitoring, TestMonitoringPerformance, TestMonitoringErrorHandling
        )
        
        test_classes = [
            TestMetricCollectors, TestCounterMetric, TestGaugeMetric, TestHistogramMetric,
            TestIntegrationMetrics, TestHealthMonitoring, TestIntegrationHealthMonitor,
            TestIntegrationMonitoring, TestMonitoringPerformance, TestMonitoringErrorHandling
        ]
        
        return await self.run_test_classes(test_classes, "monitoring")
    
    async def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        logger.info("Running performance tests...")
        
        # Run performance tests with specific markers
        performance_tests = [
            "tests/integrations/test_base.py::TestIntegrationPerformance",
            "tests/integrations/test_salesforce.py::TestSalesforcePerformance",
            "tests/integrations/test_channels.py::TestChannelsPerformance",
            "tests/integrations/test_external.py::TestExternalIntegrationsPerformance",
            "tests/integrations/test_auth.py::TestOAuth2Performance",
            "tests/integrations/test_monitoring.py::TestMonitoringPerformance"
        ]
        
        return await self.run_pytest_tests(performance_tests, "performance")
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run full integration tests."""
        logger.info("Running full integration tests...")
        
        # Run integration tests with specific markers
        integration_tests = [
            "tests/integrations/test_base.py -m integration",
            "tests/integrations/test_salesforce.py -m integration",
            "tests/integrations/test_channels.py -m integration",
            "tests/integrations/test_external.py -m integration",
            "tests/integrations/test_auth.py -m integration",
            "tests/integrations/test_monitoring.py -m integration"
        ]
        
        return await self.run_pytest_tests(integration_tests, "integration")
    
    async def run_test_classes(self, test_classes: List[type], test_type: str) -> Dict[str, Any]:
        """Run test classes using pytest programmatically."""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "duration": 0
        }
        
        start_time = time.time()
        
        for test_class in test_classes:
            try:
                # Create test instance
                test_instance = test_class()
                
                # Get test methods
                test_methods = [
                    method for method in dir(test_instance) 
                    if method.startswith('test_') and callable(getattr(test_instance, method))
                ]
                
                results["total"] += len(test_methods)
                
                # Run each test method
                for test_method in test_methods:
                    try:
                        method = getattr(test_instance, test_method)
                        
                        # Handle async methods
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                        
                        results["passed"] += 1
                        logger.debug(f"✅ {test_class.__name__}::{test_method}")
                        
                    except Exception as e:
                        results["failed"] += 1
                        error_msg = f"❌ {test_class.__name__}::{test_method}: {str(e)}"
                        results["errors"].append(error_msg)
                        logger.error(error_msg)
                        
            except Exception as e:
                error_msg = f"Failed to run {test_class.__name__}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
        
        end_time = time.time()
        results["duration"] = end_time - start_time
        
        results["status"] = "success" if results["failed"] == 0 else "failed"
        results["success_rate"] = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
        
        return results
    
    async def run_pytest_tests(self, test_paths: List[str], test_type: str) -> Dict[str, Any]:
        """Run pytest tests with specific paths and markers."""
        import subprocess
        import tempfile
        import os
        
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "duration": 0
        }
        
        start_time = time.time()
        
        # Create temporary directory for test results
        with tempfile.TemporaryDirectory() as temp_dir:
            result_file = os.path.join(temp_dir, "test_results.xml")
            
            # Build pytest command
            pytest_args = [
                "-v",
                "--tb=short",
                "--strict-markers",
                f"--junitxml={result_file}",
                "-p", "no:warnings"
            ]
            
            # Add test paths
            for test_path in test_paths:
                pytest_args.extend(["-k", test_path] if "::" in test_path else [test_path])
            
            try:
                # Run pytest
                result = subprocess.run(
                    ["python", "-m", "pytest"] + pytest_args,
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                
                # Parse results from output
                output_lines = result.stdout.split('\n')
                
                # Look for summary line
                for line in output_lines:
                    if "passed" in line and "failed" in line:
                        # Parse summary like "10 passed, 2 failed"
                        parts = line.split(',')
                        for part in parts:
                            if "passed" in part:
                                results["passed"] += int(part.split()[0])
                            elif "failed" in part:
                                results["failed"] += int(part.split()[0])
                
                results["total"] = results["passed"] + results["failed"]
                
                if result.returncode != 0:
                    results["status"] = "failed"
                    results["errors"].append(f"Pytest failed with return code {result.returncode}")
                    if result.stderr:
                        results["errors"].append(result.stderr[:500])  # First 500 chars of stderr
                else:
                    results["status"] = "success"
                    
            except subprocess.TimeoutExpired:
                results["status"] = "failed"
                results["errors"].append("Test execution timed out after 5 minutes")
            except Exception as e:
                results["status"] = "failed"
                results["errors"].append(f"Failed to run pytest: {str(e)}")
        
        end_time = time.time()
        results["duration"] = end_time - start_time
        results["success_rate"] = (results["passed"] / results["total"] * 100) if results["total"] > 0 else 0
        
        return results
    
    def generate_summary_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        suite_summaries = {}
        
        for suite_name, suite_results in results.items():
            if isinstance(suite_results, dict) and "total" in suite_results:
                total_tests += suite_results.get("total", 0)
                total_passed += suite_results.get("passed", 0)
                total_failed += suite_results.get("failed", 0)
                
                suite_summaries[suite_name] = {
                    "total": suite_results.get("total", 0),
                    "passed": suite_results.get("passed", 0),
                    "failed": suite_results.get("failed", 0),
                    "success_rate": suite_results.get("success_rate", 0),
                    "duration": suite_results.get("duration", 0),
                    "status": suite_results.get("status", "unknown")
                }
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": total_duration,
            "overall_results": {
                "total_tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "success_rate": overall_success_rate,
                "status": "success" if total_failed == 0 else "failed"
            },
            "suite_results": suite_summaries,
            "detailed_results": results
        }
        
        # Log summary
        self.log_summary_report(summary)
        
        return summary
    
    def log_summary_report(self, summary: Dict[str, Any]):
        """Log summary report."""
        logger.info("=" * 80)
        logger.info("PHASE 7 INTEGRATION TEST SUMMARY REPORT")
        logger.info("=" * 80)
        logger.info(f"Test Run: {summary['timestamp']}")
        logger.info(f"Total Duration: {summary['total_duration']:.2f} seconds")
        logger.info("")
        
        overall = summary["overall_results"]
        logger.info(f"Overall Results:")
        logger.info(f"  Total Tests: {overall['total_tests']}")
        logger.info(f"  Passed: {overall['passed']}")
        logger.info(f"  Failed: {overall['failed']}")
        logger.info(f"  Success Rate: {overall['success_rate']:.1f}%")
        logger.info(f"  Status: {'✅ SUCCESS' if overall['status'] == 'success' else '❌ FAILED'}")
        logger.info("")
        
        logger.info("Suite Results:")
        for suite_name, suite_data in summary["suite_results"].items():
            status_icon = "✅" if suite_data["status"] == "success" else "❌"
            logger.info(f"  {status_icon} {suite_name}:")
            logger.info(f"    Tests: {suite_data['total']}, Passed: {suite_data['passed']}, Failed: {suite_data['failed']}")
            logger.info(f"    Success Rate: {suite_data['success_rate']:.1f}%, Duration: {suite_data['duration']:.2f}s")
        
        logger.info("=" * 80)


async def main():
    """Main test execution function."""
    try:
        runner = IntegrationTestRunner()
        results = await runner.run_all_tests()
        
        # Exit with appropriate code
        overall_status = results["overall_results"]["status"]
        sys.exit(0 if overall_status == "success" else 1)
        
    except Exception as e:
        logger.error(f"Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())