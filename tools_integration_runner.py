#!/usr/bin/env python3
"""
Comprehensive Tool Integration Test Runner for CustomLangGraphChatBot.

This script provides a unified interface to run all types of tool tests:
1. Modular sanity checks for individual tool categories
2. Health checks for tool availability and performance
3. Integration tests with pytest
4. Validation framework for tool configurations
5. Pre-workflow validation to ensure tools are ready

Usage:
    python tools_integration_runner.py --help
    python tools_integration_runner.py --sanity-check
    python tools_integration_runner.py --health-check
    python tools_integration_runner.py --category filesystem
    python tools_integration_runner.py --pre-workflow-validation
"""

import os
import sys
import json
import time
import asyncio
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    print("Install with: pip install python-dotenv")

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our test modules
from tests.test_module_sanity import run_sanity_checks
from tests.test_tool_health import run_health_checks


class ToolIntegrationRunner:
    """Comprehensive tool integration test runner."""

    def __init__(self, verbose: bool = False, use_real_params: bool = False,
                 real_params: Optional[Dict[str, Any]] = None):
        self.verbose = verbose
        self.use_real_params = use_real_params
        self.real_params = real_params or {}
        self.results = {}
        self.start_time = None
        
    def run_pytest_tests(self, category: Optional[str] = None) -> Tuple[bool, str]:
        """Run pytest tests for tools."""
        print("🧪 Running pytest integration tests...")
        
        cmd = ["python3", "-m", "pytest", "-v"]
        
        if category:
            # Map categories to test files
            category_map = {
                "ai": "tests/test_ai_analysis_tools.py",
                "analysis": "tests/test_static_analysis_tools.py", 
                "github": "tests/test_github_tools.py",
                "filesystem": "tests/test_filesystem_tools.py",
                "communication": "tests/test_communication_tools.py",
                "registry": "tests/test_registry.py",
                "integration": "tests/test_tools_integration.py",
                "workflow": "tests/test_workflow_integration.py"
            }
            
            if category in category_map:
                cmd.append(category_map[category])
            else:
                cmd.extend(["-m", category])
        else:
            cmd.append("tests/")
        
        cmd.extend(["--tb=short", "--color=yes"])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            if success:
                print("   ✅ Pytest tests passed!")
            else:
                print("   ❌ Some pytest tests failed!")
                if self.verbose:
                    print(f"   Output: {output}")
            
            return success, output
        except Exception as e:
            print(f"   ❌ Error running pytest: {e}")
            return False, str(e)
    
    def run_sanity_checks(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Run modular sanity checks."""
        if self.use_real_params:
            print("🔍 Running modular sanity checks with REAL PARAMETERS...")
            if self.real_params.get("github_repo"):
                print(f"   🌐 Using GitHub repo: {self.real_params['github_repo']}")
            if self.real_params.get("test_file"):
                print(f"   📄 Using test file: {self.real_params['test_file']}")
        else:
            print("🔍 Running modular sanity checks...")

        try:
            results = run_sanity_checks(
                verbose=self.verbose,
                category=category,
                use_real_params=self.use_real_params,
                real_params=self.real_params
            )

            if category:
                status = results.get("overall_status", "UNKNOWN")
                print(f"   {self._get_status_icon(status)} {category.title()} tools: {status}")

                # Show real test results if available
                if self.use_real_params and results.get("tools"):
                    for tool_name, tool_result in results["tools"].items():
                        if tool_result.get("real_test"):
                            print(f"      🌐 {tool_name}: Real test completed")
                            if tool_result.get("data"):
                                for key, value in tool_result["data"].items():
                                    print(f"         {key}: {value}")
            else:
                summary = results.get("summary", {})
                overall_status = summary.get("overall_status", "UNKNOWN")
                print(f"   {self._get_status_icon(overall_status)} Overall sanity check: {overall_status}")
                print(f"   Categories - Passed: {summary.get('passed', 0)}, "
                      f"Warnings: {summary.get('warnings', 0)}, "
                      f"Failed: {summary.get('failed', 0)}")

            return results
        except Exception as e:
            print(f"   ❌ Sanity check failed: {e}")
            return {"error": str(e), "overall_status": "FAIL"}
    
    async def run_health_checks(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Run tool health checks."""
        print("🏥 Running tool health checks...")
        
        try:
            results = await run_health_checks(verbose=self.verbose, tool_name=tool_name)
            
            if tool_name:
                result = list(results.values())[0]
                status = result.status.value
                print(f"   {self._get_status_icon(status)} {tool_name}: {status}")
                print(f"   Response time: {result.response_time:.3f}s")
                print(f"   Message: {result.message}")
            else:
                from tests.test_tool_health import ToolHealthChecker
                checker = ToolHealthChecker()
                summary = checker.get_health_summary(results)
                overall_status = summary["overall_status"]
                print(f"   {self._get_status_icon(overall_status)} Overall health: {overall_status}")
                print(f"   Tools - Healthy: {summary['healthy']}, "
                      f"Degraded: {summary['degraded']}, "
                      f"Unhealthy: {summary['unhealthy']}")
                print(f"   Average response time: {summary['average_response_time']:.3f}s")
            
            return results
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return {"error": str(e)}
    
    def validate_tool_configuration(self) -> Dict[str, Any]:
        """Validate tool configurations and dependencies."""
        print("⚙️  Validating tool configurations...")
        
        validation_results = {
            "api_keys": {},
            "dependencies": {},
            "configurations": {},
            "overall_status": "PASS"
        }
        
        # Check API keys
        api_keys = {
            "GitHub": os.getenv("GITHUB_TOKEN"),
            "Grok (X.AI)": os.getenv("XAI_API_KEY"),
            "OpenAI": os.getenv("OPENAI_API_KEY"),
            "Anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "Slack": os.getenv("SLACK_WEBHOOK_URL"),
            "Email SMTP": os.getenv("EMAIL_SMTP_SERVER"),
            "Jira": os.getenv("JIRA_URL")
        }
        
        for service, key in api_keys.items():
            validation_results["api_keys"][service] = {
                "configured": bool(key),
                "status": "CONFIGURED" if key else "MISSING"
            }
        
        # Check tool dependencies
        dependencies = {
            "pylint": self._check_command_available("pylint"),
            "flake8": self._check_command_available("flake8"),
            "bandit": self._check_command_available("bandit"),
            "git": self._check_command_available("git")
        }
        
        for dep, available in dependencies.items():
            validation_results["dependencies"][dep] = {
                "available": available,
                "status": "AVAILABLE" if available else "MISSING"
            }
        
        # Check basic configurations
        try:
            from tools.registry import ToolRegistry, ToolConfig
            config = ToolConfig()
            registry = ToolRegistry(config)
            registry_validation = registry.validate_configuration()
            
            validation_results["configurations"]["registry"] = {
                "valid": registry_validation["valid"],
                "enabled_tools": len(registry_validation["enabled_tools"]),
                "warnings": len(registry_validation["warnings"]),
                "status": "VALID" if registry_validation["valid"] else "INVALID"
            }
        except Exception as e:
            validation_results["configurations"]["registry"] = {
                "valid": False,
                "error": str(e),
                "status": "ERROR"
            }
            validation_results["overall_status"] = "FAIL"
        
        # Determine overall status
        missing_critical = any(
            not validation_results["dependencies"][dep]["available"] 
            for dep in ["git"]  # Only git is truly critical
        )
        
        if missing_critical or validation_results["overall_status"] == "FAIL":
            validation_results["overall_status"] = "FAIL"
        elif any(not dep["available"] for dep in validation_results["dependencies"].values()):
            validation_results["overall_status"] = "WARNING"
        
        # Print results
        status = validation_results["overall_status"]
        print(f"   {self._get_status_icon(status)} Configuration validation: {status}")
        
        if self.verbose:
            print("   API Keys:")
            for service, info in validation_results["api_keys"].items():
                icon = "✅" if info["configured"] else "⚠️"
                print(f"      {icon} {service}: {info['status']}")
            
            print("   Dependencies:")
            for dep, info in validation_results["dependencies"].items():
                icon = "✅" if info["available"] else "❌"
                print(f"      {icon} {dep}: {info['status']}")
        
        return validation_results
    
    def _check_command_available(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        try:
            subprocess.run([command, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _get_status_icon(self, status: str) -> str:
        """Get status icon for display."""
        status_icons = {
            "PASS": "✅", "HEALTHY": "✅", "CONFIGURED": "✅", "AVAILABLE": "✅", "VALID": "✅",
            "WARNING": "⚠️", "DEGRADED": "⚠️", "MISSING": "⚠️",
            "FAIL": "❌", "UNHEALTHY": "❌", "ERROR": "❌", "INVALID": "❌"
        }
        return status_icons.get(status.upper(), "❓")
    
    async def run_pre_workflow_validation(self) -> bool:
        """Run comprehensive pre-workflow validation."""
        print("🚀 Running Pre-Workflow Validation")
        print("=" * 60)
        
        self.start_time = time.time()
        validation_passed = True
        
        # 1. Configuration validation
        config_results = self.validate_tool_configuration()
        if config_results["overall_status"] == "FAIL":
            validation_passed = False
        
        print()
        
        # 2. Sanity checks
        sanity_results = self.run_sanity_checks()
        if sanity_results.get("summary", {}).get("overall_status") == "FAIL":
            validation_passed = False
        
        print()
        
        # 3. Health checks
        health_results = await self.run_health_checks()
        if isinstance(health_results, dict) and "error" in health_results:
            validation_passed = False
        else:
            from tests.test_tool_health import ToolHealthChecker
            checker = ToolHealthChecker()
            summary = checker.get_health_summary(health_results)
            if summary["overall_status"] == "UNHEALTHY":
                validation_passed = False
        
        print()
        
        # 4. Critical pytest tests
        pytest_success, _ = self.run_pytest_tests(category="registry")
        if not pytest_success:
            validation_passed = False
        
        # Final summary
        execution_time = time.time() - self.start_time
        print("\n" + "=" * 60)
        print("📊 Pre-Workflow Validation Summary")
        print(f"   Execution time: {execution_time:.2f}s")
        
        if validation_passed:
            print("   ✅ All validations passed - Tools are ready for workflow!")
            print("   🎉 You can safely proceed with workflow execution.")
        else:
            print("   ❌ Some validations failed - Please fix issues before workflow execution.")
            print("   🔧 Check the output above for specific issues to resolve.")
        
        return validation_passed


async def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Tool Integration Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools_integration_runner.py --sanity-check
  python tools_integration_runner.py --health-check
  python tools_integration_runner.py --category filesystem
  python tools_integration_runner.py --pre-workflow-validation
  python tools_integration_runner.py --pytest-only --category ai
  python tools_integration_runner.py --all-tests

  # Real parameter testing examples:
  python tools_integration_runner.py --sanity-check --real-world-test --github-repo https://github.com/kushal45/CustomLangGraphChatBot --test-file tools/registry.py
  python tools_integration_runner.py --category github --real-world-test --github-repo https://github.com/octocat/Hello-World
  python tools_integration_runner.py --health-check --real-world-test --github-repo https://github.com/kushal45/CustomLangGraphChatBot
        """
    )
    
    parser.add_argument("--sanity-check", action="store_true", help="Run modular sanity checks")
    parser.add_argument("--health-check", action="store_true", help="Run tool health checks")
    parser.add_argument("--pytest-only", action="store_true", help="Run only pytest tests")
    parser.add_argument("--pre-workflow-validation", action="store_true", help="Run comprehensive pre-workflow validation")
    parser.add_argument("--all-tests", action="store_true", help="Run all types of tests")
    parser.add_argument("--category", choices=["filesystem", "analysis", "ai", "github", "communication", "registry"],
                       help="Test specific category only")
    parser.add_argument("--tool", help="Check specific tool only (for health checks)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--real-world-test", action="store_true", help="Use real parameters for testing")
    parser.add_argument("--github-repo", help="Real GitHub repository URL for testing")
    parser.add_argument("--test-file", help="Real file path for testing")

    args = parser.parse_args()

    # Prepare real parameters if provided
    real_params = {}
    if args.github_repo:
        real_params["github_repo"] = args.github_repo
    if args.test_file:
        real_params["test_file"] = args.test_file

    runner = ToolIntegrationRunner(
        verbose=args.verbose,
        use_real_params=args.real_world_test,
        real_params=real_params if real_params else None
    )
    success = True
    
    if args.pre_workflow_validation:
        success = await runner.run_pre_workflow_validation()
    elif args.all_tests:
        print("🚀 Running All Tool Integration Tests")
        print("=" * 50)
        
        # Run all test types
        config_results = runner.validate_tool_configuration()
        sanity_results = runner.run_sanity_checks(category=args.category)
        health_results = await runner.run_health_checks(tool_name=args.tool)
        pytest_success, _ = runner.run_pytest_tests(category=args.category)
        
        # Determine overall success
        success = (
            config_results.get("overall_status") != "FAIL" and
            sanity_results.get("summary", {}).get("overall_status") != "FAIL" and
            "error" not in health_results and
            pytest_success
        )
    elif args.sanity_check:
        sanity_results = runner.run_sanity_checks(category=args.category)
        success = sanity_results.get("summary", {}).get("overall_status") != "FAIL"
    elif args.health_check:
        health_results = await runner.run_health_checks(tool_name=args.tool)
        success = "error" not in health_results
    elif args.pytest_only:
        success, _ = runner.run_pytest_tests(category=args.category)
    else:
        # Default: run pre-workflow validation
        success = await runner.run_pre_workflow_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
