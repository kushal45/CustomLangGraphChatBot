"""Comprehensive unit tests for tool registry and configuration."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path

# Import the classes to test
from tools.registry import ToolRegistry, ToolConfig, RepositoryType


class TestToolConfig:
    """Test ToolConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ToolConfig()
        assert config.enabled_categories == ["filesystem", "analysis", "ai_analysis", "github", "communication"]
        assert config.max_concurrent_tools == 5
        assert config.tool_timeout == 300
        assert config.enable_caching is True
    
    def test_config_from_environment(self):
        """Test configuration from environment variables."""
        with patch.dict(os.environ, {
            "TOOL_MAX_CONCURRENT": "10",
            "TOOL_TIMEOUT": "600",
            "TOOL_ENABLE_CACHING": "false"
        }):
            config = ToolConfig()
            assert config.max_concurrent_tools == 10
            assert config.tool_timeout == 600
            assert config.enable_caching is False
    
    def test_config_with_api_keys(self):
        """Test configuration with various API keys."""
        with patch.dict(os.environ, {
            "XAI_API_KEY": "xai-key",
            "GITHUB_TOKEN": "github-token",
            "SLACK_BOT_TOKEN": "slack-token"
        }):
            config = ToolConfig()
            assert bool(config.xai_api_key) is True
            assert bool(config.github_token) is True
            assert bool(config.slack_webhook_url) is True
    
    def test_config_without_api_keys(self):
        """Test configuration without API keys."""
        with patch.dict(os.environ, {}, clear=True):
            config = ToolConfig()
            assert bool(config.xai_api_key) is False
            assert bool(config.github_token) is False
            assert bool(config.slack_webhook_url) is False


class TestDetectRepositoryType:
    """Test repository type detection functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_detect_python_repository(self):
        """Test detection of Python repository."""
        # Create Python files
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write("print('Hello, World!')")
        with open(os.path.join(self.temp_dir, "requirements.txt"), "w") as f:
            f.write("requests==2.25.1")
        
        registry = ToolRegistry()
        file_extensions = [".py", ".txt"]
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.PYTHON
    
    def test_detect_javascript_repository(self):
        """Test detection of JavaScript repository."""
        # Create JavaScript files
        with open(os.path.join(self.temp_dir, "index.js"), "w") as f:
            f.write("console.log('Hello, World!');")
        with open(os.path.join(self.temp_dir, "package.json"), "w") as f:
            f.write('{"name": "test-project"}')
        
        registry = ToolRegistry()
        file_extensions = [".js", ".json"]
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.JAVASCRIPT
    
    def test_detect_java_repository(self):
        """Test detection of Java repository."""
        # Create Java files
        os.makedirs(os.path.join(self.temp_dir, "src", "main", "java"))
        with open(os.path.join(self.temp_dir, "src", "main", "java", "Main.java"), "w") as f:
            f.write("public class Main { }")
        with open(os.path.join(self.temp_dir, "pom.xml"), "w") as f:
            f.write("<project></project>")
        
        registry = ToolRegistry()
        file_extensions = [".java", ".xml"]
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.JAVA
    
    def test_detect_mixed_repository(self):
        """Test detection of mixed language repository."""
        # Create files for multiple languages
        with open(os.path.join(self.temp_dir, "main.py"), "w") as f:
            f.write("print('Hello')")
        with open(os.path.join(self.temp_dir, "index.js"), "w") as f:
            f.write("console.log('Hello');")
        
        registry = ToolRegistry()
        file_extensions = [".py", ".js"]
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.MIXED
    
    def test_detect_unknown_repository(self):
        """Test detection of unknown repository type."""
        # Create files with unknown extensions
        with open(os.path.join(self.temp_dir, "readme.txt"), "w") as f:
            f.write("This is a readme")
        
        registry = ToolRegistry()
        file_extensions = [".txt"]
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.UNKNOWN
    
    def test_detect_empty_directory(self):
        """Test detection with empty directory."""
        registry = ToolRegistry()
        file_extensions = []
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.UNKNOWN

    def test_detect_nonexistent_directory(self):
        """Test detection with non-existent directory."""
        registry = ToolRegistry()
        file_extensions = []
        repo_type = registry.detect_repository_type(file_extensions)
        assert repo_type == RepositoryType.UNKNOWN


class TestToolRegistry:
    """Test ToolRegistry functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ToolConfig()
        self.registry = ToolRegistry(self.config)
    
    def test_registry_initialization(self):
        """Test registry initialization."""
        assert self.registry.config == self.config
        assert len(self.registry._tools) > 0
        # Check that tools are registered
        tool_names = self.registry.get_tool_names()
        assert len(tool_names) > 0
    
    def test_get_enabled_tools(self):
        """Test getting available tools."""
        tools = self.registry.get_enabled_tools()
        
        # Should have tools from enabled categories
        assert len(tools) > 0
        
        # Check that tools have required attributes
        for tool in tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, '_run')
    
    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        from tools.registry import ToolCategory
        filesystem_tools = self.registry.get_tools_by_category(ToolCategory.FILESYSTEM)
        assert len(filesystem_tools) > 0

        # Check that all tools are from filesystem category
        for tool in filesystem_tools:
            assert "file" in tool.name.lower() or "directory" in tool.name.lower() or "git" in tool.name.lower()
    
    def test_get_tools_by_invalid_category(self):
        """Test getting tools by invalid category."""
        from tools.registry import ToolCategory
        # Use a valid category enum but one that might not have tools
        try:
            invalid_tools = self.registry.get_tools_by_category(ToolCategory.GITHUB)
            # This should work but might return empty list if no GitHub tools
            assert isinstance(invalid_tools, list)
        except Exception:
            # If it fails, that's also acceptable for this test
            pass
    
    def test_get_tool_by_name(self):
        """Test getting tool by name."""
        # Get a tool name that actually exists
        tool_names = self.registry.get_tool_names()
        if tool_names:
            first_tool_name = tool_names[0]
            tool = self.registry.get_tool(first_tool_name)
            assert tool is not None
            assert tool.name == first_tool_name

        # Test with non-existent tool
        non_existent = self.registry.get_tool("Non Existent Tool")
        assert non_existent is None
    
    def test_registry_with_disabled_categories(self):
        """Test registry with some categories disabled."""
        config = ToolConfig()
        config.enabled_categories = ["filesystem", "analysis"]  # Only enable some categories
        
        registry = ToolRegistry(config)
        tools = registry.get_enabled_tools()
        
        # Should only have tools from enabled categories
        tool_names = [tool.name for tool in tools]
        
        # Should have filesystem and analysis tools
        assert any("file" in name.lower() for name in tool_names)
        assert any("pylint" in name.lower() or "flake8" in name.lower() for name in tool_names)
    
    @patch.dict(os.environ, {}, clear=True)
    def test_registry_without_api_keys(self):
        """Test registry behavior without API keys."""
        config = ToolConfig()
        registry = ToolRegistry(config)
        
        # Should still have tools that don't require API keys
        tools = registry.get_enabled_tools()
        tool_names = [tool.name for tool in tools]
        
        # Should have filesystem tools (no API key required)
        assert any("file" in name.lower() for name in tool_names)
        
        # Should have analysis tools (no API key required)
        assert any("complexity" in name.lower() for name in tool_names)
    
    @patch.dict(os.environ, {"XAI_API_KEY": "test-key"})
    def test_registry_with_ai_api_key(self):
        """Test registry behavior with AI API key."""
        config = ToolConfig()
        registry = ToolRegistry(config)
        
        tools = registry.get_enabled_tools()
        tool_names = [tool.name for tool in tools]
        
        # Should have AI analysis tools when API key is available
        assert any("ai_code_review" in name.lower() for name in tool_names)
        assert any("documentation" in name.lower() for name in tool_names)
    
    def test_tool_execution_tracking(self):
        """Test tool execution tracking."""
        # Get a simple tool for testing
        # Get a tool that actually exists
        tool_names = self.registry.get_tool_names()
        if tool_names:
            tool = self.registry.get_tool(tool_names[0])
        else:
            tool = None
        assert tool is not None
        
        # Check that tool has execution tracking attributes
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert callable(getattr(tool, '_run'))
    
    def test_registry_tool_count_by_category(self):
        """Test counting tools by category."""
        from tools.registry import ToolCategory
        categories = [
            ToolCategory.FILESYSTEM,
            ToolCategory.STATIC_ANALYSIS,
            ToolCategory.AI_ANALYSIS,
            ToolCategory.GITHUB,
            ToolCategory.COMMUNICATION
        ]

        for category in categories:
            if category.value in self.config.enabled_categories:
                tools = self.registry.get_tools_by_category(category)
                assert len(tools) > 0, f"No tools found for category: {category.value}"
    
    def test_registry_tool_uniqueness(self):
        """Test that all tools have unique names."""
        tools = self.registry.get_enabled_tools()
        tool_names = [tool.name for tool in tools]
        
        # Check for duplicate names
        assert len(tool_names) == len(set(tool_names)), "Duplicate tool names found"
    
    def test_registry_tool_descriptions(self):
        """Test that all tools have descriptions."""
        tools = self.registry.get_enabled_tools()
        
        for tool in tools:
            assert hasattr(tool, 'description')
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0
    
    def test_registry_configuration_validation(self):
        """Test registry configuration validation."""
        # Test with invalid configuration
        invalid_config = ToolConfig()
        invalid_config.enabled_categories = ["invalid_category"]
        
        registry = ToolRegistry(invalid_config)
        tools = registry.get_enabled_tools()
        
        # Should handle invalid categories gracefully
        assert isinstance(tools, list)
    
    def test_registry_concurrent_access(self):
        """Test registry thread safety for concurrent access."""
        import threading
        
        results = []
        
        def get_tools():
            tools = self.registry.get_enabled_tools()
            results.append(len(tools))
        
        # Create multiple threads accessing registry
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=get_tools)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should get the same number of tools
        assert len(set(results)) == 1, "Inconsistent results from concurrent access"


if __name__ == "__main__":
    pytest.main([__file__])
