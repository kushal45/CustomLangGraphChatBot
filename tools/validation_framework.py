"""
Tool Integration Validation Framework for CustomLangGraphChatBot.

This module provides comprehensive validation for tool configurations,
dependencies, API connectivity, and basic functionality before allowing
tools to be used in the main workflow.
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from .registry import ToolRegistry, ToolConfig, RepositoryType
from logging_config import get_logger

logger = get_logger(__name__)


class ValidationLevel(Enum):
    """Validation level enumeration."""
    CRITICAL = "CRITICAL"  # Must pass for workflow to proceed
    IMPORTANT = "IMPORTANT"  # Should pass, warnings if not
    OPTIONAL = "OPTIONAL"  # Nice to have, informational only


class ValidationStatus(Enum):
    """Validation status enumeration."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"


@dataclass
class ValidationResult:
    """Validation result data class."""
    validator_name: str
    status: ValidationStatus
    level: ValidationLevel
    message: str
    details: Dict[str, Any]
    execution_time: float
    timestamp: float


class ToolValidationFramework:
    """Comprehensive tool validation framework."""
    
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self.registry = ToolRegistry(self.config)
        self.validation_results = []
        self.validators = {}
        self._register_validators()
    
    def _register_validators(self):
        """Register all available validators."""
        self.validators = {
            "environment_check": self._validate_environment,
            "dependencies_check": self._validate_dependencies,
            "api_connectivity": self._validate_api_connectivity,
            "tool_registry": self._validate_tool_registry,
            "filesystem_access": self._validate_filesystem_access,
            "tool_functionality": self._validate_tool_functionality,
            "configuration_integrity": self._validate_configuration_integrity,
            "security_check": self._validate_security_settings
        }
    
    async def run_validation(self, validators: Optional[List[str]] = None, 
                           level_filter: Optional[ValidationLevel] = None) -> Dict[str, Any]:
        """Run validation checks."""
        logger.info("Starting tool validation framework")
        
        validators_to_run = validators or list(self.validators.keys())
        self.validation_results = []
        
        for validator_name in validators_to_run:
            if validator_name not in self.validators:
                logger.warning(f"Unknown validator: {validator_name}")
                continue
            
            logger.info(f"Running validator: {validator_name}")
            start_time = time.time()
            
            try:
                result = await self.validators[validator_name]()
                result.execution_time = time.time() - start_time
                result.timestamp = time.time()
                
                # Apply level filter
                if level_filter is None or result.level == level_filter:
                    self.validation_results.append(result)
                    
            except Exception as e:
                logger.error(f"Validator {validator_name} failed: {e}")
                result = ValidationResult(
                    validator_name=validator_name,
                    status=ValidationStatus.FAIL,
                    level=ValidationLevel.CRITICAL,
                    message=f"Validator execution failed: {str(e)}",
                    details={"exception": str(e)},
                    execution_time=time.time() - start_time,
                    timestamp=time.time()
                )
                self.validation_results.append(result)
        
        return self._generate_validation_summary()
    
    async def _validate_environment(self) -> ValidationResult:
        """Validate environment setup."""
        details = {}
        issues = []
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 8):
            issues.append(f"Python version {python_version.major}.{python_version.minor} is too old (requires 3.8+)")
        details["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
        
        # Check required environment variables
        required_env_vars = ["PATH"]
        optional_env_vars = ["GITHUB_TOKEN", "XAI_API_KEY", "OPENAI_API_KEY", "SLACK_WEBHOOK_URL"]
        
        for var in required_env_vars:
            if not os.getenv(var):
                issues.append(f"Required environment variable {var} not set")
        
        missing_optional = [var for var in optional_env_vars if not os.getenv(var)]
        if missing_optional:
            details["missing_optional_env_vars"] = missing_optional
        
        # Check working directory permissions
        try:
            test_file = Path.cwd() / ".validation_test"
            test_file.write_text("test")
            test_file.unlink()
            details["working_directory_writable"] = True
        except Exception as e:
            issues.append(f"Working directory not writable: {e}")
            details["working_directory_writable"] = False
        
        status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
        message = "Environment validation passed" if not issues else f"Environment issues: {'; '.join(issues)}"
        
        return ValidationResult(
            validator_name="environment_check",
            status=status,
            level=ValidationLevel.CRITICAL,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )
    
    async def _validate_dependencies(self) -> ValidationResult:
        """Validate tool dependencies."""
        details = {}
        issues = []
        
        # Check Python packages
        required_packages = ["langchain", "pydantic", "aiohttp", "requests"]
        optional_packages = ["pylint", "flake8", "bandit"]
        
        for package in required_packages:
            try:
                __import__(package)
                details[f"package_{package}"] = "available"
            except ImportError:
                issues.append(f"Required package {package} not installed")
                details[f"package_{package}"] = "missing"
        
        for package in optional_packages:
            try:
                __import__(package)
                details[f"package_{package}"] = "available"
            except ImportError:
                details[f"package_{package}"] = "missing"
        
        # Check system commands
        system_commands = {
            "git": ValidationLevel.CRITICAL,
            "pylint": ValidationLevel.OPTIONAL,
            "flake8": ValidationLevel.OPTIONAL,
            "bandit": ValidationLevel.OPTIONAL
        }
        
        for command, level in system_commands.items():
            try:
                result = subprocess.run([command, "--version"], 
                                      capture_output=True, check=True, timeout=10)
                details[f"command_{command}"] = "available"
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                details[f"command_{command}"] = "missing"
                if level == ValidationLevel.CRITICAL:
                    issues.append(f"Critical command {command} not available")
        
        status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
        message = "Dependencies validation passed" if not issues else f"Dependency issues: {'; '.join(issues)}"
        
        return ValidationResult(
            validator_name="dependencies_check",
            status=status,
            level=ValidationLevel.CRITICAL,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )
    
    async def _validate_api_connectivity(self) -> ValidationResult:
        """Validate API connectivity."""
        details = {}
        warnings = []
        
        # Check GitHub API
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"token {github_token}"}
                    async with session.get("https://api.github.com/user", 
                                         headers=headers, timeout=10) as response:
                        if response.status == 200:
                            details["github_api"] = "connected"
                        else:
                            details["github_api"] = f"error_{response.status}"
                            warnings.append(f"GitHub API returned status {response.status}")
            except Exception as e:
                details["github_api"] = f"error_{str(e)}"
                warnings.append(f"GitHub API connectivity failed: {e}")
        else:
            details["github_api"] = "no_token"
            warnings.append("GitHub token not configured")
        
        # Check AI API endpoints (basic connectivity)
        ai_apis = {
            "XAI_API_KEY": "https://api.x.ai/v1/models",
            "OPENAI_API_KEY": "https://api.openai.com/v1/models"
        }
        
        for env_var, endpoint in ai_apis.items():
            api_key = os.getenv(env_var)
            if api_key:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        headers = {"Authorization": f"Bearer {api_key}"}
                        async with session.get(endpoint, headers=headers, timeout=10) as response:
                            details[env_var.lower()] = f"status_{response.status}"
                except Exception as e:
                    details[env_var.lower()] = f"error_{str(e)}"
                    warnings.append(f"{env_var} API connectivity failed: {e}")
            else:
                details[env_var.lower()] = "no_key"
        
        status = ValidationStatus.WARNING if warnings else ValidationStatus.PASS
        message = "API connectivity validated" if not warnings else f"API warnings: {'; '.join(warnings[:3])}"
        
        return ValidationResult(
            validator_name="api_connectivity",
            status=status,
            level=ValidationLevel.IMPORTANT,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )
    
    async def _validate_tool_registry(self) -> ValidationResult:
        """Validate tool registry functionality."""
        details = {}
        issues = []
        
        try:
            # Test registry initialization
            all_tools = self.registry.get_all_tools()
            details["total_tools"] = len(all_tools)
            
            # Test tool categories
            categories = self.registry.get_category_tools()
            details["categories"] = list(categories.keys())
            details["tools_per_category"] = {cat: len(tools) for cat, tools in categories.items()}
            
            # Test configuration validation
            validation = self.registry.validate_configuration()
            details["registry_validation"] = validation
            
            if not validation["valid"]:
                issues.append("Registry configuration validation failed")
            
            # Test repository type detection
            test_extensions = ['.py', '.js', '.md']
            repo_type = self.registry.detect_repository_type(test_extensions)
            details["repo_type_detection"] = repo_type.value
            
            # Test tool retrieval
            for category in categories:
                category_tools = self.registry.get_tools_by_category(category)
                if not category_tools:
                    issues.append(f"No tools found for category {category}")
            
        except Exception as e:
            issues.append(f"Registry validation failed: {e}")
            details["error"] = str(e)
        
        status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
        message = "Tool registry validation passed" if not issues else f"Registry issues: {'; '.join(issues)}"
        
        return ValidationResult(
            validator_name="tool_registry",
            status=status,
            level=ValidationLevel.CRITICAL,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )
    
    async def _validate_filesystem_access(self) -> ValidationResult:
        """Validate filesystem access permissions."""
        details = {}
        issues = []
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Test file creation
                test_file = temp_path / "test.txt"
                test_file.write_text("test content")
                details["file_creation"] = "success"
                
                # Test file reading
                content = test_file.read_text()
                if content != "test content":
                    issues.append("File read/write mismatch")
                details["file_reading"] = "success"
                
                # Test directory operations
                test_subdir = temp_path / "subdir"
                test_subdir.mkdir()
                details["directory_creation"] = "success"
                
                # Test file permissions
                test_file.chmod(0o644)
                details["permission_setting"] = "success"
                
        except Exception as e:
            issues.append(f"Filesystem access failed: {e}")
            details["error"] = str(e)
        
        status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
        message = "Filesystem access validated" if not issues else f"Filesystem issues: {'; '.join(issues)}"
        
        return ValidationResult(
            validator_name="filesystem_access",
            status=status,
            level=ValidationLevel.CRITICAL,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )

    async def _validate_tool_functionality(self) -> ValidationResult:
        """Validate basic tool functionality."""
        details = {}
        issues = []

        try:
            # Test a few key tools with minimal operations
            test_results = {}

            # Test file reader tool
            file_reader = self.registry.get_tool("file_reader")
            if file_reader:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write("test content")
                    f.flush()

                    result = file_reader._run(f.name)
                    os.unlink(f.name)

                    if "error" not in result:
                        test_results["file_reader"] = "pass"
                    else:
                        test_results["file_reader"] = "fail"
                        issues.append("File reader tool failed basic test")

            # Test directory lister tool
            directory_lister = self.registry.get_tool("directory_lister")
            if directory_lister:
                with tempfile.TemporaryDirectory() as temp_dir:
                    query = json.dumps({"directory_path": temp_dir, "recursive": False})
                    result = directory_lister._run(query)

                    if "error" not in result:
                        test_results["directory_lister"] = "pass"
                    else:
                        test_results["directory_lister"] = "fail"
                        issues.append("Directory lister tool failed basic test")

            # Test code complexity tool
            complexity_tool = self.registry.get_tool("code_complexity")
            if complexity_tool:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write("def test(): return 42")
                    f.flush()

                    result = complexity_tool._run(f.name)
                    os.unlink(f.name)

                    if "error" not in result:
                        test_results["code_complexity"] = "pass"
                    else:
                        test_results["code_complexity"] = "fail"
                        issues.append("Code complexity tool failed basic test")

            details["tool_tests"] = test_results

        except Exception as e:
            issues.append(f"Tool functionality validation failed: {e}")
            details["error"] = str(e)

        status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
        message = "Tool functionality validated" if not issues else f"Tool issues: {'; '.join(issues)}"

        return ValidationResult(
            validator_name="tool_functionality",
            status=status,
            level=ValidationLevel.IMPORTANT,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )

    async def _validate_configuration_integrity(self) -> ValidationResult:
        """Validate configuration integrity."""
        details = {}
        warnings = []

        try:
            # Check tool configuration consistency
            config_dict = self.config.dict()
            details["config_keys"] = list(config_dict.keys())

            # Validate timeout settings
            if self.config.tool_timeout <= 0:
                warnings.append("Tool timeout should be positive")

            if self.config.max_file_size <= 0:
                warnings.append("Max file size should be positive")

            # Check enabled categories
            all_categories = ["filesystem", "analysis", "ai_analysis", "github", "communication"]
            enabled_categories = self.config.enabled_categories

            if not enabled_categories:
                warnings.append("No tool categories enabled")

            unknown_categories = set(enabled_categories) - set(all_categories)
            if unknown_categories:
                warnings.append(f"Unknown categories enabled: {unknown_categories}")

            details["enabled_categories"] = enabled_categories
            details["unknown_categories"] = list(unknown_categories)

            # Check tool selection rules
            if hasattr(self.config, 'tool_selection_rules'):
                details["tool_selection_rules"] = len(self.config.tool_selection_rules)

        except Exception as e:
            warnings.append(f"Configuration validation failed: {e}")
            details["error"] = str(e)

        status = ValidationStatus.WARNING if warnings else ValidationStatus.PASS
        message = "Configuration integrity validated" if not warnings else f"Config warnings: {'; '.join(warnings[:2])}"

        return ValidationResult(
            validator_name="configuration_integrity",
            status=status,
            level=ValidationLevel.IMPORTANT,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )

    async def _validate_security_settings(self) -> ValidationResult:
        """Validate security settings."""
        details = {}
        warnings = []

        try:
            # Check for sensitive data in environment
            sensitive_patterns = ["password", "secret", "key", "token"]
            env_vars = dict(os.environ)

            for var_name, var_value in env_vars.items():
                if any(pattern in var_name.lower() for pattern in sensitive_patterns):
                    if var_value and len(var_value) < 10:
                        warnings.append(f"Environment variable {var_name} appears to have weak value")
                    details[f"env_{var_name.lower()}"] = "configured" if var_value else "empty"

            # Check file permissions on sensitive files
            sensitive_files = [".env", "config.json", "secrets.json"]
            for filename in sensitive_files:
                filepath = Path(filename)
                if filepath.exists():
                    stat = filepath.stat()
                    # Check if file is readable by others (basic check)
                    if stat.st_mode & 0o044:  # Others can read
                        warnings.append(f"File {filename} may have overly permissive permissions")
                    details[f"file_{filename}"] = "exists"

            # Check for hardcoded secrets in common config files
            config_files = ["config.py", "settings.py", ".env"]
            for config_file in config_files:
                if Path(config_file).exists():
                    try:
                        content = Path(config_file).read_text()
                        if any(pattern in content.lower() for pattern in ["password=", "secret=", "key="]):
                            warnings.append(f"Potential hardcoded secrets in {config_file}")
                    except Exception:
                        pass  # Skip if can't read file

        except Exception as e:
            warnings.append(f"Security validation failed: {e}")
            details["error"] = str(e)

        status = ValidationStatus.WARNING if warnings else ValidationStatus.PASS
        message = "Security settings validated" if not warnings else f"Security warnings: {len(warnings)} issues"

        return ValidationResult(
            validator_name="security_check",
            status=status,
            level=ValidationLevel.OPTIONAL,
            message=message,
            details=details,
            execution_time=0,
            timestamp=0
        )

    def _generate_validation_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        total_validations = len(self.validation_results)
        passed = sum(1 for r in self.validation_results if r.status == ValidationStatus.PASS)
        failed = sum(1 for r in self.validation_results if r.status == ValidationStatus.FAIL)
        warnings = sum(1 for r in self.validation_results if r.status == ValidationStatus.WARNING)
        skipped = sum(1 for r in self.validation_results if r.status == ValidationStatus.SKIP)

        # Determine overall status
        critical_failures = sum(1 for r in self.validation_results
                              if r.status == ValidationStatus.FAIL and r.level == ValidationLevel.CRITICAL)

        if critical_failures > 0:
            overall_status = "CRITICAL_FAILURE"
        elif failed > 0:
            overall_status = "FAILURE"
        elif warnings > 0:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"

        total_execution_time = sum(r.execution_time for r in self.validation_results)

        return {
            "overall_status": overall_status,
            "total_validations": total_validations,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "critical_failures": critical_failures,
            "total_execution_time": total_execution_time,
            "timestamp": time.time(),
            "results": [
                {
                    "validator": r.validator_name,
                    "status": r.status.value,
                    "level": r.level.value,
                    "message": r.message,
                    "execution_time": r.execution_time
                }
                for r in self.validation_results
            ]
        }

    def print_validation_report(self, summary: Dict[str, Any], verbose: bool = False):
        """Print validation report."""
        print("🔍 Tool Validation Framework Report")
        print("=" * 50)

        # Overall status
        status_icons = {
            "PASS": "✅",
            "WARNING": "⚠️",
            "FAILURE": "❌",
            "CRITICAL_FAILURE": "🚨"
        }

        overall_status = summary["overall_status"]
        icon = status_icons.get(overall_status, "❓")

        print(f"Overall Status: {icon} {overall_status}")
        print(f"Total Validations: {summary['total_validations']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⏭️  Skipped: {summary['skipped']}")
        print(f"⏱️  Total Time: {summary['total_execution_time']:.3f}s")

        if summary['critical_failures'] > 0:
            print(f"🚨 Critical Failures: {summary['critical_failures']}")

        print()

        if verbose:
            print("Detailed Results:")
            print("-" * 30)

            for result in self.validation_results:
                status_icon = {
                    ValidationStatus.PASS: "✅",
                    ValidationStatus.WARNING: "⚠️",
                    ValidationStatus.FAIL: "❌",
                    ValidationStatus.SKIP: "⏭️"
                }.get(result.status, "❓")

                level_icon = {
                    ValidationLevel.CRITICAL: "🚨",
                    ValidationLevel.IMPORTANT: "⚠️",
                    ValidationLevel.OPTIONAL: "ℹ️"
                }.get(result.level, "❓")

                print(f"{status_icon} {level_icon} {result.validator_name}")
                print(f"   Status: {result.status.value}")
                print(f"   Level: {result.level.value}")
                print(f"   Message: {result.message}")
                print(f"   Time: {result.execution_time:.3f}s")

                if result.details and len(str(result.details)) < 200:
                    print(f"   Details: {result.details}")
                print()

        # Recommendations
        if overall_status in ["FAILURE", "CRITICAL_FAILURE"]:
            print("🔧 Action Required:")
            failed_critical = [r for r in self.validation_results
                             if r.status == ValidationStatus.FAIL and r.level == ValidationLevel.CRITICAL]
            for result in failed_critical:
                print(f"   • Fix {result.validator_name}: {result.message}")

        if summary['warnings'] > 0:
            print("💡 Recommendations:")
            warning_results = [r for r in self.validation_results if r.status == ValidationStatus.WARNING]
            for result in warning_results[:3]:  # Show first 3 warnings
                print(f"   • {result.validator_name}: {result.message}")


# Convenience function for external use
async def validate_tools(config: Optional[ToolConfig] = None,
                        validators: Optional[List[str]] = None,
                        verbose: bool = False) -> Dict[str, Any]:
    """Run tool validation and return results."""
    framework = ToolValidationFramework(config)
    summary = await framework.run_validation(validators)

    if verbose:
        framework.print_validation_report(summary, verbose=True)

    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tool Validation Framework")
    parser.add_argument("--validators", nargs="+", help="Specific validators to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--level", choices=["CRITICAL", "IMPORTANT", "OPTIONAL"],
                       help="Filter by validation level")

    args = parser.parse_args()

    async def main():
        level_filter = ValidationLevel(args.level) if args.level else None
        summary = await validate_tools(
            validators=args.validators,
            verbose=args.verbose
        )

        # Exit with appropriate code
        if summary["overall_status"] in ["CRITICAL_FAILURE", "FAILURE"]:
            sys.exit(1)
        else:
            sys.exit(0)

    asyncio.run(main())
