"""Comprehensive unit tests for AI analysis tools with generic AI provider support."""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Import the tools to test
from tools.ai_analysis_tools import (
    CodeReviewTool, DocumentationGeneratorTool,
    RefactoringSuggestionTool, TestGeneratorTool,
    AIConfig, AIProvider, GenericAILLM, get_ai_config
)


class TestAIConfig:
    """Test AIConfig configuration class."""

    def test_default_config_groq(self):
        """Test default configuration values for Groq."""
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            config = get_ai_config()
            assert config.provider == AIProvider.GROQ
            assert config.model_name == "llama3-8b-8192"
            assert config.temperature == 0.1
            assert config.max_tokens == 2000

    def test_config_with_multiple_providers(self):
        """Test configuration with multiple providers available."""
        with patch.dict(os.environ, {
            "GROQ_API_KEY": "groq-key",
            "GOOGLE_API_KEY": "google-key"
        }):
            config = get_ai_config()
            # Should prefer Groq as it's first in priority
            assert config.provider == AIProvider.GROQ
            assert config.api_key == "groq-key"

    def test_config_fallback_to_huggingface(self):
        """Test configuration fallback to Hugging Face."""
        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "hf-key"}, clear=True):
            config = get_ai_config()
            assert config.provider == AIProvider.HUGGINGFACE
            assert config.api_key == "hf-key"

    def test_config_explicit_provider(self):
        """Test explicit provider selection."""
        with patch.dict(os.environ, {
            "AI_PROVIDER": "google",
            "GOOGLE_API_KEY": "google-key",
            "GROQ_API_KEY": "groq-key"
        }):
            config = get_ai_config()
            assert config.provider == AIProvider.GOOGLE
            assert config.api_key == "google-key"


class TestGrokLLM:
    """Test GrokLLM wrapper class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = GrokConfig(api_key="test-key")
        self.llm = GrokLLM(self.config)
    
    @patch('requests.post')
    def test_successful_api_call(self, mock_post):
        """Test successful API call to Grok."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test message"}]
        result = self.llm.invoke(messages)
        
        assert result == "Test response"
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_api_call_failure(self, mock_post):
        """Test API call failure handling."""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test message"}]
        result = self.llm.invoke(messages)
        
        assert "Error calling Grok API" in result
    
    @patch('requests.post')
    def test_api_call_timeout(self, mock_post):
        """Test API call timeout handling."""
        # Mock timeout exception
        mock_post.side_effect = Exception("Timeout")
        
        messages = [{"role": "user", "content": "Test message"}]
        result = self.llm.invoke(messages)
        
        assert "Error calling Grok API" in result


class TestCodeReviewTool:
    """Test CodeReviewTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = CodeReviewTool()
        self.sample_code = '''
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
'''
    
    @patch('tools.ai_analysis_tools.GrokLLM.invoke')
    def test_successful_code_review(self, mock_invoke):
        """Test successful code review."""
        # Mock Grok response
        mock_response = json.dumps({
            "overall_score": 6,
            "code_quality": {
                "readability": 8,
                "maintainability": 5,
                "performance": 3
            },
            "issues": [
                {
                    "severity": "HIGH",
                    "category": "Performance",
                    "line": 4,
                    "description": "Inefficient recursive implementation",
                    "suggestion": "Use dynamic programming or iterative approach"
                }
            ],
            "strengths": ["Clear function name", "Simple logic"],
            "recommendations": ["Add memoization", "Add input validation"]
        })
        mock_invoke.return_value = mock_response
        
        query = json.dumps({
            "code": self.sample_code,
            "language": "Python",
            "context": "Fibonacci calculation function"
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["overall_score"] == 6
        assert len(result["issues"]) == 1
        assert result["issues"][0]["severity"] == "HIGH"
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")
        assert "error" in result
        assert "Invalid JSON input" in result["error"]
    
    def test_missing_code_parameter(self):
        """Test handling of missing code parameter."""
        query = json.dumps({"language": "Python"})
        result = self.tool._run(query)
        assert "error" in result
        assert "Code is required" in result["error"]
    
    @patch('tools.ai_analysis_tools.GrokLLM.invoke')
    def test_malformed_grok_response(self, mock_invoke):
        """Test handling of malformed Grok response."""
        # Mock malformed JSON response
        mock_invoke.return_value = "This is not valid JSON"
        
        query = json.dumps({
            "code": self.sample_code,
            "language": "Python"
        })
        
        result = self.tool._run(query)
        
        # Should still return a result with fallback parsing
        assert "error" not in result or "Failed to parse" in result.get("error", "")


class TestDocumentationGeneratorTool:
    """Test DocumentationGeneratorTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DocumentationGeneratorTool()
        self.sample_code = '''
def process_data(data, filter_empty=True):
    result = []
    for item in data:
        if filter_empty and not item:
            continue
        result.append(item.upper())
    return result
'''
    
    @patch('tools.ai_analysis_tools.GrokLLM.invoke')
    def test_successful_documentation_generation(self, mock_invoke):
        """Test successful documentation generation."""
        mock_response = json.dumps({
            "documented_code": '''
def process_data(data, filter_empty=True):
    """Process a list of data items with optional filtering.
    
    Args:
        data (list): List of items to process
        filter_empty (bool): Whether to filter out empty items
    
    Returns:
        list: Processed data with items converted to uppercase
    """
    result = []
    for item in data:
        if filter_empty and not item:
            continue
        result.append(item.upper())
    return result
''',
            "documentation_quality": {
                "completeness": 9,
                "clarity": 8,
                "examples_included": False
            },
            "docstring_style": "Google",
            "improvements": ["Add usage examples", "Add type hints"]
        })
        mock_invoke.return_value = mock_response
        
        query = json.dumps({
            "code": self.sample_code,
            "language": "Python",
            "style": "Google"
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert "documented_code" in result
        assert result["docstring_style"] == "Google"
        assert result["documentation_quality"]["completeness"] == 9


class TestRefactoringSuggestionTool:
    """Test RefactoringSuggestionTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = RefactoringSuggestionTool()
        self.sample_code = '''
def calculate_total(items):
    total = 0
    for item in items:
        if item['active']:
            if item['price'] > 0:
                total += item['price']
    return total
'''
    
    @patch('tools.ai_analysis_tools.GrokLLM.invoke')
    def test_successful_refactoring_suggestions(self, mock_invoke):
        """Test successful refactoring suggestions."""
        mock_response = json.dumps({
            "refactoring_score": 5,
            "potential_score": 8,
            "priority_suggestions": [
                {
                    "priority": "HIGH",
                    "category": "Structure",
                    "current_issue": "Nested if statements reduce readability",
                    "suggested_improvement": "Combine conditions or use early returns",
                    "benefits": ["Improved readability", "Reduced complexity"],
                    "effort_estimate": "LOW"
                }
            ],
            "design_patterns": ["Filter pattern", "Strategy pattern"],
            "performance_improvements": ["Use list comprehension", "Add input validation"],
            "maintainability_improvements": ["Extract helper functions", "Add type hints"]
        })
        mock_invoke.return_value = mock_response
        
        query = json.dumps({
            "code": self.sample_code,
            "language": "Python",
            "focus_areas": ["readability", "performance"]
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["refactoring_score"] == 5
        assert result["potential_score"] == 8
        assert len(result["priority_suggestions"]) == 1
        assert result["priority_suggestions"][0]["priority"] == "HIGH"


class TestTestGeneratorTool:
    """Test TestGeneratorTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = TestGeneratorTool()
        self.sample_code = '''
def divide_numbers(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
    
    @patch('tools.ai_analysis_tools.GrokLLM.invoke')
    def test_successful_test_generation(self, mock_invoke):
        """Test successful test generation."""
        mock_response = json.dumps({
            "test_code": '''
import pytest

def test_divide_numbers_success():
    assert divide_numbers(10, 2) == 5.0
    assert divide_numbers(9, 3) == 3.0

def test_divide_numbers_zero_division():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide_numbers(10, 0)

def test_divide_numbers_negative():
    assert divide_numbers(-10, 2) == -5.0
''',
            "test_cases": [
                {
                    "test_name": "test_divide_numbers_success",
                    "description": "Test successful division",
                    "test_type": "unit",
                    "coverage_area": "normal operation"
                },
                {
                    "test_name": "test_divide_numbers_zero_division",
                    "description": "Test zero division error",
                    "test_type": "edge_case",
                    "coverage_area": "error handling"
                }
            ],
            "coverage_analysis": {
                "estimated_coverage": "95%",
                "covered_functions": ["divide_numbers"],
                "uncovered_areas": ["Input type validation"]
            },
            "setup_requirements": ["pytest"],
            "edge_cases": ["Zero division", "Negative numbers"],
            "additional_test_suggestions": ["Add type checking tests", "Add performance tests"]
        })
        mock_invoke.return_value = mock_response
        
        query = json.dumps({
            "code": self.sample_code,
            "language": "Python",
            "test_framework": "pytest"
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert "test_code" in result
        assert len(result["test_cases"]) == 2
        assert result["coverage_analysis"]["estimated_coverage"] == "95%"
        assert "pytest" in result["setup_requirements"]


if __name__ == "__main__":
    pytest.main([__file__])
