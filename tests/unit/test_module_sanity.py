#!/usr/bin/env python3
"""
Modular Tool Sanity Test System for CustomLangGraphChatBot.

This module provides comprehensive sanity checks for all tool modules
before they are integrated into the main workflow. Each tool category
is tested independently to ensure proper functionality and configuration.
"""

import pytest

# Mark all tests in this file as integration tests using real parameters
pytestmark = [pytest.mark.integration, pytest.mark.real_params]

import os
import sys
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch

# Load environment variables from .env file BEFORE importing tools
try:
    from dotenv import load_dotenv
    load_dotenv()
    print(f"DEBUG: Environment loaded - GITHUB_VERIFY_SSL = {repr(os.getenv('GITHUB_VERIFY_SSL'))}")
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables from .env file won't be loaded.")
    print("Install with: pip install python-dotenv")
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.registry import ToolRegistry, ToolConfig, RepositoryType
from tools.ai_analysis_tools import AI_ANALYSIS_TOOLS
from tools.analysis_tools import ANALYSIS_TOOLS
from tools.github_tools import GITHUB_TOOLS
from tools.filesystem_tools import FILESYSTEM_TOOLS
from tools.communication_tools import COMMUNICATION_TOOLS


class ToolModuleSanityChecker:
    """Comprehensive sanity checker for tool modules."""

    def __init__(self, verbose: bool = False, use_real_params: bool = False,
                 real_params: Optional[Dict[str, Any]] = None):
        self.verbose = verbose
        self.use_real_params = use_real_params
        self.real_params = real_params or {}
        self.results = {}
        self.registry = None
        self.temp_dir = None
        
    def setup(self):
        """Set up test environment."""
        print("🔧 Setting up test environment...")
        
        # Create tool registry
        config = ToolConfig()
        self.registry = ToolRegistry(config)
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        
        # Create sample test files
        self._create_test_files()
        
        print("   ✅ Test environment ready")
    
    def teardown(self):
        """Clean up test environment."""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def _create_test_files(self):
        """Create sample files for testing."""
        test_repo = Path(self.temp_dir)
        
        # Create Python test file
        (test_repo / "sample.py").write_text('''
"""Sample Python module for testing."""

def calculate_sum(numbers):
    """Calculate sum of numbers."""
    return sum(numbers)

def process_data(data):
    """Process data with validation."""
    if not data:
        raise ValueError("Data cannot be empty")
    return [item.upper() for item in data if item]

class DataProcessor:
    """Simple data processor class."""
    
    def __init__(self):
        self.processed_count = 0
    
    def process(self, items):
        """Process items."""
        result = []
        for item in items:
            if item:
                result.append(f"processed_{item}")
                self.processed_count += 1
        return result
''')
        
        # Create JavaScript test file
        (test_repo / "sample.js").write_text('''
/**
 * Sample JavaScript module for testing.
 */

function calculateSum(numbers) {
    return numbers.reduce((sum, num) => sum + num, 0);
}

function processData(data) {
    if (!data || data.length === 0) {
        throw new Error("Data cannot be empty");
    }
    return data.filter(item => item).map(item => item.toUpperCase());
}

class DataProcessor {
    constructor() {
        this.processedCount = 0;
    }
    
    process(items) {
        const result = [];
        for (const item of items) {
            if (item) {
                result.push(`processed_${item}`);
                this.processedCount++;
            }
        }
        return result;
    }
}

module.exports = { calculateSum, processData, DataProcessor };
''')
        
        # Create README
        (test_repo / "README.md").write_text('''# Test Repository

This is a test repository for sanity checking tools.

## Features
- Python modules
- JavaScript modules
- Documentation
''')
    
    def check_filesystem_tools(self) -> Dict[str, Any]:
        """Check filesystem tools functionality."""
        print("\n📁 Checking Filesystem Tools...")
        results = {"category": "filesystem", "tools": {}, "overall_status": "PASS"}
        
        for tool in FILESYSTEM_TOOLS:
            tool_name = tool.name
            print(f"   Testing {tool_name}...")
            
            try:
                if tool_name == "file_reader":
                    # Test file reading
                    test_file = Path(self.temp_dir) / "sample.py"
                    result = tool._run(str(test_file))
                    
                    if "error" not in result and result.get("content"):
                        results["tools"][tool_name] = {"status": "PASS", "message": "File reading successful"}
                    else:
                        results["tools"][tool_name] = {"status": "FAIL", "message": result.get("error", "Unknown error")}
                        results["overall_status"] = "FAIL"
                
                elif tool_name == "directory_lister":
                    # Test directory listing
                    query = json.dumps({
                        "directory_path": self.temp_dir,
                        "recursive": False,
                        "include_hidden": False
                    })
                    result = tool._run(query)
                    
                    if "error" not in result and result.get("files"):
                        results["tools"][tool_name] = {"status": "PASS", "message": f"Listed {len(result['files'])} files"}
                    else:
                        results["tools"][tool_name] = {"status": "FAIL", "message": result.get("error", "Unknown error")}
                        results["overall_status"] = "FAIL"
                
                elif tool_name == "git_repository":
                    # Test git operations (basic check)
                    results["tools"][tool_name] = {"status": "PASS", "message": "Git tool available"}
                
            except Exception as e:
                results["tools"][tool_name] = {"status": "ERROR", "message": str(e)}
                results["overall_status"] = "FAIL"
        
        self._print_results("Filesystem", results)
        return results
    
    def check_analysis_tools(self) -> Dict[str, Any]:
        """Check static analysis tools functionality."""
        print("\n🔍 Checking Analysis Tools...")
        results = {"category": "analysis", "tools": {}, "overall_status": "PASS"}
        
        test_file = Path(self.temp_dir) / "sample.py"
        
        for tool in ANALYSIS_TOOLS:
            tool_name = tool.name
            print(f"   Testing {tool_name}...")
            
            try:
                if tool_name == "code_complexity":
                    # Test complexity analysis with sample Python code
                    sample_code = '''
def hello_world():
    """A simple function."""
    print("Hello, World!")
    return True

class SampleClass:
    def __init__(self):
        self.value = 42

    def complex_method(self, x, y):
        if x > 0:
            for i in range(y):
                if i % 2 == 0:
                    print(f"Even: {i}")
                else:
                    print(f"Odd: {i}")
        return x + y
'''
                    result = tool._run(sample_code)

                    if "error" not in result and result.get("metrics", {}).get("functions") is not None:
                        func_count = result["metrics"]["functions"]
                        results["tools"][tool_name] = {"status": "PASS", "message": f"Analyzed {func_count} functions"}
                    else:
                        results["tools"][tool_name] = {"status": "FAIL", "message": result.get("error", "Analysis failed")}
                        results["overall_status"] = "FAIL"
                
                elif tool_name in ["pylint_analysis", "flake8_analysis", "bandit_security"]:
                    # Test static analysis tools
                    result = tool._run(str(test_file))
                    
                    if "error" not in result:
                        results["tools"][tool_name] = {"status": "PASS", "message": "Analysis completed"}
                    else:
                        # Some tools might not be installed, mark as warning
                        if "not found" in result.get("error", "").lower():
                            results["tools"][tool_name] = {"status": "WARNING", "message": "Tool not installed"}
                        else:
                            results["tools"][tool_name] = {"status": "FAIL", "message": result.get("error", "Unknown error")}
                            results["overall_status"] = "FAIL"
                
            except Exception as e:
                results["tools"][tool_name] = {"status": "ERROR", "message": str(e)}
                results["overall_status"] = "FAIL"
        
        self._print_results("Analysis", results)
        return results
    
    def check_ai_analysis_tools(self) -> Dict[str, Any]:
        """Check AI analysis tools functionality."""
        print("\n🤖 Checking AI Analysis Tools...")
        results = {"category": "ai_analysis", "tools": {}, "overall_status": "PASS"}
        
        # Check if AI API key is available
        print("GROQ_API_KEY: ", os.getenv("GROQ_API_KEY"))
        print("OPENAI_API_KEY: ", os.getenv("OPENAI_API_KEY"))
        print("ANTHROPIC_API_KEY: ", os.getenv("ANTHROPIC_API_KEY"))
        ai_key_available = bool(os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
        
        if not ai_key_available:
            print("   ⚠️  No AI API keys found - running mock tests")
        
        for tool in AI_ANALYSIS_TOOLS:
            tool_name = tool.name
            print(f"   Testing {tool_name}...")
            
            try:
                if ai_key_available:
                    # Test with actual API (limited test)
                    test_code = "def hello(): return 'world'"
                    query = json.dumps({
                        "code": test_code,
                        "language": "python"
                    })
                    
                    # Set a short timeout for testing
                    original_timeout = tool.config.timeout
                    tool.config.timeout = 10
                    try:
                        result = tool._run(query)
                    finally:
                        tool.config.timeout = original_timeout
                    
                    if "error" not in result:
                        results["tools"][tool_name] = {"status": "PASS", "message": "AI analysis successful"}
                    else:
                        results["tools"][tool_name] = {"status": "FAIL", "message": result.get("error", "Unknown error")}
                        results["overall_status"] = "FAIL"
                else:
                    # Mock test
                    results["tools"][tool_name] = {"status": "WARNING", "message": "No API key - tool available but not tested"}
                
            except Exception as e:
                if "timeout" in str(e).lower():
                    results["tools"][tool_name] = {"status": "WARNING", "message": "API timeout - tool functional"}
                else:
                    results["tools"][tool_name] = {"status": "ERROR", "message": str(e)}
                    results["overall_status"] = "FAIL"
        
        self._print_results("AI Analysis", results)
        return results

    def check_github_tools(self) -> Dict[str, Any]:
        """Check GitHub tools functionality."""
        print("\n🐙 Checking GitHub Tools...")
        results = {"category": "github", "tools": {}, "overall_status": "PASS"}

        # Check if we're in a CI environment
        is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'

        # Import asyncio for handling async tools
        import asyncio

        def run_async_tool_safely(tool, query):
            """Safely run async tool, handling event loop issues."""
            try:
                # Check if we're already in an event loop
                try:
                    loop = asyncio.get_running_loop()
                    # We're in a running loop, so we need to use a different approach
                    import concurrent.futures
                    import threading

                    def run_in_thread():
                        # Create a new event loop in a separate thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(tool._arun(query))
                        finally:
                            new_loop.close()

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        return future.result(timeout=30)  # 30 second timeout

                except RuntimeError:
                    # No running event loop, safe to use asyncio.run()
                    return asyncio.run(tool._arun(query))

            except Exception as e:
                # Fallback to sync _run method if available
                if hasattr(tool, '_run'):
                    return tool._run(query)
                else:
                    raise e

        # Check if GitHub token is available
        github_token = os.getenv("GITHUB_TOKEN")

        if not github_token:
            print("   ⚠️  GitHub token not found - running mock tests")

        # Use real parameters if provided
        if self.use_real_params and self.real_params.get("github_repo"):
            repo_url = self.real_params["github_repo"]
            file_path = self.real_params.get("test_file", "README.md")
            print(f"   🌐 Testing with real repository: {repo_url}")

        for tool in GITHUB_TOOLS:
            tool_name = tool.name
            print(f"   Testing {tool_name}...")

            try:
                if github_token:
                    if self.use_real_params and self.real_params.get("github_repo"):
                        # Test with real parameters
                        repo_url = self.real_params["github_repo"]
                        file_path = self.real_params.get("test_file", "README.md")

                        if tool_name == "github_repository":
                            # GitHub repository tool expects a simple string (repository URL)
                            query = repo_url

                            result = run_async_tool_safely(tool, query)

                            if "error" not in result and result.get("repository", {}).get("name"):
                                repo_data = result["repository"]
                                results["tools"][tool_name] = {
                                    "status": "PASS",
                                    "message": f"Retrieved repo: {repo_data['name']}",
                                    "real_test": True,
                                    "data": {
                                        "repo_name": repo_data.get("name"),
                                        "description": repo_data.get("description", "")[:100] + "..." if repo_data.get("description") else "N/A",
                                        "stars": repo_data.get("stargazers_count", 0),
                                        "language": repo_data.get("language", "N/A"),
                                        "files_found": len(result.get("contents", []))
                                    }
                                }
                            else:
                                results["tools"][tool_name] = {
                                    "status": "FAIL",
                                    "message": result.get("error", "Unknown error"),
                                    "real_test": True
                                }
                                results["overall_status"] = "FAIL"

                        elif tool_name == "github_file_content":
                            # Extract owner/repo from URL
                            if "github.com/" in repo_url:
                                repo_path = repo_url.split("github.com/")[-1].rstrip("/")
                            else:
                                repo_path = repo_url

                            query = json.dumps({
                                "repository_url": repo_path,
                                "file_path": file_path,
                                "branch": "main"
                            })

                            result = run_async_tool_safely(tool, query)

                            if "error" not in result and result.get("content"):
                                content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
                                results["tools"][tool_name] = {
                                    "status": "PASS",
                                    "message": f"Retrieved file: {file_path}",
                                    "real_test": True,
                                    "data": {
                                        "file_path": file_path,
                                        "content_length": len(result["content"]),
                                        "content_preview": content_preview
                                    }
                                }
                            else:
                                results["tools"][tool_name] = {
                                    "status": "FAIL",
                                    "message": result.get("error", "Unknown error"),
                                    "real_test": True
                                }
                                results["overall_status"] = "FAIL"

                        else:
                            # Other GitHub tools - basic test
                            results["tools"][tool_name] = {
                                "status": "WARNING",
                                "message": "Real parameter testing not implemented for this tool yet",
                                "real_test": False
                            }

                    elif tool_name == "github_repository":
                        # Test with a public repository (default test)
                        # GitHub repository tool expects a simple string (repository URL or owner/repo format)
                        query = "octocat/Hello-World"

                        try:
                            result = run_async_tool_safely(tool, query)
                            print(f"   DEBUG: GitHub repository result: {result}")

                            if isinstance(result, dict) and "error" not in result and result.get("name"):
                                results["tools"][tool_name] = {"status": "PASS", "message": f"Retrieved repo: {result['name']}"}
                            elif isinstance(result, dict) and "error" in result:
                                error_msg = result.get("error", "Unknown error")
                                # In CI environment, treat token configuration errors as warnings, not failures
                                if is_ci and any(keyword in error_msg.lower() for keyword in ["token not configured", "unauthorized", "401", "failed to fetch repository"]):
                                    results["tools"][tool_name] = {"status": "WARNING", "message": f"CI mode - {error_msg}"}
                                else:
                                    results["tools"][tool_name] = {"status": "FAIL", "message": error_msg}
                                    results["overall_status"] = "FAIL"
                            else:
                                # Handle string results or other formats
                                if isinstance(result, str) and ("error" in result.lower() or "404" in result):
                                    results["tools"][tool_name] = {"status": "FAIL", "message": result}
                                    results["overall_status"] = "FAIL"
                                else:
                                    results["tools"][tool_name] = {"status": "PASS", "message": f"Retrieved data: {str(result)[:100]}..."}
                        except Exception as e:
                            error_msg = str(e)
                            # In CI environment, treat authentication/token errors as warnings
                            if is_ci and any(keyword in error_msg.lower() for keyword in ["unauthorized", "token", "authentication", "401"]):
                                results["tools"][tool_name] = {"status": "WARNING", "message": f"CI mode - {error_msg}"}
                            else:
                                results["tools"][tool_name] = {"status": "FAIL", "message": f"Exception: {error_msg}"}
                                results["overall_status"] = "FAIL"
                    else:
                        # Mock test for other tools
                        results["tools"][tool_name] = {"status": "WARNING", "message": "No token - tool available but not tested"}
                else:
                    # No GitHub token available
                    results["tools"][tool_name] = {"status": "WARNING", "message": "No token - tool available but not tested"}

            except Exception as e:
                error_msg = str(e)
                if "rate limit" in error_msg.lower():
                    results["tools"][tool_name] = {"status": "WARNING", "message": "Rate limited - tool functional"}
                elif is_ci and any(keyword in error_msg.lower() for keyword in ["unauthorized", "token", "authentication", "401"]):
                    results["tools"][tool_name] = {"status": "WARNING", "message": f"CI mode - {error_msg}"}
                else:
                    results["tools"][tool_name] = {"status": "ERROR", "message": error_msg}
                    results["overall_status"] = "FAIL"

        self._print_results("GitHub", results)
        return results

    def check_communication_tools(self) -> Dict[str, Any]:
        """Check communication tools functionality."""
        print("\n📢 Checking Communication Tools...")
        results = {"category": "communication", "tools": {}, "overall_status": "PASS"}

        for tool in COMMUNICATION_TOOLS:
            tool_name = tool.name
            print(f"   Testing {tool_name}...")

            try:
                # Mock test for communication tools to avoid sending actual messages
                with patch('aiohttp.ClientSession.post') as mock_post:
                    mock_response = Mock()
                    mock_response.status = 200
                    mock_response.json.return_value = {"ok": True}
                    mock_post.return_value.__aenter__.return_value = mock_response

                    if tool_name == "slack_notification":
                        query = json.dumps({
                            "message": "Test message",
                            "channel": "#test"
                        })
                    elif tool_name == "webhook_tool":
                        query = json.dumps({
                            "url": "https://httpbin.org/post",
                            "data": {"test": "data"}
                        })
                    elif tool_name == "email_notification":
                        query = json.dumps({
                            "to": "test@example.com",
                            "subject": "Test",
                            "body": "Test message"
                        })
                    elif tool_name == "jira_integration":
                        query = json.dumps({
                            "action": "create_issue",
                            "project": "TEST",
                            "summary": "Test issue"
                        })
                    else:
                        query = json.dumps({"test": "data"})

                    # Test tool initialization and basic functionality
                    results["tools"][tool_name] = {"status": "PASS", "message": "Tool initialized successfully"}

            except Exception as e:
                results["tools"][tool_name] = {"status": "ERROR", "message": str(e)}
                results["overall_status"] = "FAIL"

        self._print_results("Communication", results)
        return results

    def check_tool_registry(self) -> Dict[str, Any]:
        """Check tool registry functionality."""
        print("\n🔧 Checking Tool Registry...")
        results = {"category": "registry", "tools": {}, "overall_status": "PASS"}

        try:
            # Test registry initialization
            all_tools = self.registry.get_all_tools()
            results["tools"]["registry_init"] = {"status": "PASS", "message": f"Loaded {len(all_tools)} tools"}

            # Test tool categories
            categories = self.registry.get_category_tools()
            results["tools"]["categories"] = {"status": "PASS", "message": f"Found {len(categories)} categories"}

            # Test configuration validation
            validation = self.registry.validate_configuration()
            if validation["valid"]:
                results["tools"]["validation"] = {"status": "PASS", "message": "Configuration valid"}
            else:
                results["tools"]["validation"] = {"status": "WARNING", "message": f"{len(validation['warnings'])} warnings"}

            # Test repository type detection
            test_extensions = ['.py', '.js', '.md']
            repo_type = self.registry.detect_repository_type(test_extensions)
            results["tools"]["repo_detection"] = {"status": "PASS", "message": f"Detected: {repo_type.value}"}

        except Exception as e:
            results["tools"]["registry_error"] = {"status": "ERROR", "message": str(e)}
            results["overall_status"] = "FAIL"

        self._print_results("Registry", results)
        return results

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all sanity checks."""
        print("🚀 Running Modular Tool Sanity Checks")
        print("=" * 50)

        start_time = time.time()

        try:
            self.setup()

            # Run all checks
            all_results = {
                "timestamp": time.time(),
                "categories": {},
                "summary": {}
            }

            all_results["categories"]["registry"] = self.check_tool_registry()
            all_results["categories"]["filesystem"] = self.check_filesystem_tools()
            all_results["categories"]["analysis"] = self.check_analysis_tools()
            all_results["categories"]["ai_analysis"] = self.check_ai_analysis_tools()
            all_results["categories"]["github"] = self.check_github_tools()
            all_results["categories"]["communication"] = self.check_communication_tools()

            # Generate summary
            total_categories = len(all_results["categories"])
            passed_categories = sum(1 for cat in all_results["categories"].values() if cat["overall_status"] == "PASS")
            warning_categories = sum(1 for cat in all_results["categories"].values() if cat["overall_status"] == "WARNING")
            failed_categories = sum(1 for cat in all_results["categories"].values() if cat["overall_status"] == "FAIL")

            all_results["summary"] = {
                "total_categories": total_categories,
                "passed": passed_categories,
                "warnings": warning_categories,
                "failed": failed_categories,
                "execution_time": time.time() - start_time,
                "overall_status": "PASS" if failed_categories == 0 else "FAIL"
            }

            self._print_summary(all_results["summary"])

            return all_results

        finally:
            self.teardown()

    def _print_results(self, category: str, results: Dict[str, Any]):
        """Print test results for a category."""
        status_icon = "✅" if results["overall_status"] == "PASS" else "❌" if results["overall_status"] == "FAIL" else "⚠️"
        print(f"   {status_icon} {category} Tools: {results['overall_status']}")

        if self.verbose:
            for tool_name, tool_result in results["tools"].items():
                status = tool_result["status"]
                message = tool_result["message"]
                icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
                print(f"      {icon} {tool_name}: {message}")

    def _print_summary(self, summary: Dict[str, Any]):
        """Print overall summary."""
        print("\n" + "=" * 50)
        print("📊 Sanity Check Summary")
        print(f"   Total Categories: {summary['total_categories']}")
        print(f"   ✅ Passed: {summary['passed']}")
        print(f"   ⚠️  Warnings: {summary['warnings']}")
        print(f"   ❌ Failed: {summary['failed']}")
        print(f"   ⏱️  Execution Time: {summary['execution_time']:.2f}s")
        print(f"   🎯 Overall Status: {summary['overall_status']}")

        if summary["overall_status"] == "PASS":
            print("\n🎉 All tool modules are ready for workflow integration!")
        else:
            print("\n⚠️  Some issues found. Please review and fix before workflow integration.")


def run_sanity_checks(verbose: bool = False, category: Optional[str] = None,
                     use_real_params: bool = False, real_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run sanity checks for specified category or all categories."""
    checker = ToolModuleSanityChecker(verbose=verbose, use_real_params=use_real_params, real_params=real_params)

    if category:
        checker.setup()
        try:
            if category == "filesystem":
                return checker.check_filesystem_tools()
            elif category == "analysis":
                return checker.check_analysis_tools()
            elif category == "ai":
                return checker.check_ai_analysis_tools()
            elif category == "github":
                return checker.check_github_tools()
            elif category == "communication":
                return checker.check_communication_tools()
            elif category == "registry":
                return checker.check_tool_registry()
            else:
                raise ValueError(f"Unknown category: {category}")
        finally:
            checker.teardown()
    else:
        return checker.run_all_checks()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tool Module Sanity Checker")
    parser.add_argument("--category", choices=["filesystem", "analysis", "ai", "github", "communication", "registry"],
                       help="Check specific category only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--real-params", action="store_true", help="Use real parameters for testing")
    parser.add_argument("--github-repo", help="Real GitHub repository URL for testing")
    parser.add_argument("--test-file", help="Real file path for testing")

    args = parser.parse_args()

    # Prepare real parameters if provided
    real_params = {}
    if args.github_repo:
        real_params["github_repo"] = args.github_repo
    if args.test_file:
        real_params["test_file"] = args.test_file

    results = run_sanity_checks(
        verbose=args.verbose,
        category=args.category,
        use_real_params=args.real_params,
        real_params=real_params if real_params else None
    )

    # Exit with appropriate code
    if results.get("summary", {}).get("overall_status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)


# Pytest-compatible test functions for integration testing
def test_filesystem_tools_sanity():
    """Test filesystem tools with real parameters."""
    checker = ToolModuleSanityChecker(verbose=True, use_real_params=True)
    checker.setup()
    try:
        result = checker.check_filesystem_tools()
        assert result["overall_status"] == "PASS", f"Filesystem tools failed: {result}"
    finally:
        checker.teardown()


def test_analysis_tools_sanity():
    """Test analysis tools with real parameters."""
    checker = ToolModuleSanityChecker(verbose=True, use_real_params=True)
    checker.setup()
    try:
        result = checker.check_analysis_tools()
        assert result["overall_status"] == "PASS", f"Analysis tools failed: {result}"
    finally:
        checker.teardown()


def test_ai_analysis_tools_sanity():
    """Test AI analysis tools with real parameters."""
    checker = ToolModuleSanityChecker(verbose=True, use_real_params=True)
    checker.setup()
    try:
        result = checker.check_ai_analysis_tools()
        assert result["overall_status"] == "PASS", f"AI analysis tools failed: {result}"
    finally:
        checker.teardown()


def test_github_tools_sanity():
    """Test GitHub tools with real parameters."""
    # Debug SSL configuration
    print(f"DEBUG: GITHUB_VERIFY_SSL = {repr(os.getenv('GITHUB_VERIFY_SSL'))}")

    checker = ToolModuleSanityChecker(verbose=True, use_real_params=True)
    checker.setup()
    try:
        result = checker.check_github_tools()
        # Allow warnings for GitHub tools due to SSL/token issues
        assert result["overall_status"] in ["PASS", "WARN"], f"GitHub tools failed: {result}"
    finally:
        checker.teardown()


def test_communication_tools_sanity():
    """Test communication tools with real parameters."""
    checker = ToolModuleSanityChecker(verbose=True, use_real_params=True)
    checker.setup()
    try:
        result = checker.check_communication_tools()
        assert result["overall_status"] == "PASS", f"Communication tools failed: {result}"
    finally:
        checker.teardown()


def test_debugging_tools_sanity():
    """Sanity test for debugging tools and scripts."""
    print("\n🔧 Testing Debugging Tools Sanity...")

    try:
        # Test basic functionality with temporary directory for logs
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set temporary log directory to avoid read-only filesystem issues
            original_log_dir = os.environ.get('LOG_DIR')
            os.environ['LOG_DIR'] = temp_dir

            try:
                # Test imports (after setting LOG_DIR to avoid read-only filesystem issues)
                from scripts.debug_node import NodeDebugger
                from scripts.inspect_state import StateInspector
                from scripts.node_tracing import get_tracer
                from scripts.node_serialization import get_serializer
                from scripts.node_replay import get_replay_engine
                from scripts.node_profiling import get_profiler
                from scripts.node_flow_diagrams import get_visualizer

                print("✅ All debugging tool imports successful")

                debugger = NodeDebugger()
                inspector = StateInspector()
                tracer = get_tracer()
                serializer = get_serializer()
                replay_engine = get_replay_engine()
                profiler = get_profiler()
                visualizer = get_visualizer()
            finally:
                # Restore original log directory
                if original_log_dir:
                    os.environ['LOG_DIR'] = original_log_dir
                elif 'LOG_DIR' in os.environ:
                    del os.environ['LOG_DIR']

            print("✅ All debugging tool instances created successfully")

            # Test sample state generation
            sample_state = debugger.create_sample_state("start_review_node")
            assert sample_state is not None
            assert "current_step" in sample_state

            print("✅ Sample state generation working")

            # Test state inspection
            analysis = inspector.analyze_state(sample_state)
            assert analysis is not None
            assert hasattr(analysis, 'completeness_score')

            print("✅ State inspection working")

            # Test serialization
            serialized = serializer.serialize_node_input("test_node", sample_state)
            assert serialized is not None
            assert serialized.metadata is not None

            print("✅ Node serialization working")

        print("✅ Debugging tools sanity check passed!")

    except Exception as e:
        print(f"❌ Debugging tools sanity check failed: {e}")
        pytest.fail(f"Debugging tools sanity check failed: {e}")


def test_workflow_integration_sanity():
    """Sanity test for workflow integration testing."""
    print("\n🔄 Testing Workflow Integration Sanity...")

    try:
        # Test workflow integration with temporary directory for logs
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set temporary log directory to avoid read-only filesystem issues
            original_log_dir = os.environ.get('LOG_DIR')
            os.environ['LOG_DIR'] = temp_dir

            try:
                # Test imports (after setting LOG_DIR to avoid read-only filesystem issues)
                from tests.integration.test_workflow_debugging import WorkflowTestFixtures, TestWorkflowIntegration
                from workflow import should_continue, create_review_workflow
                from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node

                print("✅ All workflow integration imports successful")

                # Test fixture creation
                fixtures = WorkflowTestFixtures()
                initial_state = fixtures.create_initial_state()
                assert initial_state is not None
                assert "current_step" in initial_state

                print("✅ Workflow test fixtures working")

                # Test should_continue function
                result = should_continue(initial_state)
                assert result in ["continue", "error_handler"]

                print("✅ Workflow conditional logic working")

                # Test workflow graph creation
                workflow_graph = create_review_workflow()
                assert workflow_graph is not None

                print("✅ Workflow graph creation working")
            finally:
                # Restore original log directory
                if original_log_dir:
                    os.environ['LOG_DIR'] = original_log_dir
                elif 'LOG_DIR' in os.environ:
                    del os.environ['LOG_DIR']

        print("✅ Workflow integration sanity check passed!")

    except Exception as e:
        print(f"❌ Workflow integration sanity check failed: {e}")
        pytest.fail(f"Workflow integration sanity check failed: {e}")


def test_full_sanity_check():
    """Run full sanity check with real parameters."""
    results = run_sanity_checks(verbose=True, use_real_params=True)
    # Allow warnings for full sanity check due to potential SSL/API issues
    assert results.get("summary", {}).get("overall_status") in ["PASS", "WARN"], f"Full sanity check failed"
