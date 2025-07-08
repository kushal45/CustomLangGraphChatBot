#!/usr/bin/env python3
"""
Node Execution Tracing and Logging Enhancements

This module provides advanced tracing and logging capabilities for workflow node execution,
including detailed execution traces, performance monitoring, state change tracking,
and comprehensive debugging information.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import asyncio
import functools
import json
import time
import traceback
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus
from logging_config import get_logger, LoggingConfig, initialize_logging

# Initialize enhanced logging for tracing
initialize_logging(LoggingConfig(
    log_level="DEBUG",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/tracing",
    enable_json_logging=True
))

logger = get_logger(__name__)


@dataclass
class ExecutionTrace:
    """Detailed execution trace for a node."""
    node_name: str
    trace_id: str
    start_time: str
    end_time: Optional[str]
    execution_time: Optional[float]
    input_state_hash: str
    output_hash: Optional[str]
    success: bool
    error_message: Optional[str]
    stack_trace: Optional[str]
    performance_metrics: Dict[str, Any]
    state_changes: List[Dict[str, Any]]
    log_entries: List[Dict[str, Any]]


@dataclass
class StateChange:
    """Represents a change in state during node execution."""
    timestamp: str
    field: str
    old_value: Any
    new_value: Any
    change_type: str  # 'added', 'modified', 'removed'


class NodeTracer:
    """Advanced tracing utility for node execution."""
    
    def __init__(self, enable_state_tracking: bool = True, 
                 enable_performance_tracking: bool = True,
                 trace_output_dir: str = "logs/traces"):
        self.enable_state_tracking = enable_state_tracking
        self.enable_performance_tracking = enable_performance_tracking
        self.trace_output_dir = Path(trace_output_dir)
        try:
            self.trace_output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Handle read-only filesystem or permission issues
            print(f"Warning: Cannot create trace directory {self.trace_output_dir}: {e}")
            print("Traces will be stored in memory only.")
            # Use a temporary directory or disable file output
            import tempfile
            self.trace_output_dir = Path(tempfile.gettempdir()) / "traces"
            try:
                self.trace_output_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # If even temp directory fails, disable file output
                self.trace_output_dir = None
        
        self.active_traces: Dict[str, ExecutionTrace] = {}
        self.completed_traces: List[ExecutionTrace] = []
        
        # Performance tracking
        self.performance_thresholds = {
            "execution_time_warning": 1.0,  # seconds
            "execution_time_error": 5.0,    # seconds
            "memory_usage_warning": 100,    # MB
            "state_size_warning": 10000     # bytes
        }
    
    def generate_trace_id(self, node_name: str) -> str:
        """Generate unique trace ID for node execution."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"{node_name}_{timestamp}"
    
    def calculate_state_hash(self, state: ReviewState) -> str:
        """Calculate hash of state for change detection."""
        try:
            state_str = json.dumps(self._serialize_state_for_hash(state), sort_keys=True)
            return str(hash(state_str))
        except Exception:
            return "hash_error"
    
    def _serialize_state_for_hash(self, state: ReviewState) -> Dict[str, Any]:
        """Serialize state for hash calculation."""
        serialized = {}
        for key, value in state.items():
            if key == "status" and value:
                serialized[key] = value.value if hasattr(value, 'value') else str(value)
            elif key == "messages":
                serialized[key] = [str(msg) for msg in (value or [])]
            else:
                serialized[key] = value
        return serialized
    
    def detect_state_changes(self, old_state: ReviewState, new_state: ReviewState) -> List[StateChange]:
        """Detect changes between two states."""
        changes = []
        timestamp = datetime.now().isoformat()
        
        # Get all keys from both states
        all_keys = set(old_state.keys()) | set(new_state.keys())
        
        for key in all_keys:
            old_value = old_state.get(key)
            new_value = new_state.get(key)
            
            if key not in old_state:
                changes.append(StateChange(
                    timestamp=timestamp,
                    field=key,
                    old_value=None,
                    new_value=new_value,
                    change_type="added"
                ))
            elif key not in new_state:
                changes.append(StateChange(
                    timestamp=timestamp,
                    field=key,
                    old_value=old_value,
                    new_value=None,
                    change_type="removed"
                ))
            elif old_value != new_value:
                changes.append(StateChange(
                    timestamp=timestamp,
                    field=key,
                    old_value=old_value,
                    new_value=new_value,
                    change_type="modified"
                ))
        
        return changes
    
    def start_trace(self, node_name: str, input_state: ReviewState) -> str:
        """Start tracing node execution."""
        trace_id = self.generate_trace_id(node_name)
        
        trace = ExecutionTrace(
            node_name=node_name,
            trace_id=trace_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            execution_time=None,
            input_state_hash=self.calculate_state_hash(input_state),
            output_hash=None,
            success=False,
            error_message=None,
            stack_trace=None,
            performance_metrics={},
            state_changes=[],
            log_entries=[]
        )
        
        self.active_traces[trace_id] = trace
        
        logger.info(f"Started tracing node execution", extra={
            "trace_id": trace_id,
            "node_name": node_name,
            "input_state_hash": trace.input_state_hash,
            "tracing_enabled": True
        })
        
        return trace_id
    
    def end_trace(self, trace_id: str, output_result: Optional[Dict[str, Any]] = None, 
                  error: Optional[Exception] = None) -> ExecutionTrace:
        """End tracing node execution."""
        if trace_id not in self.active_traces:
            logger.warning(f"Trace ID not found: {trace_id}")
            return None
        
        trace = self.active_traces[trace_id]
        end_time = datetime.now()
        trace.end_time = end_time.isoformat()
        
        # Calculate execution time
        start_time = datetime.fromisoformat(trace.start_time)
        trace.execution_time = (end_time - start_time).total_seconds()
        
        # Handle success/error
        if error:
            trace.success = False
            trace.error_message = str(error)
            trace.stack_trace = traceback.format_exc()
        else:
            trace.success = True
            if output_result:
                trace.output_hash = str(hash(json.dumps(output_result, sort_keys=True, default=str)))
        
        # Performance analysis
        if self.enable_performance_tracking:
            trace.performance_metrics = self._analyze_performance(trace)
        
        # Move to completed traces
        self.completed_traces.append(trace)
        del self.active_traces[trace_id]
        
        logger.info(f"Completed tracing node execution", extra={
            "trace_id": trace_id,
            "node_name": trace.node_name,
            "execution_time": trace.execution_time,
            "success": trace.success,
            "error_message": trace.error_message
        })
        
        # Save trace to file
        self._save_trace_to_file(trace)
        
        return trace
    
    def _analyze_performance(self, trace: ExecutionTrace) -> Dict[str, Any]:
        """Analyze performance metrics for the trace."""
        metrics = {
            "execution_time": trace.execution_time,
            "performance_warnings": [],
            "performance_score": "good"
        }
        
        # Check execution time thresholds
        if trace.execution_time > self.performance_thresholds["execution_time_error"]:
            metrics["performance_warnings"].append(f"Execution time exceeded error threshold: {trace.execution_time:.2f}s")
            metrics["performance_score"] = "poor"
        elif trace.execution_time > self.performance_thresholds["execution_time_warning"]:
            metrics["performance_warnings"].append(f"Execution time exceeded warning threshold: {trace.execution_time:.2f}s")
            metrics["performance_score"] = "fair"
        
        return metrics
    
    def add_state_change(self, trace_id: str, old_state: ReviewState, new_state: ReviewState):
        """Add state change information to trace."""
        if trace_id not in self.active_traces or not self.enable_state_tracking:
            return
        
        changes = self.detect_state_changes(old_state, new_state)
        trace = self.active_traces[trace_id]
        
        for change in changes:
            trace.state_changes.append(asdict(change))
            
            logger.debug(f"State change detected", extra={
                "trace_id": trace_id,
                "field": change.field,
                "change_type": change.change_type,
                "old_value": str(change.old_value)[:100],  # Truncate for logging
                "new_value": str(change.new_value)[:100]
            })
    
    def add_log_entry(self, trace_id: str, level: str, message: str, extra_data: Dict[str, Any] = None):
        """Add log entry to trace."""
        if trace_id not in self.active_traces:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "extra_data": extra_data or {}
        }
        
        self.active_traces[trace_id].log_entries.append(log_entry)
    
    def _save_trace_to_file(self, trace: ExecutionTrace):
        """Save trace to JSON file."""
        if self.trace_output_dir is None:
            logger.debug("Trace output directory not available, skipping file save")
            return

        try:
            filename = f"{trace.node_name}_{trace.trace_id}.json"
            filepath = self.trace_output_dir / filename

            trace_data = asdict(trace)

            with open(filepath, 'w') as f:
                json.dump(trace_data, f, indent=2, default=str)

            logger.debug(f"Trace saved to file: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save trace to file: {e}")
    
    def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a trace."""
        # Check active traces first
        if trace_id in self.active_traces:
            trace = self.active_traces[trace_id]
            return {
                "trace_id": trace.trace_id,
                "node_name": trace.node_name,
                "status": "active",
                "start_time": trace.start_time,
                "duration": (datetime.now() - datetime.fromisoformat(trace.start_time)).total_seconds()
            }
        
        # Check completed traces
        for trace in self.completed_traces:
            if trace.trace_id == trace_id:
                return {
                    "trace_id": trace.trace_id,
                    "node_name": trace.node_name,
                    "status": "completed",
                    "success": trace.success,
                    "execution_time": trace.execution_time,
                    "state_changes": len(trace.state_changes),
                    "log_entries": len(trace.log_entries)
                }
        
        return None
    
    def get_all_traces_summary(self) -> Dict[str, Any]:
        """Get summary of all traces."""
        return {
            "active_traces": len(self.active_traces),
            "completed_traces": len(self.completed_traces),
            "total_traces": len(self.active_traces) + len(self.completed_traces),
            "active_trace_ids": list(self.active_traces.keys()),
            "recent_completed": [
                {
                    "trace_id": trace.trace_id,
                    "node_name": trace.node_name,
                    "success": trace.success,
                    "execution_time": trace.execution_time
                }
                for trace in self.completed_traces[-5:]  # Last 5 traces
            ]
        }


# Global tracer instance
_global_tracer: Optional[NodeTracer] = None


def get_tracer() -> NodeTracer:
    """Get global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = NodeTracer()
    return _global_tracer


def traced_node(func: Callable) -> Callable:
    """Decorator to add tracing to node functions."""
    @functools.wraps(func)
    async def wrapper(state: ReviewState) -> Dict[str, Any]:
        tracer = get_tracer()
        node_name = func.__name__
        
        # Start tracing
        trace_id = tracer.start_trace(node_name, state)
        
        try:
            # Store original state for change detection
            original_state = state.copy() if tracer.enable_state_tracking else None
            
            # Execute the node function
            logger.info(f"Executing node with tracing", extra={
                "node_name": node_name,
                "trace_id": trace_id,
                "input_state_keys": list(state.keys())
            })
            
            result = await func(state)
            
            # Detect state changes if enabled
            if tracer.enable_state_tracking and original_state:
                # Create new state with result applied
                new_state = state.copy()
                new_state.update(result)
                tracer.add_state_change(trace_id, original_state, new_state)
            
            # End tracing successfully
            tracer.end_trace(trace_id, result)
            
            logger.info(f"Node execution completed successfully", extra={
                "node_name": node_name,
                "trace_id": trace_id,
                "output_keys": list(result.keys()) if result else []
            })
            
            return result
            
        except Exception as e:
            # End tracing with error
            tracer.end_trace(trace_id, error=e)
            
            logger.error(f"Node execution failed", extra={
                "node_name": node_name,
                "trace_id": trace_id,
                "error": str(e)
            }, exc_info=True)
            
            raise
    
    return wrapper


@contextmanager
def trace_context(node_name: str, state: ReviewState):
    """Context manager for manual tracing."""
    tracer = get_tracer()
    trace_id = tracer.start_trace(node_name, state)
    
    try:
        yield trace_id
        tracer.end_trace(trace_id)
    except Exception as e:
        tracer.end_trace(trace_id, error=e)
        raise


def log_with_trace(trace_id: str, level: str, message: str, **kwargs):
    """Log message with trace context."""
    tracer = get_tracer()
    tracer.add_log_entry(trace_id, level, message, kwargs)
    
    # Also log normally
    logger_func = getattr(logger, level.lower(), logger.info)
    logger_func(message, extra={"trace_id": trace_id, **kwargs})


# Convenience functions for different log levels
def trace_debug(trace_id: str, message: str, **kwargs):
    """Log debug message with trace context."""
    log_with_trace(trace_id, "DEBUG", message, **kwargs)


def trace_info(trace_id: str, message: str, **kwargs):
    """Log info message with trace context."""
    log_with_trace(trace_id, "INFO", message, **kwargs)


def trace_warning(trace_id: str, message: str, **kwargs):
    """Log warning message with trace context."""
    log_with_trace(trace_id, "WARNING", message, **kwargs)


def trace_error(trace_id: str, message: str, **kwargs):
    """Log error message with trace context."""
    log_with_trace(trace_id, "ERROR", message, **kwargs)


if __name__ == "__main__":
    # Example usage and testing
    import asyncio
    
    async def example_node(state: ReviewState) -> Dict[str, Any]:
        """Example node for testing tracing."""
        await asyncio.sleep(0.1)  # Simulate work
        return {"current_step": "next_step", "processed": True}
    
    async def test_tracing():
        """Test the tracing functionality."""
        # Create sample state
        state = {
            "messages": [],
            "current_step": "test",
            "status": ReviewStatus.INITIALIZING,
            "repository_url": "https://github.com/test/repo",
            "enabled_tools": [],
            "tool_results": {},
            "failed_tools": [],
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {},
            "notifications_sent": [],
            "report_generated": False
        }
        
        # Test manual tracing
        print("Testing manual tracing...")
        with trace_context("test_node", state) as trace_id:
            trace_info(trace_id, "Starting test node execution")
            await asyncio.sleep(0.1)
            trace_info(trace_id, "Test node execution completed")
        
        # Test decorator tracing
        print("Testing decorator tracing...")
        traced_example = traced_node(example_node)
        result = await traced_example(state)
        print(f"Result: {result}")
        
        # Print trace summary
        tracer = get_tracer()
        summary = tracer.get_all_traces_summary()
        print(f"Trace summary: {json.dumps(summary, indent=2)}")
    
    # Run test
    asyncio.run(test_tracing())
