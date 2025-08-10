#!/usr/bin/env python3
"""
Test script for debugging repository fetching and validation.
Used by VSCode debugging configurations to test start_review_node functionality.
"""

import asyncio
import argparse
import sys
import os
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import ReviewState, ReviewStatus
from nodes import start_review_node
from debug.repository_debugging import repo_debugger
from logging_config import get_logger

logger = get_logger(__name__)

class RepositoryDebuggingTest:
    """Test harness for debugging repository operations."""
    
    def __init__(self, repository_url: str, debug_level: str = "normal"):
        self.repository_url = repository_url
        self.debug_level = debug_level
        self.test_results = {}
        
    async def test_repository_fetching(self) -> Dict[str, Any]:
        """Test complete repository fetching process with debugging."""
        print(f"\n🔍 Testing Repository Fetching: {self.repository_url}")
        print("=" * 60)
        
        # Create initial state
        initial_state = ReviewState({
            "repository_url": self.repository_url,
            "current_step": "start_review",
            "status": ReviewStatus.INITIALIZING
        })
        
        print(f"📊 Initial State: {dict(initial_state)}")
        
        try:
            # Execute start_review_node with debugging breakpoints
            result = await start_review_node(initial_state)
            
            self.test_results = {
                "success": True,
                "result": result,
                "repository_url": self.repository_url,
                "debug_session": repo_debugger.debug_session_id
            }
            
            print(f"\n✅ Repository fetching completed successfully!")
            print(f"📊 Result: {result}")
            
            return self.test_results
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "repository_url": self.repository_url,
                "debug_session": repo_debugger.debug_session_id
            }
            
            self.test_results = error_result
            
            print(f"\n❌ Repository fetching failed!")
            print(f"🚨 Error: {e}")
            print(f"🔧 Error Type: {type(e).__name__}")
            
            # Add debugging breakpoint for error analysis
            repo_debugger.debug_breakpoint(
                "error_analysis", 
                initial_state, 
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "step": "Error occurred during repository fetching"
                }
            )
            
            return error_result
            
    async def test_validation_only(self) -> Dict[str, Any]:
        """Test only URL validation without API calls."""
        print(f"\n🔍 Testing URL Validation Only: {self.repository_url}")
        print("=" * 60)
        
        # Test URL inspection
        url_inspection = repo_debugger.inspect_repository_url(self.repository_url)
        
        print(f"📊 URL Inspection Results:")
        for key, value in url_inspection.items():
            print(f"   {key}: {value}")
            
        # Add debugging breakpoint for validation analysis
        repo_debugger.debug_breakpoint(
            "validation_only_test", 
            {"repository_url": self.repository_url}, 
            {
                "url_inspection": url_inspection,
                "step": "URL validation testing"
            }
        )
        
        return {
            "validation_results": url_inspection,
            "repository_url": self.repository_url
        }
        
    async def test_failure_scenarios(self) -> Dict[str, Any]:
        """Test various failure scenarios for debugging."""
        print(f"\n🔍 Testing Failure Scenarios")
        print("=" * 60)
        
        failure_tests = [
            {"url": "", "scenario": "empty_url"},
            {"url": "invalid-url", "scenario": "invalid_format"},
            {"url": "https://github.com/nonexistent/repo", "scenario": "nonexistent_repo"},
            {"url": "https://github.com/", "scenario": "incomplete_url"}
        ]
        
        results = []
        
        for test in failure_tests:
            print(f"\n🧪 Testing scenario: {test['scenario']}")
            print(f"📊 URL: {test['url']}")
            
            try:
                state = ReviewState({
                    "repository_url": test['url'],
                    "current_step": "start_review",
                    "status": ReviewStatus.INITIALIZING
                })
                
                result = await start_review_node(state)
                
                results.append({
                    "scenario": test['scenario'],
                    "url": test['url'],
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "scenario": test['scenario'],
                    "url": test['url'],
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                
                print(f"❌ Expected failure: {e}")
                
        return {"failure_test_results": results}

def main():
    """Main function for repository debugging test."""
    parser = argparse.ArgumentParser(description="Debug repository fetching and validation")
    parser.add_argument("--repository-url", required=True, help="GitHub repository URL to test")
    parser.add_argument("--debug-level", default="normal", choices=["normal", "verbose"], 
                       help="Debug level")
    parser.add_argument("--validation-only", action="store_true", 
                       help="Test only URL validation")
    parser.add_argument("--test-failures", action="store_true", 
                       help="Test failure scenarios")
    
    args = parser.parse_args()
    
    print(f"🚀 Repository Debugging Test Started")
    print(f"📊 Repository URL: {args.repository_url}")
    print(f"🔧 Debug Level: {args.debug_level}")
    print(f"🔍 Debug Session ID: {repo_debugger.debug_session_id}")
    
    # Create test instance
    test_instance = RepositoryDebuggingTest(args.repository_url, args.debug_level)
    
    async def run_tests():
        if args.validation_only:
            return await test_instance.test_validation_only()
        elif args.test_failures:
            return await test_instance.test_failure_scenarios()
        else:
            return await test_instance.test_repository_fetching()
    
    # Run the test
    try:
        result = asyncio.run(run_tests())
        
        print(f"\n🎯 Test Completed!")
        print(f"📊 Final Results: {result}")
        
        # Print debug summary
        repo_debugger.print_debug_summary()
        
        return 0 if result.get("success", True) else 1
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
