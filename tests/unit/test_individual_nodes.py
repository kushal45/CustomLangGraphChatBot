"""
Comprehensive isolated testing infrastructure for individual workflow nodes.

This module provides detailed testing for each workflow node in isolation,
including input validation, output validation, error handling, performance
monitoring, and regression testing with state snapshots.

Part of Milestone 2: Individual Node Testing & Workflow Debugging
"""

import pytest
import asyncio
import time
import json
import copy
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import workflow components
from state import ReviewState, ReviewStatus, RepositoryInfo, ToolResult, AnalysisResults
from nodes import start_review_node, analyze_code_node, generate_report_node, error_handler_node
from tools.registry import ToolRegistry, ToolConfig
from debug.repository_debugging import repo_debugger


class NodeTestFixtures:
    """Centralized fixtures for realistic ReviewState data across all node tests."""
    
    @staticmethod
    def create_minimal_state() -> ReviewState:
        """Create minimal valid ReviewState for basic testing."""
        return ReviewState(
            messages=[],
            current_step="initializing",
            status=ReviewStatus.INITIALIZING,
            error_message=None,
            repository_url="https://github.com/test/repo",
            repository_info=None,
            repository_type=None,
            enabled_tools=[],
            tool_results={},
            failed_tools=[],
            analysis_results=None,
            files_analyzed=[],
            total_files=0,
            review_config={},
            start_time=None,
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )
    
    @staticmethod
    def create_start_review_state() -> ReviewState:
        """Create realistic state for start_review_node testing."""
        return ReviewState(
            messages=[],
            current_step="start_review",
            status=ReviewStatus.INITIALIZING,
            error_message=None,
            repository_url="https://github.com/test/python-repo",
            repository_info=None,
            repository_type=None,
            enabled_tools=[],
            tool_results={},
            failed_tools=[],
            analysis_results=None,
            files_analyzed=[],
            total_files=0,
            review_config={"include_tests": True, "max_files": 100},
            start_time=datetime.now().isoformat(),
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )
    
    @staticmethod
    def create_analyze_code_state() -> ReviewState:
        """Create realistic state for analyze_code_node testing."""
        repo_info = RepositoryInfo(
            url="https://github.com/test/python-repo",
            name="python-repo",
            full_name="test/python-repo",
            description="Test Python repository",
            language="Python",
            stars=42,
            forks=7,
            size=1024,
            default_branch="main",
            topics=["python", "testing"],
            file_structure=[
                {"path": "main.py", "type": "file", "size": 500},
                {"path": "tests/", "type": "directory", "size": 0},
                {"path": "tests/test_main.py", "type": "file", "size": 300}
            ],
            recent_commits=[
                {"sha": "abc123", "message": "Initial commit", "author": "test-user"}
            ]
        )
        
        return ReviewState(
            messages=[],
            current_step="analyze_code",
            status=ReviewStatus.ANALYZING_CODE,
            error_message=None,
            repository_url="https://github.com/test/python-repo",
            repository_info=repo_info,
            repository_type="python",
            enabled_tools=["pylint_analysis", "flake8_analysis", "code_review"],
            tool_results={},
            failed_tools=[],
            analysis_results=None,
            files_analyzed=["main.py"],
            total_files=2,
            review_config={"include_tests": True, "max_files": 100},
            start_time=datetime.now().isoformat(),
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )
    
    @staticmethod
    def create_generate_report_state() -> ReviewState:
        """Create realistic state for generate_report_node testing."""
        repo_info = RepositoryInfo(
            url="https://github.com/test/python-repo",
            name="python-repo", 
            full_name="test/python-repo",
            description="Test Python repository",
            language="Python",
            stars=42,
            forks=7,
            size=1024,
            default_branch="main",
            topics=["python", "testing"],
            file_structure=[
                {"path": "main.py", "type": "file", "size": 500},
                {"path": "tests/test_main.py", "type": "file", "size": 300}
            ],
            recent_commits=[
                {"sha": "abc123", "message": "Initial commit", "author": "test-user"}
            ]
        )
        
        # Mock tool results
        tool_results = {
            "pylint_analysis": ToolResult(
                tool_name="pylint_analysis",
                success=True,
                result={
                    "score": 8.5,
                    "issues": [
                        {"file": "main.py", "line": 10, "severity": "warning", "message": "Unused variable"}
                    ]
                },
                error_message=None,
                execution_time=2.3,
                timestamp=datetime.now().isoformat()
            ),
            "code_review": ToolResult(
                tool_name="code_review",
                success=True,
                result={
                    "overall_quality": "good",
                    "suggestions": ["Add more docstrings", "Consider error handling"]
                },
                error_message=None,
                execution_time=5.1,
                timestamp=datetime.now().isoformat()
            )
        }
        
        return ReviewState(
            messages=[],
            current_step="generate_report",
            status=ReviewStatus.GENERATING_REPORT,
            error_message=None,
            repository_url="https://github.com/test/python-repo",
            repository_info=repo_info,
            repository_type="python",
            enabled_tools=["pylint_analysis", "code_review"],
            tool_results=tool_results,
            failed_tools=[],
            analysis_results=None,
            files_analyzed=["main.py", "tests/test_main.py"],
            total_files=2,
            review_config={"include_tests": True, "max_files": 100},
            start_time=datetime.now().isoformat(),
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )
    
    @staticmethod
    def create_error_state() -> ReviewState:
        """Create state with error for error_handler_node testing."""
        return ReviewState(
            messages=[],
            current_step="analyze_code",
            status=ReviewStatus.FAILED,
            error_message="GitHub API rate limit exceeded",
            repository_url="https://github.com/test/repo",
            repository_info=None,
            repository_type="python",
            enabled_tools=["pylint_analysis"],
            tool_results={},
            failed_tools=["github_repository"],
            analysis_results=None,
            files_analyzed=[],
            total_files=0,
            review_config={},
            start_time=datetime.now().isoformat(),
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )


class NodeValidator:
    """Utilities for validating node inputs and outputs."""
    
    @staticmethod
    def validate_state_schema(state: ReviewState) -> List[str]:
        """Validate ReviewState schema and return list of validation errors."""
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
        if 'messages' in state and not isinstance(state['messages'], list):
            errors.append("Field 'messages' must be a list")
        
        if 'current_step' in state and not isinstance(state['current_step'], str):
            errors.append("Field 'current_step' must be a string")
        
        if 'enabled_tools' in state and not isinstance(state['enabled_tools'], list):
            errors.append("Field 'enabled_tools' must be a list")
        
        if 'tool_results' in state and not isinstance(state['tool_results'], dict):
            errors.append("Field 'tool_results' must be a dict")
        
        return errors
    
    @staticmethod
    def validate_node_output(output: Dict[str, Any], expected_keys: List[str] = None) -> List[str]:
        """Validate node output format and return list of validation errors."""
        errors = []
        
        if not isinstance(output, dict):
            errors.append("Node output must be a dictionary")
            return errors
        
        # Check for expected keys if provided
        if expected_keys:
            for key in expected_keys:
                if key not in output:
                    errors.append(f"Missing expected output key: {key}")
        
        return errors


class NodePerformanceMonitor:
    """Performance monitoring utilities for node execution."""
    
    @staticmethod
    async def measure_execution_time(node_func, state: ReviewState) -> tuple[Dict[str, Any], float]:
        """Measure node execution time and return (result, execution_time)."""
        start_time = time.time()
        result = await node_func(state)
        execution_time = time.time() - start_time
        return result, execution_time
    
    @staticmethod
    def create_performance_snapshot(node_name: str, execution_time: float, 
                                  state_size: int, output_size: int) -> Dict[str, Any]:
        """Create performance snapshot for regression testing."""
        return {
            "node_name": node_name,
            "execution_time": execution_time,
            "state_size": state_size,
            "output_size": output_size,
            "timestamp": datetime.now().isoformat(),
            "performance_threshold_ms": 1000  # 1 second threshold
        }


class StateSnapshotManager:
    """Utilities for creating and comparing state snapshots for regression testing."""
    
    @staticmethod
    def create_snapshot(state: ReviewState, output: Dict[str, Any]) -> Dict[str, Any]:
        """Create a snapshot of state and output for regression testing."""
        return {
            "input_state": {
                "current_step": state.get("current_step"),
                "status": state.get("status").value if state.get("status") else None,
                "repository_url": state.get("repository_url"),
                "repository_type": state.get("repository_type"),
                "enabled_tools": state.get("enabled_tools", []),
                "files_analyzed": state.get("files_analyzed", []),
                "total_files": state.get("total_files", 0),
                "error_message": state.get("error_message")
            },
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def compare_snapshots(snapshot1: Dict[str, Any], snapshot2: Dict[str, Any]) -> List[str]:
        """Compare two snapshots and return list of differences."""
        differences = []
        
        # Compare input states
        for key in snapshot1["input_state"]:
            if snapshot1["input_state"][key] != snapshot2["input_state"][key]:
                differences.append(f"Input state difference in {key}: {snapshot1['input_state'][key]} != {snapshot2['input_state'][key]}")
        
        # Compare outputs
        for key in snapshot1["output"]:
            if key not in snapshot2["output"]:
                differences.append(f"Output key missing in snapshot2: {key}")
            elif snapshot1["output"][key] != snapshot2["output"][key]:
                differences.append(f"Output difference in {key}: {snapshot1['output'][key]} != {snapshot2['output'][key]}")
        
        return differences


class TestStartReviewNode:
    """Comprehensive isolated testing for start_review_node."""

    @pytest.mark.asyncio
    async def test_start_review_node_basic_execution(self):
        """Test basic execution of start_review_node."""
        # Arrange
        state = NodeTestFixtures.create_start_review_state()

        # Act
        result = await start_review_node(state)

        # Assert
        assert isinstance(result, dict)
        assert "current_step" in result
        assert result["current_step"] == "analyze_code"

    @pytest.mark.asyncio
    async def test_start_review_node_with_debugging(self):
        """Test start_review_node with comprehensive debugging breakpoints."""
        # Arrange - Create realistic test state
        state = NodeTestFixtures.create_start_review_state()

        # Add debugging context
        test_context = {
            "test_name": "test_start_review_node_with_debugging",
            "test_purpose": "Validate repository fetching with debugging breakpoints",
            "expected_breakpoints": [
                "1_initial_state_validation",
                "2_url_validation_success",
                "3_tool_registry_init",
                "4_before_github_api_call",
                "5_after_github_api_call",
                "6_repository_info_extraction",
                "7_tool_selection_final",
                "8_final_success_state"
            ]
        }

        # 🔍 DEBUG BREAKPOINT: Test Start
        repo_debugger.debug_breakpoint(
            "test_start",
            state,
            test_context
        )

        # Act - Execute the node with debugging
        result = await start_review_node(state)

        # 🔍 DEBUG BREAKPOINT: Test Result Analysis
        repo_debugger.debug_breakpoint(
            "test_result_analysis",
            result,
            {
                "test_completed": True,
                "result_keys": list(result.keys()) if result else [],
                "success": result.get("status") != ReviewStatus.FAILED,
                "debug_session": repo_debugger.debug_session_id
            }
        )

        # Assert - Validate results with debugging context
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "current_step" in result, "Result should contain current_step"
        assert "status" in result, "Result should contain status"
        assert "repository_info" in result, "Result should contain repository_info"
        assert "enabled_tools" in result, "Result should contain enabled_tools"

        # Validate that debugging breakpoints were hit
        assert len(repo_debugger.breakpoint_history) > 0, "Debugging breakpoints should have been triggered"

        # Print debugging summary for test analysis
        print(f"\n🔍 Debugging Test Summary:")
        print(f"   Debug Session: {repo_debugger.debug_session_id}")
        print(f"   Breakpoints Hit: {len(repo_debugger.breakpoint_history)}")
        print(f"   Test Result: {'✅ PASSED' if result.get('status') != ReviewStatus.FAILED else '❌ FAILED'}")

        repo_debugger.print_debug_summary()

    @pytest.mark.asyncio
    async def test_start_review_node_input_validation(self):
        """Test input validation for start_review_node."""
        # Test with minimal valid state
        minimal_state = NodeTestFixtures.create_minimal_state()
        validation_errors = NodeValidator.validate_state_schema(minimal_state)
        assert len(validation_errors) == 0, f"State validation failed: {validation_errors}"

        # Test node execution with minimal state
        result = await start_review_node(minimal_state)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_start_review_node_output_validation(self):
        """Test output validation for start_review_node."""
        # Arrange
        state = NodeTestFixtures.create_start_review_state()
        expected_keys = ["current_step"]

        # Act
        result = await start_review_node(state)

        # Assert
        validation_errors = NodeValidator.validate_node_output(result, expected_keys)
        assert len(validation_errors) == 0, f"Output validation failed: {validation_errors}"

    @pytest.mark.asyncio
    async def test_start_review_node_error_handling(self):
        """Test error handling scenarios for start_review_node."""
        # Test with invalid state (missing required fields)
        invalid_state = {"invalid": "state"}

        try:
            result = await start_review_node(invalid_state)
            # Node should handle gracefully and return some result
            assert isinstance(result, dict)
        except Exception as e:
            # If exception is raised, it should be handled gracefully
            pytest.fail(f"Node should handle invalid state gracefully, but raised: {e}")

    @pytest.mark.asyncio
    async def test_start_review_node_performance(self):
        """Test performance monitoring for start_review_node."""
        # Arrange
        state = NodeTestFixtures.create_start_review_state()

        # Act
        result, execution_time = await NodePerformanceMonitor.measure_execution_time(
            start_review_node, state
        )

        # Assert
        assert execution_time < 1.0, f"Node execution took too long: {execution_time}s"

        # Create performance snapshot
        state_size = len(json.dumps(state, default=str))
        output_size = len(json.dumps(result, default=str))
        snapshot = NodePerformanceMonitor.create_performance_snapshot(
            "start_review_node", execution_time, state_size, output_size
        )

        assert snapshot["execution_time"] == execution_time
        assert snapshot["node_name"] == "start_review_node"

    @pytest.mark.asyncio
    async def test_start_review_node_regression_snapshot(self):
        """Test regression testing with state snapshots for start_review_node."""
        # Arrange
        state = NodeTestFixtures.create_start_review_state()

        # Act
        result = await start_review_node(state)

        # Create snapshot
        snapshot = StateSnapshotManager.create_snapshot(state, result)

        # Assert snapshot structure
        assert "input_state" in snapshot
        assert "output" in snapshot
        assert "timestamp" in snapshot
        assert snapshot["input_state"]["current_step"] == "start_review"
        assert snapshot["output"]["current_step"] == "analyze_code"

    @pytest.mark.asyncio
    async def test_start_review_node_with_different_repository_types(self):
        """Test start_review_node with different repository configurations."""
        # Test with different repository types
        test_cases = [
            {"repository_type": "python", "repository_url": "https://github.com/test/python-repo"},
            {"repository_type": "javascript", "repository_url": "https://github.com/test/js-repo"},
            {"repository_type": "mixed", "repository_url": "https://github.com/test/mixed-repo"},
        ]

        for case in test_cases:
            state = NodeTestFixtures.create_start_review_state()
            state["repository_type"] = case["repository_type"]
            state["repository_url"] = case["repository_url"]

            result = await start_review_node(state)

            assert isinstance(result, dict)
            assert "current_step" in result
            assert result["current_step"] == "analyze_code"


class TestAnalyzeCodeNode:
    """Comprehensive isolated testing for analyze_code_node."""

    @pytest.mark.asyncio
    async def test_analyze_code_node_basic_execution(self):
        """Test basic execution of analyze_code_node."""
        # Arrange
        state = NodeTestFixtures.create_analyze_code_state()

        # Act
        result = await analyze_code_node(state)

        # Assert
        assert isinstance(result, dict)
        assert "current_step" in result
        assert result["current_step"] == "generate_report"

    @pytest.mark.asyncio
    async def test_analyze_code_node_input_validation(self):
        """Test input validation for analyze_code_node."""
        # Test with properly structured state
        state = NodeTestFixtures.create_analyze_code_state()
        validation_errors = NodeValidator.validate_state_schema(state)
        assert len(validation_errors) == 0, f"State validation failed: {validation_errors}"

        # Test node execution
        result = await analyze_code_node(state)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_code_node_output_validation(self):
        """Test output validation for analyze_code_node."""
        # Arrange
        state = NodeTestFixtures.create_analyze_code_state()
        expected_keys = ["current_step"]

        # Act
        result = await analyze_code_node(state)

        # Assert
        validation_errors = NodeValidator.validate_node_output(result, expected_keys)
        assert len(validation_errors) == 0, f"Output validation failed: {validation_errors}"

    @pytest.mark.asyncio
    async def test_analyze_code_node_performance(self):
        """Test performance monitoring for analyze_code_node."""
        # Arrange
        state = NodeTestFixtures.create_analyze_code_state()

        # Act
        result, execution_time = await NodePerformanceMonitor.measure_execution_time(
            analyze_code_node, state
        )

        # Assert
        assert execution_time < 1.0, f"Node execution took too long: {execution_time}s"

        # Create performance snapshot
        state_size = len(json.dumps(state, default=str))
        output_size = len(json.dumps(result, default=str))
        snapshot = NodePerformanceMonitor.create_performance_snapshot(
            "analyze_code_node", execution_time, state_size, output_size
        )

        assert snapshot["execution_time"] == execution_time
        assert snapshot["node_name"] == "analyze_code_node"

    @pytest.mark.asyncio
    async def test_analyze_code_node_with_different_tool_configurations(self):
        """Test analyze_code_node with different enabled tools."""
        # Test with different tool configurations
        test_cases = [
            {"enabled_tools": ["pylint_analysis"]},
            {"enabled_tools": ["flake8_analysis", "bandit_analysis"]},
            {"enabled_tools": ["code_review", "complexity_analysis"]},
            {"enabled_tools": []},  # No tools enabled
        ]

        for case in test_cases:
            state = NodeTestFixtures.create_analyze_code_state()
            state["enabled_tools"] = case["enabled_tools"]

            result = await analyze_code_node(state)

            assert isinstance(result, dict)
            assert "current_step" in result
            assert result["current_step"] == "generate_report"


class TestGenerateReportNode:
    """Comprehensive isolated testing for generate_report_node."""

    @pytest.mark.asyncio
    async def test_generate_report_node_basic_execution(self):
        """Test basic execution of generate_report_node."""
        # Arrange
        state = NodeTestFixtures.create_generate_report_state()

        # Act
        result = await generate_report_node(state)

        # Assert
        assert isinstance(result, dict)
        assert "current_step" in result
        assert result["current_step"] == "complete"

    @pytest.mark.asyncio
    async def test_generate_report_node_input_validation(self):
        """Test input validation for generate_report_node."""
        # Test with properly structured state
        state = NodeTestFixtures.create_generate_report_state()
        validation_errors = NodeValidator.validate_state_schema(state)
        assert len(validation_errors) == 0, f"State validation failed: {validation_errors}"

        # Test node execution
        result = await generate_report_node(state)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_generate_report_node_output_validation(self):
        """Test output validation for generate_report_node."""
        # Arrange
        state = NodeTestFixtures.create_generate_report_state()
        expected_keys = ["current_step"]

        # Act
        result = await generate_report_node(state)

        # Assert
        validation_errors = NodeValidator.validate_node_output(result, expected_keys)
        assert len(validation_errors) == 0, f"Output validation failed: {validation_errors}"

    @pytest.mark.asyncio
    async def test_generate_report_node_performance(self):
        """Test performance monitoring for generate_report_node."""
        # Arrange
        state = NodeTestFixtures.create_generate_report_state()

        # Act
        result, execution_time = await NodePerformanceMonitor.measure_execution_time(
            generate_report_node, state
        )

        # Assert
        assert execution_time < 1.0, f"Node execution took too long: {execution_time}s"

        # Create performance snapshot
        state_size = len(json.dumps(state, default=str))
        output_size = len(json.dumps(result, default=str))
        snapshot = NodePerformanceMonitor.create_performance_snapshot(
            "generate_report_node", execution_time, state_size, output_size
        )

        assert snapshot["execution_time"] == execution_time
        assert snapshot["node_name"] == "generate_report_node"

    @pytest.mark.asyncio
    async def test_generate_report_node_with_tool_results(self):
        """Test generate_report_node with different tool result configurations."""
        # Test with various tool result scenarios
        test_cases = [
            {"tool_results": {}},  # No tool results
            {"tool_results": {"pylint_analysis": NodeTestFixtures.create_generate_report_state()["tool_results"]["pylint_analysis"]}},  # Single tool result
            {"tool_results": NodeTestFixtures.create_generate_report_state()["tool_results"]},  # Multiple tool results
        ]

        for case in test_cases:
            state = NodeTestFixtures.create_generate_report_state()
            state["tool_results"] = case["tool_results"]

            result = await generate_report_node(state)

            assert isinstance(result, dict)
            assert "current_step" in result
            assert result["current_step"] == "complete"

    @pytest.mark.asyncio
    async def test_generate_report_node_regression_snapshot(self):
        """Test regression testing with state snapshots for generate_report_node."""
        # Arrange
        state = NodeTestFixtures.create_generate_report_state()

        # Act
        result = await generate_report_node(state)

        # Create snapshot
        snapshot = StateSnapshotManager.create_snapshot(state, result)

        # Assert snapshot structure
        assert "input_state" in snapshot
        assert "output" in snapshot
        assert "timestamp" in snapshot
        assert snapshot["input_state"]["current_step"] == "generate_report"
        assert snapshot["output"]["current_step"] == "complete"


class TestErrorHandlerNode:
    """Comprehensive isolated testing for error_handler_node."""

    @pytest.mark.asyncio
    async def test_error_handler_node_basic_execution(self):
        """Test basic execution of error_handler_node."""
        # Arrange
        state = NodeTestFixtures.create_error_state()

        # Act
        result = await error_handler_node(state)

        # Assert
        assert isinstance(result, dict)
        assert "current_step" in result
        assert result["current_step"] == "error_handled"
        assert "error_handled" in result
        assert result["error_handled"] is True

    @pytest.mark.asyncio
    async def test_error_handler_node_input_validation(self):
        """Test input validation for error_handler_node."""
        # Test with error state
        state = NodeTestFixtures.create_error_state()
        validation_errors = NodeValidator.validate_state_schema(state)
        assert len(validation_errors) == 0, f"State validation failed: {validation_errors}"

        # Test node execution
        result = await error_handler_node(state)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_error_handler_node_output_validation(self):
        """Test output validation for error_handler_node."""
        # Arrange
        state = NodeTestFixtures.create_error_state()
        expected_keys = ["current_step", "error_handled"]

        # Act
        result = await error_handler_node(state)

        # Assert
        validation_errors = NodeValidator.validate_node_output(result, expected_keys)
        assert len(validation_errors) == 0, f"Output validation failed: {validation_errors}"

    @pytest.mark.asyncio
    async def test_error_handler_node_different_error_scenarios(self):
        """Test error_handler_node with different error scenarios."""
        # Test with different error messages
        error_scenarios = [
            "GitHub API rate limit exceeded",
            "Tool execution timeout",
            "Invalid repository URL",
            "Network connection failed",
            None,  # No error message
        ]

        for error_message in error_scenarios:
            state = NodeTestFixtures.create_error_state()
            state["error_message"] = error_message

            result = await error_handler_node(state)

            assert isinstance(result, dict)
            assert "current_step" in result
            assert result["current_step"] == "error_handled"
            assert "error_handled" in result
            assert result["error_handled"] is True

    @pytest.mark.asyncio
    async def test_error_handler_node_performance(self):
        """Test performance monitoring for error_handler_node."""
        # Arrange
        state = NodeTestFixtures.create_error_state()

        # Act
        result, execution_time = await NodePerformanceMonitor.measure_execution_time(
            error_handler_node, state
        )

        # Assert
        assert execution_time < 1.0, f"Node execution took too long: {execution_time}s"

        # Create performance snapshot
        state_size = len(json.dumps(state, default=str))
        output_size = len(json.dumps(result, default=str))
        snapshot = NodePerformanceMonitor.create_performance_snapshot(
            "error_handler_node", execution_time, state_size, output_size
        )

        assert snapshot["execution_time"] == execution_time
        assert snapshot["node_name"] == "error_handler_node"


class TestNodeDependencyMocking:
    """Test node behavior with mocked external dependencies."""

    @pytest.mark.asyncio
    async def test_start_review_node_with_mocked_github_tools(self):
        """Test start_review_node with mocked GitHub API calls."""
        # Arrange
        state = NodeTestFixtures.create_start_review_state()

        # Mock external dependencies
        with patch('tools.github_tools.GitHubRepositoryTool') as mock_github_tool:
            mock_github_tool.return_value.execute.return_value = {
                "success": True,
                "repository_info": {
                    "name": "test-repo",
                    "language": "Python",
                    "stars": 100
                }
            }

            # Act
            result = await start_review_node(state)

            # Assert
            assert isinstance(result, dict)
            assert "current_step" in result

    @pytest.mark.asyncio
    async def test_analyze_code_node_with_mocked_analysis_tools(self):
        """Test analyze_code_node with mocked static analysis tools."""
        # Arrange
        state = NodeTestFixtures.create_analyze_code_state()

        # Mock external analysis tools
        with patch('tools.analysis_tools.PylintTool') as mock_pylint, \
             patch('tools.analysis_tools.Flake8Tool') as mock_flake8:

            mock_pylint.return_value.execute.return_value = {
                "success": True,
                "score": 8.5,
                "issues": []
            }

            mock_flake8.return_value.execute.return_value = {
                "success": True,
                "issues": []
            }

            # Act
            result = await analyze_code_node(state)

            # Assert
            assert isinstance(result, dict)
            assert "current_step" in result

    @pytest.mark.asyncio
    async def test_generate_report_node_with_mocked_ai_tools(self):
        """Test generate_report_node with mocked AI analysis tools."""
        # Arrange
        state = NodeTestFixtures.create_generate_report_state()

        # Mock AI analysis tools
        with patch('tools.ai_analysis_tools.CodeReviewTool') as mock_ai_tool:
            mock_ai_tool.return_value.execute.return_value = {
                "success": True,
                "review": "Code quality is good with minor improvements needed.",
                "suggestions": ["Add more tests", "Improve documentation"]
            }

            # Act
            result = await generate_report_node(state)

            # Assert
            assert isinstance(result, dict)
            assert "current_step" in result


class TestNodeRegressionSuite:
    """Comprehensive regression testing suite with state snapshots."""

    @pytest.mark.asyncio
    async def test_all_nodes_regression_snapshots(self):
        """Test all nodes and create regression snapshots."""
        # Test data for all nodes
        node_test_data = [
            {
                "node_func": start_review_node,
                "state": NodeTestFixtures.create_start_review_state(),
                "expected_next_step": "analyze_code",
                "node_name": "start_review_node"
            },
            {
                "node_func": analyze_code_node,
                "state": NodeTestFixtures.create_analyze_code_state(),
                "expected_next_step": "generate_report",
                "node_name": "analyze_code_node"
            },
            {
                "node_func": generate_report_node,
                "state": NodeTestFixtures.create_generate_report_state(),
                "expected_next_step": "complete",
                "node_name": "generate_report_node"
            },
            {
                "node_func": error_handler_node,
                "state": NodeTestFixtures.create_error_state(),
                "expected_next_step": "error_handled",
                "node_name": "error_handler_node"
            }
        ]

        snapshots = []

        for test_case in node_test_data:
            # Execute node
            result = await test_case["node_func"](test_case["state"])

            # Validate basic output
            assert isinstance(result, dict)
            assert "current_step" in result
            assert result["current_step"] == test_case["expected_next_step"]

            # Create snapshot
            snapshot = StateSnapshotManager.create_snapshot(test_case["state"], result)
            snapshot["node_name"] = test_case["node_name"]
            snapshots.append(snapshot)

        # Validate all snapshots were created
        assert len(snapshots) == 4

        # Validate snapshot structure
        for snapshot in snapshots:
            assert "input_state" in snapshot
            assert "output" in snapshot
            assert "timestamp" in snapshot
            assert "node_name" in snapshot

    @pytest.mark.asyncio
    async def test_node_snapshot_comparison(self):
        """Test snapshot comparison functionality."""
        # Create two identical snapshots
        state = NodeTestFixtures.create_start_review_state()
        result = await start_review_node(state)

        snapshot1 = StateSnapshotManager.create_snapshot(state, result)
        snapshot2 = StateSnapshotManager.create_snapshot(state, result)

        # Compare snapshots (should be identical except timestamp)
        differences = StateSnapshotManager.compare_snapshots(snapshot1, snapshot2)

        # Only timestamp should be different
        timestamp_differences = [diff for diff in differences if "timestamp" not in diff]
        assert len(timestamp_differences) == 0, f"Unexpected differences: {timestamp_differences}"


class TestNodeIntegrationScenarios:
    """Test nodes in realistic integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_workflow_node_sequence(self):
        """Test complete sequence of node executions."""
        # Start with initial state
        initial_state = NodeTestFixtures.create_start_review_state()

        # Execute start_review_node
        result1 = await start_review_node(initial_state)
        assert result1["current_step"] == "analyze_code"

        # Update state for analyze_code_node
        analyze_state = NodeTestFixtures.create_analyze_code_state()
        analyze_state.update(result1)

        # Execute analyze_code_node
        result2 = await analyze_code_node(analyze_state)
        assert result2["current_step"] == "generate_report"

        # Update state for generate_report_node
        report_state = NodeTestFixtures.create_generate_report_state()
        report_state.update(result2)

        # Execute generate_report_node
        result3 = await generate_report_node(report_state)
        assert result3["current_step"] == "complete"

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery workflow with error_handler_node."""
        # Create error scenario
        error_state = NodeTestFixtures.create_error_state()

        # Execute error_handler_node
        result = await error_handler_node(error_state)

        # Validate error handling
        assert result["current_step"] == "error_handled"
        assert result["error_handled"] is True

    @pytest.mark.asyncio
    async def test_node_performance_benchmarking(self):
        """Benchmark all nodes for performance regression testing."""
        performance_results = []

        # Test all nodes
        node_test_cases = [
            (start_review_node, NodeTestFixtures.create_start_review_state(), "start_review_node"),
            (analyze_code_node, NodeTestFixtures.create_analyze_code_state(), "analyze_code_node"),
            (generate_report_node, NodeTestFixtures.create_generate_report_state(), "generate_report_node"),
            (error_handler_node, NodeTestFixtures.create_error_state(), "error_handler_node")
        ]

        for node_func, state, node_name in node_test_cases:
            # Measure performance
            result, execution_time = await NodePerformanceMonitor.measure_execution_time(node_func, state)

            # Create performance record
            performance_record = {
                "node_name": node_name,
                "execution_time": execution_time,
                "success": isinstance(result, dict) and "current_step" in result,
                "timestamp": datetime.now().isoformat()
            }

            performance_results.append(performance_record)

            # Assert performance threshold (all nodes should execute quickly since they're placeholders)
            assert execution_time < 1.0, f"{node_name} took too long: {execution_time}s"

        # Validate all performance tests passed
        assert len(performance_results) == 4
        assert all(record["success"] for record in performance_results)
