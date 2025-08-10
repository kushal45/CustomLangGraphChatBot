#!/usr/bin/env python3
"""
Node Execution Replay Functionality

This module provides comprehensive replay capabilities for workflow node executions,
enabling debugging of complex scenarios, regression testing, and deterministic
reproduction of node behaviors from serialized execution data.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node
from scripts.node_serialization import NodeSerializer, SerializedData, get_serializer
from scripts.node_tracing import NodeTracer, get_tracer, traced_node
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging
initialize_logging(LoggingConfig(
    log_level="INFO",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/replay"
))

logger = get_logger(__name__)


class ReplayMode(Enum):
    """Replay execution modes."""
    EXACT = "exact"  # Exact reproduction with original timing
    FAST = "fast"    # Fast replay without delays
    STEP = "step"    # Step-by-step with user interaction
    DEBUG = "debug"  # Debug mode with breakpoints


@dataclass
class ReplayStep:
    """Individual step in a replay sequence."""
    step_id: str
    node_name: str
    input_data: SerializedData
    expected_output: Optional[SerializedData]
    timestamp: str
    execution_time: float
    success: bool
    error_message: Optional[str]


@dataclass
class ReplaySequence:
    """Complete sequence of replay steps."""
    sequence_id: str
    name: str
    description: str
    created_at: str
    steps: List[ReplayStep]
    metadata: Dict[str, Any]


@dataclass
class ReplayResult:
    """Result of a replay execution."""
    sequence_id: str
    step_id: str
    node_name: str
    success: bool
    actual_output: Any
    expected_output: Any
    execution_time: float
    differences: List[str]
    error_message: Optional[str]


class NodeReplayEngine:
    """Advanced replay engine for node executions."""
    
    def __init__(self, mode: ReplayMode = ReplayMode.FAST):
        self.mode = mode
        self.serializer = get_serializer()
        self.tracer = get_tracer()
        self.replay_history: List[ReplayResult] = []
        
        # Available nodes for replay
        self.available_nodes = {
            "start_review_node": start_review_node,
            "analyze_code_node": analyze_code_node,
            "generate_report_node": generate_report_node,
            "error_handler_node": error_handler_node
        }
        
        # Create replay directory
        self.replay_dir = Path("logs/replay/sequences")
        try:
            self.replay_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Handle read-only filesystem or permission issues
            print(f"Warning: Cannot create replay directory {self.replay_dir}: {e}")
            print("Replay sequences will be stored in memory only.")
            # Use a temporary directory or disable file output
            import tempfile
            self.replay_dir = Path(tempfile.gettempdir()) / "replay" / "sequences"
            try:
                self.replay_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # If even temp directory fails, disable file output
                self.replay_dir = None
    
    def create_replay_step(self, node_name: str, input_state: ReviewState,
                          expected_output: Optional[Dict[str, Any]] = None) -> ReplayStep:
        """Create a replay step from current execution data."""
        logger.info(f"Creating replay step for {node_name}")
        
        # Serialize input
        input_serialized = self.serializer.serialize_node_input(node_name, input_state)
        
        # Serialize expected output if provided
        expected_serialized = None
        if expected_output:
            expected_serialized = self.serializer.serialize_node_output(node_name, expected_output)
        
        step = ReplayStep(
            step_id=f"{node_name}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            node_name=node_name,
            input_data=input_serialized,
            expected_output=expected_serialized,
            timestamp=datetime.now().isoformat(),
            execution_time=0.0,  # Will be filled during actual execution
            success=True,  # Will be updated during replay
            error_message=None
        )
        
        logger.info(f"Created replay step: {step.step_id}")
        return step
    
    async def record_node_execution(self, node_name: str, input_state: ReviewState) -> ReplayStep:
        """Record a node execution for later replay."""
        logger.info(f"Recording execution of {node_name}")
        
        if node_name not in self.available_nodes:
            raise ValueError(f"Unknown node: {node_name}")
        
        node_func = self.available_nodes[node_name]
        
        # Execute node and measure time
        start_time = time.time()
        try:
            output = await node_func(input_state)
            execution_time = time.time() - start_time
            success = True
            error_message = None
        except Exception as e:
            output = None
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
            logger.error(f"Error during recording: {e}")
        
        # Create replay step
        step = self.create_replay_step(node_name, input_state, output)
        step.execution_time = execution_time
        step.success = success
        step.error_message = error_message
        
        logger.info(f"Recorded execution: {step.step_id}, Success: {success}, Time: {execution_time:.3f}s")
        return step
    
    def create_replay_sequence(self, name: str, description: str, steps: List[ReplayStep]) -> ReplaySequence:
        """Create a replay sequence from multiple steps."""
        sequence = ReplaySequence(
            sequence_id=f"seq_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            steps=steps,
            metadata={
                "total_steps": len(steps),
                "nodes_involved": list(set(step.node_name for step in steps)),
                "estimated_duration": sum(step.execution_time for step in steps)
            }
        )
        
        logger.info(f"Created replay sequence: {sequence.sequence_id} with {len(steps)} steps")
        return sequence
    
    def save_replay_sequence(self, sequence: ReplaySequence) -> Path:
        """Save replay sequence to file."""
        if self.replay_dir is None:
            logger.debug("Replay directory not available, skipping file save")
            # Return a dummy path for compatibility
            filename = f"{sequence.name.replace(' ', '_')}_{sequence.sequence_id}.json"
            return Path(f"/tmp/{filename}")

        filename = f"{sequence.name.replace(' ', '_')}_{sequence.sequence_id}.json"
        filepath = self.replay_dir / filename

        try:
            # Convert to serializable format
            sequence_data = {
                "sequence_id": sequence.sequence_id,
                "name": sequence.name,
                "description": sequence.description,
                "created_at": sequence.created_at,
                "metadata": sequence.metadata,
                "steps": []
            }
            
            for step in sequence.steps:
                step_data = {
                    "step_id": step.step_id,
                    "node_name": step.node_name,
                    "timestamp": step.timestamp,
                    "execution_time": step.execution_time,
                    "success": step.success,
                    "error_message": step.error_message,
                    "input_data": {
                        "data": step.input_data.data,
                        "metadata": asdict(step.input_data.metadata),
                        "schema_version": step.input_data.schema_version
                    }
                }
                
                if step.expected_output:
                    step_data["expected_output"] = {
                        "data": step.expected_output.data,
                        "metadata": asdict(step.expected_output.metadata),
                        "schema_version": step.expected_output.schema_version
                    }
                
                sequence_data["steps"].append(step_data)
            
            with open(filepath, 'w') as f:
                json.dump(sequence_data, f, indent=2, default=str)
            
            logger.info(f"Saved replay sequence to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save replay sequence: {e}", exc_info=True)
            raise
    
    def load_replay_sequence(self, filepath: Union[str, Path]) -> ReplaySequence:
        """Load replay sequence from file."""
        filepath = Path(filepath)
        
        try:
            with open(filepath, 'r') as f:
                sequence_data = json.load(f)
            
            # Reconstruct steps
            steps = []
            for step_data in sequence_data["steps"]:
                # Reconstruct input data
                input_metadata = step_data["input_data"]["metadata"]
                input_metadata["format"] = input_metadata["format"]  # Already a string from JSON
                
                input_serialized = SerializedData(
                    data=step_data["input_data"]["data"],
                    metadata=self.serializer._create_metadata_from_dict(input_metadata),
                    schema_version=step_data["input_data"]["schema_version"]
                )
                
                # Reconstruct expected output if present
                expected_serialized = None
                if "expected_output" in step_data:
                    output_metadata = step_data["expected_output"]["metadata"]
                    expected_serialized = SerializedData(
                        data=step_data["expected_output"]["data"],
                        metadata=self.serializer._create_metadata_from_dict(output_metadata),
                        schema_version=step_data["expected_output"]["schema_version"]
                    )
                
                step = ReplayStep(
                    step_id=step_data["step_id"],
                    node_name=step_data["node_name"],
                    input_data=input_serialized,
                    expected_output=expected_serialized,
                    timestamp=step_data["timestamp"],
                    execution_time=step_data["execution_time"],
                    success=step_data["success"],
                    error_message=step_data.get("error_message")
                )
                
                steps.append(step)
            
            sequence = ReplaySequence(
                sequence_id=sequence_data["sequence_id"],
                name=sequence_data["name"],
                description=sequence_data["description"],
                created_at=sequence_data["created_at"],
                steps=steps,
                metadata=sequence_data["metadata"]
            )
            
            logger.info(f"Loaded replay sequence: {sequence.sequence_id} with {len(steps)} steps")
            return sequence
            
        except Exception as e:
            logger.error(f"Failed to load replay sequence: {e}", exc_info=True)
            raise
    
    async def replay_step(self, step: ReplayStep) -> ReplayResult:
        """Replay a single step."""
        logger.info(f"Replaying step: {step.step_id} ({step.node_name})")
        
        if step.node_name not in self.available_nodes:
            raise ValueError(f"Unknown node: {step.node_name}")
        
        node_func = self.available_nodes[step.node_name]
        
        # Deserialize input
        input_state = self.serializer.deserialize_node_input(step.input_data)
        
        # Execute node
        start_time = time.time()
        try:
            actual_output = await node_func(input_state)
            execution_time = time.time() - start_time
            success = True
            error_message = None
        except Exception as e:
            actual_output = None
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
            logger.error(f"Error during replay: {e}")
        
        # Compare with expected output if available
        expected_output = None
        differences = []
        
        if step.expected_output:
            expected_output = self.serializer.deserialize_node_output(step.expected_output)
            differences = self._compare_outputs(actual_output, expected_output)
        
        result = ReplayResult(
            sequence_id="",  # Will be set by sequence replay
            step_id=step.step_id,
            node_name=step.node_name,
            success=success,
            actual_output=actual_output,
            expected_output=expected_output,
            execution_time=execution_time,
            differences=differences,
            error_message=error_message
        )
        
        self.replay_history.append(result)
        
        logger.info(f"Replayed step {step.step_id}: Success={success}, "
                   f"Time={execution_time:.3f}s, Differences={len(differences)}")
        
        return result
    
    async def replay_sequence(self, sequence: ReplaySequence) -> List[ReplayResult]:
        """Replay an entire sequence."""
        logger.info(f"Replaying sequence: {sequence.sequence_id} ({sequence.name})")
        
        results = []
        
        for i, step in enumerate(sequence.steps):
            logger.info(f"Replaying step {i+1}/{len(sequence.steps)}: {step.node_name}")
            
            # Handle different replay modes
            if self.mode == ReplayMode.STEP:
                input(f"Press Enter to execute step {i+1}: {step.node_name}")
            elif self.mode == ReplayMode.EXACT:
                # Wait for original execution time (simplified)
                await asyncio.sleep(min(step.execution_time, 0.1))
            
            result = await self.replay_step(step)
            result.sequence_id = sequence.sequence_id
            results.append(result)
            
            # Stop on error if in debug mode
            if self.mode == ReplayMode.DEBUG and not result.success:
                logger.warning(f"Stopping replay due to error in step {step.step_id}")
                break
        
        logger.info(f"Completed replay of sequence {sequence.sequence_id}: "
                   f"{len(results)} steps executed")
        
        return results
    
    def _compare_outputs(self, actual: Any, expected: Any) -> List[str]:
        """Compare actual and expected outputs."""
        differences = []
        
        if type(actual) != type(expected):
            differences.append(f"Type mismatch: {type(actual)} vs {type(expected)}")
            return differences
        
        if isinstance(actual, dict) and isinstance(expected, dict):
            # Compare dictionary keys
            actual_keys = set(actual.keys())
            expected_keys = set(expected.keys())
            
            if actual_keys != expected_keys:
                missing = expected_keys - actual_keys
                extra = actual_keys - expected_keys
                if missing:
                    differences.append(f"Missing keys: {missing}")
                if extra:
                    differences.append(f"Extra keys: {extra}")
            
            # Compare values for common keys
            for key in actual_keys & expected_keys:
                if actual[key] != expected[key]:
                    differences.append(f"Value mismatch for '{key}': {actual[key]} vs {expected[key]}")
        
        elif actual != expected:
            differences.append(f"Value mismatch: {actual} vs {expected}")
        
        return differences
    
    def get_replay_summary(self) -> Dict[str, Any]:
        """Get summary of replay operations."""
        if not self.replay_history:
            return {"total_replays": 0}
        
        successful = [r for r in self.replay_history if r.success]
        failed = [r for r in self.replay_history if not r.success]
        
        return {
            "total_replays": len(self.replay_history),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.replay_history) * 100,
            "average_execution_time": sum(r.execution_time for r in self.replay_history) / len(self.replay_history),
            "nodes_replayed": list(set(r.node_name for r in self.replay_history)),
            "total_differences": sum(len(r.differences) for r in self.replay_history),
            "recent_replays": [
                {
                    "step_id": r.step_id,
                    "node_name": r.node_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "differences": len(r.differences)
                }
                for r in self.replay_history[-5:]
            ]
        }


# Global replay engine instance
_global_replay_engine: Optional[NodeReplayEngine] = None


def get_replay_engine() -> NodeReplayEngine:
    """Get global replay engine instance."""
    global _global_replay_engine
    if _global_replay_engine is None:
        _global_replay_engine = NodeReplayEngine()
    return _global_replay_engine


if __name__ == "__main__":
    # Example usage and testing
    async def test_replay_system():
        """Test the replay functionality."""
        print("Testing Node Replay System")
        print("=" * 50)
        
        replay_engine = get_replay_engine()
        
        # Create test state
        test_state = {
            "messages": [],
            "current_step": "start_review",
            "status": ReviewStatus.INITIALIZING,
            "repository_url": "https://github.com/test/replay-repo",
            "enabled_tools": ["pylint_analysis"],
            "tool_results": {},
            "failed_tools": [],
            "files_analyzed": [],
            "total_files": 0,
            "review_config": {"replay_test": True},
            "start_time": "2025-07-08T17:00:00",
            "notifications_sent": [],
            "report_generated": False
        }
        
        print("\n1. Recording node executions...")
        
        # Record multiple node executions
        steps = []
        
        # Record start_review_node
        step1 = await replay_engine.record_node_execution("start_review_node", test_state)
        steps.append(step1)
        
        # Update state for next node
        updated_state = test_state.copy()
        updated_state.update({
            "current_step": "analyze_code",
            "status": ReviewStatus.ANALYZING_CODE,
            "repository_type": "python",
            "enabled_tools": ["pylint_analysis", "code_review"]
        })
        
        # Record analyze_code_node
        step2 = await replay_engine.record_node_execution("analyze_code_node", updated_state)
        steps.append(step2)
        
        print(f"✅ Recorded {len(steps)} execution steps")
        
        print("\n2. Creating and saving replay sequence...")
        
        # Create replay sequence
        sequence = replay_engine.create_replay_sequence(
            "Test Workflow Replay",
            "Test sequence for replay functionality",
            steps
        )
        
        # Save sequence
        filepath = replay_engine.save_replay_sequence(sequence)
        print(f"✅ Saved replay sequence to {filepath}")
        
        print("\n3. Loading and replaying sequence...")
        
        # Load sequence
        loaded_sequence = replay_engine.load_replay_sequence(filepath)
        print(f"✅ Loaded sequence: {loaded_sequence.name}")
        
        # Replay sequence
        results = await replay_engine.replay_sequence(loaded_sequence)
        print(f"✅ Replayed {len(results)} steps")
        
        # Show results
        for result in results:
            status = "✅" if result.success else "❌"
            print(f"  {status} {result.node_name}: {result.execution_time:.3f}s, "
                  f"Differences: {len(result.differences)}")
        
        print("\n4. Replay Summary:")
        summary = replay_engine.get_replay_summary()
        print(json.dumps(summary, indent=2, default=str))
        
        print("\n" + "=" * 50)
        print("Replay system testing completed!")
    
    # Run test
    asyncio.run(test_replay_system())
