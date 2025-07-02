"""Shared pytest fixtures and configuration."""

import pytest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch
from typing import Generator, Dict, Any

# Import components for fixtures
from tools.registry import ToolRegistry, ToolConfig
from src.state import AnalysisState, AnalysisRequest


@pytest.fixture
def temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_python_file(temp_directory: str) -> str:
    """Create a sample Python file for testing."""
    file_path = os.path.join(temp_directory, "sample.py")
    with open(file_path, "w") as f:
        f.write('''
"""Sample Python module for testing."""

def calculate_sum(numbers):
    """Calculate the sum of a list of numbers."""
    total = 0
    for num in numbers:
        total += num
    return total

def complex_function(x, y, z):
    """A function with higher complexity for testing."""
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

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, initial_value=0):
        self.value = initial_value
    
    def add(self, number):
        """Add a number to the current value."""
        self.value += number
        return self.value
    
    def multiply(self, number):
        """Multiply the current value by a number."""
        self.value *= number
        return self.value

if __name__ == "__main__":
    calc = Calculator()
    print(calc.add(5))
    print(calc.multiply(2))
''')
    return file_path


@pytest.fixture
def sample_repository(temp_directory: str) -> str:
    """Create a sample repository structure for testing."""
    # Create directory structure
    src_dir = os.path.join(temp_directory, "src")
    tests_dir = os.path.join(temp_directory, "tests")
    os.makedirs(src_dir)
    os.makedirs(tests_dir)
    
    # Create main module
    with open(os.path.join(src_dir, "main.py"), "w") as f:
        f.write('''
"""Main application module."""

from .utils import helper_function

def main():
    """Main application entry point."""
    result = helper_function("Hello, World!")
    print(result)
    return result

if __name__ == "__main__":
    main()
''')
    
    # Create utils module
    with open(os.path.join(src_dir, "utils.py"), "w") as f:
        f.write('''
"""Utility functions."""

def helper_function(message):
    """A helper function that processes messages."""
    return f"Processed: {message}"

def validate_input(data):
    """Validate input data."""
    if not data:
        raise ValueError("Data cannot be empty")
    return True
''')
    
    # Create test file
    with open(os.path.join(tests_dir, "test_main.py"), "w") as f:
        f.write('''
"""Tests for main module."""

import pytest
from src.main import main
from src.utils import helper_function, validate_input

def test_main():
    """Test main function."""
    result = main()
    assert "Processed: Hello, World!" in result

def test_helper_function():
    """Test helper function."""
    result = helper_function("test")
    assert result == "Processed: test"

def test_validate_input():
    """Test input validation."""
    assert validate_input("valid data") is True
    
    with pytest.raises(ValueError):
        validate_input("")
''')
    
    # Create requirements.txt
    with open(os.path.join(temp_directory, "requirements.txt"), "w") as f:
        f.write("pytest>=6.0.0\nrequests>=2.25.0\n")
    
    # Create README.md
    with open(os.path.join(temp_directory, "README.md"), "w") as f:
        f.write("# Sample Repository\n\nThis is a sample repository for testing.\n")
    
    return temp_directory


@pytest.fixture
def tool_config() -> ToolConfig:
    """Create a test tool configuration."""
    config = ToolConfig()
    config.tool_timeout = 30
    config.max_file_size = 1024 * 1024  # 1MB
    config.enabled_categories = ["filesystem", "analysis", "ai_analysis", "github", "communication"]
    return config


@pytest.fixture
def tool_registry(tool_config: ToolConfig) -> ToolRegistry:
    """Create a test tool registry."""
    return ToolRegistry(tool_config)


@pytest.fixture
def sample_analysis_request(sample_repository: str) -> AnalysisRequest:
    """Create a sample analysis request."""
    return AnalysisRequest(
        repository_url=sample_repository,
        analysis_type="comprehensive",
        target_files=["src/main.py", "src/utils.py"],
        include_ai_analysis=True
    )


@pytest.fixture
def sample_analysis_state(sample_analysis_request: AnalysisRequest) -> AnalysisState:
    """Create a sample analysis state."""
    return AnalysisState(request=sample_analysis_request)


@pytest.fixture
def mock_grok_response() -> Dict[str, Any]:
    """Create a mock Grok API response."""
    return {
        "choices": [{
            "message": {
                "content": '''
{
    "issues": [
        {
            "severity": "MEDIUM",
            "line": 5,
            "message": "Consider adding input validation",
            "suggestion": "Add type hints and validation for the numbers parameter"
        }
    ],
    "overall_score": 8.5,
    "summary": "Code quality is good with minor improvements needed"
}
'''
            }
        }]
    }


@pytest.fixture
def mock_github_response() -> Dict[str, Any]:
    """Create a mock GitHub API response."""
    return {
        "name": "test-repo",
        "full_name": "test-user/test-repo",
        "description": "A test repository",
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 7,
        "open_issues_count": 3,
        "default_branch": "main",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-12-01T00:00:00Z"
    }


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess execution."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "[]"  # Empty JSON array for no issues
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess execution."""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error: Tool execution failed"
    return mock_result


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "GITHUB_TOKEN": "test-github-token",
        "XAI_API_KEY": "test-xai-key",
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        "EMAIL_SMTP_SERVER": "smtp.test.com",
        "EMAIL_USERNAME": "test@example.com",
        "EMAIL_PASSWORD": "test-password",
        "JIRA_URL": "https://test.atlassian.net",
        "JIRA_USERNAME": "test@example.com",
        "JIRA_API_TOKEN": "test-jira-token"
    }
    
    with patch.dict(os.environ, test_env):
        yield


@pytest.fixture
def large_file_content() -> str:
    """Generate large file content for performance testing."""
    lines = []
    for i in range(1000):
        lines.append(f"def function_{i}(param_{i}):")
        lines.append(f"    \"\"\"Function {i} for testing.\"\"\"")
        lines.append(f"    return param_{i} * {i}")
        lines.append("")
    return "\n".join(lines)


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "ai: Tests requiring AI API")
    config.addinivalue_line("markers", "github: Tests requiring GitHub API")
    config.addinivalue_line("markers", "network: Tests requiring network access")


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file names
        if "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        elif "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        elif "test_workflow_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_ai_analysis" in item.nodeid:
            item.add_marker(pytest.mark.ai)
        elif "test_github" in item.nodeid:
            item.add_marker(pytest.mark.github)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Mark slow tests
        if "performance" in item.nodeid or "load" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Mark network tests
        if any(keyword in item.nodeid for keyword in ["github", "slack", "webhook", "email"]):
            item.add_marker(pytest.mark.network)
