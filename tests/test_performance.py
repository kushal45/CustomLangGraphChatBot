"""Comprehensive performance and load tests."""

import pytest
import time
import threading
import asyncio
import tempfile
import os
import shutil
import psutil
import concurrent.futures
from unittest.mock import Mock, patch
from typing import List, Dict, Any

# Import components to test
from tools.registry import ToolRegistry, ToolConfig
from tools.analysis_tools import CodeComplexityTool
from tools.filesystem_tools import FileReadTool, DirectoryListTool
from src.state import AnalysisState, AnalysisRequest
from src.nodes import execute_tools


class TestToolPerformance:
    """Test individual tool performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ToolConfig()
        self.registry = ToolRegistry(self.config)
        
        # Create test files of various sizes
        self.create_test_files()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def create_test_files(self):
        """Create test files of various sizes."""
        # Small file (1KB)
        with open(os.path.join(self.temp_dir, "small.py"), "w") as f:
            f.write("def hello(): return 'Hello'\n" * 20)
        
        # Medium file (10KB)
        with open(os.path.join(self.temp_dir, "medium.py"), "w") as f:
            f.write("def function_{}(): return {}\n".format(i, i) for i in range(500))
        
        # Large file (100KB)
        with open(os.path.join(self.temp_dir, "large.py"), "w") as f:
            for i in range(5000):
                f.write(f"def function_{i}():\n    return {i}\n\n")
        
        # Create directory structure
        for i in range(10):
            subdir = os.path.join(self.temp_dir, f"subdir_{i}")
            os.makedirs(subdir)
            for j in range(5):
                with open(os.path.join(subdir, f"file_{j}.py"), "w") as f:
                    f.write(f"# File {j} in subdir {i}\n")
    
    def test_file_read_tool_performance(self):
        """Test FileReadTool performance with different file sizes."""
        tool = FileReadTool()
        
        # Test small file
        start_time = time.time()
        result = tool._run(os.path.join(self.temp_dir, "small.py"))
        small_time = time.time() - start_time
        
        assert "error" not in result
        assert small_time < 0.1  # Should be very fast
        
        # Test medium file
        start_time = time.time()
        result = tool._run(os.path.join(self.temp_dir, "medium.py"))
        medium_time = time.time() - start_time
        
        assert "error" not in result
        assert medium_time < 0.5  # Should still be fast
        
        # Test large file
        start_time = time.time()
        result = tool._run(os.path.join(self.temp_dir, "large.py"))
        large_time = time.time() - start_time
        
        assert "error" not in result
        assert large_time < 2.0  # Should complete within reasonable time
        
        # Performance should scale reasonably
        assert medium_time > small_time
        assert large_time > medium_time
    
    def test_directory_list_tool_performance(self):
        """Test DirectoryListTool performance with large directories."""
        tool = DirectoryListTool()
        
        start_time = time.time()
        result = tool._run(self.temp_dir)
        execution_time = time.time() - start_time
        
        assert "error" not in result
        assert execution_time < 1.0  # Should complete quickly
        assert result["total_items"] > 50  # Should find all created items
    
    def test_complexity_tool_performance(self):
        """Test CodeComplexityTool performance."""
        tool = CodeComplexityTool()
        
        # Test with large file
        start_time = time.time()
        with open(os.path.join(self.temp_dir, "large.py"), "r") as f:
            code = f.read()
        
        result = tool._run(code)
        execution_time = time.time() - start_time
        
        assert "error" not in result
        assert execution_time < 5.0  # Should complete within reasonable time
        assert result["total_functions"] > 1000  # Should analyze many functions
    
    def test_tool_memory_usage(self):
        """Test tool memory usage."""
        tool = FileReadTool()
        
        # Monitor memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Execute tool multiple times
        for _ in range(10):
            result = tool._run(os.path.join(self.temp_dir, "large.py"))
            assert "error" not in result
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
    
    def test_concurrent_tool_execution(self):
        """Test concurrent tool execution performance."""
        tool = FileReadTool()
        files = [
            os.path.join(self.temp_dir, "small.py"),
            os.path.join(self.temp_dir, "medium.py"),
            os.path.join(self.temp_dir, "large.py")
        ]
        
        def execute_tool(file_path):
            start_time = time.time()
            result = tool._run(file_path)
            execution_time = time.time() - start_time
            return result, execution_time
        
        # Sequential execution
        start_time = time.time()
        sequential_results = []
        for file_path in files:
            result, exec_time = execute_tool(file_path)
            sequential_results.append((result, exec_time))
        sequential_total_time = time.time() - start_time
        
        # Concurrent execution
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(execute_tool, file_path) for file_path in files]
            concurrent_results = [future.result() for future in futures]
        concurrent_total_time = time.time() - start_time
        
        # Verify all results are successful
        for result, _ in sequential_results + concurrent_results:
            assert "error" not in result
        
        # Concurrent execution should be faster (or at least not much slower)
        assert concurrent_total_time <= sequential_total_time * 1.2


class TestRegistryPerformance:
    """Test ToolRegistry performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = ToolConfig()
    
    def test_registry_initialization_performance(self):
        """Test registry initialization performance."""
        start_time = time.time()
        registry = ToolRegistry(self.config)
        initialization_time = time.time() - start_time
        
        assert initialization_time < 1.0  # Should initialize quickly
        assert len(registry.get_available_tools()) > 0
    
    def test_tool_lookup_performance(self):
        """Test tool lookup performance."""
        registry = ToolRegistry(self.config)
        
        # Test getting tools by category
        start_time = time.time()
        for _ in range(100):
            tools = registry.get_tools_by_category("filesystem")
        category_lookup_time = time.time() - start_time
        
        assert category_lookup_time < 0.1  # Should be very fast
        
        # Test getting tool by name
        start_time = time.time()
        for _ in range(100):
            tool = registry.get_tool_by_name("File Read Tool")
        name_lookup_time = time.time() - start_time
        
        assert name_lookup_time < 0.1  # Should be very fast
    
    def test_concurrent_registry_access(self):
        """Test concurrent registry access performance."""
        registry = ToolRegistry(self.config)
        results = []
        
        def access_registry():
            start_time = time.time()
            tools = registry.get_available_tools()
            tool = registry.get_tool_by_name("File Read Tool")
            execution_time = time.time() - start_time
            results.append((len(tools), tool is not None, execution_time))
        
        # Concurrent access
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_registry)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All accesses should be successful and fast
        assert len(results) == 10
        for tool_count, tool_found, exec_time in results:
            assert tool_count > 0
            assert tool_found is True
            assert exec_time < 0.1


class TestWorkflowPerformance:
    """Test workflow performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.create_test_repository()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def create_test_repository(self):
        """Create a test repository with multiple files."""
        # Create multiple Python files
        for i in range(20):
            with open(os.path.join(self.temp_dir, f"module_{i}.py"), "w") as f:
                f.write(f'''
"""Module {i} for testing."""

def function_{i}_1(x, y):
    """Function 1 in module {i}."""
    if x > 0:
        if y > 0:
            return x + y
        else:
            return x
    else:
        return 0

def function_{i}_2(data):
    """Function 2 in module {i}."""
    result = []
    for item in data:
        if item % 2 == 0:
            result.append(item * 2)
    return result

class Class_{i}:
    """Class {i} for testing."""
    
    def __init__(self, value):
        self.value = value
    
    def method_{i}(self):
        return self.value * {i}
''')
    
    @patch('src.nodes.asyncio.run')
    def test_workflow_execution_performance(self, mock_asyncio_run):
        """Test workflow execution performance."""
        from src.nodes import initialize_analysis, select_tools, execute_tools
        
        # Mock tool execution to focus on workflow performance
        mock_results = []
        for i in range(5):
            mock_results.append(Mock(
                tool_name=f"Tool {i}",
                status="success",
                data={"issues": i, "score": 8.0},
                execution_time=0.1
            ))
        mock_asyncio_run.return_value = mock_results
        
        request = AnalysisRequest(
            repository_url=self.temp_dir,
            analysis_type="comprehensive"
        )
        state = AnalysisState(request=request)
        
        # Test initialization performance
        start_time = time.time()
        state = initialize_analysis(state)
        init_time = time.time() - start_time
        
        assert init_time < 2.0  # Should initialize quickly
        assert state["status"] == "initialized"
        
        # Test tool selection performance
        start_time = time.time()
        state = select_tools(state)
        selection_time = time.time() - start_time
        
        assert selection_time < 1.0  # Should select tools quickly
        assert state["status"] == "tools_selected"
        
        # Test tool execution performance (mocked)
        start_time = time.time()
        state = execute_tools(state)
        execution_time = time.time() - start_time
        
        assert execution_time < 1.0  # Should execute quickly (mocked)
        assert state["status"] == "tools_executed"
    
    def test_large_repository_handling(self):
        """Test performance with large repository."""
        # Create a larger repository
        large_repo_dir = os.path.join(self.temp_dir, "large_repo")
        os.makedirs(large_repo_dir)
        
        # Create 100 files
        for i in range(100):
            with open(os.path.join(large_repo_dir, f"file_{i}.py"), "w") as f:
                f.write(f"# File {i}\ndef function_{i}(): pass\n" * 10)
        
        from src.nodes import initialize_analysis
        
        request = AnalysisRequest(
            repository_url=large_repo_dir,
            analysis_type="comprehensive"
        )
        state = AnalysisState(request=request)
        
        start_time = time.time()
        result = initialize_analysis(state)
        execution_time = time.time() - start_time
        
        # Should handle large repository within reasonable time
        assert execution_time < 10.0
        assert result["status"] == "initialized"


class TestLoadTesting:
    """Test system load and stress scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = ToolConfig()
        self.registry = ToolRegistry(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)
    
    def test_multiple_concurrent_workflows(self):
        """Test multiple concurrent workflow executions."""
        from src.nodes import initialize_analysis
        
        # Create test files
        for i in range(5):
            with open(os.path.join(self.temp_dir, f"test_{i}.py"), "w") as f:
                f.write(f"def test_function_{i}(): return {i}")
        
        def run_workflow():
            request = AnalysisRequest(
                repository_url=self.temp_dir,
                analysis_type="code_quality"
            )
            state = AnalysisState(request=request)
            
            start_time = time.time()
            result = initialize_analysis(state)
            execution_time = time.time() - start_time
            
            return result["status"] == "initialized", execution_time
        
        # Run multiple workflows concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_workflow) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # All workflows should succeed
        for success, exec_time in results:
            assert success is True
            assert exec_time < 5.0  # Each should complete within reasonable time
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        tool = FileReadTool()
        
        # Create a test file
        test_file = os.path.join(self.temp_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("def test(): pass\n" * 1000)
        
        # Execute tool many times
        for _ in range(50):
            result = tool._run(test_file)
            assert "error" not in result
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024
    
    def test_tool_timeout_handling(self):
        """Test tool timeout handling under load."""
        # Create a tool with short timeout
        config = ToolConfig()
        config.tool_timeout = 1  # 1 second timeout
        
        tool = CodeComplexityTool()
        tool.config = config
        
        # Create a very large file that might take time to process
        large_file_content = "def function_{}(): pass\n".format(i) for i in range(10000)
        large_file_content = "".join(large_file_content)
        
        start_time = time.time()
        result = tool._run(large_file_content)
        execution_time = time.time() - start_time
        
        # Should either complete quickly or handle timeout gracefully
        assert execution_time < 5.0  # Should not hang indefinitely
        # Result should either be successful or contain timeout error
        assert "error" not in result or "timeout" in result.get("error", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
