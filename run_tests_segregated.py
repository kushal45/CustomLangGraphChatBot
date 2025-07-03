#!/usr/bin/env python3
"""
Segregated Test Runner for CustomLangGraphChatBot.

This script provides proper segregation between different types of tests:
1. Unit tests with mocked environment (fast, no real API calls)
2. Integration tests with real parameters (slower, real API calls)
3. Performance tests (slowest, comprehensive testing)

Usage:
    python run_tests_segregated.py --help
    python run_tests_segregated.py --unit-only
    python run_tests_segregated.py --integration-only
    python run_tests_segregated.py --real-params-only
    python run_tests_segregated.py --all
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle output."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False


def run_unit_tests():
    """Run unit tests with mocked environment."""
    cmd = [
        "python", "-m", "pytest",
        "-m", "not integration and not real_params and not performance",
        "--tb=short",
        "-v",
        "--disable-warnings"
    ]
    return run_command(cmd, "Unit Tests (Mocked Environment)")


def run_integration_tests():
    """Run integration tests with real parameters."""
    cmd = [
        "python", "-m", "pytest",
        "-m", "integration and real_params", 
        "--tb=short",
        "-v",
        "--disable-warnings",
        "-s"  # Don't capture output for real API calls
    ]
    return run_command(cmd, "Integration Tests (Real Parameters)")


def run_performance_tests():
    """Run performance tests."""
    cmd = [
        "python", "-m", "pytest",
        "-m", "performance",
        "--tb=short", 
        "-v",
        "--disable-warnings"
    ]
    return run_command(cmd, "Performance Tests")


def run_specific_file_tests(file_path):
    """Run tests for a specific file."""
    cmd = [
        "python", "-m", "pytest",
        file_path,
        "--tb=short",
        "-v",
        "--disable-warnings"
    ]
    return run_command(cmd, f"Tests for {file_path}")


def run_sanity_check():
    """Run the modular sanity checker."""
    cmd = ["python", "tests/test_module_sanity.py", "--real-params", "--verbose"]
    return run_command(cmd, "Modular Sanity Check (Real Parameters)")


def run_tools_integration():
    """Run the tools integration runner."""
    cmd = ["python", "tools_integration_runner.py", "--sanity-check", "--verbose"]
    return run_command(cmd, "Tools Integration Runner")


def main():
    parser = argparse.ArgumentParser(description="Segregated Test Runner")
    parser.add_argument("--unit-only", action="store_true", 
                       help="Run only unit tests with mocked environment")
    parser.add_argument("--integration-only", action="store_true",
                       help="Run only integration tests with real parameters")
    parser.add_argument("--performance-only", action="store_true",
                       help="Run only performance tests")
    parser.add_argument("--real-params-only", action="store_true",
                       help="Run only tests that use real API parameters")
    parser.add_argument("--sanity-check", action="store_true",
                       help="Run modular sanity checker")
    parser.add_argument("--tools-integration", action="store_true",
                       help="Run tools integration runner")
    parser.add_argument("--file", type=str,
                       help="Run tests for specific file")
    parser.add_argument("--all", action="store_true",
                       help="Run all test categories in sequence")
    parser.add_argument("--exclude-slow", action="store_true",
                       help="Exclude slow tests")
    
    args = parser.parse_args()
    
    if not any([args.unit_only, args.integration_only, args.performance_only, 
                args.real_params_only, args.sanity_check, args.tools_integration,
                args.file, args.all]):
        parser.print_help()
        return
    
    success_count = 0
    total_count = 0
    
    if args.unit_only or args.all:
        total_count += 1
        if run_unit_tests():
            success_count += 1
    
    if args.integration_only or args.all:
        total_count += 1
        if run_integration_tests():
            success_count += 1
    
    if args.performance_only or args.all:
        total_count += 1
        if run_performance_tests():
            success_count += 1
    
    if args.real_params_only:
        total_count += 1
        cmd = [
            "python", "-m", "pytest",
            "-m", "real_params",
            "--tb=short",
            "-v", 
            "--disable-warnings",
            "-s"
        ]
        if run_command(cmd, "Real Parameter Tests"):
            success_count += 1
    
    if args.sanity_check or args.all:
        total_count += 1
        if run_sanity_check():
            success_count += 1
    
    if args.tools_integration or args.all:
        total_count += 1
        if run_tools_integration():
            success_count += 1
    
    if args.file:
        total_count += 1
        if run_specific_file_tests(args.file):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Successful: {success_count}/{total_count}")
    print(f"Failed: {total_count - success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
