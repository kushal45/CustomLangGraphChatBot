"""Comprehensive unit tests for static analysis tools."""

import pytest
import tempfile
import os
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the tools to test
from tools.analysis_tools import (
    PylintTool, Flake8Tool, BanditSecurityTool, CodeComplexityTool,
    CodeAnalysisConfig
)


class TestCodeAnalysisConfig:
    """Test CodeAnalysisConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = CodeAnalysisConfig()
        assert config.max_file_size == 1024 * 1024  # 1MB
        assert config.timeout == 60
        assert config.temp_dir is None


class TestPylintTool:
    """Test PylintTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = PylintTool()
        self.good_code = '''
"""A well-written Python module."""

def calculate_sum(numbers):
    """Calculate the sum of a list of numbers.
    
    Args:
        numbers (list): List of numbers to sum
        
    Returns:
        float: Sum of the numbers
    """
    return sum(numbers)


def main():
    """Main function."""
    test_numbers = [1, 2, 3, 4, 5]
    result = calculate_sum(test_numbers)
    print(f"Sum: {result}")


if __name__ == "__main__":
    main()
'''
        
        self.bad_code = '''
import os, sys
def badFunction(x,y):
    if x>0:
        if y>0:
            return x+y
    else:
        return 0
'''
    
    @patch('subprocess.run')
    def test_successful_pylint_analysis(self, mock_run):
        """Test successful pylint analysis."""
        # Mock pylint output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([
            {
                "type": "convention",
                "module": "test",
                "obj": "badFunction",
                "line": 2,
                "column": 0,
                "message": "Function name should be snake_case",
                "message-id": "C0103"
            }
        ])
        mock_run.return_value = mock_result
        
        result = self.tool._run(self.bad_code)
        
        assert "error" not in result
        assert result["tool"] == "pylint"
        assert result["total_issues"] == 1
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "convention"
    
    @patch('subprocess.run')
    def test_pylint_no_issues(self, mock_run):
        """Test pylint with no issues found."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "[]"
        mock_run.return_value = mock_result
        
        result = self.tool._run(self.good_code)
        
        assert "error" not in result
        assert result["total_issues"] == 0
        assert len(result["issues"]) == 0
    
    @patch('subprocess.run')
    def test_pylint_not_installed(self, mock_run):
        """Test handling when pylint is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.tool._run(self.good_code)
        
        assert "error" in result
        assert "Pylint not installed" in result["error"]
    
    @patch('subprocess.run')
    def test_pylint_timeout(self, mock_run):
        """Test handling of pylint timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("pylint", 60)
        
        result = self.tool._run(self.good_code)
        
        assert "error" in result
        assert "timed out" in result["error"]
    
    def test_code_too_large(self):
        """Test handling of code that's too large."""
        # Create a tool with small max file size
        tool = PylintTool()
        tool.config.max_file_size = 10  # Very small limit
        
        large_code = "x = 1\n" * 100  # Larger than limit
        result = tool._run(large_code)
        
        assert "error" in result
        assert "too large" in result["error"]


class TestFlake8Tool:
    """Test Flake8Tool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = Flake8Tool()
        self.code_with_issues = '''
import os,sys
def bad_function( x,y ):
    if x>0:
        return x+y
    else:
        return 0
'''
    
    @patch('subprocess.run')
    def test_successful_flake8_analysis(self, mock_run):
        """Test successful flake8 analysis."""
        mock_result = Mock()
        mock_result.returncode = 1  # Flake8 returns 1 when issues found
        mock_result.stdout = '''temp_file.py:1:9: E401 multiple imports on one line
temp_file.py:2:1: E302 expected 2 blank lines, found 0
temp_file.py:2:16: E201 whitespace after '('
temp_file.py:2:19: E202 whitespace before ')'
'''
        mock_run.return_value = mock_result
        
        result = self.tool._run(self.code_with_issues)
        
        assert "error" not in result
        assert result["tool"] == "flake8"
        assert result["total_issues"] == 4
        assert len(result["issues"]) == 4
        assert result["issues"][0]["code"] == "E401"
    
    @patch('subprocess.run')
    def test_flake8_no_issues(self, mock_run):
        """Test flake8 with no issues."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        result = self.tool._run("print('hello')")
        
        assert "error" not in result
        assert result["total_issues"] == 0
    
    @patch('subprocess.run')
    def test_flake8_not_installed(self, mock_run):
        """Test handling when flake8 is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.tool._run(self.code_with_issues)
        
        assert "error" in result
        assert "Flake8 not installed" in result["error"]


class TestBanditSecurityTool:
    """Test BanditSecurityTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = BanditSecurityTool()
        self.insecure_code = '''
import subprocess
import os

def run_command(user_input):
    # Security issue: shell injection
    subprocess.call(user_input, shell=True)
    
def read_file(filename):
    # Security issue: path traversal
    with open("/tmp/" + filename, "r") as f:
        return f.read()

# Security issue: hardcoded password
PASSWORD = "admin123"
'''
    
    @patch('subprocess.run')
    def test_successful_bandit_analysis(self, mock_run):
        """Test successful bandit analysis."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = json.dumps({
            "results": [
                {
                    "test_name": "subprocess_popen_with_shell_equals_true",
                    "test_id": "B602",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "line_number": 6,
                    "issue_text": "subprocess call with shell=True identified",
                    "code": "subprocess.call(user_input, shell=True)"
                }
            ],
            "metrics": {
                "_totals": {
                    "loc": 15,
                    "nosec": 0
                }
            }
        })
        mock_run.return_value = mock_result
        
        result = self.tool._run(self.insecure_code)
        
        assert "error" not in result
        assert result["tool"] == "bandit"
        assert result["total_issues"] == 1
        assert result["severity_counts"]["HIGH"] == 1
        assert result["issues"][0]["test_id"] == "B602"
    
    @patch('subprocess.run')
    def test_bandit_no_issues(self, mock_run):
        """Test bandit with no security issues."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "results": [],
            "metrics": {"_totals": {"loc": 5}}
        })
        mock_run.return_value = mock_result
        
        safe_code = '''
def safe_function():
    return "Hello, World!"
'''
        
        result = self.tool._run(safe_code)
        
        assert "error" not in result
        assert result["total_issues"] == 0
    
    @patch('subprocess.run')
    def test_bandit_not_installed(self, mock_run):
        """Test handling when bandit is not installed."""
        mock_run.side_effect = FileNotFoundError()
        
        result = self.tool._run(self.insecure_code)
        
        assert "error" in result
        assert "Bandit not installed" in result["error"]


class TestCodeComplexityTool:
    """Test CodeComplexityTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeComplexityTool()
        self.simple_code = '''
def simple_function():
    return "hello"
'''
        
        self.complex_code = '''
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            if z > 0:
                return x + z
            else:
                return x
    else:
        if y > 0:
            if z > 0:
                return y + z
            else:
                return y
        else:
            return 0

class TestClass:
    def method1(self):
        pass
    
    def method2(self):
        pass
'''
    
    def test_simple_code_complexity(self):
        """Test complexity analysis of simple code."""
        result = self.tool._run(self.simple_code)
        
        assert "error" not in result
        assert result["tool"] == "complexity_analysis"
        assert result["total_functions"] == 1
        assert result["total_classes"] == 0
        assert result["lines_of_code"] > 0
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "simple_function"
        assert result["functions"][0]["complexity"] == 1  # No branches
    
    def test_complex_code_complexity(self):
        """Test complexity analysis of complex code."""
        result = self.tool._run(self.complex_code)
        
        assert "error" not in result
        assert result["total_functions"] == 3  # complex_function + 2 methods
        assert result["total_classes"] == 1
        
        # Find the complex function
        complex_func = next(f for f in result["functions"] if f["name"] == "complex_function")
        assert complex_func["complexity"] > 5  # Should have high complexity
        assert complex_func["parameters"] == 3
    
    def test_invalid_python_code(self):
        """Test handling of invalid Python code."""
        invalid_code = '''
def invalid_function(
    # Missing closing parenthesis and colon
'''
        
        result = self.tool._run(invalid_code)
        
        assert "error" in result
        assert "Failed to parse" in result["error"]
    
    def test_empty_code(self):
        """Test handling of empty code."""
        result = self.tool._run("")
        
        assert "error" not in result
        assert result["total_functions"] == 0
        assert result["total_classes"] == 0
        assert result["lines_of_code"] == 0
    
    def test_code_with_nested_functions(self):
        """Test complexity analysis with nested functions."""
        nested_code = '''
def outer_function():
    def inner_function():
        return 1
    
    if True:
        return inner_function()
    else:
        return 0
'''
        
        result = self.tool._run(nested_code)
        
        assert "error" not in result
        assert result["total_functions"] == 2  # outer and inner
        
        # Check that both functions are detected
        function_names = [f["name"] for f in result["functions"]]
        assert "outer_function" in function_names
        assert "inner_function" in function_names


if __name__ == "__main__":
    pytest.main([__file__])
