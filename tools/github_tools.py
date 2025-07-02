"""GitHub integration tools for LangGraph workflow."""

import os
import asyncio
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
import aiohttp
import base64
from urllib.parse import urlparse


class GitHubConfig(BaseModel):
    """Configuration for GitHub API access."""
    token: str = Field(default_factory=lambda: os.getenv("GITHUB_TOKEN", ""))
    base_url: str = "https://api.github.com"
    timeout: int = 30


class GitHubRepositoryTool(BaseTool):
    """Tool for accessing GitHub repository information."""
    
    name: str = "github_repository"
    description: str = """
    Fetch repository information from GitHub including:
    - Repository metadata (name, description, language, stars, etc.)
    - File structure and contents
    - Recent commits
    - Repository statistics
    
    Input should be a repository URL or owner/repo format.
    """
    
    config: GitHubConfig = Field(default_factory=GitHubConfig)
    
    def _run(
        self,
        repository_url: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async implementation."""
        return asyncio.run(self._arun(repository_url, run_manager))
    
    async def _arun(
        self,
        repository_url: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Fetch repository information asynchronously."""
        try:
            owner, repo = self._parse_repo_url(repository_url)
            
            headers = {
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CustomLangGraphChatBot/1.0"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                # Get repository metadata
                repo_url = f"{self.config.base_url}/repos/{owner}/{repo}"
                async with session.get(repo_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"Failed to fetch repository: {response.status}"}
                    
                    repo_data = await response.json()
                
                # Get repository contents (root level)
                contents_url = f"{self.config.base_url}/repos/{owner}/{repo}/contents"
                async with session.get(contents_url, headers=headers) as response:
                    contents_data = await response.json() if response.status == 200 else []
                
                # Get recent commits
                commits_url = f"{self.config.base_url}/repos/{owner}/{repo}/commits?per_page=10"
                async with session.get(commits_url, headers=headers) as response:
                    commits_data = await response.json() if response.status == 200 else []
                
                return {
                    "repository": {
                        "name": repo_data.get("name"),
                        "full_name": repo_data.get("full_name"),
                        "description": repo_data.get("description"),
                        "language": repo_data.get("language"),
                        "stars": repo_data.get("stargazers_count"),
                        "forks": repo_data.get("forks_count"),
                        "open_issues": repo_data.get("open_issues_count"),
                        "created_at": repo_data.get("created_at"),
                        "updated_at": repo_data.get("updated_at"),
                        "default_branch": repo_data.get("default_branch"),
                        "size": repo_data.get("size"),
                        "topics": repo_data.get("topics", [])
                    },
                    "contents": [
                        {
                            "name": item.get("name"),
                            "type": item.get("type"),
                            "size": item.get("size"),
                            "path": item.get("path")
                        }
                        for item in contents_data if isinstance(contents_data, list)
                    ],
                    "recent_commits": [
                        {
                            "sha": commit.get("sha"),
                            "message": commit.get("commit", {}).get("message"),
                            "author": commit.get("commit", {}).get("author", {}).get("name"),
                            "date": commit.get("commit", {}).get("author", {}).get("date")
                        }
                        for commit in commits_data if isinstance(commits_data, list)
                    ]
                }
                
        except Exception as e:
            return {"error": f"Error fetching repository data: {str(e)}"}
    
    def _parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse repository URL to extract owner and repo name."""
        if "/" in url and not url.startswith("http"):
            # Format: owner/repo
            parts = url.split("/")
            return parts[0], parts[1]
        
        # Parse full GitHub URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        
        raise ValueError(f"Invalid repository URL format: {url}")


class GitHubFileContentTool(BaseTool):
    """Tool for fetching file contents from GitHub repository."""
    
    name: str = "github_file_content"
    description: str = """
    Fetch the contents of specific files from a GitHub repository.
    
    Input should be a JSON object with:
    - repository_url: GitHub repository URL
    - file_path: Path to the file within the repository
    - branch: Optional branch name (defaults to default branch)
    """
    
    config: GitHubConfig = Field(default_factory=GitHubConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async implementation."""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Fetch file contents asynchronously."""
        try:
            import json
            params = json.loads(query)
            
            repository_url = params.get("repository_url")
            file_path = params.get("file_path")
            branch = params.get("branch", "main")
            
            owner, repo = self._parse_repo_url(repository_url)
            
            headers = {
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CustomLangGraphChatBot/1.0"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                file_url = f"{self.config.base_url}/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
                
                async with session.get(file_url, headers=headers) as response:
                    if response.status != 200:
                        return {"error": f"Failed to fetch file: {response.status}"}
                    
                    file_data = await response.json()
                    
                    # Decode base64 content
                    if file_data.get("encoding") == "base64":
                        content = base64.b64decode(file_data.get("content", "")).decode("utf-8")
                    else:
                        content = file_data.get("content", "")
                    
                    return {
                        "file_path": file_path,
                        "content": content,
                        "size": file_data.get("size"),
                        "sha": file_data.get("sha"),
                        "encoding": file_data.get("encoding")
                    }
                    
        except Exception as e:
            return {"error": f"Error fetching file content: {str(e)}"}
    
    def _parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse repository URL to extract owner and repo name."""
        if "/" in url and not url.startswith("http"):
            parts = url.split("/")
            return parts[0], parts[1]
        
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        
        raise ValueError(f"Invalid repository URL format: {url}")


class GitHubPullRequestTool(BaseTool):
    """Tool for accessing GitHub pull request information."""
    
    name: str = "github_pull_request"
    description: str = """
    Fetch pull request information from GitHub including:
    - PR metadata (title, description, status, etc.)
    - Changed files and diffs
    - Comments and reviews
    
    Input should be a JSON object with:
    - repository_url: GitHub repository URL
    - pr_number: Pull request number (optional, if not provided, lists recent PRs)
    """
    
    config: GitHubConfig = Field(default_factory=GitHubConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async implementation."""
        return asyncio.run(self._arun(query, run_manager))
    
    async def _arun(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Fetch pull request information asynchronously."""
        try:
            import json
            params = json.loads(query)
            
            repository_url = params.get("repository_url")
            pr_number = params.get("pr_number")
            
            owner, repo = self._parse_repo_url(repository_url)
            
            headers = {
                "Authorization": f"token {self.config.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "CustomLangGraphChatBot/1.0"
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.config.timeout)) as session:
                if pr_number:
                    # Get specific PR
                    pr_url = f"{self.config.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
                    async with session.get(pr_url, headers=headers) as response:
                        if response.status != 200:
                            return {"error": f"Failed to fetch PR: {response.status}"}
                        
                        pr_data = await response.json()
                        
                        # Get PR files
                        files_url = f"{self.config.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
                        async with session.get(files_url, headers=headers) as files_response:
                            files_data = await files_response.json() if files_response.status == 200 else []
                        
                        return {
                            "pull_request": {
                                "number": pr_data.get("number"),
                                "title": pr_data.get("title"),
                                "body": pr_data.get("body"),
                                "state": pr_data.get("state"),
                                "created_at": pr_data.get("created_at"),
                                "updated_at": pr_data.get("updated_at"),
                                "author": pr_data.get("user", {}).get("login"),
                                "base_branch": pr_data.get("base", {}).get("ref"),
                                "head_branch": pr_data.get("head", {}).get("ref"),
                                "mergeable": pr_data.get("mergeable"),
                                "additions": pr_data.get("additions"),
                                "deletions": pr_data.get("deletions"),
                                "changed_files": pr_data.get("changed_files")
                            },
                            "files": [
                                {
                                    "filename": file.get("filename"),
                                    "status": file.get("status"),
                                    "additions": file.get("additions"),
                                    "deletions": file.get("deletions"),
                                    "changes": file.get("changes"),
                                    "patch": file.get("patch", "")[:1000]  # Limit patch size
                                }
                                for file in files_data if isinstance(files_data, list)
                            ]
                        }
                else:
                    # List recent PRs
                    prs_url = f"{self.config.base_url}/repos/{owner}/{repo}/pulls?state=all&per_page=10"
                    async with session.get(prs_url, headers=headers) as response:
                        if response.status != 200:
                            return {"error": f"Failed to fetch PRs: {response.status}"}
                        
                        prs_data = await response.json()
                        
                        return {
                            "pull_requests": [
                                {
                                    "number": pr.get("number"),
                                    "title": pr.get("title"),
                                    "state": pr.get("state"),
                                    "created_at": pr.get("created_at"),
                                    "author": pr.get("user", {}).get("login"),
                                    "base_branch": pr.get("base", {}).get("ref"),
                                    "head_branch": pr.get("head", {}).get("ref")
                                }
                                for pr in prs_data if isinstance(prs_data, list)
                            ]
                        }
                        
        except Exception as e:
            return {"error": f"Error fetching pull request data: {str(e)}"}
    
    def _parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse repository URL to extract owner and repo name."""
        if "/" in url and not url.startswith("http"):
            parts = url.split("/")
            return parts[0], parts[1]
        
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        
        raise ValueError(f"Invalid repository URL format: {url}")


# Tool instances for easy import
github_repository_tool = GitHubRepositoryTool()
github_file_content_tool = GitHubFileContentTool()
github_pull_request_tool = GitHubPullRequestTool()

# List of all GitHub tools
GITHUB_TOOLS = [
    github_repository_tool,
    github_file_content_tool,
    github_pull_request_tool
]
