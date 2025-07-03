"""File system and repository management tools for LangGraph workflow."""

import os
import tempfile
import shutil
import subprocess
import zipfile
import tarfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
from .logging_utils import log_tool_execution, LoggedBaseTool
from logging_config import get_logger

logger = get_logger(__name__)


class FileSystemConfig(BaseModel):
    """Configuration for file system tools."""
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_files_per_directory: int = 1000
    allowed_extensions: List[str] = Field(default_factory=lambda: [
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.go', 
        '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r', '.m',
        '.txt', '.md', '.json', '.yaml', '.yml', '.xml', '.toml', '.ini'
    ])
    temp_dir: Optional[str] = None


class FileReadTool(BaseTool):
    """Tool for reading file contents."""
    
    name: str = "file_reader"
    description: str = """
    Read the contents of a file from the file system.
    
    Input should be a file path as a string.
    Returns the file contents and metadata.
    """
    
    config: FileSystemConfig = Field(default_factory=FileSystemConfig)
    
    def _run(
        self,
        file_path: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Read file contents."""
        try:
            path = Path(file_path)
            
            # Security checks
            if not path.exists():
                return {"error": f"File does not exist: {file_path}"}
            
            if not path.is_file():
                return {"error": f"Path is not a file: {file_path}"}
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > self.config.max_file_size:
                return {"error": f"File too large: {file_size} bytes (max: {self.config.max_file_size})"}
            
            # Check file extension
            if path.suffix.lower() not in self.config.allowed_extensions:
                return {"error": f"File type not allowed: {path.suffix}"}
            
            # Read file content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try with different encoding
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read()
            
            return {
                "file_path": str(path),
                "content": content,
                "size": file_size,
                "extension": path.suffix,
                "name": path.name,
                "lines": len(content.splitlines()),
                "encoding": "utf-8"
            }
            
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}


class DirectoryListTool(BaseTool):
    """Tool for listing directory contents."""
    
    name: str = "directory_lister"
    description: str = """
    List the contents of a directory including files and subdirectories.
    
    Input should be a JSON object with:
    - directory_path: Path to the directory
    - recursive: Whether to list recursively (optional, default: False)
    - include_hidden: Whether to include hidden files (optional, default: False)
    """
    
    config: FileSystemConfig = Field(default_factory=FileSystemConfig)
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """List directory contents."""
        try:
            import json
            params = json.loads(query)
            
            directory_path = params.get("directory_path", "")
            recursive = params.get("recursive", False)
            include_hidden = params.get("include_hidden", False)
            
            path = Path(directory_path)
            
            # Security checks
            if not path.exists():
                return {"error": f"Directory does not exist: {directory_path}"}
            
            if not path.is_dir():
                return {"error": f"Path is not a directory: {directory_path}"}
            
            files = []
            directories = []
            total_files = 0
            
            def process_path(current_path: Path, relative_to: Path):
                nonlocal total_files
                
                if total_files >= self.config.max_files_per_directory:
                    return
                
                try:
                    for item in current_path.iterdir():
                        if total_files >= self.config.max_files_per_directory:
                            break
                        
                        # Skip hidden files if not requested
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        
                        relative_path = item.relative_to(relative_to)
                        
                        if item.is_file():
                            file_info = {
                                "name": item.name,
                                "path": str(relative_path),
                                "size": item.stat().st_size,
                                "extension": item.suffix,
                                "modified": item.stat().st_mtime
                            }
                            files.append(file_info)
                            total_files += 1
                        
                        elif item.is_dir():
                            dir_info = {
                                "name": item.name,
                                "path": str(relative_path),
                                "type": "directory"
                            }
                            directories.append(dir_info)
                            
                            # Recurse if requested
                            if recursive:
                                process_path(item, relative_to)
                
                except PermissionError:
                    pass  # Skip directories we can't access
            
            process_path(path, path)
            
            # Filter files by allowed extensions
            allowed_files = [
                f for f in files 
                if f["extension"].lower() in self.config.allowed_extensions or f["extension"] == ""
            ]
            
            return {
                "directory_path": str(path),
                "total_files": len(allowed_files),
                "total_directories": len(directories),
                "files": allowed_files,
                "directories": directories,
                "truncated": total_files >= self.config.max_files_per_directory
            }
            
        except Exception as e:
            return {"error": f"Failed to list directory: {str(e)}"}


class GitRepositoryTool(BaseTool):
    """Tool for Git repository operations."""
    
    name: str = "git_repository"
    description: str = """
    Perform Git repository operations including:
    - Clone repositories
    - Get repository information
    - List branches and commits
    - Get file history
    
    Input should be a JSON object with:
    - operation: The Git operation to perform (clone, info, branches, commits, file_history)
    - repository_url: URL of the repository (for clone operation)
    - local_path: Local path for repository operations
    - additional_params: Additional parameters specific to the operation
    """
    
    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Perform Git repository operations."""
        try:
            import json
            params = json.loads(query)
            
            operation = params.get("operation", "")
            repository_url = params.get("repository_url", "")
            local_path = params.get("local_path", "")
            additional_params = params.get("additional_params", {})
            
            if operation == "clone":
                return self._clone_repository(repository_url, local_path, additional_params)
            elif operation == "info":
                return self._get_repository_info(local_path)
            elif operation == "branches":
                return self._list_branches(local_path)
            elif operation == "commits":
                return self._list_commits(local_path, additional_params)
            elif operation == "file_history":
                return self._get_file_history(local_path, additional_params)
            else:
                return {"error": f"Unknown Git operation: {operation}"}
                
        except Exception as e:
            return {"error": f"Git operation failed: {str(e)}"}
    
    def _clone_repository(self, repository_url: str, local_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clone a Git repository."""
        try:
            depth = params.get("depth", None)
            branch = params.get("branch", None)
            
            cmd = ["git", "clone"]
            
            if depth:
                cmd.extend(["--depth", str(depth)])
            
            if branch:
                cmd.extend(["--branch", branch])
            
            cmd.extend([repository_url, local_path])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return {
                    "operation": "clone",
                    "success": True,
                    "local_path": local_path,
                    "repository_url": repository_url,
                    "message": "Repository cloned successfully"
                }
            else:
                return {
                    "operation": "clone",
                    "success": False,
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Git clone operation timed out"}
        except Exception as e:
            return {"error": f"Clone failed: {str(e)}"}
    
    def _get_repository_info(self, local_path: str) -> Dict[str, Any]:
        """Get repository information."""
        try:
            if not Path(local_path).exists():
                return {"error": "Repository path does not exist"}
            
            # Get remote URL
            result = subprocess.run(
                ["git", "-C", local_path, "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=30
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Get current branch
            result = subprocess.run(
                ["git", "-C", local_path, "branch", "--show-current"],
                capture_output=True, text=True, timeout=30
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Get last commit
            result = subprocess.run(
                ["git", "-C", local_path, "log", "-1", "--format=%H|%s|%an|%ad"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                commit_parts = result.stdout.strip().split("|")
                last_commit = {
                    "hash": commit_parts[0] if len(commit_parts) > 0 else "",
                    "message": commit_parts[1] if len(commit_parts) > 1 else "",
                    "author": commit_parts[2] if len(commit_parts) > 2 else "",
                    "date": commit_parts[3] if len(commit_parts) > 3 else ""
                }
            else:
                last_commit = {}
            
            return {
                "operation": "info",
                "local_path": local_path,
                "remote_url": remote_url,
                "current_branch": current_branch,
                "last_commit": last_commit
            }
            
        except Exception as e:
            return {"error": f"Failed to get repository info: {str(e)}"}
    
    def _list_branches(self, local_path: str) -> Dict[str, Any]:
        """List repository branches."""
        try:
            result = subprocess.run(
                ["git", "-C", local_path, "branch", "-a"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                branches = []
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        is_current = line.startswith('*')
                        branch_name = line.lstrip('* ').strip()
                        branches.append({
                            "name": branch_name,
                            "current": is_current,
                            "remote": branch_name.startswith('remotes/')
                        })
                
                return {
                    "operation": "branches",
                    "branches": branches
                }
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": f"Failed to list branches: {str(e)}"}
    
    def _list_commits(self, local_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """List repository commits."""
        try:
            limit = params.get("limit", 10)
            branch = params.get("branch", "")
            
            cmd = ["git", "-C", local_path, "log", f"--max-count={limit}", "--format=%H|%s|%an|%ad|%ae"]
            
            if branch:
                cmd.append(branch)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 4:
                            commits.append({
                                "hash": parts[0],
                                "message": parts[1],
                                "author": parts[2],
                                "date": parts[3],
                                "email": parts[4] if len(parts) > 4 else ""
                            })
                
                return {
                    "operation": "commits",
                    "commits": commits
                }
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": f"Failed to list commits: {str(e)}"}
    
    def _get_file_history(self, local_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get file history."""
        try:
            file_path = params.get("file_path", "")
            limit = params.get("limit", 10)
            
            if not file_path:
                return {"error": "File path is required for file history"}
            
            result = subprocess.run(
                ["git", "-C", local_path, "log", f"--max-count={limit}", "--format=%H|%s|%an|%ad", "--", file_path],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                history = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 4:
                            history.append({
                                "hash": parts[0],
                                "message": parts[1],
                                "author": parts[2],
                                "date": parts[3]
                            })
                
                return {
                    "operation": "file_history",
                    "file_path": file_path,
                    "history": history
                }
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": f"Failed to get file history: {str(e)}"}


# Tool instances for easy import
file_read_tool = FileReadTool()
directory_list_tool = DirectoryListTool()
git_repository_tool = GitRepositoryTool()

# List of all filesystem tools
FILESYSTEM_TOOLS = [
    file_read_tool,
    directory_list_tool,
    git_repository_tool
]
