"""
Integration Tests for analyze_code_node with Static Analysis Framework

This module provides comprehensive integration tests for the analyze_code_node
with the new language-agnostic static analysis framework.

Part of Milestone 3: analyze_code_node Integration & Debugging
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from nodes import analyze_code_node
from state import ReviewState, ReviewStatus
from tools.static_analysis_framework import AnalysisStatus, IssueSeverity

class TestAnalyzeCodeNodeIntegration:
    """Integration tests for analyze_code_node with static analysis."""
    
    def setup_method(self):
        """Setup method to disable debugging for all tests."""
        from debug.repository_debugging import repo_debugger
        repo_debugger.set_debug_enabled(False)
    
    @pytest.fixture
    def sample_repository_state(self):
        """Provide sample repository state for testing."""
        return {
            "repository_url": "https://github.com/test/python-repo",
            "current_step": "analyze_code",
            "status": ReviewStatus.FETCHING_REPOSITORY,
            "repository_info": {
                "name": "python-repo",
                "full_name": "test/python-repo",
                "description": "Test Python repository",
                "language": "Python",
                "stars": 42,
                "forks": 7,
                "files": [
                    {
                        "name": "main.py",
                        "type": "file",
                        "content": "import os\nimport sys\n\ndef main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()\n"
                    },
                    {
                        "name": "utils.py",
                        "type": "file",
                        "content": "def helper_function():\n    unused_var = 42\n    return 'helper'\n"
                    },
                    {
                        "name": "requirements.txt",
                        "type": "file",
                        "content": "requests==2.28.0\nnumpy==1.21.0\n"
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mixed_language_repository_state(self):
        """Provide mixed language repository state for testing."""
        return {
            "repository_url": "https://github.com/test/mixed-repo",
            "current_step": "analyze_code",
            "status": ReviewStatus.FETCHING_REPOSITORY,
            "repository_info": {
                "name": "mixed-repo",
                "full_name": "test/mixed-repo",
                "description": "Test mixed language repository",
                "language": "JavaScript",
                "stars": 100,
                "forks": 20,
                "files": [
                    {
                        "name": "app.js",
                        "type": "file",
                        "content": "const express = require('express');\nconst app = express();\n\napp.get('/', (req, res) => {\n    res.send('Hello World');\n});\n\napp.listen(3000);\n"
                    },
                    {
                        "name": "script.py",
                        "type": "file",
                        "content": "import json\n\ndef process_data(data):\n    return json.dumps(data)\n"
                    },
                    {
                        "name": "config.json",
                        "type": "file",
                        "content": "{\n    \"port\": 3000,\n    \"debug\": true\n}\n"
                    }
                ]
            }
        }
    
    @pytest.mark.asyncio
    @patch('tools.static_analysis_framework.StaticAnalysisOrchestrator.analyze_repository')
    async def test_successful_python_analysis(self, mock_analyze, sample_repository_state):
        """Test successful analysis of Python repository."""
        # Mock successful analysis result
        from tools.static_analysis_framework import (
            RepositoryAnalysisResult, LanguageAnalysisResult, ToolAnalysisResult, AnalysisIssue
        )
        
        # Create mock issues
        mock_issues = [
            AnalysisIssue(
                file_path="main.py",
                line_number=1,
                column=1,
                severity=IssueSeverity.LOW,
                category="convention",
                message="Missing module docstring",
                rule_id="C0114"
            ),
            AnalysisIssue(
                file_path="utils.py",
                line_number=2,
                column=5,
                severity=IssueSeverity.MEDIUM,
                category="warning",
                message="Unused variable 'unused_var'",
                rule_id="W0612"
            )
        ]
        
        # Create mock tool result
        mock_tool_result = ToolAnalysisResult(
            tool_name="pylint",
            language="python",
            status=AnalysisStatus.SUCCESS,
            issues=mock_issues,
            metrics={"total_issues": 2},
            execution_time=1.5
        )
        
        # Create mock language result
        mock_language_result = LanguageAnalysisResult(
            language="python",
            file_count=2,
            tool_results=[mock_tool_result],
            total_issues=2
        )
        
        # Create mock repository result
        mock_repository_result = RepositoryAnalysisResult(
            repository_url="https://github.com/test/python-repo",
            analysis_id="test_analysis_123",
            timestamp="2024-01-01T00:00:00",
            languages_detected={"python"},
            language_results={"python": mock_language_result},
            overall_metrics={
                "total_files_analyzed": 2,
                "total_issues_found": 2,
                "languages_analyzed": 1,
                "tools_executed": 1
            }
        )
        
        mock_analyze.return_value = mock_repository_result
        
        # Execute analyze_code_node
        result = await analyze_code_node(sample_repository_state)
        
        # Verify results
        assert result["current_step"] == "generate_report"
        assert "analysis_results" in result
        assert "static_analysis" in result["analysis_results"]
        
        analysis_summary = result["analysis_results"]["static_analysis"]["summary"]
        assert analysis_summary["total_issues"] == 2
        assert analysis_summary["languages_analyzed"] == 1
        assert analysis_summary["tools_executed"] == 1
        
        # Verify language details
        language_details = result["analysis_results"]["static_analysis"]["language_details"]
        assert "python" in language_details
        assert language_details["python"]["file_count"] == 2
        assert language_details["python"]["total_issues"] == 2
        assert "pylint" in language_details["python"]["tools_used"]
    
    @pytest.mark.asyncio
    @patch('tools.static_analysis_framework.StaticAnalysisOrchestrator.analyze_repository')
    async def test_mixed_language_analysis(self, mock_analyze, mixed_language_repository_state):
        """Test analysis of repository with multiple languages."""
        from tools.static_analysis_framework import (
            RepositoryAnalysisResult, LanguageAnalysisResult, ToolAnalysisResult
        )
        
        # Create mock results for multiple languages
        python_result = LanguageAnalysisResult(
            language="python",
            file_count=1,
            tool_results=[ToolAnalysisResult(
                tool_name="pylint",
                language="python",
                status=AnalysisStatus.SUCCESS,
                issues=[],
                execution_time=0.8
            )],
            total_issues=0
        )
        
        javascript_result = LanguageAnalysisResult(
            language="javascript",
            file_count=1,
            tool_results=[ToolAnalysisResult(
                tool_name="eslint",
                language="javascript",
                status=AnalysisStatus.SUCCESS,
                issues=[],
                execution_time=1.2
            )],
            total_issues=0
        )
        
        mock_repository_result = RepositoryAnalysisResult(
            repository_url="https://github.com/test/mixed-repo",
            analysis_id="test_mixed_123",
            timestamp="2024-01-01T00:00:00",
            languages_detected={"python", "javascript"},
            language_results={
                "python": python_result,
                "javascript": javascript_result
            },
            overall_metrics={
                "total_files_analyzed": 2,
                "total_issues_found": 0,
                "languages_analyzed": 2,
                "tools_executed": 2
            }
        )
        
        mock_analyze.return_value = mock_repository_result
        
        # Execute analyze_code_node
        result = await analyze_code_node(mixed_language_repository_state)
        
        # Verify results
        assert result["current_step"] == "generate_report"
        
        analysis_summary = result["analysis_results"]["static_analysis"]["summary"]
        assert analysis_summary["languages_analyzed"] == 2
        assert analysis_summary["tools_executed"] == 2
        
        language_details = result["analysis_results"]["static_analysis"]["language_details"]
        assert "python" in language_details
        assert "javascript" in language_details
    
    @pytest.mark.asyncio
    async def test_missing_repository_info(self):
        """Test handling of missing repository information."""
        state = {
            "repository_url": "https://github.com/test/empty-repo",
            "current_step": "analyze_code",
            "status": ReviewStatus.FETCHING_REPOSITORY,
            "repository_info": {}  # Empty repository info
        }
        
        result = await analyze_code_node(state)
        
        # Should go to error handler
        assert result["current_step"] == "error_handler"
        assert "error" in result
        assert "No repository information" in result["error"]
    
    @pytest.mark.asyncio
    async def test_no_files_for_analysis(self):
        """Test handling of repository with no files."""
        state = {
            "repository_url": "https://github.com/test/no-files-repo",
            "current_step": "analyze_code",
            "status": ReviewStatus.FETCHING_REPOSITORY,
            "repository_info": {
                "name": "no-files-repo",
                "files": []  # No files
            }
        }
        
        result = await analyze_code_node(state)
        
        # Should go to error handler
        assert result["current_step"] == "error_handler"
        assert "error" in result
        assert "No repository information" in result["error"]
    
    @pytest.mark.asyncio
    @patch('tools.static_analysis_integration.StaticAnalysisAdapter.analyze_repository_for_node')
    async def test_analysis_exception_handling(self, mock_analyze, sample_repository_state):
        """Test handling of analysis exceptions."""
        # Mock analysis to raise an exception
        mock_analyze.side_effect = Exception("Analysis tool not found")
        
        result = await analyze_code_node(sample_repository_state)
        
        # Should go to error handler
        assert result["current_step"] == "error_handler"
        assert "error" in result
        assert "Analysis tool not found" in result["error"]
    
    @pytest.mark.asyncio
    @patch('tools.static_analysis_framework.StaticAnalysisOrchestrator.analyze_repository')
    async def test_analysis_with_failed_tools(self, mock_analyze, sample_repository_state):
        """Test analysis when some tools fail."""
        from tools.static_analysis_framework import (
            RepositoryAnalysisResult, LanguageAnalysisResult, ToolAnalysisResult
        )
        
        # Create mock results with one failed tool
        successful_tool = ToolAnalysisResult(
            tool_name="pylint",
            language="python",
            status=AnalysisStatus.SUCCESS,
            issues=[],
            execution_time=1.0
        )
        
        failed_tool = ToolAnalysisResult(
            tool_name="bandit",
            language="python",
            status=AnalysisStatus.FAILED,
            error_message="Tool not installed",
            execution_time=0.1
        )
        
        mock_language_result = LanguageAnalysisResult(
            language="python",
            file_count=2,
            tool_results=[successful_tool, failed_tool],
            total_issues=0
        )
        
        mock_repository_result = RepositoryAnalysisResult(
            repository_url="https://github.com/test/python-repo",
            analysis_id="test_partial_123",
            timestamp="2024-01-01T00:00:00",
            languages_detected={"python"},
            language_results={"python": mock_language_result},
            overall_metrics={
                "total_files_analyzed": 2,
                "total_issues_found": 0,
                "languages_analyzed": 1,
                "tools_executed": 2
            }
        )
        
        mock_analyze.return_value = mock_repository_result
        
        # Execute analyze_code_node
        result = await analyze_code_node(sample_repository_state)
        
        # Should still succeed with partial results
        assert result["current_step"] == "generate_report"
        
        language_details = result["analysis_results"]["static_analysis"]["language_details"]
        python_details = language_details["python"]
        
        # Check that both tools are recorded
        tool_results = python_details["tool_results"]
        assert len(tool_results) == 2
        
        # Find the failed tool result
        failed_result = next(tr for tr in tool_results if tr["tool_name"] == "bandit")
        assert failed_result["status"] == "failed"
        assert failed_result["error_message"] == "Tool not installed"
    
    @pytest.mark.asyncio
    @patch('tools.static_analysis_framework.StaticAnalysisOrchestrator.analyze_repository')
    async def test_analysis_with_recommendations(self, mock_analyze, sample_repository_state):
        """Test analysis that generates recommendations."""
        from tools.static_analysis_framework import (
            RepositoryAnalysisResult, LanguageAnalysisResult, ToolAnalysisResult, AnalysisIssue
        )
        
        # Create many issues to trigger recommendations
        many_issues = [
            AnalysisIssue(
                file_path=f"file_{i}.py",
                line_number=1,
                column=1,
                severity=IssueSeverity.HIGH,
                category="error",
                message=f"Error {i}",
                rule_id=f"E{i:03d}"
            )
            for i in range(50)  # Many issues to trigger recommendations
        ]
        
        mock_tool_result = ToolAnalysisResult(
            tool_name="pylint",
            language="python",
            status=AnalysisStatus.SUCCESS,
            issues=many_issues,
            execution_time=2.0
        )
        
        mock_language_result = LanguageAnalysisResult(
            language="python",
            file_count=5,
            tool_results=[mock_tool_result],
            total_issues=50
        )
        
        mock_repository_result = RepositoryAnalysisResult(
            repository_url="https://github.com/test/python-repo",
            analysis_id="test_recommendations_123",
            timestamp="2024-01-01T00:00:00",
            languages_detected={"python"},
            language_results={"python": mock_language_result},
            overall_metrics={
                "total_files_analyzed": 5,
                "total_issues_found": 50,
                "languages_analyzed": 1,
                "tools_executed": 1
            }
        )
        
        mock_analyze.return_value = mock_repository_result
        
        # Execute analyze_code_node
        result = await analyze_code_node(sample_repository_state)
        
        # Verify recommendations are generated
        recommendations = result["analysis_results"]["static_analysis"]["recommendations"]
        assert len(recommendations) > 0
        
        # Should have a high issue density recommendation
        high_density_rec = next(
            (rec for rec in recommendations if rec["type"] == "code_quality"), 
            None
        )
        assert high_density_rec is not None
        assert high_density_rec["priority"] == "high"
