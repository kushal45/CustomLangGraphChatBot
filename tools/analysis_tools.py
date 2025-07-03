"""Static code analysis tools for LangGraph workflow."""

import os
import tempfile
import subprocess
import json
import ast
from typing import Dict, Any, List, Optional
from langchain.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field
from .logging_utils import log_tool_execution, LoggedBaseTool
from logging_config import get_logger

logger = get_logger(__name__)


class CodeAnalysisConfig(BaseModel):
    """Configuration for code analysis tools."""
    max_file_size: int = 1024 * 1024  # 1MB
    timeout: int = 60
    temp_dir: Optional[str] = None


class PylintTool(BaseTool, LoggedBaseTool):
    """Tool for running Pylint static analysis on Python code."""

    name: str = "pylint_analysis"
    description: str = """
    Run Pylint static analysis on Python code to detect:
    - Code quality issues
    - Style violations
    - Potential bugs
    - Code smells

    Input should be Python code as a string.
    """

    config: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)

    def __init__(self, **kwargs):
        BaseTool.__init__(self, **kwargs)
        LoggedBaseTool.__init__(self)
    
    @log_tool_execution
    def _run(
        self,
        code: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run Pylint analysis on the provided code."""
        try:
            self.log_info("Starting Pylint analysis", extra={
                "code_length": len(code),
                "max_file_size": self.config.max_file_size
            })

            if len(code) > self.config.max_file_size:
                self.log_warning("Code too large for analysis", extra={
                    "code_length": len(code),
                    "max_allowed": self.config.max_file_size
                })
                return {"error": "Code too large for analysis"}

            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name

            self.log_debug("Created temporary file for Pylint analysis", extra={
                "temp_file": temp_file_path
            })
            
            try:
                # Run pylint
                result = subprocess.run(
                    ['python3', '-m', 'pylint', '--output-format=json', '--reports=no', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout
                )
                
                # Parse JSON output
                if result.stdout:
                    issues = json.loads(result.stdout)
                else:
                    issues = []
                
                # Categorize issues
                errors = [issue for issue in issues if issue.get('type') == 'error']
                warnings = [issue for issue in issues if issue.get('type') == 'warning']
                conventions = [issue for issue in issues if issue.get('type') == 'convention']
                refactors = [issue for issue in issues if issue.get('type') == 'refactor']
                
                return {
                    "tool": "pylint",
                    "total_issues": len(issues),
                    "errors": len(errors),
                    "warnings": len(warnings),
                    "conventions": len(conventions),
                    "refactors": len(refactors),
                    "issues": [
                        {
                            "type": issue.get("type"),
                            "message": issue.get("message"),
                            "line": issue.get("line"),
                            "column": issue.get("column"),
                            "symbol": issue.get("symbol"),
                            "message_id": issue.get("message-id")
                        }
                        for issue in issues[:20]  # Limit to first 20 issues
                    ],
                    "score": self._extract_score(result.stderr) if result.stderr else None
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except subprocess.TimeoutExpired:
            return {"error": "Pylint analysis timed out"}
        except FileNotFoundError:
            return {"error": "Pylint not installed. Install with: pip install pylint"}
        except Exception as e:
            return {"error": f"Pylint analysis failed: {str(e)}"}
    
    def _extract_score(self, stderr: str) -> Optional[float]:
        """Extract score from pylint stderr output."""
        try:
            for line in stderr.split('\n'):
                if 'Your code has been rated at' in line:
                    score_part = line.split('Your code has been rated at')[1].split('/')[0].strip()
                    return float(score_part)
        except:
            pass
        return None


class Flake8Tool(BaseTool):
    """Tool for running Flake8 style checking on Python code."""
    
    name: str = "flake8_analysis"
    description: str = """
    Run Flake8 style checking on Python code to detect:
    - PEP 8 style violations
    - Syntax errors
    - Undefined names
    - Unused imports
    
    Input should be Python code as a string.
    """
    
    config: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    
    def _run(
        self,
        code: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run Flake8 analysis on the provided code."""
        try:
            if len(code) > self.config.max_file_size:
                return {"error": "Code too large for analysis"}
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Run flake8
                result = subprocess.run(
                    ['python3', '-m', 'flake8', '--format=json', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout
                )
                
                # Parse output
                issues = []
                if result.stdout:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                issue = json.loads(line)
                                issues.append(issue)
                            except json.JSONDecodeError:
                                # Fallback to parsing standard format
                                parts = line.split(':')
                                if len(parts) >= 4:
                                    issues.append({
                                        "filename": parts[0],
                                        "line_number": int(parts[1]),
                                        "column_number": int(parts[2]),
                                        "code": parts[3].strip().split()[0],
                                        "text": ' '.join(parts[3].strip().split()[1:])
                                    })
                
                # Categorize by error type
                error_counts = {}
                for issue in issues:
                    code = issue.get('code', 'Unknown')
                    error_counts[code] = error_counts.get(code, 0) + 1
                
                return {
                    "tool": "flake8",
                    "total_issues": len(issues),
                    "error_counts": error_counts,
                    "issues": [
                        {
                            "line": issue.get("line_number"),
                            "column": issue.get("column_number"),
                            "code": issue.get("code"),
                            "message": issue.get("text")
                        }
                        for issue in issues[:20]  # Limit to first 20 issues
                    ]
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except subprocess.TimeoutExpired:
            return {"error": "Flake8 analysis timed out"}
        except FileNotFoundError:
            return {"error": "Flake8 not installed. Install with: pip install flake8"}
        except Exception as e:
            return {"error": f"Flake8 analysis failed: {str(e)}"}


class BanditSecurityTool(BaseTool):
    """Tool for running Bandit security analysis on Python code."""
    
    name: str = "bandit_security"
    description: str = """
    Run Bandit security analysis on Python code to detect:
    - Security vulnerabilities
    - Common security anti-patterns
    - Hardcoded passwords/secrets
    - Insecure function usage
    
    Input should be Python code as a string.
    """
    
    config: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    
    def _run(
        self,
        code: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Run Bandit security analysis on the provided code."""
        try:
            if len(code) > self.config.max_file_size:
                return {"error": "Code too large for analysis"}
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # Run bandit
                result = subprocess.run(
                    ['python3', '-m', 'bandit', '-f', 'json', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout
                )
                
                # Parse JSON output
                if result.stdout:
                    bandit_output = json.loads(result.stdout)
                    results = bandit_output.get('results', [])
                    metrics = bandit_output.get('metrics', {})
                else:
                    results = []
                    metrics = {}
                
                # Categorize by severity
                severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
                for issue in results:
                    severity = issue.get('issue_severity', 'LOW')
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                return {
                    "tool": "bandit",
                    "total_issues": len(results),
                    "severity_counts": severity_counts,
                    "metrics": {
                        "files_scanned": metrics.get('_totals', {}).get('loc', 0),
                        "lines_of_code": metrics.get('_totals', {}).get('loc', 0)
                    },
                    "issues": [
                        {
                            "test_name": issue.get("test_name"),
                            "test_id": issue.get("test_id"),
                            "severity": issue.get("issue_severity"),
                            "confidence": issue.get("issue_confidence"),
                            "line": issue.get("line_number"),
                            "message": issue.get("issue_text"),
                            "code": issue.get("code", "")[:200]  # Limit code snippet
                        }
                        for issue in results[:15]  # Limit to first 15 issues
                    ]
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except subprocess.TimeoutExpired:
            return {"error": "Bandit analysis timed out"}
        except FileNotFoundError:
            return {"error": "Bandit not installed. Install with: pip install bandit"}
        except Exception as e:
            return {"error": f"Bandit analysis failed: {str(e)}"}


class CodeComplexityTool(BaseTool):
    """Tool for analyzing code complexity using AST."""
    
    name: str = "code_complexity"
    description: str = """
    Analyze Python code complexity including:
    - Cyclomatic complexity
    - Function/class counts
    - Lines of code metrics
    - Nesting depth
    
    Input should be Python code as a string.
    """
    
    def _run(
        self,
        code: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Dict[str, Any]:
        """Analyze code complexity."""
        try:
            tree = ast.parse(code)
            
            # Initialize metrics
            metrics = {
                "lines_of_code": len(code.splitlines()),
                "functions": 0,
                "classes": 0,
                "imports": 0,
                "complexity_score": 0,
                "max_nesting_depth": 0,
                "function_details": []
            }
            
            # Analyze AST
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    metrics["functions"] += 1
                    complexity = self._calculate_cyclomatic_complexity(node)
                    metrics["function_details"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": complexity,
                        "args_count": len(node.args.args)
                    })
                    metrics["complexity_score"] += complexity
                
                elif isinstance(node, ast.ClassDef):
                    metrics["classes"] += 1
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    metrics["imports"] += 1
            
            # Calculate average complexity
            if metrics["functions"] > 0:
                metrics["average_complexity"] = metrics["complexity_score"] / metrics["functions"]
            else:
                metrics["average_complexity"] = 0
            
            # Determine quality rating
            avg_complexity = metrics["average_complexity"]
            if avg_complexity <= 5:
                quality_rating = "Good"
            elif avg_complexity <= 10:
                quality_rating = "Moderate"
            else:
                quality_rating = "Complex"
            
            return {
                "tool": "complexity_analysis",
                "metrics": metrics,
                "quality_rating": quality_rating,
                "recommendations": self._get_recommendations(metrics)
            }
            
        except SyntaxError as e:
            return {"error": f"Syntax error in code: {str(e)}"}
        except Exception as e:
            return {"error": f"Complexity analysis failed: {str(e)}"}
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _get_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics."""
        recommendations = []
        
        if metrics["average_complexity"] > 10:
            recommendations.append("Consider breaking down complex functions into smaller ones")
        
        if metrics["functions"] == 0 and metrics["lines_of_code"] > 50:
            recommendations.append("Consider organizing code into functions for better modularity")
        
        if any(func["complexity"] > 15 for func in metrics["function_details"]):
            recommendations.append("Some functions have very high complexity - consider refactoring")
        
        if metrics["classes"] == 0 and metrics["functions"] > 10:
            recommendations.append("Consider using classes to organize related functions")
        
        return recommendations


# Tool instances for easy import
pylint_tool = PylintTool()
flake8_tool = Flake8Tool()
bandit_security_tool = BanditSecurityTool()
code_complexity_tool = CodeComplexityTool()

# List of all analysis tools
ANALYSIS_TOOLS = [
    pylint_tool,
    flake8_tool,
    bandit_security_tool,
    code_complexity_tool
]
