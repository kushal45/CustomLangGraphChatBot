#!/usr/bin/env python3
"""
Visual Node Execution Flow Diagrams

This module provides comprehensive visualization capabilities for workflow node execution,
creating visual flow diagrams, execution timelines, performance heatmaps, and
interactive workflow documentation.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import ReviewState, ReviewStatus
from scripts.node_profiling import ProfilingSession, PerformanceMetrics
from scripts.node_replay import ReplaySequence, ReplayResult
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging
initialize_logging(LoggingConfig(
    log_level="INFO",
    log_format="detailed",
    enable_console_logging=True,
    enable_file_logging=True,
    log_dir="logs/diagrams"
))

logger = get_logger(__name__)


@dataclass
class FlowNode:
    """Represents a node in the execution flow."""
    id: str
    name: str
    type: str  # 'start', 'process', 'decision', 'end', 'error'
    execution_time: float
    memory_usage: float
    status: str  # 'success', 'failed', 'pending'
    timestamp: str
    input_size: int
    output_size: int
    bottlenecks: List[str]


@dataclass
class FlowEdge:
    """Represents a connection between nodes."""
    from_node: str
    to_node: str
    condition: Optional[str]
    data_flow: str  # 'state', 'error', 'result'
    weight: float  # execution time or data size


@dataclass
class ExecutionFlow:
    """Complete execution flow representation."""
    flow_id: str
    name: str
    description: str
    created_at: str
    nodes: List[FlowNode]
    edges: List[FlowEdge]
    metadata: Dict[str, Any]


class NodeFlowVisualizer:
    """Advanced visualization engine for node execution flows."""
    
    def __init__(self, output_dir: str = "logs/diagrams/flows"):
        self.output_dir = Path(output_dir)
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Handle read-only filesystem or permission issues
            print(f"Warning: Cannot create diagrams directory {self.output_dir}: {e}")
            print("Diagrams will be stored in memory only.")
            # Use a temporary directory or disable file output
            import tempfile
            self.output_dir = Path(tempfile.gettempdir()) / "diagrams" / "flows"
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                # If even temp directory fails, disable file output
                self.output_dir = None
        
        self.flows: List[ExecutionFlow] = []
        
        # Node type mappings
        self.node_types = {
            "start_review_node": "start",
            "analyze_code_node": "process",
            "generate_report_node": "process",
            "error_handler_node": "error"
        }
        
        # Color schemes for different visualizations
        self.color_schemes = {
            "performance": {
                "fast": "#2ecc71",      # Green
                "medium": "#f39c12",    # Orange
                "slow": "#e74c3c",      # Red
                "error": "#9b59b6"      # Purple
            },
            "memory": {
                "low": "#3498db",       # Blue
                "medium": "#f39c12",    # Orange
                "high": "#e74c3c",      # Red
                "critical": "#8e44ad"   # Purple
            },
            "status": {
                "success": "#2ecc71",   # Green
                "failed": "#e74c3c",    # Red
                "pending": "#95a5a6"    # Gray
            }
        }
    
    def create_flow_from_profiling_session(self, session: ProfilingSession) -> ExecutionFlow:
        """Create execution flow from profiling session data."""
        logger.info(f"Creating flow diagram from profiling session: {session.session_id}")
        
        nodes = []
        edges = []
        
        # Create nodes from metrics
        for i, metric in enumerate(session.metrics):
            node_type = self.node_types.get(metric.node_name, "process")
            
            # Determine status based on performance
            if metric.bottlenecks:
                status = "failed" if any("Critical" in b for b in metric.bottlenecks) else "success"
            else:
                status = "success"
            
            node = FlowNode(
                id=f"node_{i}",
                name=metric.node_name,
                type=node_type,
                execution_time=metric.execution_time,
                memory_usage=metric.memory_usage.current_memory_mb,
                status=status,
                timestamp=metric.memory_usage.timestamp,
                input_size=0,  # Would need to be tracked separately
                output_size=0,  # Would need to be tracked separately
                bottlenecks=metric.bottlenecks
            )
            nodes.append(node)
            
            # Create edge to next node
            if i < len(session.metrics) - 1:
                edge = FlowEdge(
                    from_node=f"node_{i}",
                    to_node=f"node_{i+1}",
                    condition=None,
                    data_flow="state",
                    weight=metric.execution_time
                )
                edges.append(edge)
        
        flow = ExecutionFlow(
            flow_id=f"flow_{session.session_id}",
            name=f"Profiling Flow - {session.session_id}",
            description=f"Execution flow from profiling session with {len(nodes)} nodes",
            created_at=datetime.now().isoformat(),
            nodes=nodes,
            edges=edges,
            metadata={
                "source": "profiling_session",
                "session_id": session.session_id,
                "total_execution_time": session.session_summary.get("total_execution_time", 0),
                "performance_score": session.session_summary.get("performance_score", 0)
            }
        )
        
        self.flows.append(flow)
        logger.info(f"Created flow with {len(nodes)} nodes and {len(edges)} edges")
        return flow
    
    def create_flow_from_replay_sequence(self, sequence: ReplaySequence, 
                                       results: List[ReplayResult]) -> ExecutionFlow:
        """Create execution flow from replay sequence and results."""
        logger.info(f"Creating flow diagram from replay sequence: {sequence.sequence_id}")
        
        nodes = []
        edges = []
        
        # Create nodes from replay results
        for i, (step, result) in enumerate(zip(sequence.steps, results)):
            node_type = self.node_types.get(step.node_name, "process")
            
            node = FlowNode(
                id=f"replay_node_{i}",
                name=step.node_name,
                type=node_type,
                execution_time=result.execution_time,
                memory_usage=0,  # Not tracked in replay
                status="success" if result.success else "failed",
                timestamp=step.timestamp,
                input_size=len(str(step.input_data.data)),
                output_size=len(str(result.actual_output)) if result.actual_output else 0,
                bottlenecks=result.differences
            )
            nodes.append(node)
            
            # Create edge to next node
            if i < len(results) - 1:
                edge = FlowEdge(
                    from_node=f"replay_node_{i}",
                    to_node=f"replay_node_{i+1}",
                    condition=None,
                    data_flow="state",
                    weight=result.execution_time
                )
                edges.append(edge)
        
        flow = ExecutionFlow(
            flow_id=f"replay_flow_{sequence.sequence_id}",
            name=f"Replay Flow - {sequence.name}",
            description=f"Execution flow from replay sequence: {sequence.description}",
            created_at=datetime.now().isoformat(),
            nodes=nodes,
            edges=edges,
            metadata={
                "source": "replay_sequence",
                "sequence_id": sequence.sequence_id,
                "total_steps": len(sequence.steps),
                "success_rate": sum(1 for r in results if r.success) / len(results) * 100
            }
        )
        
        self.flows.append(flow)
        logger.info(f"Created replay flow with {len(nodes)} nodes and {len(edges)} edges")
        return flow
    
    def generate_mermaid_diagram(self, flow: ExecutionFlow, 
                               visualization_type: str = "performance") -> str:
        """Generate Mermaid diagram code for the execution flow."""
        logger.info(f"Generating Mermaid diagram for flow: {flow.flow_id}")
        
        mermaid_code = ["graph TD"]
        
        # Add nodes with styling based on visualization type
        for node in flow.nodes:
            # Determine node shape based on type
            if node.type == "start":
                shape_start, shape_end = "(", ")"
            elif node.type == "decision":
                shape_start, shape_end = "{", "}"
            elif node.type == "error":
                shape_start, shape_end = "((", "))"
            else:
                shape_start, shape_end = "[", "]"
            
            # Create node label with metrics
            if visualization_type == "performance":
                label = f"{node.name}<br/>{node.execution_time:.3f}s"
                color = self._get_performance_color(node.execution_time)
            elif visualization_type == "memory":
                label = f"{node.name}<br/>{node.memory_usage:.1f}MB"
                color = self._get_memory_color(node.memory_usage)
            else:  # status
                label = f"{node.name}<br/>{node.status}"
                color = self.color_schemes["status"][node.status]
            
            mermaid_code.append(f"    {node.id}{shape_start}\"{label}\"{shape_end}")
            mermaid_code.append(f"    {node.id} --> {node.id}")
            mermaid_code.append(f"    style {node.id} fill:{color}")
        
        # Add edges
        for edge in flow.edges:
            if edge.condition:
                label = f"|{edge.condition}|"
            else:
                label = ""
            
            mermaid_code.append(f"    {edge.from_node} --> {label} {edge.to_node}")
        
        # Add title and metadata
        mermaid_code.insert(1, f"    %% {flow.name}")
        mermaid_code.insert(2, f"    %% Created: {flow.created_at}")
        
        return "\n".join(mermaid_code)
    
    def _get_performance_color(self, execution_time: float) -> str:
        """Get color based on execution time performance."""
        if execution_time < 0.1:
            return self.color_schemes["performance"]["fast"]
        elif execution_time < 1.0:
            return self.color_schemes["performance"]["medium"]
        else:
            return self.color_schemes["performance"]["slow"]
    
    def _get_memory_color(self, memory_usage: float) -> str:
        """Get color based on memory usage."""
        if memory_usage < 50:
            return self.color_schemes["memory"]["low"]
        elif memory_usage < 100:
            return self.color_schemes["memory"]["medium"]
        elif memory_usage < 200:
            return self.color_schemes["memory"]["high"]
        else:
            return self.color_schemes["memory"]["critical"]
    
    def generate_html_visualization(self, flow: ExecutionFlow) -> str:
        """Generate interactive HTML visualization using Mermaid.js."""
        logger.info(f"Generating HTML visualization for flow: {flow.flow_id}")
        
        # Generate different diagram types
        performance_diagram = self.generate_mermaid_diagram(flow, "performance")
        memory_diagram = self.generate_mermaid_diagram(flow, "memory")
        status_diagram = self.generate_mermaid_diagram(flow, "status")
        
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{flow.name} - Execution Flow Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .tabs {{
            display: flex;
            margin-bottom: 20px;
            border-bottom: 1px solid #ddd;
        }}
        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 16px;
        }}
        .tab.active {{
            border-bottom: 2px solid #007bff;
            color: #007bff;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .diagram {{
            text-align: center;
            margin: 20px 0;
        }}
        .metadata {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .metadata h3 {{
            margin-top: 0;
        }}
        .node-details {{
            margin-top: 20px;
        }}
        .node-card {{
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
        }}
        .performance-good {{ color: #28a745; }}
        .performance-warning {{ color: #ffc107; }}
        .performance-danger {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{flow.name}</h1>
            <p>{flow.description}</p>
            <p><strong>Created:</strong> {flow.created_at}</p>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('performance')">Performance View</button>
            <button class="tab" onclick="showTab('memory')">Memory View</button>
            <button class="tab" onclick="showTab('status')">Status View</button>
            <button class="tab" onclick="showTab('details')">Node Details</button>
        </div>
        
        <div id="performance" class="tab-content active">
            <h2>Performance Execution Flow</h2>
            <div class="diagram">
                <div class="mermaid">
{performance_diagram}
                </div>
            </div>
        </div>
        
        <div id="memory" class="tab-content">
            <h2>Memory Usage Flow</h2>
            <div class="diagram">
                <div class="mermaid">
{memory_diagram}
                </div>
            </div>
        </div>
        
        <div id="status" class="tab-content">
            <h2>Execution Status Flow</h2>
            <div class="diagram">
                <div class="mermaid">
{status_diagram}
                </div>
            </div>
        </div>
        
        <div id="details" class="tab-content">
            <h2>Detailed Node Information</h2>
            <div class="node-details">
                {self._generate_node_details_html(flow.nodes)}
            </div>
        </div>
        
        <div class="metadata">
            <h3>Flow Metadata</h3>
            {self._generate_metadata_html(flow.metadata)}
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true }});
        
        function showTab(tabName) {{
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            // Remove active class from all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab
            event.target.classList.add('active');
        }}
    </script>
</body>
</html>
        """
        
        return html_template
    
    def _generate_node_details_html(self, nodes: List[FlowNode]) -> str:
        """Generate HTML for detailed node information."""
        html_parts = []
        
        for node in nodes:
            # Determine performance class
            if node.execution_time < 0.1:
                perf_class = "performance-good"
            elif node.execution_time < 1.0:
                perf_class = "performance-warning"
            else:
                perf_class = "performance-danger"
            
            bottlenecks_html = ""
            if node.bottlenecks:
                bottlenecks_html = "<br><strong>Issues:</strong> " + ", ".join(node.bottlenecks)
            
            html_parts.append(f"""
                <div class="node-card">
                    <h4>{node.name} ({node.type})</h4>
                    <p><strong>Status:</strong> {node.status}</p>
                    <p><strong>Execution Time:</strong> <span class="{perf_class}">{node.execution_time:.3f}s</span></p>
                    <p><strong>Memory Usage:</strong> {node.memory_usage:.1f}MB</p>
                    <p><strong>Timestamp:</strong> {node.timestamp}</p>
                    {bottlenecks_html}
                </div>
            """)
        
        return "".join(html_parts)
    
    def _generate_metadata_html(self, metadata: Dict[str, Any]) -> str:
        """Generate HTML for flow metadata."""
        html_parts = []
        
        for key, value in metadata.items():
            if isinstance(value, (int, float)):
                if key.endswith("_time"):
                    formatted_value = f"{value:.3f}s"
                elif key.endswith("_score"):
                    formatted_value = f"{value:.1f}"
                else:
                    formatted_value = str(value)
            else:
                formatted_value = str(value)
            
            html_parts.append(f"<p><strong>{key.replace('_', ' ').title()}:</strong> {formatted_value}</p>")
        
        return "".join(html_parts)
    
    def save_flow_diagram(self, flow: ExecutionFlow, format: str = "html") -> Path:
        """Save flow diagram to file."""
        if format == "html":
            content = self.generate_html_visualization(flow)
            filename = f"{flow.flow_id}_visualization.html"
        elif format == "mermaid":
            content = self.generate_mermaid_diagram(flow)
            filename = f"{flow.flow_id}_diagram.mmd"
        else:
            raise ValueError(f"Unsupported format: {format}")

        if self.output_dir is None:
            logger.debug("Output directory not available, skipping file save")
            # Return a dummy path for compatibility
            return Path(f"/tmp/{filename}")

        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            
            logger.info(f"Saved flow diagram to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save flow diagram: {e}", exc_info=True)
            raise
    
    def save_flow_data(self, flow: ExecutionFlow) -> Path:
        """Save flow data as JSON for later analysis."""
        filename = f"{flow.flow_id}_data.json"

        if self.output_dir is None:
            logger.debug("Output directory not available, skipping file save")
            # Return a dummy path for compatibility
            return Path(f"/tmp/{filename}")

        filepath = self.output_dir / filename
        
        try:
            # Convert flow to serializable format
            flow_data = {
                "flow_id": flow.flow_id,
                "name": flow.name,
                "description": flow.description,
                "created_at": flow.created_at,
                "metadata": flow.metadata,
                "nodes": [asdict(node) for node in flow.nodes],
                "edges": [asdict(edge) for edge in flow.edges]
            }
            
            with open(filepath, 'w') as f:
                json.dump(flow_data, f, indent=2, default=str)
            
            logger.info(f"Saved flow data to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save flow data: {e}", exc_info=True)
            raise
    
    def generate_summary_report(self) -> str:
        """Generate summary report of all flows."""
        if not self.flows:
            return "No flows available for summary."
        
        total_flows = len(self.flows)
        total_nodes = sum(len(flow.nodes) for flow in self.flows)
        avg_execution_time = sum(
            sum(node.execution_time for node in flow.nodes) 
            for flow in self.flows
        ) / total_nodes if total_nodes > 0 else 0
        
        report = f"""
Flow Visualization Summary Report
================================

Total Flows: {total_flows}
Total Nodes: {total_nodes}
Average Node Execution Time: {avg_execution_time:.3f}s

Flow Details:
"""
        
        for flow in self.flows:
            total_time = sum(node.execution_time for node in flow.nodes)
            success_rate = sum(1 for node in flow.nodes if node.status == "success") / len(flow.nodes) * 100
            
            report += f"""
- {flow.name}
  ID: {flow.flow_id}
  Nodes: {len(flow.nodes)}
  Total Execution Time: {total_time:.3f}s
  Success Rate: {success_rate:.1f}%
  Source: {flow.metadata.get('source', 'unknown')}
"""
        
        return report


# Global visualizer instance
_global_visualizer: Optional[NodeFlowVisualizer] = None


def get_visualizer() -> NodeFlowVisualizer:
    """Get global visualizer instance."""
    global _global_visualizer
    if _global_visualizer is None:
        _global_visualizer = NodeFlowVisualizer()
    return _global_visualizer


if __name__ == "__main__":
    # Example usage and testing
    def test_flow_visualization():
        """Test the flow visualization functionality."""
        print("Testing Node Flow Visualization System")
        print("=" * 50)
        
        visualizer = get_visualizer()
        
        # Create sample flow data
        sample_nodes = [
            FlowNode(
                id="node_0",
                name="start_review_node",
                type="start",
                execution_time=0.001,
                memory_usage=41.5,
                status="success",
                timestamp="2025-07-08T17:00:00",
                input_size=1000,
                output_size=1200,
                bottlenecks=[]
            ),
            FlowNode(
                id="node_1",
                name="analyze_code_node",
                type="process",
                execution_time=0.150,
                memory_usage=85.2,
                status="success",
                timestamp="2025-07-08T17:00:01",
                input_size=1200,
                output_size=2500,
                bottlenecks=["High execution time: 0.150s"]
            ),
            FlowNode(
                id="node_2",
                name="generate_report_node",
                type="process",
                execution_time=0.003,
                memory_usage=42.1,
                status="success",
                timestamp="2025-07-08T17:00:02",
                input_size=2500,
                output_size=5000,
                bottlenecks=[]
            )
        ]
        
        sample_edges = [
            FlowEdge("node_0", "node_1", None, "state", 0.001),
            FlowEdge("node_1", "node_2", None, "state", 0.150)
        ]
        
        sample_flow = ExecutionFlow(
            flow_id="test_flow_001",
            name="Sample Workflow Execution",
            description="Test flow for visualization system",
            created_at=datetime.now().isoformat(),
            nodes=sample_nodes,
            edges=sample_edges,
            metadata={
                "source": "test",
                "total_execution_time": 0.154,
                "performance_score": 85.0,
                "success_rate": 100.0
            }
        )
        
        print("\n1. Generating Mermaid diagrams...")
        
        # Generate different diagram types
        performance_diagram = visualizer.generate_mermaid_diagram(sample_flow, "performance")
        memory_diagram = visualizer.generate_mermaid_diagram(sample_flow, "memory")
        status_diagram = visualizer.generate_mermaid_diagram(sample_flow, "status")
        
        print("✅ Generated Mermaid diagrams")
        
        print("\n2. Saving flow visualizations...")
        
        # Save HTML visualization
        html_path = visualizer.save_flow_diagram(sample_flow, "html")
        print(f"✅ Saved HTML visualization: {html_path}")
        
        # Save Mermaid diagram
        mermaid_path = visualizer.save_flow_diagram(sample_flow, "mermaid")
        print(f"✅ Saved Mermaid diagram: {mermaid_path}")
        
        # Save flow data
        data_path = visualizer.save_flow_data(sample_flow)
        print(f"✅ Saved flow data: {data_path}")
        
        print("\n3. Generating summary report...")
        visualizer.flows.append(sample_flow)  # Add to visualizer for summary
        summary = visualizer.generate_summary_report()
        print(summary)
        
        print("\n" + "=" * 50)
        print("Flow visualization testing completed!")
        print(f"Open {html_path} in your browser to view the interactive visualization!")
    
    # Run test
    test_flow_visualization()
