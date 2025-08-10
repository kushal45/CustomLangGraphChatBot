#!/usr/bin/env python3
"""
Product Manager Validation Runner

This script provides an easy-to-use interface for Product Managers to run
validation tests and get comprehensive reports on the LangGraph-UI integration.

Usage:
    python scripts/run_product_validation.py --suite daily
    python scripts/run_product_validation.py --suite weekly
    python scripts/run_product_validation.py --suite all
    python scripts/run_product_validation.py --report
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from validation.product_manager_dashboard import ProductManagerDashboard, ValidationStatus, ValidationPriority
except ImportError:
    print("Error: Could not import validation dashboard. Please ensure all dependencies are installed.")
    sys.exit(1)

class ProductValidationRunner:
    """Main runner for Product Manager validation tasks."""
    
    def __init__(self):
        self.dashboard = ProductManagerDashboard()
        self.results_dir = project_root / "validation" / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_daily_validation(self):
        """Run daily validation suite."""
        print("🔄 Running Daily Validation Suite...")
        print("=" * 50)
        
        suites_to_run = [
            "component_integration",
            "workflow_end_to_end", 
            "performance_monitoring"
        ]
        
        all_results = []
        for suite_name in suites_to_run:
            print(f"\n📋 Running {suite_name}...")
            try:
                results = await self.dashboard.run_validation_suite(suite_name)
                all_results.extend(results)
                self._print_suite_summary(suite_name, results)
            except Exception as e:
                print(f"❌ Error running {suite_name}: {str(e)}")
        
        self._print_overall_summary(all_results, "Daily Validation")
        self._save_results(all_results, "daily")
        
        return all_results
    
    async def run_weekly_validation(self):
        """Run weekly validation suite."""
        print("🔄 Running Weekly Validation Suite...")
        print("=" * 50)
        
        suites_to_run = [
            "component_integration",
            "workflow_end_to_end",
            "ui_chatbot_integration",
            "performance_monitoring",
            "user_experience"
        ]
        
        all_results = []
        for suite_name in suites_to_run:
            print(f"\n📋 Running {suite_name}...")
            try:
                results = await self.dashboard.run_validation_suite(suite_name)
                all_results.extend(results)
                self._print_suite_summary(suite_name, results)
            except Exception as e:
                print(f"❌ Error running {suite_name}: {str(e)}")
        
        self._print_overall_summary(all_results, "Weekly Validation")
        self._save_results(all_results, "weekly")
        
        return all_results
    
    async def run_all_validation(self):
        """Run complete validation suite."""
        print("🔄 Running Complete Validation Suite...")
        print("=" * 50)
        
        all_suite_names = list(self.dashboard.validation_suites.keys())
        all_results = []
        
        for suite_name in all_suite_names:
            print(f"\n📋 Running {suite_name}...")
            try:
                results = await self.dashboard.run_validation_suite(suite_name)
                all_results.extend(results)
                self._print_suite_summary(suite_name, results)
            except Exception as e:
                print(f"❌ Error running {suite_name}: {str(e)}")
        
        self._print_overall_summary(all_results, "Complete Validation")
        self._save_results(all_results, "complete")
        
        return all_results
    
    def generate_report(self):
        """Generate comprehensive validation report."""
        print("📊 Generating Validation Report...")
        print("=" * 50)
        
        report = self.dashboard.generate_validation_report()
        
        # Print summary
        summary = report.get("summary", {})
        print(f"\n📈 Validation Summary:")
        print(f"   Total Tests: {summary.get('total_tests', 0)}")
        print(f"   Passed: {summary.get('passed', 0)} ✅")
        print(f"   Failed: {summary.get('failed', 0)} ❌")
        print(f"   Warnings: {summary.get('warnings', 0)} ⚠️")
        print(f"   Success Rate: {summary.get('success_rate', 0)}%")
        
        # Print critical issues
        critical_issues = report.get("critical_issues", 0)
        high_issues = report.get("high_priority_issues", 0)
        
        if critical_issues > 0:
            print(f"\n🚨 CRITICAL ISSUES: {critical_issues}")
        if high_issues > 0:
            print(f"⚠️  HIGH PRIORITY ISSUES: {high_issues}")
        
        # Print alerts
        alerts = report.get("alerts", [])
        if alerts:
            print(f"\n🔔 Active Alerts:")
            for alert in alerts:
                print(f"   {alert['level']}: {alert['message']}")
        
        # Print recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Save report
        self._save_report(report)
        
        return report
    
    def _print_suite_summary(self, suite_name: str, results):
        """Print summary for a validation suite."""
        passed = len([r for r in results if r.status == ValidationStatus.PASS])
        failed = len([r for r in results if r.status == ValidationStatus.FAIL])
        warnings = len([r for r in results if r.status == ValidationStatus.WARNING])
        total = len(results)
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"   Results: {passed}✅ {failed}❌ {warnings}⚠️  ({success_rate:.1f}% success)")
        
        # Show failed tests
        failed_tests = [r for r in results if r.status == ValidationStatus.FAIL]
        if failed_tests:
            print(f"   Failed Tests:")
            for test in failed_tests:
                priority_icon = "🚨" if test.priority == ValidationPriority.CRITICAL else "⚠️"
                print(f"     {priority_icon} {test.test_name}: {test.message}")
    
    def _print_overall_summary(self, all_results, validation_type):
        """Print overall validation summary."""
        total = len(all_results)
        passed = len([r for r in all_results if r.status == ValidationStatus.PASS])
        failed = len([r for r in all_results if r.status == ValidationStatus.FAIL])
        warnings = len([r for r in all_results if r.status == ValidationStatus.WARNING])
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\n" + "=" * 50)
        print(f"🎯 {validation_type} Summary")
        print(f"=" * 50)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Warnings: {warnings} ⚠️")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Overall status
        if failed == 0:
            print(f"🎉 Status: ALL TESTS PASSED!")
        elif failed <= 2:
            print(f"⚠️  Status: Minor issues detected")
        else:
            print(f"🚨 Status: Multiple failures - investigation required")
        
        # Critical failures
        critical_failures = [r for r in all_results if r.status == ValidationStatus.FAIL and r.priority == ValidationPriority.CRITICAL]
        if critical_failures:
            print(f"\n🚨 CRITICAL FAILURES DETECTED:")
            for failure in critical_failures:
                print(f"   - {failure.test_name}: {failure.message}")
    
    def _save_results(self, results, validation_type):
        """Save validation results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{validation_type}_validation_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            serializable_results.append({
                "test_name": result.test_name,
                "status": result.status.value,
                "priority": result.priority.value,
                "execution_time": result.execution_time,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp
            })
        
        with open(filepath, 'w') as f:
            json.dump({
                "validation_type": validation_type,
                "timestamp": timestamp,
                "results": serializable_results
            }, f, indent=2)
        
        print(f"📁 Results saved to: {filepath}")
    
    def _save_report(self, report):
        """Save validation report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"validation_report_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📁 Report saved to: {filepath}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Product Manager Validation Runner")
    parser.add_argument(
        "--suite", 
        choices=["daily", "weekly", "all"],
        help="Validation suite to run"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate validation report from existing results"
    )
    
    args = parser.parse_args()
    
    runner = ProductValidationRunner()
    
    try:
        if args.report:
            runner.generate_report()
        elif args.suite == "daily":
            await runner.run_daily_validation()
        elif args.suite == "weekly":
            await runner.run_weekly_validation()
        elif args.suite == "all":
            await runner.run_all_validation()
        else:
            print("Please specify --suite (daily|weekly|all) or --report")
            print("\nExamples:")
            print("  python scripts/run_product_validation.py --suite daily")
            print("  python scripts/run_product_validation.py --suite weekly")
            print("  python scripts/run_product_validation.py --report")
            return
        
        print(f"\n✅ Validation completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Validation interrupted by user")
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
