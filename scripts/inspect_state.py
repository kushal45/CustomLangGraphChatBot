#!/usr/bin/env python3
"""
State Inspection Utilities

This script provides comprehensive inspection and analysis capabilities for ReviewState objects,
allowing developers to examine state structure, validate data integrity, compare states,
and visualize state transitions during workflow debugging.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
Usage:
    python scripts/inspect_state.py --file state.json --analyze
    python scripts/inspect_state.py --file state.json --validate
    python scripts/inspect_state.py --compare state1.json state2.json
    python scripts/inspect_state.py --interactive
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import difflib

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import workflow components
from state import ReviewState, ReviewStatus, RepositoryInfo, ToolResult, AnalysisResults
from logging_config import get_logger, initialize_logging, LoggingConfig

# Initialize logging for inspection
initialize_logging(LoggingConfig(
    log_level="INFO",
    log_format="simple",
    enable_console_logging=True,
    enable_file_logging=False
))

logger = get_logger(__name__)


@dataclass
class StateAnalysis:
    """Analysis results for a ReviewState object."""
    total_size: int
    field_count: int
    non_empty_fields: int
    status: str
    current_step: str
    has_errors: bool
    tool_count: int
    successful_tools: int
    failed_tools: int
    files_analyzed: int
    execution_time: Optional[float]
    completeness_score: float
    validation_errors: List[str]


@dataclass
class StateComparison:
    """Comparison results between two ReviewState objects."""
    added_fields: List[str]
    removed_fields: List[str]
    modified_fields: List[str]
    status_change: Optional[Tuple[str, str]]
    step_change: Optional[Tuple[str, str]]
    tool_changes: Dict[str, str]
    size_change: int
    similarity_score: float


class StateSerializer:
    """Enhanced state serialization utilities."""
    
    @staticmethod
    def serialize_state(state: ReviewState) -> Dict[str, Any]:
        """Serialize ReviewState to JSON-compatible dictionary."""
        serialized = {}
        
        for key, value in state.items():
            if key == "status" and value:
                serialized[key] = value.value if hasattr(value, 'value') else str(value)
            elif key == "messages":
                serialized[key] = [
                    {"type": type(msg).__name__, "content": str(msg)} 
                    for msg in (value or [])
                ]
            else:
                serialized[key] = value
        
        return serialized
    
    @staticmethod
    def deserialize_state(data: Dict[str, Any]) -> ReviewState:
        """Deserialize dictionary to ReviewState object."""
        if "status" in data and isinstance(data["status"], str):
            try:
                data["status"] = ReviewStatus(data["status"])
            except ValueError:
                data["status"] = ReviewStatus.INITIALIZING
        
        if "messages" not in data:
            data["messages"] = []
        
        # Ensure all required fields exist
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
        
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        return data


class StateInspector:
    """Main utility for inspecting and analyzing ReviewState objects."""
    
    def __init__(self):
        self.inspection_history: List[Dict[str, Any]] = []
    
    def load_state_from_file(self, filepath: str) -> ReviewState:
        """Load ReviewState from JSON file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return StateSerializer.deserialize_state(data)
        except Exception as e:
            logger.error(f"Failed to load state from {filepath}: {e}")
            raise
    
    def analyze_state(self, state: ReviewState) -> StateAnalysis:
        """Perform comprehensive analysis of a ReviewState object."""
        serialized = StateSerializer.serialize_state(state)
        
        # Basic metrics
        total_size = len(json.dumps(serialized, default=str))
        field_count = len(state)
        non_empty_fields = sum(1 for v in state.values() if v is not None and v != [] and v != {})
        
        # Status and step information
        status = state.get("status", ReviewStatus.INITIALIZING)
        status_str = status.value if hasattr(status, 'value') else str(status)
        current_step = state.get("current_step", "unknown")
        
        # Error analysis
        has_errors = bool(state.get("error_message")) or bool(state.get("failed_tools"))
        
        # Tool analysis
        tool_results = state.get("tool_results", {})
        tool_count = len(tool_results)
        successful_tools = sum(1 for result in tool_results.values() 
                             if isinstance(result, dict) and result.get("success", False))
        failed_tools = len(state.get("failed_tools", []))
        
        # File analysis
        files_analyzed = len(state.get("files_analyzed", []))
        
        # Execution time calculation
        execution_time = None
        start_time = state.get("start_time")
        end_time = state.get("end_time")
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                execution_time = (end_dt - start_dt).total_seconds()
            except:
                pass
        
        # Completeness score (0-100)
        completeness_factors = [
            bool(state.get("repository_url")),
            bool(state.get("repository_info")),
            bool(state.get("enabled_tools")),
            bool(tool_results),
            bool(state.get("files_analyzed")),
            status_str != "initializing",
            not has_errors
        ]
        completeness_score = (sum(completeness_factors) / len(completeness_factors)) * 100
        
        # Validation
        validation_errors = self.validate_state(state)
        
        return StateAnalysis(
            total_size=total_size,
            field_count=field_count,
            non_empty_fields=non_empty_fields,
            status=status_str,
            current_step=current_step,
            has_errors=has_errors,
            tool_count=tool_count,
            successful_tools=successful_tools,
            failed_tools=failed_tools,
            files_analyzed=files_analyzed,
            execution_time=execution_time,
            completeness_score=completeness_score,
            validation_errors=validation_errors
        )
    
    def validate_state(self, state: ReviewState) -> List[str]:
        """Validate ReviewState structure and data integrity."""
        errors = []
        
        # Required fields validation
        required_fields = [
            'messages', 'current_step', 'status', 'repository_url',
            'enabled_tools', 'tool_results', 'failed_tools', 'files_analyzed',
            'total_files', 'review_config', 'notifications_sent', 'report_generated'
        ]
        
        for field in required_fields:
            if field not in state:
                errors.append(f"Missing required field: {field}")
        
        # Type validation
        type_checks = [
            ('messages', list),
            ('current_step', str),
            ('enabled_tools', list),
            ('tool_results', dict),
            ('failed_tools', list),
            ('files_analyzed', list),
            ('total_files', int),
            ('review_config', dict),
            ('notifications_sent', list),
            ('report_generated', bool)
        ]
        
        for field, expected_type in type_checks:
            if field in state and state[field] is not None:
                if not isinstance(state[field], expected_type):
                    errors.append(f"Field '{field}' should be {expected_type.__name__}, got {type(state[field]).__name__}")
        
        # Business logic validation
        if 'total_files' in state and 'files_analyzed' in state:
            if state['total_files'] > 0 and len(state['files_analyzed']) > state['total_files']:
                errors.append("More files analyzed than total files")
        
        if 'tool_results' in state and 'failed_tools' in state:
            successful_tools = set(state['tool_results'].keys())
            failed_tools = set(state['failed_tools'])
            if successful_tools & failed_tools:
                errors.append("Tools cannot be both successful and failed")
        
        # Status consistency validation
        status = state.get('status')
        current_step = state.get('current_step', '')
        
        if status == ReviewStatus.COMPLETED and current_step != 'complete':
            errors.append("Status is COMPLETED but current_step is not 'complete'")
        
        if status == ReviewStatus.FAILED and not state.get('error_message'):
            errors.append("Status is FAILED but no error_message provided")
        
        return errors
    
    def compare_states(self, state1: ReviewState, state2: ReviewState) -> StateComparison:
        """Compare two ReviewState objects and identify differences."""
        serialized1 = StateSerializer.serialize_state(state1)
        serialized2 = StateSerializer.serialize_state(state2)
        
        # Field changes
        keys1 = set(serialized1.keys())
        keys2 = set(serialized2.keys())
        
        added_fields = list(keys2 - keys1)
        removed_fields = list(keys1 - keys2)
        
        modified_fields = []
        for key in keys1 & keys2:
            if serialized1[key] != serialized2[key]:
                modified_fields.append(key)
        
        # Status and step changes
        status_change = None
        if serialized1.get('status') != serialized2.get('status'):
            status_change = (serialized1.get('status'), serialized2.get('status'))
        
        step_change = None
        if serialized1.get('current_step') != serialized2.get('current_step'):
            step_change = (serialized1.get('current_step'), serialized2.get('current_step'))
        
        # Tool changes
        tools1 = set(serialized1.get('tool_results', {}).keys())
        tools2 = set(serialized2.get('tool_results', {}).keys())
        
        tool_changes = {}
        for tool in tools1 - tools2:
            tool_changes[tool] = "removed"
        for tool in tools2 - tools1:
            tool_changes[tool] = "added"
        for tool in tools1 & tools2:
            if serialized1['tool_results'][tool] != serialized2['tool_results'][tool]:
                tool_changes[tool] = "modified"
        
        # Size change
        size1 = len(json.dumps(serialized1, default=str))
        size2 = len(json.dumps(serialized2, default=str))
        size_change = size2 - size1
        
        # Similarity score (simple implementation)
        total_fields = len(keys1 | keys2)
        unchanged_fields = len(keys1 & keys2) - len(modified_fields)
        similarity_score = (unchanged_fields / total_fields) * 100 if total_fields > 0 else 100
        
        return StateComparison(
            added_fields=added_fields,
            removed_fields=removed_fields,
            modified_fields=modified_fields,
            status_change=status_change,
            step_change=step_change,
            tool_changes=tool_changes,
            size_change=size_change,
            similarity_score=similarity_score
        )
    
    def print_state_summary(self, state: ReviewState, analysis: StateAnalysis):
        """Print a formatted summary of state analysis."""
        print(f"\n{'='*60}")
        print(f"REVIEWSTATE INSPECTION SUMMARY")
        print(f"{'='*60}")
        
        # Basic information
        print(f"Status: {analysis.status}")
        print(f"Current Step: {analysis.current_step}")
        print(f"Repository: {state.get('repository_url', 'N/A')}")
        print(f"Repository Type: {state.get('repository_type', 'N/A')}")
        
        # Size and structure
        print(f"\nStructure:")
        print(f"  Total Size: {analysis.total_size} bytes")
        print(f"  Field Count: {analysis.field_count}")
        print(f"  Non-empty Fields: {analysis.non_empty_fields}")
        print(f"  Completeness Score: {analysis.completeness_score:.1f}%")
        
        # Tool information
        print(f"\nTool Execution:")
        print(f"  Enabled Tools: {len(state.get('enabled_tools', []))}")
        print(f"  Executed Tools: {analysis.tool_count}")
        print(f"  Successful Tools: {analysis.successful_tools}")
        print(f"  Failed Tools: {analysis.failed_tools}")
        
        # File analysis
        print(f"\nFile Analysis:")
        print(f"  Files Analyzed: {analysis.files_analyzed}")
        print(f"  Total Files: {state.get('total_files', 0)}")
        
        # Timing
        if analysis.execution_time:
            print(f"\nTiming:")
            print(f"  Execution Time: {analysis.execution_time:.2f}s")
        
        # Errors and validation
        if analysis.has_errors:
            print(f"\nErrors:")
            if state.get('error_message'):
                print(f"  Error Message: {state['error_message']}")
            if state.get('failed_tools'):
                print(f"  Failed Tools: {', '.join(state['failed_tools'])}")
        
        if analysis.validation_errors:
            print(f"\nValidation Errors:")
            for error in analysis.validation_errors:
                print(f"  ❌ {error}")
        else:
            print(f"\nValidation: ✅ All checks passed")
        
        print(f"{'='*60}\n")
    
    def print_comparison_summary(self, comparison: StateComparison):
        """Print a formatted summary of state comparison."""
        print(f"\n{'='*60}")
        print(f"STATE COMPARISON SUMMARY")
        print(f"{'='*60}")
        
        print(f"Similarity Score: {comparison.similarity_score:.1f}%")
        print(f"Size Change: {comparison.size_change:+d} bytes")
        
        if comparison.status_change:
            print(f"Status Change: {comparison.status_change[0]} → {comparison.status_change[1]}")
        
        if comparison.step_change:
            print(f"Step Change: {comparison.step_change[0]} → {comparison.step_change[1]}")
        
        if comparison.added_fields:
            print(f"\nAdded Fields: {', '.join(comparison.added_fields)}")
        
        if comparison.removed_fields:
            print(f"Removed Fields: {', '.join(comparison.removed_fields)}")
        
        if comparison.modified_fields:
            print(f"Modified Fields: {', '.join(comparison.modified_fields)}")
        
        if comparison.tool_changes:
            print(f"\nTool Changes:")
            for tool, change in comparison.tool_changes.items():
                print(f"  {tool}: {change}")
        
        print(f"{'='*60}\n")
    
    def interactive_mode(self):
        """Interactive state inspection mode."""
        print("\n🔍 Interactive State Inspection Mode")
        print("Available commands:")
        print("  load <file> - Load state from JSON file")
        print("  analyze - Analyze current state")
        print("  validate - Validate current state")
        print("  show - Show current state (pretty printed)")
        print("  compare <file> - Compare current state with another file")
        print("  history - Show inspection history")
        print("  quit - Exit interactive mode")
        
        current_state = None
        
        while True:
            try:
                command = input("\ninspect> ").strip().split()
                if not command:
                    continue
                
                if command[0] == "quit":
                    break
                elif command[0] == "load" and len(command) > 1:
                    try:
                        current_state = self.load_state_from_file(command[1])
                        print(f"✅ State loaded from {command[1]}")
                    except Exception as e:
                        print(f"❌ Failed to load state: {e}")
                elif command[0] == "analyze":
                    if current_state:
                        analysis = self.analyze_state(current_state)
                        self.print_state_summary(current_state, analysis)
                    else:
                        print("❌ No state loaded. Use 'load <file>' first.")
                elif command[0] == "validate":
                    if current_state:
                        errors = self.validate_state(current_state)
                        if errors:
                            print("❌ Validation errors found:")
                            for error in errors:
                                print(f"  - {error}")
                        else:
                            print("✅ State validation passed")
                    else:
                        print("❌ No state loaded. Use 'load <file>' first.")
                elif command[0] == "show":
                    if current_state:
                        serialized = StateSerializer.serialize_state(current_state)
                        print(json.dumps(serialized, indent=2, default=str))
                    else:
                        print("❌ No state loaded. Use 'load <file>' first.")
                elif command[0] == "compare" and len(command) > 1:
                    if current_state:
                        try:
                            other_state = self.load_state_from_file(command[1])
                            comparison = self.compare_states(current_state, other_state)
                            self.print_comparison_summary(comparison)
                        except Exception as e:
                            print(f"❌ Failed to compare states: {e}")
                    else:
                        print("❌ No state loaded. Use 'load <file>' first.")
                elif command[0] == "history":
                    if self.inspection_history:
                        for i, record in enumerate(self.inspection_history):
                            print(f"{i+1}. {record['timestamp']} - {record['action']}")
                    else:
                        print("No inspection history")
                else:
                    print("Unknown command. Type 'quit' to exit.")
            
            except KeyboardInterrupt:
                print("\nExiting interactive mode...")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point for the state inspection utility."""
    parser = argparse.ArgumentParser(
        description="Inspect and analyze ReviewState objects with detailed validation and comparison"
    )
    
    parser.add_argument("--file", "-f", help="JSON file containing ReviewState")
    parser.add_argument("--analyze", "-a", action="store_true", help="Perform comprehensive state analysis")
    parser.add_argument("--validate", "-v", action="store_true", help="Validate state structure and data")
    parser.add_argument("--compare", "-c", help="Compare with another state file")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive inspection mode")
    parser.add_argument("--output", "-o", help="Save analysis results to file")
    
    args = parser.parse_args()
    
    inspector = StateInspector()
    
    # Interactive mode
    if args.interactive:
        inspector.interactive_mode()
        return
    
    # Load state file
    if args.file:
        try:
            state = inspector.load_state_from_file(args.file)
            print(f"✅ State loaded from {args.file}")
        except Exception as e:
            print(f"❌ Failed to load state: {e}")
            return
    else:
        if not args.interactive:
            print("❌ No state file provided. Use --file or --interactive mode.")
            parser.print_help()
            return
    
    # Perform analysis
    if args.analyze:
        analysis = inspector.analyze_state(state)
        inspector.print_state_summary(state, analysis)
        
        if args.output:
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "file": args.file,
                "analysis": {
                    "total_size": analysis.total_size,
                    "field_count": analysis.field_count,
                    "non_empty_fields": analysis.non_empty_fields,
                    "status": analysis.status,
                    "current_step": analysis.current_step,
                    "has_errors": analysis.has_errors,
                    "tool_count": analysis.tool_count,
                    "successful_tools": analysis.successful_tools,
                    "failed_tools": analysis.failed_tools,
                    "files_analyzed": analysis.files_analyzed,
                    "execution_time": analysis.execution_time,
                    "completeness_score": analysis.completeness_score,
                    "validation_errors": analysis.validation_errors
                }
            }
            
            with open(args.output, 'w') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            print(f"Analysis results saved to: {args.output}")
    
    # Perform validation
    if args.validate:
        errors = inspector.validate_state(state)
        if errors:
            print("❌ Validation errors found:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✅ State validation passed")
    
    # Perform comparison
    if args.compare:
        try:
            other_state = inspector.load_state_from_file(args.compare)
            comparison = inspector.compare_states(state, other_state)
            inspector.print_comparison_summary(comparison)
        except Exception as e:
            print(f"❌ Failed to compare states: {e}")
    
    # If no specific action, show basic info
    if not any([args.analyze, args.validate, args.compare]):
        analysis = inspector.analyze_state(state)
        print(f"State loaded: {analysis.status} - {analysis.current_step}")
        print(f"Size: {analysis.total_size} bytes, Completeness: {analysis.completeness_score:.1f}%")
        print("Use --analyze for detailed analysis or --help for more options.")


if __name__ == "__main__":
    main()
