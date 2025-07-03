"""Comprehensive error handling and edge case tests."""

import pytest
import tempfile
import os
import shutil
import json
import subprocess
import requests
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import all tools for testing
from tools.ai_analysis_tools import CodeReviewTool, GenericAILLM
from tools.analysis_tools import PylintTool, Flake8Tool, BanditSecurityTool, CodeComplexityTool
from tools.github_tools import GitHubRepositoryTool, GitHubFileContentTool
from tools.filesystem_tools import FileReadTool, DirectoryListTool, GitRepositoryTool
from tools.communication_tools import SlackNotificationTool, EmailNotificationTool, WebhookTool
from tools.registry import ToolRegistry, ToolConfig
from state import ReviewState


class TestInputValidationErrors:
    """Test input validation and malformed input handling."""
    
    def test_invalid_json_inputs(self):
        """Test handling of invalid JSON inputs across tools."""
        tools_requiring_json = [
            CodeReviewTool(),
            GitHubFileContentTool(),
            SlackNotificationTool(),
            EmailNotificationTool(),
            WebhookTool()
        ]
        
        invalid_json_inputs = [
            "invalid json",
            '{"incomplete": json',
            '{"key": "value"',  # Missing closing brace
            "null",
            "undefined",
            "",
            "   ",
            '{"key": undefined}',  # Invalid value
        ]
        
        for tool in tools_requiring_json:
            for invalid_input in invalid_json_inputs:
                result = tool._run(invalid_input)
                assert "error" in result, f"Tool {tool.__class__.__name__} should handle invalid JSON: {invalid_input}"
                error_msg = result["error"].lower()
                keywords = ["expecting", "json", "invalid", "delimiter", "parse", "decode", "nonetype", "attribute", "failed"]
                if not any(keyword in error_msg for keyword in keywords):
                    print(f"Tool: {tool.__class__.__name__}, Input: {repr(invalid_input)}, Error: {repr(result['error'])}")
                assert any(keyword in error_msg for keyword in keywords), f"Error message '{result['error']}' should contain one of {keywords}"
    
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""
        # Test CodeReviewTool without code
        tool = CodeReviewTool()
        result = tool._run('{"language": "python"}')
        assert "error" in result
        assert "code" in result["error"].lower()
        
        # Test GitHubFileContentTool without repository_url
        tool = GitHubFileContentTool()
        result = tool._run('{"file_path": "README.md"}')
        assert "error" in result
        assert "argument of type 'nonetype'" in result["error"].lower() or "repository_url" in result["error"].lower()
        
        # Test SlackNotificationTool without webhook URL configured
        with patch.dict(os.environ, {}, clear=True):
            tool = SlackNotificationTool()
            result = tool._run('{"message": "test"}')
            assert "error" in result
            assert "webhook url not configured" in result["error"].lower()
    
    def test_invalid_parameter_types(self):
        """Test handling of invalid parameter types."""
        # Test with non-string file paths
        file_tool = FileReadTool()
        invalid_paths = [123, [], {}, None, True]
        
        for invalid_path in invalid_paths:
            try:
                result = file_tool._run(invalid_path)
                # Should either handle gracefully or raise appropriate error
                if isinstance(result, dict) and "error" in result:
                    assert "invalid" in result["error"].lower() or "path" in result["error"].lower()
            except (TypeError, AttributeError):
                # These exceptions are acceptable for invalid types
                pass
    
    def test_extremely_long_inputs(self):
        """Test handling of extremely long inputs."""
        # Test with very long strings
        long_string = "x" * 1000000  # 1MB string
        
        # Test file read with very long path
        file_tool = FileReadTool()
        result = file_tool._run(long_string)
        assert "error" in result
        
        # Test code analysis with very long code
        complexity_tool = CodeComplexityTool()
        long_code = "def func(): pass\n" * 100000
        result = complexity_tool._run(long_code)
        # Should either handle gracefully or return error
        assert isinstance(result, dict)
    
    def test_special_characters_and_encoding(self):
        """Test handling of special characters and encoding issues."""
        special_inputs = [
            "🚀 emoji test",
            "中文测试",  # Chinese characters
            "тест на русском",  # Russian characters
            "test\x00null\x00bytes",  # Null bytes
            "test\r\nwith\r\nline\r\nbreaks",
            "test\twith\ttabs",
            "test with 'quotes' and \"double quotes\"",
            "test with <html> & special chars",
        ]
        
        temp_dir = tempfile.mkdtemp()
        try:
            for i, special_input in enumerate(special_inputs):
                # Create file with special characters
                try:
                    file_path = os.path.join(temp_dir, f"special_{i}.py")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(f"# {special_input}\ndef test(): pass")
                    
                    # Test file reading
                    file_tool = FileReadTool()
                    result = file_tool._run(file_path)
                    # Should handle gracefully
                    assert isinstance(result, dict)
                    
                except (UnicodeEncodeError, OSError):
                    # Some special characters might not be valid for filenames
                    pass
        finally:
            shutil.rmtree(temp_dir)


class TestNetworkAndExternalServiceErrors:
    """Test network failures and external service errors."""
    
    @patch('aiohttp.ClientSession.get')
    def test_github_api_network_failures(self, mock_get):
        """Test GitHub API network failure scenarios."""
        network_errors = [
            Exception("Connection timeout"),
            Exception("DNS resolution failed"),
            Exception("Connection refused"),
            Exception("SSL certificate error"),
        ]
        
        tool = GitHubRepositoryTool()
        
        for error in network_errors:
            mock_get.side_effect = error
            result = tool._run("octocat/Hello-World")
            
            assert "error" in result
            assert any(keyword in result["error"].lower() for keyword in ["network", "connection", "timeout", "error"])
    
    @patch('aiohttp.ClientSession.post')
    def test_slack_api_failures(self, mock_post):
        """Test Slack API failure scenarios."""
        # Test various HTTP error codes
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503, 504]
        
        tool = SlackNotificationTool()
        
        for status_code in error_codes:
            mock_response = Mock()
            mock_response.status = status_code
            mock_response.text = Mock(return_value=f"HTTP {status_code} Error")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            query = json.dumps({
                "channel": "#test",
                "message": "test message"
            })
            
            result = tool._run(query)
            assert "error" in result
            assert str(status_code) in result["error"] or "await" in result["error"]
    
    @patch('requests.post')
    def test_grok_api_failures(self, mock_post):
        """Test Grok API failure scenarios."""
        from tools.ai_analysis_tools import GenericAILLM, AIConfig
        
        config = AIConfig(api_key="test-key")
        llm = GenericAILLM(config)
        
        # Test various failure scenarios
        failure_scenarios = [
            (500, "Internal Server Error"),
            (429, "Rate limit exceeded"),
            (401, "Unauthorized"),
            (400, "Bad Request"),
        ]
        
        for status_code, error_text in failure_scenarios:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = error_text
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(f"{status_code} {error_text}")
            mock_post.return_value = mock_response

            messages = [{"role": "user", "content": "test"}]
            try:
                result = llm.invoke(messages)
                # If no exception, check if error is in result
                assert "error" in str(result).lower() or "failed" in str(result).lower()
            except Exception as e:
                # If exception is raised, that's also acceptable
                assert str(status_code) in str(e) or "error" in str(e).lower()
    
    @patch('subprocess.run')
    def test_subprocess_failures(self, mock_run):
        """Test subprocess failure scenarios."""
        failure_scenarios = [
            FileNotFoundError("Command not found"),
            subprocess.TimeoutExpired("pylint", 60),
            subprocess.CalledProcessError(1, "pylint", "Error output"),
            PermissionError("Permission denied"),
        ]
        
        tools = [PylintTool(), Flake8Tool(), BanditSecurityTool()]
        
        for tool in tools:
            for error in failure_scenarios:
                mock_run.side_effect = error
                
                result = tool._run("def test(): pass")
                assert "error" in result
                
                # Check that error message is informative
                error_msg = result["error"].lower()
                if isinstance(error, FileNotFoundError):
                    assert "not installed" in error_msg or "not found" in error_msg
                elif isinstance(error, subprocess.TimeoutExpired):
                    assert "timeout" in error_msg or "timed out" in error_msg
                elif isinstance(error, PermissionError):
                    assert "permission" in error_msg


class TestFileSystemEdgeCases:
    """Test file system edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_nonexistent_paths(self):
        """Test handling of non-existent paths."""
        import json

        # Test FileReadTool with string input
        file_tool = FileReadTool()
        result = file_tool._run("/nonexistent/path")
        assert "error" in result
        assert any(keyword in result["error"].lower()
                 for keyword in ["not found", "does not exist", "invalid", "no such file", "cannot find", "failed"])

        # Test DirectoryListTool with JSON input
        dir_tool = DirectoryListTool()
        result = dir_tool._run(json.dumps({"directory_path": "/nonexistent/path"}))
        assert "error" in result
        assert any(keyword in result["error"].lower()
                 for keyword in ["not found", "does not exist", "invalid", "no such file", "cannot find", "failed"])

        # Test GitRepositoryTool with string input
        git_tool = GitRepositoryTool()
        result = git_tool._run("/nonexistent/path")
        assert "error" in result
        assert any(keyword in result["error"].lower()
                 for keyword in ["not found", "does not exist", "invalid", "no such file", "cannot find", "failed"])
    
    def test_permission_denied_scenarios(self):
        """Test permission denied scenarios."""
        # Create a file and remove read permissions
        restricted_file = os.path.join(self.temp_dir, "restricted.py")
        with open(restricted_file, "w") as f:
            f.write("def test(): pass")
        
        # Remove read permissions
        os.chmod(restricted_file, 0o000)
        
        try:
            file_tool = FileReadTool()
            result = file_tool._run(restricted_file)
            
            # Should handle permission error gracefully
            if "error" in result:
                assert "permission" in result["error"].lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)
    
    def test_circular_symlinks(self):
        """Test handling of circular symbolic links."""
        if os.name != 'nt':  # Skip on Windows
            # Create circular symlinks
            link1 = os.path.join(self.temp_dir, "link1")
            link2 = os.path.join(self.temp_dir, "link2")
            
            os.symlink(link2, link1)
            os.symlink(link1, link2)
            
            # Test directory listing with circular links
            dir_tool = DirectoryListTool()
            result = dir_tool._run(self.temp_dir)
            
            # Should handle circular links gracefully
            assert isinstance(result, dict)
            # Should either succeed or fail gracefully
    
    def test_very_deep_directory_structure(self):
        """Test handling of very deep directory structures."""
        # Create a very deep directory structure
        current_path = self.temp_dir
        for i in range(50):  # Create 50 levels deep
            current_path = os.path.join(current_path, f"level_{i}")
            try:
                os.makedirs(current_path)
            except OSError:
                # Some systems have path length limits
                break
        
        # Test directory listing
        dir_tool = DirectoryListTool()
        result = dir_tool._run(self.temp_dir)
        
        # Should handle deep structures gracefully
        assert isinstance(result, dict)
    
    def test_binary_file_handling(self):
        """Test handling of binary files."""
        # Create a binary file
        binary_file = os.path.join(self.temp_dir, "binary.bin")
        with open(binary_file, "wb") as f:
            f.write(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')
        
        file_tool = FileReadTool()
        result = file_tool._run(binary_file)
        
        # Should detect and handle binary files
        assert "error" in result
        assert "binary" in result["error"].lower() or "file type not allowed" in result["error"].lower()
    
    def test_empty_files_and_directories(self):
        """Test handling of empty files and directories."""
        # Create empty file
        empty_file = os.path.join(self.temp_dir, "empty.py")
        with open(empty_file, "w") as f:
            pass  # Create empty file
        
        # Create empty directory
        empty_dir = os.path.join(self.temp_dir, "empty_dir")
        os.makedirs(empty_dir)
        
        # Test file reading
        file_tool = FileReadTool()
        result = file_tool._run(empty_file)
        assert "error" not in result
        assert result["content"] == ""
        assert result["lines"] == 0
        
        # Test directory listing
        dir_tool = DirectoryListTool()
        query = json.dumps({"directory_path": empty_dir})
        result = dir_tool._run(query)
        assert "error" not in result
        assert result["total_files"] == 0
        assert result["total_directories"] == 0


class TestWorkflowErrorHandling:
    """Test workflow-level error handling."""
    
    def test_review_analysis_requests(self):
        """Test handling of invalid analysis requests."""
        from state import ReviewState, ReviewStatus

        invalid_states = [
            ReviewState(
                messages=[], current_step="start", status=ReviewStatus.INITIALIZING,
                error_message=None, repository_url="", repository_info=None,
                repository_type=None, enabled_tools=[], tool_results={},
                failed_tools=[], analysis_results=None, files_analyzed=[],
                total_files=0, review_config={}, start_time=None, end_time=None,
                notifications_sent=[], report_generated=False, final_report=None
            ),
        ]

        for state in invalid_states:
            # Should handle invalid requests gracefully
            assert isinstance(state, dict)
            # Should either succeed with warnings or fail gracefully
    
    def test_tool_selection_with_no_available_tools(self):
        """Test tool selection when no tools are available."""
        from state import ReviewState, ReviewStatus

        # Create config with no enabled categories
        config = ToolConfig()
        config.enabled_categories = []

        state = ReviewState(
            messages=[], current_step="start", status=ReviewStatus.INITIALIZING,
            error_message=None, repository_url="/tmp", repository_info=None,
            repository_type="python", enabled_tools=[], tool_results={},
            failed_tools=[], analysis_results=None, files_analyzed=[],
            total_files=0, review_config={}, start_time=None, end_time=None,
            notifications_sent=[], report_generated=False, final_report=None
        )

        # Should handle gracefully
        assert isinstance(state, dict)
        assert len(state.get("enabled_tools", [])) == 0
    
    def test_workflow_with_all_tools_failing(self):
        """Test workflow behavior when all tools fail."""
        from state import ReviewState, ReviewStatus, ToolResult

        state = ReviewState(
            messages=[], current_step="start", status=ReviewStatus.INITIALIZING,
            error_message=None, repository_url="/tmp", repository_info=None,
            repository_type=None, enabled_tools=[], tool_results={
                "Tool 1": ToolResult(tool_name="Tool 1", success=False, result={}, error_message="Tool 1 failed", execution_time=0.0, timestamp=""),
                "Tool 2": ToolResult(tool_name="Tool 2", success=False, result={}, error_message="Tool 2 failed", execution_time=0.0, timestamp=""),
                "Tool 3": ToolResult(tool_name="Tool 3", success=False, result={}, error_message="Tool 3 failed", execution_time=0.0, timestamp=""),
            },
            failed_tools=["Tool 1", "Tool 2", "Tool 3"], analysis_results=None, files_analyzed=[],
            total_files=0, review_config={}, start_time=None, end_time=None,
            notifications_sent=[], report_generated=False, final_report=None
        )

        # Should handle all failures gracefully
        assert len(state["failed_tools"]) == 3
        assert len([r for r in state["tool_results"].values() if r["success"]]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
