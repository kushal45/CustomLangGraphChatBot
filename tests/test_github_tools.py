"""Comprehensive unit tests for GitHub integration tools."""

import pytest
import json
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
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
    
    @patch('aiohttp.ClientSession.get')
    def test_successful_repository_fetch(self, mock_get):
        """Test successful repository information fetch."""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_repo_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = self.tool._run("octocat/Hello-World")
        
        assert "error" not in result
        assert result["name"] == "Hello-World"
        assert result["full_name"] == "octocat/Hello-World"
        assert result["language"] == "C"
        assert result["stargazers_count"] == 80
    
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
        
        # Test with .git extension
        owner, repo = self.tool._parse_repo_url("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"


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
        assert result["name"] == "README.md"
        assert result["content"] == "Hello World"  # Decoded content
        assert result["size"] == 5362
        assert result["type"] == "file"
    
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
        assert "Invalid JSON" in result["error"]
    
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters."""
        # Missing file_path
        query = json.dumps({"repository_url": "octocat/Hello-World"})
        result = self.tool._run(query)
        
        assert "error" in result
        assert "file_path" in result["error"]
        
        # Missing repository_url
        query = json.dumps({"file_path": "README.md"})
        result = self.tool._run(query)
        
        assert "error" in result
        assert "repository_url" in result["error"]


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
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=self.mock_pr_data)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        query = json.dumps({
            "repository_url": "octocat/Hello-World",
            "pr_number": 1347
        })
        
        result = self.tool._run(query)
        
        assert "error" not in result
        assert result["number"] == 1347
        assert result["title"] == "new-feature"
        assert result["state"] == "open"
        assert result["additions"] == 100
        assert result["deletions"] == 3
    
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
        assert "Invalid JSON" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__])
