"""Comprehensive integration tests for workflow components."""

import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock

# Import workflow components to test
from src.state import AnalysisState, AnalysisRequest, AnalysisResult
from src.nodes import (
    initialize_analysis, select_tools, execute_tools, 
    aggregate_results, generate_report
)
from src.workflow import create_analysis_workflow
from tools.registry import ToolRegistry, ToolConfig


class TestAnalysisState:
    """Test AnalysisState data model."""
    
    def test_analysis_state_initialization(self):
        """Test AnalysisState initialization."""
        request = AnalysisRequest(
            repository_url="https://github.com/test/repo",
            analysis_type="comprehensive",
            target_files=["main.py", "utils.py"]
        )
        
        state = AnalysisState(request=request)
        
        assert state.request == request
        assert state.selected_tools == []
        assert state.tool_results == []
        assert state.final_report is None
        assert state.errors == []
        assert state.status == "initialized"
    
    def test_analysis_request_validation(self):
        """Test AnalysisRequest validation."""
        # Valid request
        request = AnalysisRequest(
            repository_url="https://github.com/test/repo",
            analysis_type="security"
        )
        assert request.repository_url == "https://github.com/test/repo"
        assert request.analysis_type == "security"
        assert request.target_files == []
    
    def test_analysis_result_creation(self):
        """Test AnalysisResult creation."""
        result = AnalysisResult(
            tool_name="Test Tool",
            status="success",
            data={"issues": 5, "score": 8.5},
            execution_time=2.5
        )
        
        assert result.tool_name == "Test Tool"
        assert result.status == "success"
        assert result.data["issues"] == 5
        assert result.execution_time == 2.5
        assert result.error is None


class TestWorkflowNodes:
    """Test individual workflow nodes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ToolConfig()
        self.registry = ToolRegistry(self.config)
        
        # Create test repository structure
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write('''
def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total

if __name__ == "__main__":
    print(calculate_sum([1, 2, 3, 4, 5]))
''')
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_initialize_analysis_node(self):
        """Test initialize_analysis node."""
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="code_quality"
        )
        state = AnalysisState(request=request)
        
        result = initialize_analysis(state)
        
        assert result["status"] == "initialized"
        assert result["repository_type"] in ["python", "mixed", "unknown"]
        assert "available_tools" in result
        assert len(result["available_tools"]) > 0
    
    def test_select_tools_node(self):
        """Test select_tools node."""
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="comprehensive"
        )
        state = AnalysisState(request=request)
        state.repository_type = "python"
        state.available_tools = self.registry.get_available_tools()
        
        result = select_tools(state)
        
        assert result["status"] == "tools_selected"
        assert len(result["selected_tools"]) > 0
        
        # Should select appropriate tools for Python repository
        tool_names = [tool.name for tool in result["selected_tools"]]
        assert any("complexity" in name.lower() for name in tool_names)
    
    def test_select_tools_for_security_analysis(self):
        """Test tool selection for security analysis."""
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="security"
        )
        state = AnalysisState(request=request)
        state.repository_type = "python"
        state.available_tools = self.registry.get_available_tools()
        
        result = select_tools(state)
        
        tool_names = [tool.name for tool in result["selected_tools"]]
        # Should prioritize security tools
        assert any("bandit" in name.lower() or "security" in name.lower() for name in tool_names)
    
    @patch('src.nodes.asyncio.run')
    def test_execute_tools_node(self, mock_asyncio_run):
        """Test execute_tools node."""
        # Mock tool execution
        mock_results = [
            AnalysisResult(
                tool_name="Code Complexity Tool",
                status="success",
                data={"total_functions": 1, "average_complexity": 2.0},
                execution_time=1.5
            )
        ]
        mock_asyncio_run.return_value = mock_results
        
        request = AnalysisRequest(repository_url=self.temp_dir)
        state = AnalysisState(request=request)
        state.selected_tools = [self.registry.get_tool_by_name("Code Complexity Tool")]
        
        result = execute_tools(state)
        
        assert result["status"] == "tools_executed"
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0].tool_name == "Code Complexity Tool"
        assert result["tool_results"][0].status == "success"
    
    def test_aggregate_results_node(self):
        """Test aggregate_results node."""
        request = AnalysisRequest(repository_url=self.temp_dir)
        state = AnalysisState(request=request)
        state.tool_results = [
            AnalysisResult(
                tool_name="Tool 1",
                status="success",
                data={"issues": 3, "score": 7.5}
            ),
            AnalysisResult(
                tool_name="Tool 2",
                status="success",
                data={"issues": 1, "score": 9.0}
            ),
            AnalysisResult(
                tool_name="Tool 3",
                status="error",
                error="Tool failed"
            )
        ]
        
        result = aggregate_results(state)
        
        assert result["status"] == "results_aggregated"
        assert result["summary"]["total_tools"] == 3
        assert result["summary"]["successful_tools"] == 2
        assert result["summary"]["failed_tools"] == 1
        assert result["summary"]["total_issues"] == 4
        assert result["summary"]["average_score"] == 8.25  # (7.5 + 9.0) / 2
    
    def test_generate_report_node(self):
        """Test generate_report node."""
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="comprehensive"
        )
        state = AnalysisState(request=request)
        state.summary = {
            "total_tools": 3,
            "successful_tools": 2,
            "failed_tools": 1,
            "total_issues": 5,
            "average_score": 7.8
        }
        state.tool_results = [
            AnalysisResult(
                tool_name="Code Review Tool",
                status="success",
                data={"issues": [{"severity": "HIGH", "message": "Security issue"}]}
            )
        ]
        
        result = generate_report(state)
        
        assert result["status"] == "completed"
        assert "final_report" in result
        
        report = result["final_report"]
        assert "repository_url" in report
        assert "analysis_type" in report
        assert "summary" in report
        assert "detailed_results" in report
        assert "recommendations" in report


class TestWorkflowIntegration:
    """Test end-to-end workflow integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a more complex test repository
        os.makedirs(os.path.join(self.temp_dir, "src"))
        os.makedirs(os.path.join(self.temp_dir, "tests"))
        
        # Main module
        with open(os.path.join(self.temp_dir, "src", "calculator.py"), "w") as f:
            f.write('''
"""A simple calculator module."""

def add(a, b):
    """Add two numbers."""
    return a + b

def divide(a, b):
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

def complex_function(x, y, z):
    """A function with higher complexity."""
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    else:
        return 0
''')
        
        # Test file
        with open(os.path.join(self.temp_dir, "tests", "test_calculator.py"), "w") as f:
            f.write('''
import pytest
from src.calculator import add, divide

def test_add():
    assert add(2, 3) == 5

def test_divide():
    assert divide(10, 2) == 5
    
def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(10, 0)
''')
        
        # Requirements file
        with open(os.path.join(self.temp_dir, "requirements.txt"), "w") as f:
            f.write("pytest>=6.0.0\n")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_workflow_execution(self):
        """Test complete workflow execution."""
        # Create workflow
        workflow = create_analysis_workflow()
        
        # Create initial state
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="comprehensive"
        )
        initial_state = AnalysisState(request=request)
        
        # Execute workflow (mock the LangGraph execution)
        with patch('src.workflow.app.invoke') as mock_invoke:
            # Mock the workflow execution result
            mock_final_state = AnalysisState(request=request)
            mock_final_state.status = "completed"
            mock_final_state.final_report = {
                "repository_url": self.temp_dir,
                "analysis_type": "comprehensive",
                "summary": {
                    "total_tools": 3,
                    "successful_tools": 3,
                    "total_issues": 2
                },
                "detailed_results": [],
                "recommendations": ["Add more tests", "Improve documentation"]
            }
            mock_invoke.return_value = mock_final_state
            
            # Execute workflow
            result = workflow.invoke(initial_state)
            
            assert result.status == "completed"
            assert result.final_report is not None
            assert result.final_report["analysis_type"] == "comprehensive"
    
    @patch('tools.analysis_tools.subprocess.run')
    def test_workflow_with_real_tools(self, mock_subprocess):
        """Test workflow with real tool execution (mocked subprocess)."""
        # Mock subprocess calls for static analysis tools
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"  # Empty JSON array for no issues
        mock_subprocess.return_value = mock_result
        
        # Create workflow
        workflow = create_analysis_workflow()
        
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="code_quality",
            target_files=["src/calculator.py"]
        )
        
        # Test individual nodes with real tool execution
        state = AnalysisState(request=request)
        
        # Initialize analysis
        state = initialize_analysis(state)
        assert state["status"] == "initialized"
        
        # Select tools
        state = select_tools(state)
        assert state["status"] == "tools_selected"
        assert len(state["selected_tools"]) > 0
    
    def test_workflow_error_handling(self):
        """Test workflow error handling."""
        # Test with invalid repository
        request = AnalysisRequest(
            repository_url="/nonexistent/path",
            analysis_type="comprehensive"
        )
        state = AnalysisState(request=request)
        
        result = initialize_analysis(state)
        
        # Should handle errors gracefully
        assert "error" in result or result["status"] == "initialized"
    
    def test_workflow_with_specific_tools(self):
        """Test workflow with specific tool selection."""
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="custom",
            specific_tools=["Code Complexity Tool"]
        )
        state = AnalysisState(request=request)
        state.repository_type = "python"
        
        config = ToolConfig()
        registry = ToolRegistry(config)
        state.available_tools = registry.get_available_tools()
        
        result = select_tools(state)
        
        # Should select only the specified tool
        tool_names = [tool.name for tool in result["selected_tools"]]
        assert "Code Complexity Tool" in tool_names
    
    def test_workflow_performance_tracking(self):
        """Test workflow performance tracking."""
        request = AnalysisRequest(repository_url=self.temp_dir)
        state = AnalysisState(request=request)
        
        # Mock tool results with execution times
        state.tool_results = [
            AnalysisResult(
                tool_name="Fast Tool",
                status="success",
                data={},
                execution_time=0.5
            ),
            AnalysisResult(
                tool_name="Slow Tool",
                status="success",
                data={},
                execution_time=5.0
            )
        ]
        
        result = aggregate_results(state)
        
        assert "performance" in result["summary"]
        assert result["summary"]["performance"]["total_execution_time"] == 5.5
        assert result["summary"]["performance"]["average_execution_time"] == 2.75


if __name__ == "__main__":
    pytest.main([__file__])
