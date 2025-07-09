#!/usr/bin/env python3
"""
Demo script to test real parameter functionality in the testing framework.

This script demonstrates how to use the enhanced testing framework with real parameters
instead of mocked responses, specifically for GitHub tools.

Usage:
    python test_real_params_demo.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.unit.test_module_sanity import run_sanity_checks
from tools_integration_runner import ToolIntegrationRunner


def demo_sanity_check_with_real_params():
    """Demonstrate sanity checking with real GitHub parameters."""
    print("🎯 Demo: Sanity Check with Real GitHub Parameters")
    print("=" * 60)
    
    # Real parameters for testing
    real_params = {
        "github_repo": "https://github.com/kushal45/CustomLangGraphChatBot",
        "test_file": "tools/registry.py"
    }
    
    print(f"📍 Testing with repository: {real_params['github_repo']}")
    print(f"📄 Testing with file: {real_params['test_file']}")
    print()
    
    # Check if GitHub token is available
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("⚠️  WARNING: GITHUB_TOKEN not found in environment variables")
        print("   Real GitHub API calls will fail without authentication")
        print("   Set GITHUB_TOKEN environment variable for full testing")
        print()
    
    # Run sanity check with real parameters
    results = run_sanity_checks(
        verbose=True,
        category="github",
        use_real_params=True,
        real_params=real_params
    )
    
    print("\n📊 Results Summary:")
    print(f"   Overall Status: {results.get('overall_status', 'UNKNOWN')}")
    
    if results.get("tools"):
        for tool_name, tool_result in results["tools"].items():
            status = tool_result.get("status", "UNKNOWN")
            message = tool_result.get("message", "No message")
            real_test = tool_result.get("real_test", False)
            
            print(f"   {tool_name}: {status} {'(Real Test)' if real_test else '(Mock Test)'}")
            print(f"      {message}")
            
            # Show additional data if available
            if tool_result.get("data"):
                print("      Data retrieved:")
                for key, value in tool_result["data"].items():
                    print(f"         {key}: {value}")
    
    return results


async def demo_integration_runner_with_real_params():
    """Demonstrate integration runner with real parameters."""
    print("\n🎯 Demo: Integration Runner with Real Parameters")
    print("=" * 60)
    
    # Real parameters for testing
    real_params = {
        "github_repo": "https://github.com/octocat/Hello-World",
        "test_file": "README.md"
    }
    
    print(f"📍 Testing with repository: {real_params['github_repo']}")
    print(f"📄 Testing with file: {real_params['test_file']}")
    print()
    
    # Create integration runner with real parameters
    runner = ToolIntegrationRunner(
        verbose=True,
        use_real_params=True,
        real_params=real_params
    )
    
    # Run sanity checks with real parameters
    results = runner.run_sanity_checks(category="github")
    
    print("\n📊 Integration Runner Results:")
    print(f"   Overall Status: {results.get('overall_status', 'UNKNOWN')}")
    
    return results


def demo_mock_vs_real_comparison():
    """Compare mock testing vs real parameter testing."""
    print("\n🎯 Demo: Mock vs Real Parameter Testing Comparison")
    print("=" * 60)
    
    real_params = {
        "github_repo": "https://github.com/kushal45/CustomLangGraphChatBot",
        "test_file": "README.md"
    }
    
    print("1️⃣ Running with MOCK parameters...")
    mock_results = run_sanity_checks(
        verbose=False,
        category="github",
        use_real_params=False
    )
    
    print("\n2️⃣ Running with REAL parameters...")
    real_results = run_sanity_checks(
        verbose=False,
        category="github",
        use_real_params=True,
        real_params=real_params
    )
    
    print("\n📊 Comparison Results:")
    print(f"   Mock Test Status: {mock_results.get('overall_status', 'UNKNOWN')}")
    print(f"   Real Test Status: {real_results.get('overall_status', 'UNKNOWN')}")
    
    print("\n   Mock Test Details:")
    if mock_results.get("tools"):
        for tool_name, tool_result in mock_results["tools"].items():
            print(f"      {tool_name}: {tool_result.get('status')} - {tool_result.get('message')}")
    
    print("\n   Real Test Details:")
    if real_results.get("tools"):
        for tool_name, tool_result in real_results["tools"].items():
            print(f"      {tool_name}: {tool_result.get('status')} - {tool_result.get('message')}")
            if tool_result.get("data"):
                print(f"         Real data retrieved: {len(tool_result['data'])} fields")


def main():
    """Main demo function."""
    print("🚀 Real Parameter Testing Framework Demo")
    print("=" * 60)
    print("This demo shows how to test tools with actual parameters")
    print("instead of mocked responses.")
    print()
    
    # Check environment
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        print("✅ GitHub token found - real API calls will work")
    else:
        print("⚠️  GitHub token not found - some tests may fail")
        print("   Set GITHUB_TOKEN environment variable for full functionality")
    
    print()
    
    try:
        # Demo 1: Basic sanity check with real parameters
        demo_sanity_check_with_real_params()
        
        # Demo 2: Integration runner with real parameters
        asyncio.run(demo_integration_runner_with_real_params())
        
        # Demo 3: Comparison between mock and real testing
        demo_mock_vs_real_comparison()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Set GITHUB_TOKEN environment variable for full API access")
        print("2. Try running with different repositories and files")
        print("3. Use the VSCode debug configurations for interactive testing")
        print("4. Run: python tools_integration_runner.py --real-world-test --github-repo <your-repo>")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
