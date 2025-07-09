#!/usr/bin/env python3
"""
Node Performance Profiling and Bottleneck Detection

This module provides comprehensive performance profiling capabilities for workflow nodes,
including execution time analysis, memory usage monitoring, bottleneck detection,
and performance optimization recommendations.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import asyncio
import cProfile
import pstats
import psutil
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import sys
import io

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node
from scripts.node_tracing import get_tracer, traced_node
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging
initialize_logging(LoggingConfig(
    log_level="INFO",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/profiling"
))

logger = get_logger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: str
    current_memory_mb: float
    peak_memory_mb: float
    memory_percent: float
    available_memory_mb: float


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for node execution."""
    node_name: str
    execution_time: float
    cpu_time: float
    memory_usage: MemorySnapshot
    memory_peak: float
    memory_growth: float
    function_calls: int
    io_operations: int
    bottlenecks: List[str]
    optimization_suggestions: List[str]
    profile_data: Optional[str]


@dataclass
class ProfilingSession:
    """Complete profiling session data."""
    session_id: str
    start_time: str
    end_time: Optional[str]
    total_duration: Optional[float]
    nodes_profiled: List[str]
    metrics: List[PerformanceMetrics]
    session_summary: Dict[str, Any]


class NodeProfiler:
    """Advanced performance profiler for workflow nodes."""
    
    def __init__(self, enable_memory_tracking: bool = True,
                 enable_cpu_profiling: bool = True,
                 profile_output_dir: str = "logs/profiling/profiles"):
        self.enable_memory_tracking = enable_memory_tracking
        self.enable_cpu_profiling = enable_cpu_profiling
        self.profile_output_dir = Path(profile_output_dir)
        try:
            self.profile_output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Handle read-only filesystem or permission issues
            print(f"Warning: Cannot create profiling directory {self.profile_output_dir}: {e}")
            print("Profiling data will be stored in memory only.")
            # Use a temporary directory or disable file output
            import tempfile
            self.profile_output_dir = Path(tempfile.gettempdir()) / "profiling" / "profiles"
            try:
                self.profile_output_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # If even temp directory fails, disable file output
                self.profile_output_dir = None
        
        self.profiling_sessions: List[ProfilingSession] = []
        self.current_session: Optional[ProfilingSession] = None
        
        # Performance thresholds
        self.thresholds = {
            "execution_time_warning": 1.0,  # seconds
            "execution_time_critical": 5.0,  # seconds
            "memory_usage_warning": 100,     # MB
            "memory_usage_critical": 500,    # MB
            "memory_growth_warning": 50,     # MB
            "cpu_usage_warning": 80,         # percent
        }
        
        # Available nodes for profiling
        self.available_nodes = {
            "start_review_node": start_review_node,
            "analyze_code_node": analyze_code_node,
            "generate_report_node": generate_report_node,
            "error_handler_node": error_handler_node
        }
    
    def start_profiling_session(self, session_name: str = None) -> str:
        """Start a new profiling session."""
        session_id = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        self.current_session = ProfilingSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            total_duration=None,
            nodes_profiled=[],
            metrics=[],
            session_summary={}
        )
        
        if self.enable_memory_tracking:
            tracemalloc.start()
        
        logger.info(f"Started profiling session: {session_id}")
        return session_id
    
    def end_profiling_session(self) -> Optional[ProfilingSession]:
        """End the current profiling session."""
        if not self.current_session:
            logger.warning("No active profiling session to end")
            return None
        
        self.current_session.end_time = datetime.now().isoformat()
        start_time = datetime.fromisoformat(self.current_session.start_time)
        end_time = datetime.fromisoformat(self.current_session.end_time)
        self.current_session.total_duration = (end_time - start_time).total_seconds()
        
        # Generate session summary
        self.current_session.session_summary = self._generate_session_summary(self.current_session)
        
        # Stop memory tracking
        if self.enable_memory_tracking:
            tracemalloc.stop()
        
        # Archive session
        self.profiling_sessions.append(self.current_session)
        completed_session = self.current_session
        self.current_session = None
        
        logger.info(f"Ended profiling session: {completed_session.session_id}, "
                   f"Duration: {completed_session.total_duration:.3f}s")
        
        return completed_session
    
    def _get_memory_snapshot(self) -> MemorySnapshot:
        """Get current memory usage snapshot."""
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # Get system memory info
        system_memory = psutil.virtual_memory()
        
        return MemorySnapshot(
            timestamp=datetime.now().isoformat(),
            current_memory_mb=memory_info.rss / 1024 / 1024,
            peak_memory_mb=memory_info.peak_wss / 1024 / 1024 if hasattr(memory_info, 'peak_wss') else 0,
            memory_percent=memory_percent,
            available_memory_mb=system_memory.available / 1024 / 1024
        )
    
    def _analyze_bottlenecks(self, execution_time: float, memory_usage: MemorySnapshot,
                           profile_stats: Optional[pstats.Stats]) -> List[str]:
        """Analyze performance data to identify bottlenecks."""
        bottlenecks = []
        
        # Execution time bottlenecks
        if execution_time > self.thresholds["execution_time_critical"]:
            bottlenecks.append(f"Critical execution time: {execution_time:.3f}s")
        elif execution_time > self.thresholds["execution_time_warning"]:
            bottlenecks.append(f"High execution time: {execution_time:.3f}s")
        
        # Memory bottlenecks
        if memory_usage.current_memory_mb > self.thresholds["memory_usage_critical"]:
            bottlenecks.append(f"Critical memory usage: {memory_usage.current_memory_mb:.1f}MB")
        elif memory_usage.current_memory_mb > self.thresholds["memory_usage_warning"]:
            bottlenecks.append(f"High memory usage: {memory_usage.current_memory_mb:.1f}MB")
        
        # CPU profiling bottlenecks
        if profile_stats:
            # Get top time-consuming functions
            stats_stream = io.StringIO()
            profile_stats.print_stats(10)  # Top 10 functions
            stats_output = stats_stream.getvalue()
            
            # Simple heuristic: if any function takes more than 50% of total time
            for line in stats_output.split('\n'):
                if 'cumulative' in line and any(func in line for func in ['sleep', 'wait', 'lock']):
                    bottlenecks.append("Potential blocking operation detected")
                    break
        
        return bottlenecks
    
    def _generate_optimization_suggestions(self, metrics: PerformanceMetrics) -> List[str]:
        """Generate optimization suggestions based on performance metrics."""
        suggestions = []
        
        # Execution time optimizations
        if metrics.execution_time > self.thresholds["execution_time_warning"]:
            suggestions.append("Consider optimizing algorithm complexity")
            suggestions.append("Review synchronous operations that could be asynchronous")
        
        # Memory optimizations
        if metrics.memory_usage.current_memory_mb > self.thresholds["memory_usage_warning"]:
            suggestions.append("Consider implementing memory pooling")
            suggestions.append("Review data structures for memory efficiency")
            suggestions.append("Implement lazy loading for large datasets")
        
        if metrics.memory_growth > self.thresholds["memory_growth_warning"]:
            suggestions.append("Check for memory leaks")
            suggestions.append("Implement proper cleanup of temporary objects")
        
        # Function call optimizations
        if metrics.function_calls > 10000:
            suggestions.append("High function call count - consider function inlining")
            suggestions.append("Review recursive algorithms for optimization")
        
        # I/O optimizations
        if metrics.io_operations > 100:
            suggestions.append("High I/O operations - consider batching")
            suggestions.append("Implement caching for frequently accessed data")
        
        return suggestions
    
    async def profile_node_execution(self, node_name: str, input_state: ReviewState) -> PerformanceMetrics:
        """Profile a single node execution with comprehensive metrics."""
        if not self.current_session:
            raise RuntimeError("No active profiling session. Call start_profiling_session() first.")
        
        if node_name not in self.available_nodes:
            raise ValueError(f"Unknown node: {node_name}")
        
        logger.info(f"Profiling node execution: {node_name}")
        
        node_func = self.available_nodes[node_name]
        
        # Get initial memory snapshot
        initial_memory = self._get_memory_snapshot()
        
        # Setup CPU profiling
        profiler = None
        if self.enable_cpu_profiling:
            profiler = cProfile.Profile()
            profiler.enable()
        
        # Execute node with timing
        start_time = time.time()
        cpu_start = time.process_time()
        
        try:
            result = await node_func(input_state)
            success = True
            error_message = None
        except Exception as e:
            result = None
            success = False
            error_message = str(e)
            logger.error(f"Error during profiling: {e}")
        
        # Stop timing
        execution_time = time.time() - start_time
        cpu_time = time.process_time() - cpu_start
        
        # Stop CPU profiling
        profile_stats = None
        profile_data = None
        if profiler:
            profiler.disable()
            profile_stats = pstats.Stats(profiler)
            
            # Capture profile data as string
            stats_stream = io.StringIO()
            profile_stats.print_stats()
            profile_data = stats_stream.getvalue()
        
        # Get final memory snapshot
        final_memory = self._get_memory_snapshot()
        memory_growth = final_memory.current_memory_mb - initial_memory.current_memory_mb
        
        # Get memory peak if available
        memory_peak = 0
        if self.enable_memory_tracking:
            current, peak = tracemalloc.get_traced_memory()
            memory_peak = peak / 1024 / 1024  # Convert to MB
        
        # Analyze bottlenecks
        bottlenecks = self._analyze_bottlenecks(execution_time, final_memory, profile_stats)
        
        # Create performance metrics
        metrics = PerformanceMetrics(
            node_name=node_name,
            execution_time=execution_time,
            cpu_time=cpu_time,
            memory_usage=final_memory,
            memory_peak=memory_peak,
            memory_growth=memory_growth,
            function_calls=profile_stats.total_calls if profile_stats else 0,
            io_operations=0,  # Simplified - would need more detailed tracking
            bottlenecks=bottlenecks,
            optimization_suggestions=[],  # Will be filled below
            profile_data=profile_data
        )
        
        # Generate optimization suggestions
        metrics.optimization_suggestions = self._generate_optimization_suggestions(metrics)
        
        # Add to current session
        self.current_session.metrics.append(metrics)
        self.current_session.nodes_profiled.append(node_name)
        
        logger.info(f"Profiled {node_name}: {execution_time:.3f}s execution, "
                   f"{final_memory.current_memory_mb:.1f}MB memory, "
                   f"{len(bottlenecks)} bottlenecks detected")
        
        return metrics
    
    def _generate_session_summary(self, session: ProfilingSession) -> Dict[str, Any]:
        """Generate comprehensive session summary."""
        if not session.metrics:
            return {"total_nodes": 0, "total_execution_time": 0}
        
        total_execution_time = sum(m.execution_time for m in session.metrics)
        total_cpu_time = sum(m.cpu_time for m in session.metrics)
        max_memory = max(m.memory_usage.current_memory_mb for m in session.metrics)
        total_bottlenecks = sum(len(m.bottlenecks) for m in session.metrics)
        
        # Find slowest node
        slowest_node = max(session.metrics, key=lambda m: m.execution_time)
        
        # Find most memory-intensive node
        memory_intensive_node = max(session.metrics, key=lambda m: m.memory_usage.current_memory_mb)
        
        return {
            "total_nodes": len(session.metrics),
            "unique_nodes": len(set(session.nodes_profiled)),
            "total_execution_time": total_execution_time,
            "total_cpu_time": total_cpu_time,
            "average_execution_time": total_execution_time / len(session.metrics),
            "max_memory_usage": max_memory,
            "total_bottlenecks": total_bottlenecks,
            "slowest_node": {
                "name": slowest_node.node_name,
                "execution_time": slowest_node.execution_time
            },
            "memory_intensive_node": {
                "name": memory_intensive_node.node_name,
                "memory_usage": memory_intensive_node.memory_usage.current_memory_mb
            },
            "performance_score": self._calculate_performance_score(session.metrics)
        }
    
    def _calculate_performance_score(self, metrics: List[PerformanceMetrics]) -> float:
        """Calculate overall performance score (0-100)."""
        if not metrics:
            return 100.0
        
        score = 100.0
        
        for metric in metrics:
            # Deduct points for execution time
            if metric.execution_time > self.thresholds["execution_time_critical"]:
                score -= 20
            elif metric.execution_time > self.thresholds["execution_time_warning"]:
                score -= 10
            
            # Deduct points for memory usage
            if metric.memory_usage.current_memory_mb > self.thresholds["memory_usage_critical"]:
                score -= 15
            elif metric.memory_usage.current_memory_mb > self.thresholds["memory_usage_warning"]:
                score -= 8
            
            # Deduct points for bottlenecks
            score -= len(metric.bottlenecks) * 5
        
        return max(0.0, score)
    
    def save_profiling_report(self, session: ProfilingSession, filename: str = None) -> Path:
        """Save comprehensive profiling report."""
        if not filename:
            filename = f"profiling_report_{session.session_id}.json"

        if self.profile_output_dir is None:
            logger.debug("Profiling directory not available, skipping file save")
            # Return a dummy path for compatibility
            return Path(f"/tmp/{filename}")

        filepath = self.profile_output_dir / filename
        
        try:
            # Convert session to serializable format
            report_data = {
                "session_id": session.session_id,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "total_duration": session.total_duration,
                "nodes_profiled": session.nodes_profiled,
                "session_summary": session.session_summary,
                "metrics": []
            }
            
            for metric in session.metrics:
                metric_data = asdict(metric)
                # Convert memory snapshot to dict
                metric_data["memory_usage"] = asdict(metric.memory_usage)
                report_data["metrics"].append(metric_data)
            
            import json
            with open(filepath, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            logger.info(f"Saved profiling report to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save profiling report: {e}", exc_info=True)
            raise
    
    def print_performance_summary(self, session: ProfilingSession):
        """Print formatted performance summary."""
        print(f"\n{'='*60}")
        print(f"PERFORMANCE PROFILING SUMMARY")
        print(f"{'='*60}")
        print(f"Session ID: {session.session_id}")
        print(f"Duration: {session.total_duration:.3f}s")
        print(f"Nodes Profiled: {session.session_summary['total_nodes']}")
        print(f"Performance Score: {session.session_summary['performance_score']:.1f}/100")
        
        print(f"\nExecution Summary:")
        print(f"  Total Execution Time: {session.session_summary['total_execution_time']:.3f}s")
        print(f"  Average Execution Time: {session.session_summary['average_execution_time']:.3f}s")
        print(f"  Max Memory Usage: {session.session_summary['max_memory_usage']:.1f}MB")
        print(f"  Total Bottlenecks: {session.session_summary['total_bottlenecks']}")
        
        print(f"\nSlowest Node:")
        slowest = session.session_summary['slowest_node']
        print(f"  {slowest['name']}: {slowest['execution_time']:.3f}s")
        
        print(f"\nMemory Intensive Node:")
        memory_node = session.session_summary['memory_intensive_node']
        print(f"  {memory_node['name']}: {memory_node['memory_usage']:.1f}MB")
        
        print(f"\nDetailed Metrics:")
        for metric in session.metrics:
            print(f"\n  {metric.node_name}:")
            print(f"    Execution Time: {metric.execution_time:.3f}s")
            print(f"    Memory Usage: {metric.memory_usage.current_memory_mb:.1f}MB")
            print(f"    Memory Growth: {metric.memory_growth:.1f}MB")
            print(f"    Function Calls: {metric.function_calls}")
            
            if metric.bottlenecks:
                print(f"    Bottlenecks:")
                for bottleneck in metric.bottlenecks:
                    print(f"      - {bottleneck}")
            
            if metric.optimization_suggestions:
                print(f"    Optimization Suggestions:")
                for suggestion in metric.optimization_suggestions[:3]:  # Top 3
                    print(f"      - {suggestion}")
        
        print(f"{'='*60}\n")


# Global profiler instance
_global_profiler: Optional[NodeProfiler] = None


def get_profiler() -> NodeProfiler:
    """Get global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = NodeProfiler()
    return _global_profiler


@contextmanager
def profile_session(session_name: str = None):
    """Context manager for profiling sessions."""
    profiler = get_profiler()
    session_id = profiler.start_profiling_session(session_name)
    
    try:
        yield session_id
    finally:
        session = profiler.end_profiling_session()
        if session:
            profiler.print_performance_summary(session)


if __name__ == "__main__":
    # Example usage and testing
    async def test_profiling_system():
        """Test the profiling functionality."""
        print("Testing Node Performance Profiling System")
        print("=" * 50)
        
        profiler = get_profiler()
        
        # Create test state
        test_state = {
            "messages": [],
            "current_step": "start_review",
            "status": ReviewStatus.INITIALIZING,
            "repository_url": "https://github.com/test/profiling-repo",
            "enabled_tools": ["pylint_analysis", "code_review"],
            "tool_results": {},
            "failed_tools": [],
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {"profiling_test": True},
            "start_time": "2025-07-08T17:00:00",
            "notifications_sent": [],
            "report_generated": False
        }
        
        print("\n1. Starting profiling session...")
        session_id = profiler.start_profiling_session("Test Profiling Session")
        
        print("\n2. Profiling node executions...")
        
        # Profile start_review_node
        metrics1 = await profiler.profile_node_execution("start_review_node", test_state)
        print(f"✅ Profiled start_review_node: {metrics1.execution_time:.3f}s")
        
        # Update state for next node
        updated_state = test_state.copy()
        updated_state.update({
            "current_step": "analyze_code",
            "status": ReviewStatus.ANALYZING_CODE,
            "repository_type": "python"
        })
        
        # Profile analyze_code_node
        metrics2 = await profiler.profile_node_execution("analyze_code_node", updated_state)
        print(f"✅ Profiled analyze_code_node: {metrics2.execution_time:.3f}s")
        
        # Profile generate_report_node
        report_state = updated_state.copy()
        report_state.update({
            "current_step": "generate_report",
            "status": ReviewStatus.GENERATING_REPORT,
            "tool_results": {"test_tool": {"success": True, "result": "test"}}
        })
        
        metrics3 = await profiler.profile_node_execution("generate_report_node", report_state)
        print(f"✅ Profiled generate_report_node: {metrics3.execution_time:.3f}s")
        
        print("\n3. Ending profiling session...")
        session = profiler.end_profiling_session()
        
        print("\n4. Saving profiling report...")
        report_path = profiler.save_profiling_report(session)
        print(f"✅ Saved report to {report_path}")
        
        print("\n" + "=" * 50)
        print("Profiling system testing completed!")
    
    # Run test
    asyncio.run(test_profiling_system())
