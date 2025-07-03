#!/usr/bin/env python3
"""
Tool Health Check System for CustomLangGraphChatBot.

This module provides continuous health monitoring for all tools,
checking availability, performance, and functionality to ensure
tools are working correctly before workflow execution.
"""

import os
import sys
import json
import time
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.registry import ToolRegistry, ToolConfig


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheckResult:
    """Health check result data class."""
    tool_name: str
    status: HealthStatus
    response_time: float
    message: str
    details: Dict[str, Any]
    timestamp: float


class ToolHealthChecker:
    """Comprehensive health checker for tools."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.registry = None
        self.health_history = {}
        
    def setup(self):
        """Set up health checker."""
        config = ToolConfig()
        config.tool_timeout = self.timeout
        self.registry = ToolRegistry(config)
    
    async def check_tool_health(self, tool_name: str) -> HealthCheckResult:
        """Check health of a specific tool."""
        start_time = time.time()
        
        try:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                return HealthCheckResult(
                    tool_name=tool_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="Tool not found",
                    details={},
                    timestamp=time.time()
                )
            
            # Perform health check based on tool type
            if tool_name in ["file_reader", "directory_lister"]:
                result = await self._check_filesystem_tool_health(tool)
            elif tool_name in ["pylint_analysis", "flake8_analysis", "code_complexity"]:
                result = await self._check_analysis_tool_health(tool)
            elif tool_name in ["ai_code_review", "ai_documentation_generator"]:
                result = await self._check_ai_tool_health(tool)
            elif tool_name in ["github_repository", "github_file_content"]:
                result = await self._check_github_tool_health(tool)
            elif tool_name in ["slack_notification", "email_notification"]:
                result = await self._check_communication_tool_health(tool)
            else:
                result = await self._check_generic_tool_health(tool)
            
            response_time = time.time() - start_time
            result.response_time = response_time
            result.timestamp = time.time()
            
            # Store in history
            if tool_name not in self.health_history:
                self.health_history[tool_name] = []
            self.health_history[tool_name].append(result)
            
            # Keep only last 10 results
            if len(self.health_history[tool_name]) > 10:
                self.health_history[tool_name] = self.health_history[tool_name][-10:]
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                tool_name=tool_name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e)},
                timestamp=time.time()
            )
    
    async def _check_filesystem_tool_health(self, tool) -> HealthCheckResult:
        """Check filesystem tool health."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_file = Path(temp_dir) / "health_check.txt"
                test_file.write_text("Health check test content")
                
                if tool.name == "file_reader":
                    result = tool._run(str(test_file))
                    if "error" not in result and result.get("content"):
                        return HealthCheckResult(
                            tool_name=tool.name,
                            status=HealthStatus.HEALTHY,
                            response_time=0,
                            message="File reading successful",
                            details={"file_size": len(result["content"])}
                        )
                elif tool.name == "directory_lister":
                    query = json.dumps({"directory_path": temp_dir, "recursive": False})
                    result = tool._run(query)
                    if "error" not in result and result.get("files"):
                        return HealthCheckResult(
                            tool_name=tool.name,
                            status=HealthStatus.HEALTHY,
                            response_time=0,
                            message="Directory listing successful",
                            details={"files_found": len(result["files"])}
                        )
                
                return HealthCheckResult(
                    tool_name=tool.name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message="Tool test failed",
                    details={}
                )
                
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Filesystem check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_analysis_tool_health(self, tool) -> HealthCheckResult:
        """Check analysis tool health."""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write('''
def test_function():
    """Test function for health check."""
    return "healthy"
''')
                f.flush()
                
                result = tool._run(f.name)
                os.unlink(f.name)
                
                if "error" not in result:
                    return HealthCheckResult(
                        tool_name=tool.name,
                        status=HealthStatus.HEALTHY,
                        response_time=0,
                        message="Analysis completed successfully",
                        details={"analysis_type": tool.name}
                    )
                elif "not found" in result.get("error", "").lower():
                    return HealthCheckResult(
                        tool_name=tool.name,
                        status=HealthStatus.DEGRADED,
                        response_time=0,
                        message="Tool not installed but available",
                        details={"error": result["error"]}
                    )
                else:
                    return HealthCheckResult(
                        tool_name=tool.name,
                        status=HealthStatus.UNHEALTHY,
                        response_time=0,
                        message="Analysis failed",
                        details={"error": result.get("error", "Unknown error")}
                    )
                    
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Analysis check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_ai_tool_health(self, tool) -> HealthCheckResult:
        """Check AI tool health."""
        try:
            # Check if API keys are available
            api_keys = [
                os.getenv("XAI_API_KEY"),
                os.getenv("OPENAI_API_KEY"),
                os.getenv("ANTHROPIC_API_KEY")
            ]
            
            if not any(api_keys):
                return HealthCheckResult(
                    tool_name=tool.name,
                    status=HealthStatus.DEGRADED,
                    response_time=0,
                    message="No API keys configured",
                    details={"available_keys": [k for k in api_keys if k]}
                )
            
            # Quick connectivity test (mock for health check)
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="AI tool configured and ready",
                details={"api_configured": True}
            )
            
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"AI check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_github_tool_health(self, tool) -> HealthCheckResult:
        """Check GitHub tool health."""
        try:
            github_token = os.getenv("GITHUB_TOKEN")
            
            if not github_token:
                return HealthCheckResult(
                    tool_name=tool.name,
                    status=HealthStatus.DEGRADED,
                    response_time=0,
                    message="GitHub token not configured",
                    details={"token_available": False}
                )
            
            # Basic connectivity test (mock for health check)
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="GitHub tool configured and ready",
                details={"token_available": True}
            )
            
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"GitHub check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_communication_tool_health(self, tool) -> HealthCheckResult:
        """Check communication tool health."""
        try:
            # Check configuration
            config_available = False
            
            if tool.name == "slack_notification":
                config_available = bool(os.getenv("SLACK_WEBHOOK_URL"))
            elif tool.name == "email_notification":
                config_available = bool(os.getenv("EMAIL_SMTP_SERVER"))
            
            if not config_available:
                return HealthCheckResult(
                    tool_name=tool.name,
                    status=HealthStatus.DEGRADED,
                    response_time=0,
                    message="Communication tool not configured",
                    details={"configured": False}
                )
            
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="Communication tool configured and ready",
                details={"configured": True}
            )
            
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Communication check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    async def _check_generic_tool_health(self, tool) -> HealthCheckResult:
        """Check generic tool health."""
        try:
            # Basic tool availability check
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.HEALTHY,
                response_time=0,
                message="Tool available",
                details={"type": type(tool).__name__}
            )
            
        except Exception as e:
            return HealthCheckResult(
                tool_name=tool.name,
                status=HealthStatus.UNHEALTHY,
                response_time=0,
                message=f"Generic check failed: {str(e)}",
                details={"error": str(e)}
            )

    async def check_all_tools_health(self) -> Dict[str, HealthCheckResult]:
        """Check health of all tools."""
        if not self.registry:
            self.setup()

        all_tools = self.registry.get_all_tools()
        results = {}

        # Create tasks for concurrent health checks
        tasks = []
        for tool in all_tools:
            task = asyncio.create_task(self.check_tool_health(tool.name))
            tasks.append(task)

        # Wait for all health checks to complete
        health_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(health_results):
            if isinstance(result, Exception):
                tool_name = all_tools[i].name
                results[tool_name] = HealthCheckResult(
                    tool_name=tool_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time=0,
                    message=f"Health check exception: {str(result)}",
                    details={"exception": str(result)},
                    timestamp=time.time()
                )
            else:
                results[result.tool_name] = result

        return results

    def get_health_summary(self, results: Dict[str, HealthCheckResult]) -> Dict[str, Any]:
        """Generate health summary from results."""
        total_tools = len(results)
        healthy_count = sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for r in results.values() if r.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for r in results.values() if r.status == HealthStatus.UNHEALTHY)

        avg_response_time = sum(r.response_time for r in results.values()) / total_tools if total_tools > 0 else 0

        overall_status = HealthStatus.HEALTHY
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED

        return {
            "total_tools": total_tools,
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "overall_status": overall_status.value,
            "average_response_time": avg_response_time,
            "timestamp": time.time()
        }

    def print_health_report(self, results: Dict[str, HealthCheckResult], verbose: bool = False):
        """Print health report."""
        summary = self.get_health_summary(results)

        print("🏥 Tool Health Check Report")
        print("=" * 50)

        # Overall status
        status_icon = {
            "HEALTHY": "✅",
            "DEGRADED": "⚠️",
            "UNHEALTHY": "❌"
        }.get(summary["overall_status"], "❓")

        print(f"Overall Status: {status_icon} {summary['overall_status']}")
        print(f"Total Tools: {summary['total_tools']}")
        print(f"✅ Healthy: {summary['healthy']}")
        print(f"⚠️  Degraded: {summary['degraded']}")
        print(f"❌ Unhealthy: {summary['unhealthy']}")
        print(f"⏱️  Avg Response Time: {summary['average_response_time']:.3f}s")


async def run_health_checks(verbose: bool = False, tool_name: Optional[str] = None) -> Dict[str, Any]:
    """Run health checks for tools."""
    checker = ToolHealthChecker()
    checker.setup()

    if tool_name:
        # Check specific tool
        result = await checker.check_tool_health(tool_name)
        return {tool_name: result}
    else:
        # Check all tools
        results = await checker.check_all_tools_health()
        checker.print_health_report(results, verbose=verbose)
        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tool Health Checker")
    parser.add_argument("--tool", help="Check specific tool only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    async def main():
        results = await run_health_checks(verbose=args.verbose, tool_name=args.tool)

        # Exit with appropriate code
        if args.tool:
            result = list(results.values())[0]
            sys.exit(0 if result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED] else 1)
        else:
            checker = ToolHealthChecker()
            summary = checker.get_health_summary(results)
            sys.exit(0 if summary["overall_status"] != "UNHEALTHY" else 1)

    asyncio.run(main())
