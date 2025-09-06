"""
Phase 7 validation script - comprehensive validation of all integration implementations.
"""

import asyncio
import sys
import time
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import inspect
from dataclasses import dataclass

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Validation result for a specific component."""
    component: str
    status: str  # "pass", "fail", "warning"
    message: str
    details: Dict[str, Any]
    duration: float


class Phase7Validator:
    """Comprehensive validator for Phase 7 implementations."""
    
    def __init__(self):
        self.validation_results = []
        self.start_time = None
        self.end_time = None
        
    async def validate_phase7(self) -> Dict[str, Any]:
        """Validate all Phase 7 implementations."""
        logger.info("Starting Phase 7 Validation")
        self.start_time = time.time()
        
        validation_suites = [
            ("Package Structure", self.validate_package_structure),
            ("Base Integration Infrastructure", self.validate_base_infrastructure),
            ("Salesforce Integration", self.validate_salesforce_integration),
            ("Multi-Channel Adapters", self.validate_channel_adapters),
            ("External Service Connectors", self.validate_external_connectors),
            ("OAuth Provider", self.validate_oauth_provider),
            ("Monitoring System", self.validate_monitoring_system),
            ("Test Coverage", self.validate_test_coverage),
            ("Code Quality", self.validate_code_quality),
            ("Documentation", self.validate_documentation),
        ]
        
        for suite_name, validation_func in validation_suites:
            try:
                logger.info(f"Validating {suite_name}...")
                await validation_func()
                logger.info(f"✅ {suite_name} validation completed")
            except Exception as e:
                logger.error(f"❌ {suite_name} validation failed: {e}")
                self.validation_results.append(ValidationResult(
                    component=suite_name,
                    status="fail",
                    message=f"Validation failed: {str(e)}",
                    details={"error": str(e)},
                    duration=0.0
                ))
        
        self.end_time = time.time()
        
        # Generate validation report
        report = self.generate_validation_report()
        
        logger.info("Phase 7 Validation completed")
        return report
    
    async def validate_package_structure(self):
        """Validate package structure and imports."""
        start_time = time.time()
        
        required_packages = [
            "src.integrations",
            "src.integrations.base",
            "src.integrations.config",
            "src.integrations.salesforce",
            "src.integrations.channels",
            "src.integrations.external",
            "src.integrations.auth",
            "src.integrations.monitoring",
        ]
        
        for package in required_packages:
            try:
                module = importlib.import_module(package)
                self.validation_results.append(ValidationResult(
                    component=f"Package: {package}",
                    status="pass",
                    message="Package exists and can be imported",
                    details={"module": str(module)},
                    duration=time.time() - start_time
                ))
            except ImportError as e:
                self.validation_results.append(ValidationResult(
                    component=f"Package: {package}",
                    status="fail",
                    message="Package cannot be imported",
                    details={"error": str(e)},
                    duration=time.time() - start_time
                ))
    
    async def validate_base_infrastructure(self):
        """Validate base integration infrastructure."""
        start_time = time.time()
        
        # Validate base classes
        from src.integrations.base import (
            BaseIntegrationImpl, OAuth2Client, RateLimiter, 
            RetryHandler, CircuitBreaker, BaseIntegration
        )
        
        components = [
            ("BaseIntegrationImpl", BaseIntegrationImpl),
            ("OAuth2Client", OAuth2Client),
            ("RateLimiter", RateLimiter),
            ("RetryHandler", RetryHandler),
            ("CircuitBreaker", CircuitBreaker),
            ("BaseIntegration", BaseIntegration)
        ]
        
        for name, component in components:
            if self.validate_component(name, component):
                self.validation_results.append(ValidationResult(
                    component=f"Base Infrastructure: {name}",
                    status="pass",
                    message="Component properly implemented",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"Base Infrastructure: {name}",
                    status="fail",
                    message="Component implementation issues",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
    
    async def validate_salesforce_integration(self):
        """Validate Salesforce integration implementation."""
        start_time = time.time()
        
        from src.integrations.salesforce import (
            SalesforceClient, SalesforceServiceCloud, 
            SalesforceCase, SalesforceSyncEngine
        )
        
        components = [
            ("SalesforceClient", SalesforceClient),
            ("SalesforceServiceCloud", SalesforceServiceCloud),
            ("SalesforceCase", SalesforceCase),
            ("SalesforceSyncEngine", SalesforceSyncEngine)
        ]
        
        for name, component in components:
            if self.validate_component(name, component):
                self.validation_results.append(ValidationResult(
                    component=f"Salesforce: {name}",
                    status="pass",
                    message="Salesforce component properly implemented",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"Salesforce: {name}",
                    status="fail",
                    message="Salesforce component implementation issues",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
    
    async def validate_channel_adapters(self):
        """Validate multi-channel adapters."""
        start_time = time.time()
        
        from src.integrations.channels import (
            SlackIntegration, TeamsIntegration, EmailIntegration,
            WhatsAppIntegration, WebhookIntegration
        )
        
        adapters = [
            ("SlackIntegration", SlackIntegration),
            ("TeamsIntegration", TeamsIntegration),
            ("EmailIntegration", EmailIntegration),
            ("WhatsAppIntegration", WhatsAppIntegration),
            ("WebhookIntegration", WebhookIntegration)
        ]
        
        for name, adapter in adapters:
            if self.validate_component(name, adapter):
                self.validation_results.append(ValidationResult(
                    component=f"Channel Adapter: {name}",
                    status="pass",
                    message="Channel adapter properly implemented",
                    details={"class": str(adapter)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"Channel Adapter: {name}",
                    status="fail",
                    message="Channel adapter implementation issues",
                    details={"class": str(adapter)},
                    duration=time.time() - start_time
                ))
    
    async def validate_external_connectors(self):
        """Validate external service connectors."""
        start_time = time.time()
        
        from src.integrations.external import (
            JiraIntegration, ServiceNowIntegration, ZendeskIntegration
        )
        
        connectors = [
            ("JiraIntegration", JiraIntegration),
            ("ServiceNowIntegration", ServiceNowIntegration),
            ("ZendeskIntegration", ZendeskIntegration)
        ]
        
        for name, connector in connectors:
            if self.validate_component(name, connector):
                self.validation_results.append(ValidationResult(
                    component=f"External Connector: {name}",
                    status="pass",
                    message="External connector properly implemented",
                    details={"class": str(connector)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"External Connector: {name}",
                    status="fail",
                    message="External connector implementation issues",
                    details={"class": str(connector)},
                    duration=time.time() - start_time
                ))
    
    async def validate_oauth_provider(self):
        """Validate OAuth 2.0 provider implementation."""
        start_time = time.time()
        
        from src.integrations.auth import (
            OAuth2Provider, OAuth2Client, OAuth2Token, 
            OAuth2AuthorizationCode, AuthenticationRequest, TokenValidationResult
        )
        
        components = [
            ("OAuth2Provider", OAuth2Provider),
            ("OAuth2Client", OAuth2Client),
            ("OAuth2Token", OAuth2Token),
            ("OAuth2AuthorizationCode", OAuth2AuthorizationCode),
            ("AuthenticationRequest", AuthenticationRequest),
            ("TokenValidationResult", TokenValidationResult)
        ]
        
        for name, component in components:
            if self.validate_component(name, component):
                self.validation_results.append(ValidationResult(
                    component=f"OAuth Provider: {name}",
                    status="pass",
                    message="OAuth component properly implemented",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"OAuth Provider: {name}",
                    status="fail",
                    message="OAuth component implementation issues",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
    
    async def validate_monitoring_system(self):
        """Validate monitoring and observability system."""
        start_time = time.time()
        
        from src.integrations.monitoring import (
            IntegrationMetrics, HealthCheckExecutor, IntegrationHealthMonitor,
            IntegrationMonitoring, CounterMetric, GaugeMetric, HistogramMetric
        )
        
        components = [
            ("IntegrationMetrics", IntegrationMetrics),
            ("HealthCheckExecutor", HealthCheckExecutor),
            ("IntegrationHealthMonitor", IntegrationHealthMonitor),
            ("IntegrationMonitoring", IntegrationMonitoring),
            ("CounterMetric", CounterMetric),
            ("GaugeMetric", GaugeMetric),
            ("HistogramMetric", HistogramMetric)
        ]
        
        for name, component in components:
            if self.validate_component(name, component):
                self.validation_results.append(ValidationResult(
                    component=f"Monitoring: {name}",
                    status="pass",
                    message="Monitoring component properly implemented",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"Monitoring: {name}",
                    status="fail",
                    message="Monitoring component implementation issues",
                    details={"class": str(component)},
                    duration=time.time() - start_time
                ))
    
    async def validate_test_coverage(self):
        """Validate test coverage."""
        start_time = time.time()
        
        test_files = [
            "tests/integrations/test_base.py",
            "tests/integrations/test_salesforce.py",
            "tests/integrations/test_channels.py",
            "tests/integrations/test_external.py",
            "tests/integrations/test_auth.py",
            "tests/integrations/test_monitoring.py",
            "tests/integrations/conftest.py",
            "tests/integrations/run_tests.py"
        ]
        
        for test_file in test_files:
            file_path = project_root / test_file
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                    test_count = content.count("def test_")
                    
                    self.validation_results.append(ValidationResult(
                        component=f"Test Coverage: {test_file}",
                        status="pass",
                        message=f"Test file exists with {test_count} tests",
                        details={"file": str(file_path), "test_count": test_count},
                        duration=time.time() - start_time
                    ))
            else:
                self.validation_results.append(ValidationResult(
                    component=f"Test Coverage: {test_file}",
                    status="fail",
                    message="Test file does not exist",
                    details={"file": str(file_path)},
                    duration=time.time() - start_time
                ))
    
    async def validate_code_quality(self):
        """Validate code quality aspects."""
        start_time = time.time()
        
        # Check for type hints
        from src.integrations.base import BaseIntegrationImpl
        
        # Validate BaseIntegrationImpl has proper type hints
        methods_to_check = ['authenticate', 'health_check', 'sync_data']
        
        for method_name in methods_to_check:
            method = getattr(BaseIntegrationImpl, method_name)
            if asyncio.iscoroutinefunction(method):
                sig = inspect.signature(method)
                has_return_annotation = sig.return_annotation != inspect.Signature.empty
                
                self.validation_results.append(ValidationResult(
                    component=f"Code Quality: {method_name}",
                    status="pass" if has_return_annotation else "warning",
                    message=f"Method has {'proper' if has_return_annotation else 'missing'} return type annotations",
                    details={"method": method_name, "return_annotation": str(sig.return_annotation)},
                    duration=time.time() - start_time
                ))
    
    async def validate_documentation(self):
        """Validate documentation completeness."""
        start_time = time.time()
        
        # Check for docstrings in key files
        key_files = [
            "src/integrations/base.py",
            "src/integrations/salesforce/client.py",
            "src/integrations/channels/slack.py",
            "src/integrations/external/jira.py",
            "src/integrations/auth/oauth2_provider.py",
            "src/integrations/monitoring/metrics.py"
        ]
        
        for file_path in key_files:
            full_path = project_root / file_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    content = f.read()
                    has_module_docstring = content.strip().startswith('"""')
                    
                    self.validation_results.append(ValidationResult(
                        component=f"Documentation: {file_path}",
                        status="pass" if has_module_docstring else "warning",
                        message=f"File has {'module-level' if has_module_docstring else 'missing'} docstring",
                        details={"file": str(full_path)},
                        duration=time.time() - start_time
                    ))
    
    def validate_component(self, name: str, component) -> bool:
        """Validate a component has required methods and attributes."""
        try:
            # Check if it's a class
            if not inspect.isclass(component):
                return False
            
            # Check for required base methods
            required_methods = ['__init__']
            
            # Component-specific checks
            if 'Integration' in name:
                required_methods.extend(['authenticate', 'health_check'])
            
            if 'Client' in name:
                required_methods.extend(['connect', 'disconnect'])
            
            if 'Provider' in name:
                required_methods.extend(['start', 'stop'])
            
            # Check methods exist
            for method in required_methods:
                if not hasattr(component, method):
                    return False
            
            # Check for async methods where appropriate
            async_methods = ['authenticate', 'health_check', 'sync_data', 'connect', 'disconnect']
            for method_name in async_methods:
                if hasattr(component, method_name):
                    method = getattr(component, method_name)
                    if callable(method) and not asyncio.iscoroutinefunction(method):
                        # Should be async for integration methods
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating component {name}: {e}")
            return False
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_checks = len(self.validation_results)
        passed_checks = sum(1 for r in self.validation_results if r.status == "pass")
        failed_checks = sum(1 for r in self.validation_results if r.status == "fail")
        warning_checks = sum(1 for r in self.validation_results if r.status == "warning")
        
        total_duration = self.end_time - self.start_time if self.start_time and self.end_time else 0
        
        # Group results by category
        categories = {}
        for result in self.validation_results:
            category = result.component.split(":")[0] if ":" in result.component else "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        # Category summaries
        category_summaries = {}
        for category, results in categories.items():
            cat_passed = sum(1 for r in results if r.status == "pass")
            cat_failed = sum(1 for r in results if r.status == "fail")
            cat_warning = sum(1 for r in results if r.status == "warning")
            
            category_summaries[category] = {
                "total": len(results),
                "passed": cat_passed,
                "failed": cat_failed,
                "warning": cat_warning,
                "success_rate": (cat_passed / len(results) * 100) if len(results) > 0 else 0
            }
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration": total_duration,
            "overall_results": {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "warning": warning_checks,
                "success_rate": (passed_checks / total_checks * 100) if total_checks > 0 else 0,
                "status": "success" if failed_checks == 0 else "warning" if failed_checks < 5 else "failed"
            },
            "category_summaries": category_summaries,
            "detailed_results": [
                {
                    "component": result.component,
                    "status": result.status,
                    "message": result.message,
                    "details": result.details,
                    "duration": result.duration
                }
                for result in self.validation_results
            ]
        }
        
        self.log_validation_report(report)
        return report
    
    def log_validation_report(self, report: Dict[str, Any]):
        """Log validation report."""
        logger.info("=" * 80)
        logger.info("PHASE 7 VALIDATION REPORT")
        logger.info("=" * 80)
        logger.info(f"Validation Run: {report['timestamp']}")
        logger.info(f"Total Duration: {report['total_duration']:.2f} seconds")
        logger.info("")
        
        overall = report["overall_results"]
        status_icon = {"success": "✅", "warning": "⚠️", "failed": "❌"}.get(overall["status"], "❓")
        
        logger.info(f"Overall Results: {status_icon}")
        logger.info(f"  Total Checks: {overall['total_checks']}")
        logger.info(f"  Passed: {overall['passed']}")
        logger.info(f"  Failed: {overall['failed']}")
        logger.info(f"  Warning: {overall['warning']}")
        logger.info(f"  Success Rate: {overall['success_rate']:.1f}%")
        logger.info("")
        
        logger.info("Category Summaries:")
        for category, summary in report["category_summaries"].items():
            status_icon = "✅" if summary["failed"] == 0 else "⚠️" if summary["failed"] < 3 else "❌"
            logger.info(f"  {status_icon} {category}:")
            logger.info(f"    Checks: {summary['total']}, Passed: {summary['passed']}, Failed: {summary['failed']}, Warning: {summary['warning']}")
            logger.info(f"    Success Rate: {summary['success_rate']:.1f}%")
        
        # Log failed validations
        failed_validations = [r for r in self.validation_results if r.status == "fail"]
        if failed_validations:
            logger.info("")
            logger.info("Failed Validations:")
            for result in failed_validations[:10]:  # Show first 10 failures
                logger.info(f"  ❌ {result.component}: {result.message}")
        
        logger.info("=" * 80)


# Global project root
project_root = Path(__file__).parent.parent.parent


async def main():
    """Main validation execution function."""
    try:
        validator = Phase7Validator()
        report = await validator.validate_phase7()
        
        # Exit with appropriate code
        overall_status = report["overall_results"]["status"]
        sys.exit(0 if overall_status == "success" else 1)
        
    except Exception as e:
        logger.error(f"Validation execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())