"""
Comprehensive modular tests for GitHub integration tools.

This module tests all GitHub-related tools independently with proper mocking
and comprehensive scenario coverage.

Run with: pytest tests/test_github_tools.py -v
Run specific test: pytest tests/test_github_tools.py::TestGitHubRepositoryTool::test_successful_repository_fetch -v
"""

import pytest
import json
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from aiohttp import ClientSession

# Import the tools to test
from tools.github_tools import (
    GitHubRepositoryTool, GitHubFileContentTool, GitHubPullRequestTool,
    GitHubConfig
)


class TestGitHubConfig:
    """Test GitHubConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GitHubConfig()
        assert config.base_url == "https://api.github.com"
        assert config.timeout == 30
    
    def test_config_with_token(self):
        """Test configuration with GitHub token."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            config = GitHubConfig()
            assert config.token == "test-token"
    
    def test_config_without_token(self):
        """Test configuration without GitHub token."""
        with patch.dict(os.environ, {}, clear=True):
            config = GitHubConfig()
            assert config.token == ""


class TestGitHubRepositoryTool:
    """Test GitHubRepositoryTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = GitHubRepositoryTool()
        self.mock_repo_data = {
            "id": 1296269,
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "description": "This your first repo!",
            "private": False,
            "html_url": "https://github.com/octocat/Hello-World",
            "clone_url": "https://github.com/octocat/Hello-World.git",
            "language": "C",
            "stargazers_count": 80,
            "watchers_count": 9,
            "forks_count": 9,
            "open_issues_count": 0,
            "default_branch": "master",
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z"
        }
    
    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
    @patch('aiohttp.ClientSession.get')
    def test_successful_repository_fetch(self, mock_get):
        """Test successful repository information fetch."""
        # Mock successful API response for repository metadata
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_repo_data)

        # Mock successful API response for contents and commits
        mock_contents_response = AsyncMock()
        mock_contents_response.status = 200
        mock_contents_response.json = AsyncMock(return_value=[])

        mock_commits_response = AsyncMock()
        mock_commits_response.status = 200
        mock_commits_response.json = AsyncMock(return_value=[])

        # Configure the mock to return different responses for different URLs
        mock_get.return_value.__aenter__.side_effect = [
            mock_response,  # Repository metadata
            mock_contents_response,  # Repository contents
            mock_commits_response   # Recent commits
        ]

        result = self.tool._run("octocat/Hello-World")

        assert "error" not in result
        assert "repository" in result
        assert result["repository"]["name"] == "Hello-World"
        assert result["repository"]["full_name"] == "octocat/Hello-World"
        assert result["repository"]["language"] == "C"
        assert result["repository"]["stars"] == 80
        assert "contents" in result
        assert "recent_commits" in result
    
    @patch('aiohttp.ClientSession.get')
    def test_repository_not_found(self, mock_get):
        """Test handling of repository not found."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = self.tool._run("nonexistent/repo")
        
        assert "error" in result
        assert "404" in result["error"]
    
    @patch('aiohttp.ClientSession.get')
    def test_api_rate_limit(self, mock_get):
        """Test handling of API rate limit."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="API rate limit exceeded")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = self.tool._run("octocat/Hello-World")
        
        assert "error" in result
        assert "403" in result["error"]
    
    def test_invalid_repository_url(self):
        """Test handling of invalid repository URL."""
        result = self.tool._run("invalid-url")
        
        assert "error" in result
        assert "Invalid repository URL" in result["error"]
    
    @patch('aiohttp.ClientSession.get')
    def test_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")
        
        result = self.tool._run("octocat/Hello-World")
        
        assert "error" in result
        assert "Network error" in result["error"]
    
    def test_parse_repo_url_formats(self):
        """Test parsing different repository URL formats."""
        # Test owner/repo format
        owner, repo = self.tool._parse_repo_url("octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

        # Test full GitHub URL
        owner, repo = self.tool._parse_repo_url("https://github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

        # Test with .git extension - the implementation strips .git
        owner, repo = self.tool._parse_repo_url("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"  # Implementation strips .git extension


class TestGitHubFileContentTool:
    """Test GitHubFileContentTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = GitHubFileContentTool()
        self.mock_file_data = {
            "name": "README.md",
            "path": "README.md",
            "sha": "3d21ec53a331a6f037a91c368710b99387d012c1",
            "size": 5362,
            "url": "https://api.github.com/repos/octocat/Hello-World/contents/README.md",
            "html_url": "https://github.com/octocat/Hello-World/blob/master/README.md",
            "git_url": "https://api.github.com/repos/octocat/Hello-World/git/blobs/3d21ec53a331a6f037a91c368710b99387d012c1",
            "download_url": "https://raw.githubusercontent.com/octocat/Hello-World/master/README.md",
            "type": "file",
            "content": "SGVsbG8gV29ybGQ=",  # Base64 encoded "Hello World"
            "encoding": "base64"
        }
    
    @patch('aiohttp.ClientSession.get')
    def test_successful_file_fetch(self, mock_get):
        """Test successful file content fetch."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_file_data)
        mock_get.return_value.__aenter__.return_value = mock_response

        query = json.dumps({
            "repository_url": "octocat/Hello-World",
            "file_path": "README.md"
        })

        result = self.tool._run(query)

        assert "error" not in result
        # GitHubFileContentTool returns file_path, content, size, sha, encoding (NOT name or type)
        assert result["file_path"] == "README.md"
        assert result["content"] == "Hello World"  # Decoded content
        assert result["size"] == 5362
        assert result["sha"] == "3d21ec53a331a6f037a91c368710b99387d012c1"
        assert result["encoding"] == "base64"
    
    @patch('aiohttp.ClientSession.get')
    def test_file_not_found(self, mock_get):
        """Test handling of file not found."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps({
            "repository_url": "octocat/Hello-World",
            "file_path": "nonexistent.txt"
        })
        
        result = self.tool._run(query)
        
        assert "error" in result
        assert "404" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")

        assert "error" in result
        # Actual error message from implementation
        assert "Expecting value" in result["error"]
    
    @patch('aiohttp.ClientSession.get')
    def test_missing_required_parameters(self, mock_get):
        """Test handling of missing required parameters."""
        # Mock to prevent actual network calls
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_get.return_value.__aenter__.return_value = mock_response

        # Missing file_path - this will cause None to be passed to URL construction
        query = json.dumps({"repository_url": "octocat/Hello-World"})
        result = self.tool._run(query)

        assert "error" in result
        # The actual error message from the implementation
        assert "Failed to fetch file" in result["error"]
        
        # Missing repository_url
        query = json.dumps({"file_path": "README.md"})
        result = self.tool._run(query)

        assert "error" in result
        # The actual error message when repository_url is None
        assert "NoneType" in result["error"] or "Error fetching file content" in result["error"]


class TestGitHubPullRequestTool:
    """Test GitHubPullRequestTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = GitHubPullRequestTool()
        self.mock_pr_data = {
            "id": 1,
            "number": 1347,
            "state": "open",
            "title": "new-feature",
            "body": "Please pull these awesome changes",
            "user": {
                "login": "octocat",
                "id": 1
            },
            "created_at": "2011-01-26T19:01:12Z",
            "updated_at": "2011-01-26T19:14:43Z",
            "head": {
                "ref": "new-topic",
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"
            },
            "base": {
                "ref": "master",
                "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"
            },
            "mergeable": True,
            "additions": 100,
            "deletions": 3,
            "changed_files": 5
        }
    
    @patch('aiohttp.ClientSession.get')
    def test_successful_pr_fetch(self, mock_get):
        """Test successful pull request fetch."""
        # Mock PR data response
        mock_pr_response = AsyncMock()
        mock_pr_response.status = 200
        mock_pr_response.json = AsyncMock(return_value=self.mock_pr_data)

        # Mock files response
        mock_files_response = AsyncMock()
        mock_files_response.status = 200
        mock_files_response.json = AsyncMock(return_value=[])

        # Configure mock to return different responses for different URLs
        mock_get.return_value.__aenter__.side_effect = [
            mock_pr_response,    # PR data
            mock_files_response  # PR files
        ]
        
        query = json.dumps({
            "repository_url": "octocat/Hello-World",
            "pr_number": 1347
        })
        
        result = self.tool._run(query)

        assert "error" not in result
        # GitHubPullRequestTool returns nested structure with pull_request object
        assert "pull_request" in result
        assert result["pull_request"]["number"] == 1347
        assert result["pull_request"]["title"] == "new-feature"
        assert result["pull_request"]["state"] == "open"
        assert result["pull_request"]["additions"] == 100
        assert result["pull_request"]["deletions"] == 3
        assert "files" in result
    
    @patch('aiohttp.ClientSession.get')
    def test_list_recent_prs(self, mock_get):
        """Test listing recent pull requests."""
        mock_prs_list = [self.mock_pr_data]
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_prs_list)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps({
            "repository_url": "octocat/Hello-World"
            # No pr_number provided, should list recent PRs
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert "pull_requests" in result
        assert len(result["pull_requests"]) == 1
        assert result["pull_requests"][0]["number"] == 1347
    
    @patch('aiohttp.ClientSession.get')
    def test_pr_not_found(self, mock_get):
        """Test handling of pull request not found."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_get.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps({
            "repository_url": "octocat/Hello-World",
            "pr_number": 9999
        })
        
        result = self.tool._run(query)
        
        assert "error" in result
        assert "404" in result["error"]
    
    def test_invalid_json_input(self):
        """Test handling of invalid JSON input."""
        result = self.tool._run("invalid json")

        assert "error" in result
        # Actual error message from implementation
        assert "Expecting value" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__])
