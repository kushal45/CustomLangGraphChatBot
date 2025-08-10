#!/usr/bin/env python3
"""
Individual Node Debugging Utility

This script provides comprehensive debugging capabilities for individual workflow nodes,
allowing developers to execute, inspect, and debug nodes in isolation with detailed
logging, state inspection, and performance monitoring.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
Usage:
    python scripts/debug_node.py --node start_review_node --state-file debug_state.json
    python scripts/debug_node.py --node analyze_code_node --interactive
    python scripts/debug_node.py --list-nodes
"""

import argparse
import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import workflow components
from state import ReviewState, ReviewStatus, RepositoryInfo, ToolResult, AnalysisResults
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging for debugging
initialize_logging(LoggingConfig(
    log_level="DEBUG",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/debug"
))

logger = get_logger(__name__)


@dataclass
class NodeExecutionResult:
    """Result of node execution with debugging information."""
    node_name: str
    success: bool
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    execution_time: float
    input_state_size: int
    output_size: int
    timestamp: str
    traceback: Optional[str] = None


class StateSerializer:
    """Utilities for serializing and deserializing ReviewState objects."""
    
    @staticmethod
    def serialize_state(state: ReviewState) -> Dict[str, Any]:
        """Serialize ReviewState to JSON-compatible dictionary."""
        serialized = {}
        
        for key, value in state.items():
            if key == "status" and value:
                # Handle ReviewStatus enum
                serialized[key] = value.value if hasattr(value, 'value') else str(value)
            elif key == "messages":
                # Handle BaseMessage objects
                serialized[key] = [
                    {"type": type(msg).__name__, "content": str(msg)} 
                    for msg in (value or [])
                ]
            else:
                # Handle other types
                serialized[key] = value
        
        return serialized
    
    @staticmethod
    def deserialize_state(data: Dict[str, Any]) -> ReviewState:
        """Deserialize dictionary to ReviewState object."""
        # Handle status enum
        if "status" in data and isinstance(data["status"], str):
            try:
                data["status"] = ReviewStatus(data["status"])
            except ValueError:
                data["status"] = ReviewStatus.INITIALIZING
        
        # Handle messages (simplified for debugging)
        if "messages" not in data:
            data["messages"] = []
        
        # Ensure all required fields exist with defaults
        defaults = {
            "messages": [],
            "current_step": "initializing",
            "status": ReviewStatus.INITIALIZING,
            "error_message": None,
            "repository_url": "",
            "repository_info": None,
            "repository_type": None,
            "enabled_tools": [],
            "tool_results": {},
            "failed_tools": [],
            "analysis_results": None,
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {},
            "start_time": None,
            "end_time": None,
            "notifications_sent": [],
            "report_generated": False,
            "final_report": None
        }
        
        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        return data


class NodeDebugger:
    """Main debugging utility for individual workflow nodes."""
    
    # Available nodes for debugging
    AVAILABLE_NODES = {
        "start_review_node": start_review_node,
        "analyze_code_node": analyze_code_node,
        "generate_report_node": generate_report_node,
        "error_handler_node": error_handler_node
    }
    
    def __init__(self):
        self.execution_history: List[NodeExecutionResult] = []
    
    def list_available_nodes(self) -> List[str]:
        """Get list of available nodes for debugging."""
        return list(self.AVAILABLE_NODES.keys())
    
    def create_sample_state(self, node_name: str) -> ReviewState:
        """Create sample state appropriate for the given node."""
        base_state = {
            "messages": [],
            "current_step": "initializing",
            "status": ReviewStatus.INITIALIZING,
            "error_message": None,
            "repository_url": "https://github.com/test/debug-repo",
            "repository_info": None,
            "repository_type": "python",
            "enabled_tools": ["pylint_analysis", "code_review"],
            "tool_results": {},
            "failed_tools": [],
            "analysis_results": None,
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {"debug_mode": True},
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "notifications_sent": [],
            "report_generated": False,
            "final_report": None
        }
        
        # Customize state based on node
        if node_name == "start_review_node":
            base_state["current_step"] = "start_review"
            base_state["status"] = ReviewStatus.INITIALIZING
        elif node_name == "analyze_code_node":
            base_state["current_step"] = "analyze_code"
            base_state["status"] = ReviewStatus.ANALYZING_CODE
            base_state["repository_info"] = {
                "url": "https://github.com/test/debug-repo",
                "name": "debug-repo",
                "full_name": "test/debug-repo",
                "description": "Debug repository for testing",
                "language": "Python",
                "stars": 1,
                "forks": 0,
                "size": 1024,
                "default_branch": "main",
                "topics": ["debug", "testing"],
                "file_structure": [
                    {"path": "main.py", "type": "file", "size": 500}
                ],
                "recent_commits": [
                    {"sha": "debug123", "message": "Debug commit", "author": "debugger"}
                ]
            }
        elif node_name == "generate_report_node":
            base_state["current_step"] = "generate_report"
            base_state["status"] = ReviewStatus.GENERATING_REPORT
            base_state["tool_results"] = {
                "pylint_analysis": {
                    "tool_name": "pylint_analysis",
                    "success": True,
                    "result": {"score": 8.5, "issues": []},
                    "error_message": None,
                    "execution_time": 2.1,
                    "timestamp": datetime.now().isoformat()
                }
            }
        elif node_name == "error_handler_node":
            base_state["current_step"] = "error_handler"
            base_state["status"] = ReviewStatus.FAILED
            base_state["error_message"] = "Debug error for testing"
            base_state["failed_tools"] = ["debug_tool"]
        
        return base_state
    
    async def execute_node(self, node_name: str, state: ReviewState, 
                          enable_tracing: bool = True) -> NodeExecutionResult:
        """Execute a single node with debugging and performance monitoring."""
        if node_name not in self.AVAILABLE_NODES:
            raise ValueError(f"Unknown node: {node_name}. Available: {list(self.AVAILABLE_NODES.keys())}")
        
        node_func = self.AVAILABLE_NODES[node_name]
        
        logger.info(f"Starting execution of {node_name}", extra={
            "node_name": node_name,
            "input_state_keys": list(state.keys()),
            "current_step": state.get("current_step"),
            "status": state.get("status")
        })
        
        # Measure input state size
        input_state_size = len(json.dumps(StateSerializer.serialize_state(state), default=str))
        
        # Execute node with timing
        start_time = time.time()
        result = None
        error = None
        traceback_str = None
        
        try:
            if enable_tracing:
                logger.debug(f"Input state for {node_name}: {StateSerializer.serialize_state(state)}")
            
            result = await node_func(state)
            
            if enable_tracing:
                logger.debug(f"Output from {node_name}: {result}")
            
            logger.info(f"Successfully executed {node_name}", extra={
                "node_name": node_name,
                "output_keys": list(result.keys()) if result else [],
                "execution_time": time.time() - start_time
            })
            
        except Exception as e:
            error = str(e)
            traceback_str = traceback.format_exc()
            logger.error(f"Error executing {node_name}: {error}", extra={
                "node_name": node_name,
                "error": error,
                "traceback": traceback_str
            })
        
        execution_time = time.time() - start_time
        output_size = len(json.dumps(result, default=str)) if result else 0
        
        # Create execution result
        execution_result = NodeExecutionResult(
            node_name=node_name,
            success=error is None,
            result=result,
            error=error,
            execution_time=execution_time,
            input_state_size=input_state_size,
            output_size=output_size,
            timestamp=datetime.now().isoformat(),
            traceback=traceback_str
        )
        
        self.execution_history.append(execution_result)
        return execution_result
    
    def print_execution_summary(self, result: NodeExecutionResult):
        """Print a formatted summary of node execution."""
        print(f"\n{'='*60}")
        print(f"NODE EXECUTION SUMMARY: {result.node_name}")
        print(f"{'='*60}")
        print(f"Status: {'✅ SUCCESS' if result.success else '❌ FAILED'}")
        print(f"Execution Time: {result.execution_time:.3f}s")
        print(f"Input State Size: {result.input_state_size} bytes")
        print(f"Output Size: {result.output_size} bytes")
        print(f"Timestamp: {result.timestamp}")
        
        if result.success and result.result:
            print(f"\nOutput Keys: {list(result.result.keys())}")
            print(f"Next Step: {result.result.get('current_step', 'N/A')}")
        
        if result.error:
            print(f"\nError: {result.error}")
            if result.traceback:
                print(f"Traceback:\n{result.traceback}")
        
        print(f"{'='*60}\n")
    
    def save_execution_log(self, filepath: str):
        """Save execution history to file."""
        log_data = []
        for result in self.execution_history:
            log_data.append({
                "node_name": result.node_name,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time,
                "input_state_size": result.input_state_size,
                "output_size": result.output_size,
                "timestamp": result.timestamp,
                "traceback": result.traceback
            })
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"Execution log saved to: {filepath}")


def load_state_from_file(filepath: str) -> ReviewState:
    """Load ReviewState from JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return StateSerializer.deserialize_state(data)
    except Exception as e:
        logger.error(f"Failed to load state from {filepath}: {e}")
        raise


def save_state_to_file(state: ReviewState, filepath: str):
    """Save ReviewState to JSON file."""
    try:
        serialized = StateSerializer.serialize_state(state)
        with open(filepath, 'w') as f:
            json.dump(serialized, f, indent=2, default=str)
        print(f"State saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save state to {filepath}: {e}")
        raise


async def interactive_mode(debugger: NodeDebugger):
    """Interactive debugging mode."""
    print("\n🔧 Interactive Node Debugging Mode")
    print("Available commands:")
    print("  list - List available nodes")
    print("  run <node_name> - Run node with sample state")
    print("  state <node_name> - Show sample state for node")
    print("  history - Show execution history")
    print("  quit - Exit interactive mode")
    
    while True:
        try:
            command = input("\ndebug> ").strip().split()
            if not command:
                continue
            
            if command[0] == "quit":
                break
            elif command[0] == "list":
                nodes = debugger.list_available_nodes()
                print(f"Available nodes: {', '.join(nodes)}")
            elif command[0] == "run" and len(command) > 1:
                node_name = command[1]
                if node_name in debugger.AVAILABLE_NODES:
                    state = debugger.create_sample_state(node_name)
                    result = await debugger.execute_node(node_name, state)
                    debugger.print_execution_summary(result)
                else:
                    print(f"Unknown node: {node_name}")
            elif command[0] == "state" and len(command) > 1:
                node_name = command[1]
                if node_name in debugger.AVAILABLE_NODES:
                    state = debugger.create_sample_state(node_name)
                    serialized = StateSerializer.serialize_state(state)
                    print(json.dumps(serialized, indent=2, default=str))
                else:
                    print(f"Unknown node: {node_name}")
            elif command[0] == "history":
                if debugger.execution_history:
                    for i, result in enumerate(debugger.execution_history):
                        status = "✅" if result.success else "❌"
                        print(f"{i+1}. {result.node_name} {status} ({result.execution_time:.3f}s)")
                else:
                    print("No execution history")
            else:
                print("Unknown command. Type 'quit' to exit.")
        
        except KeyboardInterrupt:
            print("\nExiting interactive mode...")
            break
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """Main entry point for the node debugging utility."""
    parser = argparse.ArgumentParser(
        description="Debug individual workflow nodes with detailed inspection and logging"
    )
    
    parser.add_argument("--node", "-n", help="Node name to execute")
    parser.add_argument("--state-file", "-s", help="JSON file containing ReviewState")
    parser.add_argument("--output-file", "-o", help="Save execution result to file")
    parser.add_argument("--list-nodes", "-l", action="store_true", help="List available nodes")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive debugging mode")
    parser.add_argument("--sample-state", action="store_true", help="Generate sample state for node")
    parser.add_argument("--save-log", help="Save execution history to file")
    parser.add_argument("--enable-tracing", action="store_true", default=True, help="Enable detailed tracing")
    
    args = parser.parse_args()
    
    debugger = NodeDebugger()
    
    # List available nodes
    if args.list_nodes:
        nodes = debugger.list_available_nodes()
        print("Available nodes for debugging:")
        for node in nodes:
            print(f"  - {node}")
        return
    
    # Interactive mode
    if args.interactive:
        await interactive_mode(debugger)
        return
    
    # Generate sample state
    if args.sample_state and args.node:
        if args.node not in debugger.AVAILABLE_NODES:
            print(f"Error: Unknown node '{args.node}'. Use --list-nodes to see available nodes.")
            return
        
        state = debugger.create_sample_state(args.node)
        serialized = StateSerializer.serialize_state(state)
        
        if args.output_file:
            save_state_to_file(state, args.output_file)
        else:
            print(json.dumps(serialized, indent=2, default=str))
        return
    
    # Execute specific node
    if args.node:
        if args.node not in debugger.AVAILABLE_NODES:
            print(f"Error: Unknown node '{args.node}'. Use --list-nodes to see available nodes.")
            return
        
        # Load or create state
        if args.state_file:
            state = load_state_from_file(args.state_file)
        else:
            print(f"No state file provided. Using sample state for {args.node}")
            state = debugger.create_sample_state(args.node)
        
        # Execute node
        result = await debugger.execute_node(args.node, state, args.enable_tracing)
        debugger.print_execution_summary(result)
        
        # Save result if requested
        if args.output_file:
            output_data = {
                "execution_result": {
                    "node_name": result.node_name,
                    "success": result.success,
                    "result": result.result,
                    "error": result.error,
                    "execution_time": result.execution_time,
                    "timestamp": result.timestamp
                },
                "input_state": StateSerializer.serialize_state(state)
            }
            
            with open(args.output_file, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            print(f"Execution result saved to: {args.output_file}")
    
    # Save execution log
    if args.save_log:
        debugger.save_execution_log(args.save_log)
    
    # If no specific action, show help
    if not any([args.node, args.list_nodes, args.interactive, args.sample_state]):
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
