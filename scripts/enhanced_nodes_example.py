#!/usr/bin/env python3
"""
Enhanced Nodes with Tracing Example

This module demonstrates how to integrate the advanced tracing system
into existing workflow nodes, providing detailed execution traces,
performance monitoring, and state change tracking.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus, RepositoryInfo, ToolResult
from scripts.node_tracing import traced_node, trace_info, trace_debug, trace_warning, trace_error
from logging_config import get_logger

logger = get_logger(__name__)


@traced_node
async def enhanced_start_review_node(state: ReviewState) -> Dict[str, Any]:
    """Enhanced start_review_node with comprehensive tracing."""
    logger.info("Starting enhanced review process", extra={
        "workflow_step": "start_review",
        "repository_url": state.get("repository_url"),
        "state_keys": list(state.keys()) if state else []
    })
    
    # Simulate repository fetching with detailed tracing
    try:
        # Validate input
        repository_url = state.get("repository_url")
        if not repository_url:
            raise ValueError("Repository URL is required")
        
        logger.debug("Validating repository URL", extra={
            "repository_url": repository_url
        })
        
        # Simulate repository info fetching
        await asyncio.sleep(0.1)  # Simulate API call
        
        # Create mock repository info
        repository_info = RepositoryInfo(
            url=repository_url,
            name=repository_url.split('/')[-1],
            full_name=repository_url.replace('https://github.com/', ''),
            description="Enhanced repository with tracing",
            language="Python",
            stars=42,
            forks=7,
            size=2048,
            default_branch="main",
            topics=["python", "tracing", "debugging"],
            file_structure=[
                {"path": "main.py", "type": "file", "size": 1000},
                {"path": "tests/", "type": "directory", "size": 0},
                {"path": "tests/test_main.py", "type": "file", "size": 500}
            ],
            recent_commits=[
                {"sha": "abc123", "message": "Add tracing support", "author": "developer"}
            ]
        )
        
        # Determine repository type
        repository_type = "python"  # Simplified detection
        
        # Enable appropriate tools based on repository type
        enabled_tools = []
        if repository_type == "python":
            enabled_tools = ["pylint_analysis", "flake8_analysis", "bandit_analysis", "code_review"]
        elif repository_type == "javascript":
            enabled_tools = ["eslint_analysis", "code_review"]
        else:
            enabled_tools = ["code_review"]
        
        logger.info("Repository analysis completed", extra={
            "repository_type": repository_type,
            "enabled_tools": enabled_tools,
            "file_count": len(repository_info["file_structure"])
        })
        
        # Prepare result with enhanced state
        result = {
            "current_step": "analyze_code",
            "status": ReviewStatus.ANALYZING_CODE,
            "repository_info": repository_info,
            "repository_type": repository_type,
            "enabled_tools": enabled_tools,
            "total_files": len([f for f in repository_info["file_structure"] if f["type"] == "file"]),
            "start_time": state.get("start_time") or "2025-07-08T17:00:00"
        }
        
        logger.info("Enhanced review process started successfully", extra={
            "workflow_step": "start_review",
            "result_keys": list(result.keys()),
            "next_step": result["current_step"]
        })
        
        return result
        
    except Exception as e:
        logger.error("Failed to start review process", extra={
            "workflow_step": "start_review",
            "error": str(e),
            "repository_url": state.get("repository_url")
        }, exc_info=True)
        
        return {
            "current_step": "error_handler",
            "status": ReviewStatus.FAILED,
            "error_message": f"Failed to start review: {str(e)}"
        }


@traced_node
async def enhanced_analyze_code_node(state: ReviewState) -> Dict[str, Any]:
    """Enhanced analyze_code_node with comprehensive tracing."""
    logger.info("Starting enhanced code analysis", extra={
        "workflow_step": "analyze_code",
        "current_step": state.get("current_step"),
        "enabled_tools": state.get("enabled_tools", []),
        "repository_type": state.get("repository_type")
    })
    
    try:
        enabled_tools = state.get("enabled_tools", [])
        repository_info = state.get("repository_info")
        
        if not enabled_tools:
            logger.warning("No tools enabled for analysis")
            return {
                "current_step": "generate_report",
                "status": ReviewStatus.GENERATING_REPORT,
                "tool_results": {},
                "files_analyzed": []
            }
        
        # Simulate tool execution with detailed tracing
        tool_results = {}
        files_analyzed = []
        failed_tools = []
        
        for tool_name in enabled_tools:
            logger.debug(f"Executing tool: {tool_name}", extra={
                "tool_name": tool_name,
                "workflow_step": "analyze_code"
            })
            
            try:
                # Simulate tool execution
                await asyncio.sleep(0.05)  # Simulate tool execution time
                
                # Create mock tool result based on tool type
                if tool_name == "pylint_analysis":
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=True,
                        result={
                            "score": 8.5,
                            "issues": [
                                {"file": "main.py", "line": 10, "severity": "warning", "message": "Unused variable 'x'"},
                                {"file": "main.py", "line": 25, "severity": "info", "message": "Consider using f-strings"}
                            ],
                            "files_checked": ["main.py"]
                        },
                        error_message=None,
                        execution_time=0.05,
                        timestamp="2025-07-08T17:00:00"
                    )
                elif tool_name == "code_review":
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=True,
                        result={
                            "overall_quality": "good",
                            "suggestions": [
                                "Add more comprehensive docstrings",
                                "Consider adding type hints",
                                "Improve error handling in main function"
                            ],
                            "complexity_score": 7.2,
                            "maintainability": "high"
                        },
                        error_message=None,
                        execution_time=0.08,
                        timestamp="2025-07-08T17:00:00"
                    )
                else:
                    # Generic tool result
                    tool_result = ToolResult(
                        tool_name=tool_name,
                        success=True,
                        result={"status": "completed", "issues": []},
                        error_message=None,
                        execution_time=0.03,
                        timestamp="2025-07-08T17:00:00"
                    )
                
                tool_results[tool_name] = tool_result
                
                # Track analyzed files
                if "files_checked" in tool_result["result"]:
                    files_analyzed.extend(tool_result["result"]["files_checked"])
                
                logger.info(f"Tool execution completed: {tool_name}", extra={
                    "tool_name": tool_name,
                    "success": tool_result["success"],
                    "execution_time": tool_result["execution_time"]
                })
                
            except Exception as tool_error:
                logger.error(f"Tool execution failed: {tool_name}", extra={
                    "tool_name": tool_name,
                    "error": str(tool_error)
                })
                failed_tools.append(tool_name)
        
        # Remove duplicates from files_analyzed
        files_analyzed = list(set(files_analyzed))
        
        # Calculate analysis summary
        successful_tools = len(tool_results)
        total_issues = sum(
            len(result["result"].get("issues", []))
            for result in tool_results.values()
            if result["success"]
        )
        
        logger.info("Code analysis completed", extra={
            "workflow_step": "analyze_code",
            "successful_tools": successful_tools,
            "failed_tools": len(failed_tools),
            "files_analyzed": len(files_analyzed),
            "total_issues": total_issues
        })
        
        result = {
            "current_step": "generate_report",
            "status": ReviewStatus.GENERATING_REPORT,
            "tool_results": tool_results,
            "failed_tools": failed_tools,
            "files_analyzed": files_analyzed,
            "analysis_summary": {
                "successful_tools": successful_tools,
                "failed_tools": len(failed_tools),
                "total_issues": total_issues,
                "files_processed": len(files_analyzed)
            }
        }
        
        return result
        
    except Exception as e:
        logger.error("Code analysis failed", extra={
            "workflow_step": "analyze_code",
            "error": str(e)
        }, exc_info=True)
        
        return {
            "current_step": "error_handler",
            "status": ReviewStatus.FAILED,
            "error_message": f"Code analysis failed: {str(e)}"
        }


@traced_node
async def enhanced_generate_report_node(state: ReviewState) -> Dict[str, Any]:
    """Enhanced generate_report_node with comprehensive tracing."""
    logger.info("Starting enhanced report generation", extra={
        "workflow_step": "generate_report",
        "current_step": state.get("current_step"),
        "tool_results_count": len(state.get("tool_results", {})),
        "files_analyzed": len(state.get("files_analyzed", []))
    })
    
    try:
        tool_results = state.get("tool_results", {})
        failed_tools = state.get("failed_tools", [])
        files_analyzed = state.get("files_analyzed", [])
        repository_info = state.get("repository_info", {})
        
        # Simulate report generation
        await asyncio.sleep(0.1)  # Simulate report processing time
        
        # Aggregate results
        total_issues = 0
        all_suggestions = []
        quality_scores = []
        
        for tool_name, tool_result in tool_results.items():
            if tool_result["success"]:
                result_data = tool_result["result"]
                
                # Count issues
                if "issues" in result_data:
                    total_issues += len(result_data["issues"])
                
                # Collect suggestions
                if "suggestions" in result_data:
                    all_suggestions.extend(result_data["suggestions"])
                
                # Collect quality scores
                if "score" in result_data:
                    quality_scores.append(result_data["score"])
                elif "complexity_score" in result_data:
                    quality_scores.append(result_data["complexity_score"])
        
        # Calculate overall quality score
        overall_score = sum(quality_scores) / len(quality_scores) if quality_scores else 7.0
        
        # Generate comprehensive report
        final_report = {
            "repository": {
                "url": repository_info.get("url", ""),
                "name": repository_info.get("name", ""),
                "language": repository_info.get("language", ""),
                "stars": repository_info.get("stars", 0)
            },
            "analysis_summary": {
                "tools_executed": len(tool_results),
                "tools_failed": len(failed_tools),
                "files_analyzed": len(files_analyzed),
                "total_issues": total_issues,
                "overall_score": round(overall_score, 2)
            },
            "detailed_results": tool_results,
            "failed_tools": failed_tools,
            "recommendations": list(set(all_suggestions)),  # Remove duplicates
            "files_processed": files_analyzed,
            "generated_at": "2025-07-08T17:00:00",
            "report_version": "1.0"
        }
        
        logger.info("Report generation completed", extra={
            "workflow_step": "generate_report",
            "total_issues": total_issues,
            "overall_score": overall_score,
            "recommendations_count": len(final_report["recommendations"]),
            "report_size": len(str(final_report))
        })
        
        result = {
            "current_step": "complete",
            "status": ReviewStatus.COMPLETED,
            "final_report": final_report,
            "report_generated": True,
            "end_time": "2025-07-08T17:00:00"
        }
        
        return result
        
    except Exception as e:
        logger.error("Report generation failed", extra={
            "workflow_step": "generate_report",
            "error": str(e)
        }, exc_info=True)
        
        return {
            "current_step": "error_handler",
            "status": ReviewStatus.FAILED,
            "error_message": f"Report generation failed: {str(e)}"
        }


@traced_node
async def enhanced_error_handler_node(state: ReviewState) -> Dict[str, Any]:
    """Enhanced error_handler_node with comprehensive tracing."""
    error_message = state.get("error_message", "Unknown error occurred")
    failed_tools = state.get("failed_tools", [])
    current_step = state.get("current_step", "unknown")
    
    logger.error("Enhanced workflow error handler activated", extra={
        "workflow_step": "error_handler",
        "error_message": error_message,
        "failed_tools": failed_tools,
        "current_step": current_step,
        "state_keys": list(state.keys()) if state else []
    })
    
    try:
        # Analyze error context
        error_context = {
            "original_step": current_step,
            "error_message": error_message,
            "failed_tools": failed_tools,
            "partial_results": bool(state.get("tool_results")),
            "files_processed": len(state.get("files_analyzed", [])),
            "recovery_possible": len(failed_tools) < len(state.get("enabled_tools", []))
        }
        
        # Generate error report
        error_report = {
            "error_summary": {
                "message": error_message,
                "step": current_step,
                "timestamp": "2025-07-08T17:00:00"
            },
            "context": error_context,
            "partial_results": state.get("tool_results", {}),
            "recovery_suggestions": [
                "Check repository URL and access permissions",
                "Verify tool configurations",
                "Review network connectivity",
                "Check API rate limits"
            ]
        }
        
        logger.info("Error analysis completed", extra={
            "workflow_step": "error_handler",
            "error_context": error_context,
            "recovery_possible": error_context["recovery_possible"]
        })
        
        result = {
            "current_step": "error_handled",
            "status": ReviewStatus.FAILED,
            "error_handled": True,
            "error_report": error_report,
            "end_time": "2025-07-08T17:00:00"
        }
        
        logger.info("Enhanced error handled successfully", extra={
            "workflow_step": "error_handler",
            "result": result
        })
        
        return result
        
    except Exception as e:
        logger.critical("Error handler itself failed", extra={
            "workflow_step": "error_handler",
            "handler_error": str(e),
            "original_error": error_message
        }, exc_info=True)
        
        return {
            "current_step": "critical_error",
            "status": ReviewStatus.FAILED,
            "error_handled": False,
            "critical_error": True,
            "error_message": f"Error handler failed: {str(e)}"
        }


async def test_enhanced_nodes():
    """Test the enhanced nodes with tracing."""
    print("Testing Enhanced Nodes with Tracing")
    print("=" * 50)
    
    # Create initial state
    initial_state = {
        "messages": [],
        "current_step": "start_review",
        "status": ReviewStatus.INITIALIZING,
        "error_message": None,
        "repository_url": "https://github.com/test/enhanced-repo",
        "repository_info": None,
        "repository_type": None,
        "enabled_tools": [],
        "tool_results": {},
        "failed_tools": [],
        "analysis_results": None,
        "files_analyzed": [],
        "total_files": 0,
        "review_config": {"tracing_enabled": True},
        "start_time": "2025-07-08T17:00:00",
        "end_time": None,
        "notifications_sent": [],
        "report_generated": False,
        "final_report": None
    }
    
    # Test complete workflow with tracing
    print("\n1. Testing start_review_node...")
    result1 = await enhanced_start_review_node(initial_state)
    print(f"Result: {result1.get('current_step')} - {result1.get('status')}")
    
    # Update state with result
    current_state = initial_state.copy()
    current_state.update(result1)
    
    print("\n2. Testing analyze_code_node...")
    result2 = await enhanced_analyze_code_node(current_state)
    print(f"Result: {result2.get('current_step')} - Tools: {len(result2.get('tool_results', {}))}")
    
    # Update state with result
    current_state.update(result2)
    
    print("\n3. Testing generate_report_node...")
    result3 = await enhanced_generate_report_node(current_state)
    print(f"Result: {result3.get('current_step')} - Report generated: {result3.get('report_generated')}")
    
    # Test error handling
    print("\n4. Testing error_handler_node...")
    error_state = initial_state.copy()
    error_state.update({
        "error_message": "Test error for tracing",
        "failed_tools": ["test_tool"],
        "current_step": "analyze_code"
    })
    
    result4 = await enhanced_error_handler_node(error_state)
    print(f"Result: {result4.get('current_step')} - Error handled: {result4.get('error_handled')}")
    
    print("\n" + "=" * 50)
    print("Enhanced nodes testing completed!")
    
    # Show trace summary
    from scripts.node_tracing import get_tracer
    tracer = get_tracer()
    summary = tracer.get_all_traces_summary()
    print(f"\nTrace Summary:")
    print(f"Total traces: {summary['total_traces']}")
    print(f"Recent completed traces:")
    for trace in summary['recent_completed']:
        print(f"  - {trace['node_name']}: {trace['success']} ({trace['execution_time']:.3f}s)")


if __name__ == "__main__":
    asyncio.run(test_enhanced_nodes())
