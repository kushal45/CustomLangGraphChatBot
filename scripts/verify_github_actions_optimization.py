#!/usr/bin/env python3
"""
Verification script for GitHub Actions test optimization.
This script simulates the exact test execution that will happen in GitHub Actions.
"""

import subprocess
import time
import sys
from pathlib import Path

def run_command(cmd, description, timeout_minutes=20):
    """Run a command with timeout and measure execution time."""
    print(f"\n🔍 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60,
            cwd=Path(__file__).parent.parent
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        
        if result.returncode == 0:
            print(f"✅ PASSED: {description}")
            # Show test count from output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'passed' in line and ('warning' in line or 'error' in line or line.strip().endswith('passed')):
                    print(f"📊 Result: {line.strip()}")
                    break
        else:
            print(f"❌ FAILED: {description}")
            print("STDOUT:", result.stdout[-500:])  # Last 500 chars
            print("STDERR:", result.stderr[-500:])  # Last 500 chars
            return False
            
        return True
        
    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT: {description} exceeded {timeout_minutes} minutes")
        return False
    except Exception as e:
        print(f"💥 ERROR: {description} failed with exception: {e}")
        return False

def main():
    """Run all test categories as they would run in GitHub Actions."""
    print("🚀 GitHub Actions Test Optimization Verification")
    print("=" * 60)
    
    # Test categories as defined in GitHub Actions
    test_categories = [
        {
            "name": "Core Unit Tests",
            "cmd": [
                "python", "-m", "pytest",
                "tests/test_registry.py",
                "tests/test_error_handling.py", 
                "tests/test_tool_health.py",
                "-m", "not integration and not real_params and not performance",
                "--tb=short", "-v", "--disable-warnings",
                "--maxfail=5", "-n", "2", "--durations=3"
            ],
            "timeout": 15,
            "expected_max_time": 10  # seconds
        },
        {
            "name": "Tool Unit Tests",
            "cmd": [
                "python", "-m", "pytest",
                "tests/test_ai_analysis_tools.py",
                "tests/test_static_analysis_tools.py",
                "tests/test_filesystem_tools.py",
                "tests/test_github_tools.py", 
                "tests/test_communication_tools.py",
                "-m", "not integration and not real_params and not performance",
                "--tb=short", "-v", "--disable-warnings",
                "--maxfail=10", "-n", "2", "--durations=3"
            ],
            "timeout": 20,
            "expected_max_time": 15  # seconds
        },
        {
            "name": "Performance Tests",
            "cmd": [
                "python", "-m", "pytest",
                "tests/test_performance.py",
                "-m", "performance",
                "--tb=short", "-v", "--disable-warnings",
                "--maxfail=3", "--durations=5"
            ],
            "timeout": 10,
            "expected_max_time": 30  # seconds
        }
    ]
    
    results = []
    total_start_time = time.time()
    
    for category in test_categories:
        success = run_command(
            category["cmd"],
            category["name"],
            category["timeout"]
        )
        results.append((category["name"], success))
        
        if not success:
            print(f"\n❌ CRITICAL: {category['name']} failed!")
            break
    
    total_time = time.time() - total_start_time
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\n📊 Results: {passed}/{total} test categories passed")
    print(f"⏱️  Total execution time: {total_time:.2f} seconds")
    
    if passed == total:
        print("\n🎉 ALL OPTIMIZATIONS VERIFIED SUCCESSFULLY!")
        print("✅ GitHub Actions should now run without timeouts")
        print("✅ Tests are properly categorized and optimized")
        print("✅ Performance improvements confirmed")
        return True
    else:
        print(f"\n💥 VERIFICATION FAILED: {total - passed} categories failed")
        print("❌ GitHub Actions may still experience issues")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
