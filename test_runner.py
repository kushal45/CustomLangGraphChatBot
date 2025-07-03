#!/usr/bin/env python3
"""
Enhanced test runner for CustomLangGraphChatBot external tools system.

This script provides multiple ways to test the tools:
1. Comprehensive pytest test suite with coverage
2. Manual integration tests
3. Individual tool testing
4. End-to-end workflow simulation
5. Performance benchmarking
6. CI/CD integration support
"""

import os
import sys
import json
import tempfile
import subprocess
import time
import argparse
import pytest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.registry import ToolRegistry, ToolConfig, RepositoryType


class TestRunner:
    """Enhanced test runner with pytest integration and reporting."""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def run_pytest_tests(self, category: Optional[str] = None, coverage: bool = True,
                        verbose: bool = True) -> Tuple[bool, str]:
        """Run pytest tests with optional category filtering and coverage."""
        print(f"🧪 Running pytest tests{f' for category: {category}' if category else ''}...")

        cmd = ["python", "-m", "pytest"]

        if category:
            # Map categories to test files
            category_map = {
                "ai": "tests/test_ai_analysis_tools.py",
                "analysis": "tests/test_static_analysis_tools.py",
                "github": "tests/test_github_tools.py",
                "filesystem": "tests/test_filesystem_tools.py",
                "communication": "tests/test_communication_tools.py",
                "registry": "tests/test_registry.py",
                "integration": "tests/test_workflow_integration.py",
                "performance": "tests/test_performance.py",
                "error": "tests/test_error_handling.py",
                "api": "tests/test_api_integration.py"
            }

            if category in category_map:
                cmd.append(category_map[category])
            else:
                cmd.extend(["-m", category])
        else:
            cmd.append("tests/")

        if verbose:
            cmd.append("-v")

        if coverage:
            cmd.extend([
                "--cov=src",
                "--cov=tools",
                "--cov-report=term",
                "--cov-report=html:htmlcov"
            ])

        cmd.extend(["--tb=short", "--color=yes"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            success = result.returncode == 0
            output = result.stdout + result.stderr

            if success:
                print("   ✅ All pytest tests passed!")
            else:
                print("   ❌ Some pytest tests failed!")
                print(f"   Output: {output}")

            return success, output
        except Exception as e:
            print(f"   ❌ Error running pytest: {e}")
            return False, str(e)

    def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmarks."""
        print("⚡ Running performance benchmarks...")

        cmd = [
            "python", "-m", "pytest",
            "tests/test_performance.py",
            "-v", "-s", "--durations=10"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            success = result.returncode == 0

            benchmark_results = {
                "success": success,
                "output": result.stdout + result.stderr,
                "execution_time": "See output for detailed timings"
            }

            if success:
                print("   ✅ Performance benchmarks completed!")
            else:
                print("   ⚠️  Some performance tests had issues")

            return benchmark_results
        except Exception as e:
            print(f"   ❌ Error running performance tests: {e}")
            return {"success": False, "error": str(e)}

    def generate_coverage_report(self) -> bool:
        """Generate detailed coverage report."""
        print("📊 Generating coverage report...")

        cmd = [
            "python", "-m", "pytest",
            "--cov=src", "--cov=tools",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            "tests/"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            success = result.returncode == 0

            if success:
                print("   ✅ Coverage report generated!")
                print("   📁 HTML report: htmlcov/index.html")
                print("   📁 XML report: coverage.xml")
            else:
                print("   ❌ Error generating coverage report")
                print(f"   Output: {result.stdout + result.stderr}")

            return success
        except Exception as e:
            print(f"   ❌ Error generating coverage: {e}")
            return False


def test_tool_registry():
    """Test the tool registry system."""
    print("🔧 Testing Tool Registry...")
    
    config = ToolConfig()
    registry = ToolRegistry(config)
    
    # Test basic functionality
    all_tools = registry.get_all_tools()
    print(f"   ✓ Loaded {len(all_tools)} tools")
    
    # Test tool categories
    categories = registry.get_category_tools()
    for category, tools in categories.items():
        print(f"   ✓ {category}: {len(tools)} tools")
    
    # Test configuration validation
    validation = registry.validate_configuration()
    print(f"   ✓ Configuration valid: {validation['valid']}")
    print(f"   ✓ Enabled tools: {len(validation['enabled_tools'])}")
    print(f"   ✓ Warnings: {len(validation['warnings'])}")
    
    if validation['warnings']:
        print("   ⚠️  Configuration warnings:")
        for warning in validation['warnings']:
            print(f"      - {warning}")
    
    return registry


@pytest.fixture
def registry():
    """Create a ToolRegistry instance for testing."""
    return ToolRegistry()


@pytest.fixture
def test_repo_path(tmp_path):
    """Create a temporary test repository path."""
    return str(tmp_path)


def test_filesystem_tools(registry: ToolRegistry):
    """Test file system tools with a temporary repository."""
    print("\n📁 Testing File System Tools...")
    
    # Create a temporary test repository
    with tempfile.TemporaryDirectory() as temp_dir:
        test_repo = Path(temp_dir)
        
        # Create test files
        (test_repo / "main.py").write_text('''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "success"

def calculate(a, b):
    """Calculate sum with validation."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("Arguments must be numbers")
    return a + b

if __name__ == "__main__":
    hello_world()
    result = calculate(5, 3)
    print(f"5 + 3 = {result}")
''')
        
        (test_repo / "utils.py").write_text('''
import os
import json

def read_file(filepath):
    """Read file contents safely."""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def save_json(data, filepath):
    """Save data as JSON."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
''')
        
        (test_repo / "README.md").write_text("# Test Repository\n\nThis is a test repository.")
        
        # Test directory listing
        dir_tool = registry.get_tool("directory_lister")
        if dir_tool:
            query = json.dumps({
                "directory_path": str(test_repo),
                "recursive": False,
                "include_hidden": False
            })
            result = dir_tool._run(query)
            
            if "error" not in result:
                print(f"   ✓ Directory listing: {result['total_files']} files, {result['total_directories']} directories")
                for file_info in result['files']:
                    print(f"      - {file_info['name']} ({file_info['size']} bytes)")
            else:
                print(f"   ❌ Directory listing failed: {result['error']}")
        
        # Test file reading
        file_tool = registry.get_tool("file_reader")
        if file_tool:
            result = file_tool._run(str(test_repo / "main.py"))
            
            if "error" not in result:
                print(f"   ✓ File reading: {result['name']} ({result['lines']} lines)")
            else:
                print(f"   ❌ File reading failed: {result['error']}")
        
        return str(test_repo)


def test_static_analysis_tools(registry: ToolRegistry, test_repo_path: str):
    """Test static analysis tools."""
    print("\n🔍 Testing Static Analysis Tools...")
    
    main_py_path = Path(test_repo_path) / "main.py"
    
    # Test complexity analysis
    complexity_tool = registry.get_tool("code_complexity")
    if complexity_tool:
        result = complexity_tool._run(str(main_py_path))
        
        if "error" not in result:
            print(f"   ✓ Complexity analysis: {len(result['functions'])} functions analyzed")
            for func in result['functions']:
                print(f"      - {func['name']}: complexity {func['complexity']}")
        else:
            print(f"   ❌ Complexity analysis failed: {result['error']}")
    
    # Test Pylint (if available)
    pylint_tool = registry.get_tool("pylint_analysis")
    if pylint_tool and registry.is_tool_enabled("pylint_analysis"):
        result = pylint_tool._run(str(main_py_path))
        
        if "error" not in result:
            print(f"   ✓ Pylint analysis: score {result.get('score', 'N/A')}")
            if result.get('issues'):
                print(f"      - Found {len(result['issues'])} issues")
        else:
            print(f"   ⚠️  Pylint analysis: {result['error']}")
    else:
        print("   ⚠️  Pylint tool not available or not enabled")
    
    # Test Flake8 (if available)
    flake8_tool = registry.get_tool("flake8_analysis")
    if flake8_tool and registry.is_tool_enabled("flake8_analysis"):
        result = flake8_tool._run(str(main_py_path))
        
        if "error" not in result:
            print(f"   ✓ Flake8 analysis: {len(result.get('issues', []))} style issues")
        else:
            print(f"   ⚠️  Flake8 analysis: {result['error']}")
    else:
        print("   ⚠️  Flake8 tool not available or not enabled")


def test_ai_analysis_tools(registry: ToolRegistry):
    """Test AI-powered analysis tools."""
    print("\n🤖 Testing AI Analysis Tools...")
    
    # Check if Grok (X.AI) API key is available
    if not os.getenv("XAI_API_KEY"):
        print("   ⚠️  Grok (X.AI) API key not found - skipping AI tool tests")
        print("   💡 Set XAI_API_KEY environment variable to test AI tools")
        return
    
    # Test code review tool
    review_tool = registry.get_tool("ai_code_review")
    if review_tool:
        test_code = '''
def process_data(data):
    result = []
    for item in data:
        if item:
            result.append(item.upper())
    return result
'''
        
        query = json.dumps({
            "code": test_code,
            "file_path": "test.py",
            "language": "python"
        })
        
        try:
            print("   🔄 Running AI code review (this may take a moment)...")
            result = review_tool._run(query)
            
            if "error" not in result:
                print(f"   ✓ AI code review completed")
                print(f"      - Overall score: {result.get('overall_score', 'N/A')}")
                print(f"      - Issues found: {len(result.get('issues', []))}")
                print(f"      - Recommendations: {len(result.get('recommendations', []))}")
            else:
                print(f"   ❌ AI code review failed: {result['error']}")
        except Exception as e:
            print(f"   ❌ AI code review error: {e}")


def test_github_tools(registry: ToolRegistry):
    """Test GitHub integration tools."""
    print("\n🐙 Testing GitHub Tools...")
    
    # Check if GitHub token is available
    if not os.getenv("GITHUB_TOKEN"):
        print("   ⚠️  GitHub token not found - skipping GitHub tool tests")
        print("   💡 Set GITHUB_TOKEN environment variable to test GitHub tools")
        return
    
    # Test with a public repository
    github_tool = registry.get_tool("github_repository")
    if github_tool:
        query = json.dumps({
            "repository_url": "https://github.com/octocat/Hello-World",
            "include_file_structure": True,
            "max_files": 10
        })
        
        try:
            print("   🔄 Fetching repository information...")
            result = github_tool._run(query)
            
            if "error" not in result:
                print(f"   ✓ Repository info retrieved")
                print(f"      - Name: {result.get('name', 'N/A')}")
                print(f"      - Language: {result.get('language', 'N/A')}")
                print(f"      - Stars: {result.get('stars', 'N/A')}")
                print(f"      - Files: {len(result.get('file_structure', []))}")
            else:
                print(f"   ❌ GitHub repository fetch failed: {result['error']}")
        except Exception as e:
            print(f"   ❌ GitHub tool error: {e}")


def test_repository_type_detection(registry: ToolRegistry):
    """Test repository type detection."""
    print("\n🔍 Testing Repository Type Detection...")
    
    test_cases = [
        (['.py', '.txt', '.md'], RepositoryType.PYTHON, "Python project"),
        (['.js', '.json', '.md'], RepositoryType.JAVASCRIPT, "JavaScript project"),
        (['.ts', '.json', '.md'], RepositoryType.TYPESCRIPT, "TypeScript project"),
        (['.py', '.js', '.java'], RepositoryType.MIXED, "Mixed language project"),
        (['.txt', '.md'], RepositoryType.UNKNOWN, "Unknown project type"),
    ]
    
    for extensions, expected_type, description in test_cases:
        detected_type = registry.detect_repository_type(extensions)
        status = "✓" if detected_type == expected_type else "❌"
        print(f"   {status} {description}: {detected_type.value}")


def run_comprehensive_test():
    """Run comprehensive test suite."""
    print("🚀 CustomLangGraphChatBot Tools Test Suite")
    print("=" * 50)
    
    try:
        # Test tool registry
        registry = test_tool_registry()
        
        # Test repository type detection
        test_repository_type_detection(registry)
        
        # Test file system tools
        test_repo_path = test_filesystem_tools(registry)
        
        # Test static analysis tools
        test_static_analysis_tools(registry, test_repo_path)
        
        # Test AI analysis tools
        test_ai_analysis_tools(registry)
        
        # Test GitHub tools
        test_github_tools(registry)
        
        print("\n" + "=" * 50)
        print("🎉 Test suite completed!")
        
        # Print summary
        validation = registry.validate_configuration()
        print(f"\n📊 Summary:")
        print(f"   • Total tools available: {len(registry.get_all_tools())}")
        print(f"   • Tools enabled: {len(validation['enabled_tools'])}")
        print(f"   • Tools disabled: {len(validation['disabled_tools'])}")
        print(f"   • Configuration warnings: {len(validation['warnings'])}")
        
        if validation['warnings']:
            print(f"\n⚠️  To enable all tools, configure:")
            for warning in validation['warnings']:
                if "GitHub token" in warning:
                    print(f"   • Set GITHUB_TOKEN environment variable")
                elif "Grok API key" in warning:
                    print(f"   • Set XAI_API_KEY environment variable")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "registry":
            test_tool_registry()
        elif command == "filesystem":
            registry = ToolRegistry()
            test_filesystem_tools(registry)
        elif command == "analysis":
            registry = ToolRegistry()
            # Create a temporary test file for analysis
            with tempfile.TemporaryDirectory() as temp_dir:
                test_static_analysis_tools(registry, temp_dir)
        elif command == "ai":
            registry = ToolRegistry()
            test_ai_analysis_tools(registry)
        elif command == "github":
            registry = ToolRegistry()
            test_github_tools(registry)
        else:
            print(f"Unknown command: {command}")
            print("Available commands: registry, filesystem, analysis, ai, github")
    else:
        run_comprehensive_test()


def main():
    """Enhanced main function with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced test runner for CustomLangGraphChatBot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_runner.py                    # Run all tests with coverage
  python test_runner.py --category ai      # Run AI analysis tests only
  python test_runner.py --pytest-only     # Run only pytest tests
  python test_runner.py --manual-only     # Run only manual tests
  python test_runner.py --performance     # Run performance benchmarks
  python test_runner.py --coverage        # Generate coverage report
  python test_runner.py --quick           # Quick test run (no coverage)
        """
    )

    parser.add_argument(
        "category",
        nargs="?",
        choices=["filesystem", "analysis", "ai", "github", "communication", "all"],
        help="Test category to run (default: all)"
    )

    parser.add_argument(
        "--pytest-only",
        action="store_true",
        help="Run only pytest tests"
    )

    parser.add_argument(
        "--manual-only",
        action="store_true",
        help="Run only manual integration tests"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance benchmarks"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate detailed coverage report"
    )

    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test run without coverage"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = TestRunner()
    runner.start_time = time.time()

    print("🚀 CustomLangGraphChatBot Enhanced Test Runner")
    print("=" * 60)

    overall_success = True

    # Handle specific modes
    if args.coverage:
        success = runner.generate_coverage_report()
        overall_success &= success
    elif args.performance:
        results = runner.run_performance_benchmark()
        overall_success &= results["success"]
    elif args.pytest_only:
        success, _ = runner.run_pytest_tests(
            category=args.category,
            coverage=not args.quick,
            verbose=args.verbose
        )
        overall_success &= success
    elif args.manual_only:
        # Run manual tests based on category
        if args.category == "filesystem" or args.category is None:
            overall_success &= test_filesystem_tools()
        if args.category == "analysis" or args.category is None:
            overall_success &= test_analysis_tools()
        if args.category == "ai" or args.category is None:
            overall_success &= test_ai_analysis_tools()
        if args.category == "github" or args.category is None:
            overall_success &= test_github_tools()
        if args.category == "communication" or args.category is None:
            overall_success &= test_communication_tools()
    else:
        # Run comprehensive tests (default)
        print("🧪 Running comprehensive test suite...")
        print()

        # 1. Run pytest tests
        pytest_success, _ = runner.run_pytest_tests(
            category=args.category,
            coverage=not args.quick,
            verbose=args.verbose
        )
        overall_success &= pytest_success
        print()

        # 2. Run manual integration tests if no specific category
        if not args.category or args.category == "all":
            print("🔧 Running manual integration tests...")
            overall_success &= test_tool_registry()
            overall_success &= test_filesystem_tools()
            overall_success &= test_analysis_tools()
            overall_success &= test_ai_analysis_tools()
            overall_success &= test_github_tools()
            overall_success &= test_communication_tools()
            print()

        # 3. Run performance tests if requested
        if args.performance:
            results = runner.run_performance_benchmark()
            overall_success &= results["success"]

    # Final summary
    runner.end_time = time.time()
    total_time = runner.end_time - runner.start_time

    print("=" * 60)
    print(f"🏁 Test Summary")
    print(f"   Total execution time: {total_time:.2f} seconds")

    if overall_success:
        print("   ✅ All tests passed successfully!")
        print("   🎉 Your CustomLangGraphChatBot is ready to use!")
        sys.exit(0)
    else:
        print("   ❌ Some tests failed!")
        print("   🔧 Please check the output above for details.")
        print("   💡 Run 'python validate_setup.py' to check configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
