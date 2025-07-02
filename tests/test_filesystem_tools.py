"""Comprehensive unit tests for file system tools."""

import pytest
import tempfile
import os
import json
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the tools to test
from tools.filesystem_tools import (
    FileReadTool, DirectoryListTool, GitRepositoryTool,
    FileSystemConfig
)


class TestFileSystemConfig:
    """Test FileSystemConfig configuration class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FileSystemConfig()
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert config.allowed_extensions == ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.md', '.txt', '.json', '.yaml', '.yml']
        assert config.blocked_paths == ['/etc', '/var', '/usr', '/bin', '/sbin']


class TestFileReadTool:
    """Test FileReadTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = FileReadTool()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test files
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write('''def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return "Hello, World!"

if __name__ == "__main__":
    hello_world()
''')
        
        self.large_file = os.path.join(self.temp_dir, "large.py")
        with open(self.large_file, "w") as f:
            f.write("# Large file\n" * 1000)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_successful_file_read(self):
        """Test successful file reading."""
        result = self.tool._run(self.test_file)
        
        assert "error" not in result
        assert result["file_path"] == self.test_file
        assert "def hello_world():" in result["content"]
        assert result["size"] > 0
        assert result["lines"] == 7
        assert result["extension"] == ".py"
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        non_existent = os.path.join(self.temp_dir, "nonexistent.py")
        result = self.tool._run(non_existent)
        
        assert "error" in result
        assert "File not found" in result["error"]
    
    def test_directory_instead_of_file(self):
        """Test handling when path is a directory."""
        result = self.tool._run(self.temp_dir)
        
        assert "error" in result
        assert "is a directory" in result["error"]
    
    def test_blocked_path(self):
        """Test handling of blocked system paths."""
        result = self.tool._run("/etc/passwd")
        
        assert "error" in result
        assert "blocked path" in result["error"]
    
    def test_disallowed_extension(self):
        """Test handling of disallowed file extensions."""
        exe_file = os.path.join(self.temp_dir, "test.exe")
        with open(exe_file, "w") as f:
            f.write("fake executable")
        
        result = self.tool._run(exe_file)
        
        assert "error" in result
        assert "not allowed" in result["error"]
    
    def test_file_too_large(self):
        """Test handling of files that are too large."""
        # Create a tool with small max file size
        tool = FileReadTool()
        tool.config.max_file_size = 100  # Very small limit
        
        result = tool._run(self.large_file)
        
        assert "error" in result
        assert "too large" in result["error"]
    
    def test_permission_denied(self):
        """Test handling of permission denied."""
        # Create a file and remove read permissions
        restricted_file = os.path.join(self.temp_dir, "restricted.py")
        with open(restricted_file, "w") as f:
            f.write("restricted content")
        
        os.chmod(restricted_file, 0o000)  # No permissions
        
        try:
            result = self.tool._run(restricted_file)
            assert "error" in result
            assert "Permission denied" in result["error"]
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_file, 0o644)
    
    def test_binary_file_detection(self):
        """Test detection and handling of binary files."""
        binary_file = os.path.join(self.temp_dir, "test.bin")
        with open(binary_file, "wb") as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')
        
        result = self.tool._run(binary_file)
        
        assert "error" in result
        assert "binary file" in result["error"]


class TestDirectoryListTool:
    """Test DirectoryListTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = DirectoryListTool()
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        os.makedirs(os.path.join(self.temp_dir, "subdir1"))
        os.makedirs(os.path.join(self.temp_dir, "subdir2"))
        
        # Create test files
        with open(os.path.join(self.temp_dir, "file1.py"), "w") as f:
            f.write("# File 1")
        with open(os.path.join(self.temp_dir, "file2.js"), "w") as f:
            f.write("// File 2")
        with open(os.path.join(self.temp_dir, "subdir1", "nested.py"), "w") as f:
            f.write("# Nested file")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_successful_directory_listing(self):
        """Test successful directory listing."""
        result = self.tool._run(self.temp_dir)
        
        assert "error" not in result
        assert result["directory_path"] == self.temp_dir
        assert result["total_items"] == 4  # 2 files + 2 subdirs
        assert result["file_count"] == 2
        assert result["directory_count"] == 2
        
        # Check that files are listed
        file_names = [item["name"] for item in result["items"] if item["type"] == "file"]
        assert "file1.py" in file_names
        assert "file2.js" in file_names
        
        # Check that directories are listed
        dir_names = [item["name"] for item in result["items"] if item["type"] == "directory"]
        assert "subdir1" in dir_names
        assert "subdir2" in dir_names
    
    def test_directory_not_found(self):
        """Test handling of non-existent directory."""
        non_existent = os.path.join(self.temp_dir, "nonexistent")
        result = self.tool._run(non_existent)
        
        assert "error" in result
        assert "Directory not found" in result["error"]
    
    def test_file_instead_of_directory(self):
        """Test handling when path is a file."""
        file_path = os.path.join(self.temp_dir, "file1.py")
        result = self.tool._run(file_path)
        
        assert "error" in result
        assert "not a directory" in result["error"]
    
    def test_blocked_path(self):
        """Test handling of blocked system paths."""
        result = self.tool._run("/etc")
        
        assert "error" in result
        assert "blocked path" in result["error"]
    
    def test_empty_directory(self):
        """Test listing of empty directory."""
        empty_dir = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_dir)
        
        result = self.tool._run(empty_dir)
        
        assert "error" not in result
        assert result["total_items"] == 0
        assert result["file_count"] == 0
        assert result["directory_count"] == 0
        assert len(result["items"]) == 0
    
    def test_permission_denied(self):
        """Test handling of permission denied."""
        restricted_dir = os.path.join(self.temp_dir, "restricted")
        os.makedirs(restricted_dir)
        os.chmod(restricted_dir, 0o000)  # No permissions
        
        try:
            result = self.tool._run(restricted_dir)
            assert "error" in result
            assert "Permission denied" in result["error"]
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)


class TestGitRepositoryTool:
    """Test GitRepositoryTool functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tool = GitRepositoryTool()
        self.temp_dir = tempfile.mkdtemp()
        
        # Initialize a git repository
        os.chdir(self.temp_dir)
        os.system("git init")
        os.system("git config user.email 'test@example.com'")
        os.system("git config user.name 'Test User'")
        
        # Create and commit some files
        with open("README.md", "w") as f:
            f.write("# Test Repository")
        with open("main.py", "w") as f:
            f.write("print('Hello, World!')")
        
        os.system("git add .")
        os.system("git commit -m 'Initial commit'")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir("/")
        shutil.rmtree(self.temp_dir)
    
    def test_successful_git_analysis(self):
        """Test successful git repository analysis."""
        result = self.tool._run(self.temp_dir)
        
        assert "error" not in result
        assert result["repository_path"] == self.temp_dir
        assert result["is_git_repository"] is True
        assert result["total_files"] == 2
        assert result["total_commits"] >= 1
        assert result["current_branch"] == "master" or result["current_branch"] == "main"
        
        # Check file analysis
        assert len(result["files"]) == 2
        file_names = [f["name"] for f in result["files"]]
        assert "README.md" in file_names
        assert "main.py" in file_names
    
    def test_non_git_directory(self):
        """Test analysis of non-git directory."""
        non_git_dir = tempfile.mkdtemp()
        try:
            result = self.tool._run(non_git_dir)
            
            assert "error" not in result
            assert result["is_git_repository"] is False
            assert "Not a git repository" in result["message"]
        finally:
            shutil.rmtree(non_git_dir)
    
    def test_directory_not_found(self):
        """Test handling of non-existent directory."""
        non_existent = os.path.join(self.temp_dir, "nonexistent")
        result = self.tool._run(non_existent)
        
        assert "error" in result
        assert "Directory not found" in result["error"]
    
    def test_blocked_path(self):
        """Test handling of blocked system paths."""
        result = self.tool._run("/etc")
        
        assert "error" in result
        assert "blocked path" in result["error"]
    
    @patch('subprocess.run')
    def test_git_command_failure(self, mock_run):
        """Test handling of git command failures."""
        # Mock git command failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: not a git repository"
        mock_run.return_value = mock_result
        
        result = self.tool._run(self.temp_dir)
        
        # Should still return a result indicating it's not a git repo
        assert result["is_git_repository"] is False
    
    def test_empty_git_repository(self):
        """Test analysis of empty git repository."""
        empty_git_dir = tempfile.mkdtemp()
        try:
            os.chdir(empty_git_dir)
            os.system("git init")
            os.system("git config user.email 'test@example.com'")
            os.system("git config user.name 'Test User'")
            
            result = self.tool._run(empty_git_dir)
            
            assert "error" not in result
            assert result["is_git_repository"] is True
            assert result["total_files"] == 0
            assert result["total_commits"] == 0
        finally:
            os.chdir("/")
            shutil.rmtree(empty_git_dir)


if __name__ == "__main__":
    pytest.main([__file__])
