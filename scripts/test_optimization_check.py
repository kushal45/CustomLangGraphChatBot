#!/usr/bin/env python3
"""
Test optimization verification script.
This script simulates the GitHub Actions test execution to verify optimizations work.
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, timeout=300):
    """Run a command with timeout and return result."""
    print(f"Running: {cmd}")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        print(f"Completed in {duration:.2f}s")
        return result, duration
    except subprocess.TimeoutExpired:
        print(f"Command timed out after {timeout}s")
        return None, timeout

def test_unit_core():
    """Test core unit tests."""
    cmd = """python -m pytest \
        tests/test_registry.py \
        tests/test_error_handling.py \
        tests/test_tool_health.py \
        -m "not integration and not real_params and not performance" \
        --tb=short \
        -v \
        --disable-warnings \
        --maxfail=5 \
        -n 2"""
    
    result, duration = run_command(cmd, timeout=900)  # 15 minutes
    if result and result.returncode == 0:
        print("✅ Core unit tests passed")
        return True
    else:
        print("❌ Core unit tests failed")
        if result:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        return False

def test_unit_tools():
    """Test tool unit tests."""
    cmd = """python -m pytest \
        tests/test_ai_analysis_tools.py \
        tests/test_static_analysis_tools.py \
        tests/test_filesystem_tools.py \
        tests/test_github_tools.py \
        tests/test_communication_tools.py \
        -m "not integration and not real_params and not performance" \
        --tb=short \
        -v \
        --disable-warnings \
        --maxfail=10 \
        -n 2"""
    
    result, duration = run_command(cmd, timeout=1200)  # 20 minutes
    if result and result.returncode == 0:
        print("✅ Tool unit tests passed")
        return True
    else:
        print("❌ Tool unit tests failed")
        if result:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        return False

def test_performance():
    """Test performance tests."""
    cmd = """python -m pytest \
        tests/test_performance.py \
        -m "performance" \
        --tb=short \
        -v \
        --disable-warnings \
        --durations=10 \
        --maxfail=3"""
    
    result, duration = run_command(cmd, timeout=600)  # 10 minutes
    if result and result.returncode == 0:
        print("✅ Performance tests passed")
        return True
    else:
        print("❌ Performance tests failed")
        if result:
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
        return False

def main():
    """Main test execution."""
    print("🚀 Starting test optimization verification...")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    results = []
    
    print("\n📋 Testing Core Unit Tests...")
    results.append(test_unit_core())
    
    print("\n🔧 Testing Tool Unit Tests...")
    results.append(test_unit_tools())
    
    print("\n⚡ Testing Performance Tests...")
    results.append(test_performance())
    
    print("\n📊 Summary:")
    print(f"Core Unit Tests: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"Tool Unit Tests: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"Performance Tests: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    if all(results):
        print("\n🎉 All test optimizations working correctly!")
        return 0
    else:
        print("\n💥 Some tests failed - check output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
