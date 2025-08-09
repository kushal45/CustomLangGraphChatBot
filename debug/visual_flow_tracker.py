"""
Visual Flow Tracker for LangGraph Debugging
Provides comprehensive visual representation of workflow execution with debugging breakpoints.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import sys

class FlowStage(Enum):
    """Enumeration of workflow stages for visual tracking."""
    INITIALIZATION = "🚀 INITIALIZATION"
    URL_VALIDATION = "🔍 URL_VALIDATION" 
    TOOL_REGISTRY = "🔧 TOOL_REGISTRY"
    GITHUB_API_CALL = "🌐 GITHUB_API_CALL"
    DATA_PROCESSING = "📊 DATA_PROCESSING"
    TOOL_SELECTION = "⚙️ TOOL_SELECTION"
    COMPLETION = "✅ COMPLETION"
    ERROR_HANDLING = "❌ ERROR_HANDLING"

class FlowVisualizer:
    """Visual flow tracker for LangGraph workflow debugging."""
    
    def __init__(self):
        self.flow_steps = []
        self.current_stage = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now()
        
    def track_flow_step(self, step_name: str, stage: FlowStage, 
                       state: Dict[str, Any], context: Optional[Dict[str, Any]] = None,
                       status: str = "IN_PROGRESS") -> None:
        """Track a flow step with visual representation."""
        
        step_data = {
            "timestamp": datetime.now().isoformat(),
            "step_name": step_name,
            "stage": stage,
            "status": status,
            "state_summary": self._create_state_summary(state),
            "context": context or {},
            "duration_ms": self._get_duration_ms()
        }
        
        self.flow_steps.append(step_data)
        self.current_stage = stage
        
        # Print visual representation
        self._print_flow_step(step_data)
        
    def _create_state_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a concise summary of the state for visualization."""
        summary = {
            "keys_count": len(state.keys()) if state else 0,
            "has_repository_url": "repository_url" in state if state else False,
            "has_repository_info": "repository_info" in state if state else False,
            "current_step": state.get("current_step") if state else None,
            "status": str(state.get("status")) if state else None
        }
        
        # Add specific data based on what's available
        if state and "repository_url" in state:
            summary["repository_url"] = state["repository_url"]
            
        if state and "enabled_tools" in state:
            summary["enabled_tools_count"] = len(state.get("enabled_tools", []))
            
        if state and "repository_type" in state:
            summary["repository_type"] = state["repository_type"]
            
        return summary
        
    def _get_duration_ms(self) -> int:
        """Get duration since start in milliseconds."""
        return int((datetime.now() - self.start_time).total_seconds() * 1000)
        
    def _print_flow_step(self, step_data: Dict[str, Any]) -> None:
        """Print visual representation of the flow step."""
        stage = step_data["stage"]
        step_name = step_data["step_name"]
        status = step_data["status"]
        duration = step_data["duration_ms"]
        
        # Status emoji
        status_emoji = {
            "IN_PROGRESS": "🔄",
            "COMPLETED": "✅", 
            "FAILED": "❌",
            "SKIPPED": "⏭️"
        }.get(status, "❓")
        
        print(f"\n{stage.value} {status_emoji}")
        print(f"├── Step: {step_name}")
        print(f"├── Status: {status}")
        print(f"├── Duration: {duration}ms")
        
        # Print state summary
        state_summary = step_data["state_summary"]
        print(f"├── State Summary:")
        print(f"│   ├── Keys: {state_summary['keys_count']}")
        print(f"│   ├── Has URL: {state_summary['has_repository_url']}")
        print(f"│   ├── Has Repo Info: {state_summary['has_repository_info']}")
        print(f"│   └── Current Step: {state_summary['current_step']}")
        
        # Print context if available
        if step_data["context"]:
            print(f"├── Context:")
            for key, value in step_data["context"].items():
                if isinstance(value, (str, int, bool)):
                    print(f"│   ├── {key}: {value}")
                elif isinstance(value, list):
                    print(f"│   ├── {key}: [{len(value)} items]")
                elif isinstance(value, dict):
                    print(f"│   ├── {key}: {{{len(value)} keys}}")
                else:
                    print(f"│   ├── {key}: {type(value).__name__}")
                    
        print(f"└── Timestamp: {step_data['timestamp']}")
        
    def print_complete_flow(self) -> None:
        """Print the complete flow visualization."""
        print(f"\n{'='*80}")
        print(f"🔍 LANGGRAPH WORKFLOW EXECUTION FLOW")
        print(f"{'='*80}")
        print(f"📊 Session ID: {self.session_id}")
        print(f"⏱️ Total Duration: {self._get_duration_ms()}ms")
        print(f"📈 Total Steps: {len(self.flow_steps)}")
        print(f"🎯 Current Stage: {self.current_stage.value if self.current_stage else 'None'}")
        
        # Print flow diagram
        print(f"\n📋 EXECUTION FLOW DIAGRAM:")
        print(f"{'─'*80}")
        
        for i, step in enumerate(self.flow_steps, 1):
            stage = step["stage"]
            status = step["status"]
            step_name = step["step_name"]
            duration = step["duration_ms"]
            
            # Connection line
            if i > 1:
                print("    │")
                print("    ▼")
                
            # Status symbol
            status_symbol = {
                "IN_PROGRESS": "🔄",
                "COMPLETED": "✅",
                "FAILED": "❌", 
                "SKIPPED": "⏭️"
            }.get(status, "❓")
            
            print(f"{i:2d}. {stage.value} {status_symbol}")
            print(f"    └── {step_name} ({duration}ms)")
            
        print(f"{'─'*80}")
        
        # Print summary statistics
        self._print_flow_statistics()
        
    def _print_flow_statistics(self) -> None:
        """Print flow execution statistics."""
        if not self.flow_steps:
            return
            
        print(f"\n📊 EXECUTION STATISTICS:")
        print(f"{'─'*40}")
        
        # Status distribution
        status_counts = {}
        total_duration = 0
        
        for step in self.flow_steps:
            status = step["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
            total_duration += step["duration_ms"]
            
        print(f"Status Distribution:")
        for status, count in status_counts.items():
            emoji = {
                "COMPLETED": "✅",
                "FAILED": "❌", 
                "IN_PROGRESS": "🔄",
                "SKIPPED": "⏭️"
            }.get(status, "❓")
            print(f"  {emoji} {status}: {count}")
            
        print(f"\nTiming:")
        print(f"  ⏱️ Total Duration: {total_duration}ms")
        print(f"  📈 Average Step Duration: {total_duration // len(self.flow_steps)}ms")
        
        # Stage progression
        stages_visited = list(set(step["stage"] for step in self.flow_steps))
        print(f"\nStages Visited: {len(stages_visited)}")
        for stage in stages_visited:
            print(f"  {stage.value}")
            
    def create_mermaid_diagram(self) -> str:
        """Create a Mermaid diagram representation of the flow."""
        mermaid = ["graph TD"]
        
        # Add nodes
        for i, step in enumerate(self.flow_steps):
            node_id = f"step{i+1}"
            stage = step["stage"]
            step_name = step["step_name"]
            status = step["status"]
            
            # Node styling based on status
            if status == "COMPLETED":
                style = "fill:#d4edda,stroke:#155724"
            elif status == "FAILED":
                style = "fill:#f8d7da,stroke:#721c24"
            elif status == "IN_PROGRESS":
                style = "fill:#fff3cd,stroke:#856404"
            else:
                style = "fill:#e2e3e5,stroke:#383d41"
                
            mermaid.append(f'    {node_id}["{stage.value}<br/>{step_name}"]')
            mermaid.append(f'    style {node_id} {style}')
            
        # Add connections
        for i in range(len(self.flow_steps) - 1):
            mermaid.append(f"    step{i+1} --> step{i+2}")
            
        return "\n".join(mermaid)
        
    def export_flow_data(self) -> Dict[str, Any]:
        """Export complete flow data for analysis."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "total_duration_ms": self._get_duration_ms(),
            "total_steps": len(self.flow_steps),
            "current_stage": self.current_stage.value if self.current_stage else None,
            "flow_steps": self.flow_steps,
            "mermaid_diagram": self.create_mermaid_diagram()
        }

# Global flow visualizer instance
flow_visualizer = FlowVisualizer()

def track_debug_flow(step_name: str, stage: FlowStage, state: Dict[str, Any], 
                    context: Optional[Dict[str, Any]] = None, status: str = "IN_PROGRESS") -> None:
    """Convenience function to track debug flow steps."""
    flow_visualizer.track_flow_step(step_name, stage, state, context, status)

def print_complete_debug_flow() -> None:
    """Convenience function to print complete debug flow."""
    flow_visualizer.print_complete_flow()

def get_mermaid_diagram() -> str:
    """Convenience function to get Mermaid diagram."""
    return flow_visualizer.create_mermaid_diagram()

def export_debug_flow() -> Dict[str, Any]:
    """Convenience function to export debug flow data."""
    return flow_visualizer.export_flow_data()
