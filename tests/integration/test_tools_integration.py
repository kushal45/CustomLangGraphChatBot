"""Integration tests for external tools system."""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Import our tools
from tools.registry import ToolRegistry, ToolConfig, RepositoryType
from tools.github_tools import GitHubRepositoryTool, GitHubFileContentTool
from tools.analysis_tools import PylintTool, Flake8Tool, CodeComplexityTool
from tools.ai_analysis_tools import CodeReviewTool
from tools.filesystem_tools import FileReadTool, DirectoryListTool
from tools.communication_tools import SlackNotificationTool


class TestToolRegistry:
    """Test the tool registry and configuration system."""
    
    def test_tool_registry_initialization(self):
        """Test that tool registry initializes correctly."""
        config = ToolConfig()
        registry = ToolRegistry(config)
        
        # Check that all tools are registered
        all_tools = registry.get_all_tools()
        assert len(all_tools) > 0
        
        # Check specific tools exist
        assert registry.get_tool("github_repository") is not None
        assert registry.get_tool("pylint_analysis") is not None
        assert registry.get_tool("ai_code_review") is not None
        assert registry.get_tool("file_reader") is not None
    
    def test_repository_type_detection(self):
        """Test repository type detection based on file extensions."""
        registry = ToolRegistry()
        
        # Test Python repository
        python_extensions = ['.py', '.txt', '.md']
        assert registry.detect_repository_type(python_extensions) == RepositoryType.PYTHON
        
        # Test JavaScript repository
        js_extensions = ['.js', '.json', '.md']
        assert registry.detect_repository_type(js_extensions) == RepositoryType.JAVASCRIPT
        
        # Test mixed repository
        mixed_extensions = ['.py', '.js', '.java', '.cpp']
        assert registry.detect_repository_type(mixed_extensions) == RepositoryType.MIXED
    
    def test_tools_for_repository_type(self):
        """Test getting tools for specific repository types."""
        registry = ToolRegistry()
        
        # Test Python repository tools
        python_tools = registry.get_tools_for_repository(RepositoryType.PYTHON)
        tool_names = [tool.name for tool in python_tools]
        
        assert "pylint_analysis" in tool_names
        assert "flake8_analysis" in tool_names
        assert "bandit_security" in tool_names
        assert "github_repository" in tool_names


class TestFileSystemTools:
    """Test file system and repository tools."""
    
    def test_file_read_tool(self):
        """Test file reading functionality."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('Hello, World!')\n")
            temp_file = f.name
        
        try:
            tool = FileReadTool()
            result = tool._run(temp_file)
            
            assert "error" not in result
            assert result["content"] == "print('Hello, World!')\n"
            assert result["extension"] == ".py"
            assert result["lines"] == 1
        finally:
            os.unlink(temp_file)
    
    def test_file_read_tool_security(self):
        """Test file reading security checks."""
        tool = FileReadTool()
        
        # Test non-existent file
        result = tool._run("/non/existent/file.py")
        assert "error" in result
        assert "does not exist" in result["error"]
    
    def test_directory_list_tool(self):
        """Test directory listing functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            (Path(temp_dir) / "test.py").write_text("# Test file")
            (Path(temp_dir) / "README.md").write_text("# README")
            (Path(temp_dir) / "subdir").mkdir()
            
            tool = DirectoryListTool()
            query = json.dumps({
                "directory_path": temp_dir,
                "recursive": False,
                "include_hidden": False
            })
            
            result = tool._run(query)
            
            assert "error" not in result
            assert result["total_files"] >= 2
            assert result["total_directories"] >= 1
            
            # Check that files are listed
            file_names = [f["name"] for f in result["files"]]
            assert "test.py" in file_names
            assert "README.md" in file_names


class TestStaticAnalysisTools:
    """Test static code analysis tools."""
    
    def test_code_complexity_tool(self):
        """Test code complexity analysis."""
        # Create a simple Python file with known complexity
        python_code = '''def simple_function():
    return "hello"

def complex_function(x):
    if x > 0:
        if x > 10:
            return "high"
        else:
            return "medium"
    else:
        return "low"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(python_code)
            temp_file = f.name
        
        try:
            tool = CodeComplexityTool()
            result = tool._run(python_code)

            assert "error" not in result
            assert "metrics" in result
            assert result["metrics"]["functions"] == 2

            # Check that complex_function has higher complexity
            function_details = result["metrics"]["function_details"]
            complex_func = next(f for f in function_details if f["name"] == "complex_function")
            simple_func = next(f for f in function_details if f["name"] == "simple_function")

            assert complex_func["complexity"] > simple_func["complexity"]
        finally:
            os.unlink(temp_file)


class TestAIAnalysisTools:
    """Test AI-powered analysis tools."""
    
    @patch('tools.ai_analysis_tools.GenericAILLM')
    def test_code_review_tool_mock(self, mock_ai_llm):
        """Test code review tool with mocked OpenAI."""
        # Mock the OpenAI response
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "overall_score": 8.5,
            "issues": [
                {
                    "type": "style",
                    "severity": "low",
                    "line": 1,
                    "message": "Consider adding a docstring",
                    "suggestion": "Add a docstring to describe the function"
                }
            ],
            "strengths": ["Clean and readable code"],
            "recommendations": ["Add documentation"]
        }
        
        # Mock the AI LLM to return a JSON response
        mock_ai_instance = Mock()
        mock_ai_instance.invoke.return_value = json.dumps({
            "overall_score": 8.5,
            "issues": [
                {
                    "type": "style",
                    "severity": "low",
                    "line": 1,
                    "message": "Consider adding a docstring",
                    "suggestion": "Add a docstring to describe the function"
                }
            ],
            "strengths": ["Clean and readable code"],
            "recommendations": ["Add documentation"]
        })
        mock_ai_llm.return_value = mock_ai_instance

        tool = CodeReviewTool()

        query = json.dumps({
            "code": "def hello(): return 'world'",
            "language": "python"
        })

        result = tool._run(query)

        assert "error" not in result
        assert "review" in result
        assert "tool" in result
        assert result["tool"] == "ai_code_review"


class TestIntegrationFlow:
    """Test complete integration flows."""
    
    def test_python_repository_analysis_flow(self):
        """Test complete analysis flow for a Python repository."""
        # Create a temporary Python project
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create Python files
            (project_path / "main.py").write_text('''
def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
''')
            
            (project_path / "utils.py").write_text('''
import os

def get_file_size(filepath):
    if os.path.exists(filepath):
        return os.path.getsize(filepath)
    return 0
''')
            
            # Initialize tool registry
            registry = ToolRegistry()
            
            # Test directory listing
            dir_tool = registry.get_tool("directory_lister")
            dir_query = json.dumps({
                "directory_path": str(project_path),
                "recursive": True,
                "include_hidden": False
            })
            dir_result = dir_tool._run(dir_query)
            
            assert "error" not in dir_result
            assert dir_result["total_files"] == 2
            
            # Test file reading
            file_tool = registry.get_tool("file_reader")
            main_file_result = file_tool._run(str(project_path / "main.py"))
            
            assert "error" not in main_file_result
            assert "calculate_sum" in main_file_result["content"]
            
            # Test complexity analysis
            complexity_tool = registry.get_tool("code_complexity")
            # Read the file content first
            with open(project_path / "main.py", 'r') as f:
                main_py_content = f.read()
            complexity_result = complexity_tool._run(main_py_content)

            assert "error" not in complexity_result
            assert "metrics" in complexity_result
            assert complexity_result["metrics"]["functions"] >= 2
    
    def test_tool_configuration_validation(self):
        """Test tool configuration and validation."""
        import os
        from unittest.mock import patch

        # Test with minimal configuration (no environment variables)
        env_vars_to_clear = [
            'GITHUB_TOKEN', 'GROQ_API_KEY', 'HUGGINGFACE_API_KEY',
            'TOGETHER_API_KEY', 'GOOGLE_API_KEY', 'OPENROUTER_API_KEY',
            'XAI_API_KEY', 'OPENAI_API_KEY'
        ]

        with patch.dict(os.environ, {var: '' for var in env_vars_to_clear}, clear=False):
            config = ToolConfig()
            registry = ToolRegistry(config)

            validation = registry.validate_configuration()

            assert "valid" in validation
            assert "warnings" in validation
            assert "enabled_tools" in validation
            assert "disabled_tools" in validation

            # Should have warnings about missing API keys
            assert len(validation["warnings"]) > 0

            # Should still have some enabled tools (filesystem tools don't need API keys)
            assert len(validation["enabled_tools"]) > 0


# Utility functions for manual testing
def create_test_repository():
    """Create a test repository for manual testing."""
    test_dir = Path("test_repository")
    test_dir.mkdir(exist_ok=True)
    
    # Create Python files
    (test_dir / "main.py").write_text('''
"""Main module for the test application."""

import sys
from typing import List, Optional

def process_data(data: List[str], filter_empty: bool = True) -> List[str]:
    """Process a list of strings."""
    if filter_empty:
        return [item.strip() for item in data if item.strip()]
    return [item.strip() for item in data]

def main():
    """Main function."""
    sample_data = ["hello", " world ", "", "python"]
    result = process_data(sample_data)
    print("Processed data:", result)

if __name__ == "__main__":
    main()
''')
    
    (test_dir / "utils.py").write_text('''
"""Utility functions."""

import os
import json
from pathlib import Path

def read_config(config_path: str) -> dict:
    """Read configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON in {config_path}")
        return {}

def ensure_directory(path: str) -> bool:
    """Ensure directory exists."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Failed to create directory {path}: {e}")
        return False
''')
    
    (test_dir / "config.json").write_text('''
{
    "app_name": "Test Application",
    "version": "1.0.0",
    "debug": true,
    "features": {
        "logging": true,
        "metrics": false
    }
}
''')
    
    print(f"Test repository created at: {test_dir.absolute()}")
    return test_dir


if __name__ == "__main__":
    # Run manual tests
    print("Creating test repository...")
    test_repo = create_test_repository()
    
    print("\nTesting tool registry...")
    registry = ToolRegistry()
    validation = registry.validate_configuration()
    
    print(f"Configuration valid: {validation['valid']}")
    print(f"Enabled tools: {len(validation['enabled_tools'])}")
    print(f"Warnings: {len(validation['warnings'])}")
    
    print("\nTesting file system tools...")
    file_tool = registry.get_tool("file_reader")
    result = file_tool._run(str(test_repo / "main.py"))
    
    if "error" not in result:
        print(f"Successfully read file: {result['name']} ({result['lines']} lines)")
    else:
        print(f"Error reading file: {result['error']}")
    
    print("\nTesting directory listing...")
    dir_tool = registry.get_tool("directory_lister")
    dir_query = json.dumps({
        "directory_path": str(test_repo),
        "recursive": False,
        "include_hidden": False
    })
    dir_result = dir_tool._run(dir_query)
    
    if "error" not in dir_result:
        print(f"Directory contains {dir_result['total_files']} files and {dir_result['total_directories']} directories")
    else:
        print(f"Error listing directory: {dir_result['error']}")
    
    print("\nManual testing complete!")
