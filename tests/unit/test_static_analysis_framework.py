"""
Unit Tests for Language-Agnostic Static Analysis Framework

This module provides comprehensive unit tests for the static analysis framework,
ensuring that the language-agnostic design works correctly across different
programming languages and analysis tools.

Part of Milestone 3: analyze_code_node Integration & Debugging
"""

import pytest
import asyncio
import tempfile
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from tools.static_analysis_framework import (
    StaticAnalysisOrchestrator,
    AnalysisConfig,
    FileExtensionLanguageDetector,
    PythonPylintAnalyzer,
    JavaScriptESLintAnalyzer,
    AnalysisStateTracker,
    AnalyzerFactory,
    RepositoryAnalysisResult,
    LanguageAnalysisResult,
    ToolAnalysisResult,
    AnalysisIssue,
    AnalysisStatus,
    IssueSeverity
)

from tools.static_analysis_integration import (
    StaticAnalysisAdapter,
    analyze_repository_with_static_analysis,
    create_custom_analysis_config
)

class TestLanguageDetection:
    """Test language detection functionality."""
    
    def setup_method(self):
        """Setup method to disable debugging for all tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.detector = FileExtensionLanguageDetector()
    
    def test_python_file_detection(self):
        """Test detection of Python files."""
        assert self.detector.detect_language("test.py") == "python"
        assert self.detector.detect_language("script.pyw") == "python"
        assert self.detector.detect_language("types.pyi") == "python"
    
    def test_javascript_file_detection(self):
        """Test detection of JavaScript/TypeScript files."""
        assert self.detector.detect_language("app.js") == "javascript"
        assert self.detector.detect_language("component.jsx") == "javascript"
        assert self.detector.detect_language("types.ts") == "typescript"
        assert self.detector.detect_language("component.tsx") == "typescript"
    
    def test_other_languages_detection(self):
        """Test detection of other programming languages."""
        assert self.detector.detect_language("Main.java") == "java"
        assert self.detector.detect_language("main.c") == "c"
        assert self.detector.detect_language("main.cpp") == "cpp"
        assert self.detector.detect_language("main.go") == "go"
        assert self.detector.detect_language("main.rs") == "rust"
    
    def test_special_files_detection(self):
        """Test detection of special files."""
        assert self.detector.detect_language("Dockerfile") == "dockerfile"
        assert self.detector.detect_language("Makefile") == "makefile"
        assert self.detector.detect_language("config.json") == "json"
        assert self.detector.detect_language("config.yaml") == "yaml"
    
    def test_unknown_file_detection(self):
        """Test handling of unknown file types."""
        assert self.detector.detect_language("unknown.xyz") is None
        assert self.detector.detect_language("") is None
    
    def test_supported_languages(self):
        """Test getting supported languages."""
        supported = self.detector.get_supported_languages()
        assert "python" in supported
        assert "javascript" in supported
        assert "typescript" in supported
        assert "java" in supported

class TestAnalysisConfig:
    """Test analysis configuration functionality."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AnalysisConfig()
        assert config.max_file_size == 1024 * 1024
        assert config.timeout_per_tool == 60
        assert config.max_concurrent_tools == 4
        assert config.include_metrics is True
        assert config.severity_threshold == IssueSeverity.INFO
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AnalysisConfig(
            max_file_size=512 * 1024,
            timeout_per_tool=30,
            severity_threshold=IssueSeverity.HIGH
        )
        assert config.max_file_size == 512 * 1024
        assert config.timeout_per_tool == 30
        assert config.severity_threshold == IssueSeverity.HIGH
    
    def test_file_exclusion(self):
        """Test file exclusion patterns."""
        config = AnalysisConfig()
        assert not config.should_analyze_file("node_modules/package.js")
        assert not config.should_analyze_file("dist/bundle.min.js")
        assert not config.should_analyze_file(".git/config")
        assert config.should_analyze_file("src/main.py")
        assert config.should_analyze_file("lib/utils.js")

class TestPythonPylintAnalyzer:
    """Test Python Pylint analyzer."""
    
    def setup_method(self):
        """Setup method for tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.config = AnalysisConfig()
        self.analyzer = PythonPylintAnalyzer(self.config)
    
    def test_analyzer_setup(self):
        """Test analyzer initialization."""
        assert self.analyzer.get_tool_name() == "pylint"
        assert self.analyzer.supports_language("python")
        assert not self.analyzer.supports_language("javascript")
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_successful_analysis(self, mock_subprocess):
        """Test successful Pylint analysis."""
        # Mock subprocess result
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            json.dumps([{
                "type": "warning",
                "module": "test",
                "obj": "",
                "line": 1,
                "column": 0,
                "path": "test.py",
                "symbol": "unused-import",
                "message": "Unused import",
                "message-id": "W0611"
            }]).encode(),
            b""
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        # Execute analysis
        result = await self.analyzer.analyze("test.py", "import os\nprint('hello')", "python")
        
        # Verify results
        assert result.tool_name == "pylint"
        assert result.language == "python"
        assert result.status == AnalysisStatus.SUCCESS
        assert len(result.issues) == 1
        assert result.issues[0].severity == IssueSeverity.HIGH
        assert result.issues[0].message == "Unused import"
    
    @pytest.mark.asyncio
    async def test_unsupported_language(self):
        """Test analysis with unsupported language."""
        result = await self.analyzer.analyze("test.js", "console.log('hello');", "javascript")
        
        assert result.tool_name == "pylint"
        assert result.language == "javascript"
        assert result.status == AnalysisStatus.UNSUPPORTED
        assert len(result.issues) == 0
    
    def test_severity_mapping(self):
        """Test Pylint severity mapping."""
        assert self.analyzer._map_pylint_severity("error") == IssueSeverity.CRITICAL
        assert self.analyzer._map_pylint_severity("warning") == IssueSeverity.HIGH
        assert self.analyzer._map_pylint_severity("refactor") == IssueSeverity.MEDIUM
        assert self.analyzer._map_pylint_severity("convention") == IssueSeverity.LOW
        assert self.analyzer._map_pylint_severity("info") == IssueSeverity.INFO

class TestJavaScriptESLintAnalyzer:
    """Test JavaScript ESLint analyzer."""
    
    def setup_method(self):
        """Setup method for tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.config = AnalysisConfig()
        self.analyzer = JavaScriptESLintAnalyzer(self.config)
    
    def test_analyzer_setup(self):
        """Test analyzer initialization."""
        assert self.analyzer.get_tool_name() == "eslint"
        assert self.analyzer.supports_language("javascript")
        assert self.analyzer.supports_language("typescript")
        assert not self.analyzer.supports_language("python")
    
    @pytest.mark.asyncio
    @patch('asyncio.create_subprocess_exec')
    async def test_successful_analysis(self, mock_subprocess):
        """Test successful ESLint analysis."""
        # Mock subprocess result
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (
            json.dumps([{
                "filePath": "test.js",
                "messages": [{
                    "ruleId": "no-unused-vars",
                    "severity": 2,
                    "message": "Variable is defined but never used",
                    "line": 1,
                    "column": 5
                }]
            }]).encode(),
            b""
        )
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process
        
        # Execute analysis
        result = await self.analyzer.analyze("test.js", "var unused = 1;", "javascript")
        
        # Verify results
        assert result.tool_name == "eslint"
        assert result.language == "javascript"
        assert result.status == AnalysisStatus.SUCCESS
        assert len(result.issues) == 1
        assert result.issues[0].severity == IssueSeverity.HIGH
        assert "never used" in result.issues[0].message
    
    def test_severity_mapping(self):
        """Test ESLint severity mapping."""
        assert self.analyzer._map_eslint_severity(2) == IssueSeverity.HIGH
        assert self.analyzer._map_eslint_severity(1) == IssueSeverity.MEDIUM
        assert self.analyzer._map_eslint_severity(0) == IssueSeverity.INFO

class TestAnalysisStateTracker:
    """Test analysis state tracking."""
    
    def setup_method(self):
        """Setup method for tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.tracker = AnalysisStateTracker()
    
    def test_analysis_lifecycle_tracking(self):
        """Test complete analysis lifecycle tracking."""
        analysis_id = "test_analysis_123"
        repository_info = {"url": "https://github.com/test/repo", "files": []}
        
        # Start analysis
        self.tracker.start_analysis(analysis_id, repository_info)
        assert analysis_id in self.tracker.analysis_states
        assert self.tracker.analysis_states[analysis_id]["status"] == "started"
        
        # Start language analysis
        self.tracker.start_language_analysis(analysis_id, "python", 5)
        lang_state = self.tracker.analysis_states[analysis_id]["languages"]["python"]
        assert lang_state["status"] == "started"
        assert lang_state["file_count"] == 5
        
        # Start tool execution
        self.tracker.start_tool_execution(analysis_id, "python", "pylint")
        tool_state = lang_state["tools"]["pylint"]
        assert tool_state["status"] == "running"
        
        # Complete tool execution
        mock_result = ToolAnalysisResult(
            tool_name="pylint",
            language="python",
            status=AnalysisStatus.SUCCESS,
            issues=[],
            execution_time=1.5
        )
        self.tracker.complete_tool_execution(analysis_id, "python", "pylint", mock_result)
        assert tool_state["status"] == "completed"
        assert tool_state["execution_time"] == 1.5
    
    def test_error_tracking(self):
        """Test error tracking functionality."""
        analysis_id = "test_error_123"
        repository_info = {"url": "https://github.com/test/repo"}
        
        self.tracker.start_analysis(analysis_id, repository_info)
        self.tracker.fail_analysis(analysis_id, "Test error")
        
        state = self.tracker.analysis_states[analysis_id]
        assert state["status"] == "failed"
        assert state["error"] == "Test error"

class TestAnalyzerFactory:
    """Test analyzer factory functionality."""
    
    def setup_method(self):
        """Setup method for tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.config = AnalysisConfig()
    
    def test_create_known_analyzers(self):
        """Test creating known analyzers."""
        pylint = AnalyzerFactory.create_analyzer("pylint", self.config)
        assert pylint is not None
        assert pylint.get_tool_name() == "pylint"
        
        eslint = AnalyzerFactory.create_analyzer("eslint", self.config)
        assert eslint is not None
        assert eslint.get_tool_name() == "eslint"
    
    def test_create_unknown_analyzer(self):
        """Test creating unknown analyzer."""
        unknown = AnalyzerFactory.create_analyzer("unknown_tool", self.config)
        assert unknown is None
    
    def test_get_available_analyzers(self):
        """Test getting available analyzers."""
        available = AnalyzerFactory.get_available_analyzers()
        assert "pylint" in available
        assert "eslint" in available

class TestStaticAnalysisIntegration:
    """Test static analysis integration layer."""
    
    def setup_method(self):
        """Setup method for tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
        self.adapter = StaticAnalysisAdapter()
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.config is not None
        assert self.adapter.orchestrator is not None
        assert self.adapter.integration_metrics["total_analyses"] == 0
    
    def test_repository_info_extraction(self):
        """Test repository information extraction from state."""
        state = {
            "repository_url": "https://github.com/test/repo",
            "repository_info": {
                "name": "test-repo",
                "language": "Python",
                "files": [{"name": "main.py", "content": "print('hello')"}],
                "stars": 100,
                "forks": 20
            }
        }
        
        repo_info = self.adapter._extract_repository_info_from_state(state)
        assert repo_info["url"] == "https://github.com/test/repo"
        assert repo_info["name"] == "test-repo"
        assert repo_info["language"] == "Python"
        assert len(repo_info["files"]) == 1
    
    def test_repository_info_validation(self):
        """Test repository information validation."""
        # Valid repository info
        valid_info = {
            "url": "https://github.com/test/repo",
            "files": [{"name": "main.py", "content": "print('hello')"}]
        }
        assert self.adapter._validate_repository_info(valid_info) is True
        
        # Invalid repository info - missing URL
        invalid_info_no_url = {
            "files": [{"name": "main.py", "content": "print('hello')"}]
        }
        assert self.adapter._validate_repository_info(invalid_info_no_url) is False
        
        # Invalid repository info - no files
        invalid_info_no_files = {
            "url": "https://github.com/test/repo",
            "files": []
        }
        assert self.adapter._validate_repository_info(invalid_info_no_files) is False
    
    def test_create_custom_config(self):
        """Test creating custom analysis configuration."""
        config = create_custom_analysis_config(
            timeout_per_tool=30,
            max_concurrent_tools=2
        )
        assert config.timeout_per_tool == 30
        assert config.max_concurrent_tools == 2
