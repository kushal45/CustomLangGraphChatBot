"""
Language-Agnostic Static Analysis Framework

This module provides a comprehensive framework for integrating static analysis tools
across multiple programming languages without coupling to specific languages or tools.

Architecture follows SOLID principles:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Extensible for new languages and tools
- Liskov Substitution: All analyzers implement common interfaces
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions

Part of Milestone 3: analyze_code_node Integration & Debugging
"""

import os
import asyncio
import tempfile
import subprocess
import json
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime
from logging_config import get_logger

logger = get_logger(__name__)

# ============================================================================
# CORE ABSTRACTIONS & PROTOCOLS (Interface Segregation Principle)
# ============================================================================

class AnalysisResult(Protocol):
    """Protocol for analysis results."""
    tool_name: str
    language: str
    status: str
    issues: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    execution_time: float

class LanguageDetector(Protocol):
    """Protocol for language detection."""
    def detect_language(self, file_path: str, content: str) -> Optional[str]:
        ...
    
    def get_supported_languages(self) -> Set[str]:
        ...

class StaticAnalyzer(Protocol):
    """Protocol for static analysis tools."""
    async def analyze(self, file_path: str, content: str, language: str) -> AnalysisResult:
        ...
    
    def supports_language(self, language: str) -> bool:
        ...
    
    def get_tool_name(self) -> str:
        ...

class AnalysisOrchestrator(Protocol):
    """Protocol for orchestrating analysis across multiple tools."""
    async def analyze_repository(self, repository_info: Dict[str, Any]) -> Dict[str, Any]:
        ...

# ============================================================================
# ENUMS & DATA STRUCTURES
# ============================================================================

class AnalysisStatus(Enum):
    """Analysis execution status."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    UNSUPPORTED = "unsupported"

class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class AnalysisIssue:
    """Represents a single analysis issue."""
    file_path: str
    line_number: int
    column: Optional[int]
    severity: IssueSeverity
    category: str
    message: str
    rule_id: Optional[str] = None
    suggestion: Optional[str] = None

@dataclass
class ToolAnalysisResult:
    """Result from a single static analysis tool."""
    tool_name: str
    language: str
    status: AnalysisStatus
    issues: List[AnalysisIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    raw_output: Optional[str] = None

@dataclass
class LanguageAnalysisResult:
    """Aggregated results for a specific language."""
    language: str
    file_count: int
    tool_results: List[ToolAnalysisResult] = field(default_factory=list)
    aggregated_metrics: Dict[str, Any] = field(default_factory=dict)
    total_issues: int = 0
    issues_by_severity: Dict[IssueSeverity, int] = field(default_factory=dict)

@dataclass
class RepositoryAnalysisResult:
    """Complete analysis results for a repository."""
    repository_url: str
    analysis_id: str
    timestamp: str
    languages_detected: Set[str] = field(default_factory=set)
    language_results: Dict[str, LanguageAnalysisResult] = field(default_factory=dict)
    overall_metrics: Dict[str, Any] = field(default_factory=dict)
    execution_summary: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# LANGUAGE DETECTION (Single Responsibility Principle)
# ============================================================================

class FileExtensionLanguageDetector:
    """Detects programming languages based on file extensions."""
    
    def __init__(self):
        self.extension_map = {
            # Python
            '.py': 'python',
            '.pyw': 'python',
            '.pyi': 'python',
            
            # JavaScript/TypeScript
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.mjs': 'javascript',
            
            # Java
            '.java': 'java',
            '.class': 'java',
            
            # C/C++
            '.c': 'c',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.hxx': 'cpp',
            
            # C#
            '.cs': 'csharp',
            
            # Go
            '.go': 'go',
            
            # Rust
            '.rs': 'rust',
            
            # Ruby
            '.rb': 'ruby',
            '.rbw': 'ruby',
            
            # PHP
            '.php': 'php',
            '.phtml': 'php',
            
            # Shell
            '.sh': 'shell',
            '.bash': 'shell',
            '.zsh': 'shell',
            
            # Configuration files
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.toml': 'toml',
            '.ini': 'ini',
            
            # Documentation
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.txt': 'text',
        }
    
    def detect_language(self, file_path: str, content: str = "") -> Optional[str]:
        """Detect language based on file extension."""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Handle special cases
        if path.name.lower() in ['dockerfile', 'makefile', 'rakefile']:
            return path.name.lower()
        
        return self.extension_map.get(extension)
    
    def get_supported_languages(self) -> Set[str]:
        """Get all supported languages."""
        return set(self.extension_map.values())

# ============================================================================
# ANALYSIS CONFIGURATION (Open/Closed Principle)
# ============================================================================

@dataclass
class AnalysisConfig:
    """Configuration for static analysis execution."""
    max_file_size: int = 1024 * 1024  # 1MB
    timeout_per_tool: int = 60  # seconds
    max_concurrent_tools: int = 4
    temp_dir: Optional[str] = None
    include_metrics: bool = True
    include_suggestions: bool = True
    severity_threshold: IssueSeverity = IssueSeverity.INFO
    excluded_patterns: List[str] = field(default_factory=lambda: [
        '*.min.js', '*.bundle.js', 'node_modules/*', '.git/*', '__pycache__/*'
    ])
    
    def should_analyze_file(self, file_path: str) -> bool:
        """Check if file should be analyzed based on exclusion patterns."""
        path = Path(file_path)
        for pattern in self.excluded_patterns:
            if path.match(pattern):
                return False
        return True

# ============================================================================
# BASE ANALYZER IMPLEMENTATION (Template Method Pattern)
# ============================================================================

class BaseStaticAnalyzer(ABC):
    """Base class for static analysis tools implementing common functionality."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.supported_languages: Set[str] = set()
        self._setup_analyzer()

    @abstractmethod
    def _setup_analyzer(self) -> None:
        """Setup analyzer-specific configuration."""
        pass

    @abstractmethod
    async def _execute_analysis(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        """Execute the actual analysis tool."""
        pass

    @abstractmethod
    def _parse_results(self, raw_output: str, language: str) -> List[AnalysisIssue]:
        """Parse tool output into standardized issues."""
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """Get the name of this analysis tool."""
        pass

    def supports_language(self, language: str) -> bool:
        """Check if this analyzer supports the given language."""
        return language in self.supported_languages

    async def analyze(self, file_path: str, content: str, language: str) -> ToolAnalysisResult:
        """Analyze a file and return standardized results."""
        start_time = datetime.now()

        if not self.supports_language(language):
            return ToolAnalysisResult(
                tool_name=self.get_tool_name(),
                language=language,
                status=AnalysisStatus.UNSUPPORTED,
                execution_time=0.0
            )

        try:
            # Execute analysis with timeout
            raw_result = await asyncio.wait_for(
                self._execute_analysis(file_path, content, language),
                timeout=self.config.timeout_per_tool
            )

            # Parse results
            issues = self._parse_results(raw_result.get('output', ''), language)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()

            # Build metrics
            metrics = self._calculate_metrics(issues, raw_result)

            return ToolAnalysisResult(
                tool_name=self.get_tool_name(),
                language=language,
                status=AnalysisStatus.SUCCESS,
                issues=issues,
                metrics=metrics,
                execution_time=execution_time,
                raw_output=raw_result.get('output')
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolAnalysisResult(
                tool_name=self.get_tool_name(),
                language=language,
                status=AnalysisStatus.TIMEOUT,
                execution_time=execution_time,
                error_message=f"Analysis timed out after {self.config.timeout_per_tool}s"
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Analysis failed for {self.get_tool_name()}: {str(e)}")
            return ToolAnalysisResult(
                tool_name=self.get_tool_name(),
                language=language,
                status=AnalysisStatus.FAILED,
                execution_time=execution_time,
                error_message=str(e)
            )

    def _calculate_metrics(self, issues: List[AnalysisIssue], raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics from analysis results."""
        severity_counts = {}
        for severity in IssueSeverity:
            severity_counts[severity.value] = sum(1 for issue in issues if issue.severity == severity)

        return {
            'total_issues': len(issues),
            'issues_by_severity': severity_counts,
            'tool_specific_metrics': raw_result.get('metrics', {}),
            'analysis_timestamp': datetime.now().isoformat()
        }

# ============================================================================
# CONCRETE ANALYZER IMPLEMENTATIONS (Open/Closed Principle)
# ============================================================================

class PythonPylintAnalyzer(BaseStaticAnalyzer):
    """Pylint analyzer for Python code."""

    def _setup_analyzer(self) -> None:
        """Setup Pylint-specific configuration."""
        self.supported_languages = {'python'}
        self.tool_command = ['pylint', '--output-format=json', '--reports=no']

    def get_tool_name(self) -> str:
        return "pylint"

    async def _execute_analysis(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        """Execute Pylint analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()

            try:
                process = await asyncio.create_subprocess_exec(
                    *self.tool_command, temp_file.name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                return {
                    'output': stdout.decode('utf-8'),
                    'error': stderr.decode('utf-8'),
                    'return_code': process.returncode
                }
            finally:
                os.unlink(temp_file.name)

    def _parse_results(self, raw_output: str, language: str) -> List[AnalysisIssue]:
        """Parse Pylint JSON output."""
        issues = []
        try:
            if raw_output.strip():
                pylint_results = json.loads(raw_output)
                for result in pylint_results:
                    severity = self._map_pylint_severity(result.get('type', 'info'))
                    issues.append(AnalysisIssue(
                        file_path=result.get('path', ''),
                        line_number=result.get('line', 0),
                        column=result.get('column'),
                        severity=severity,
                        category=result.get('type', 'unknown'),
                        message=result.get('message', ''),
                        rule_id=result.get('message-id'),
                        suggestion=result.get('suggestion')
                    ))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse Pylint output: {raw_output[:100]}...")

        return issues

    def _map_pylint_severity(self, pylint_type: str) -> IssueSeverity:
        """Map Pylint message types to our severity levels."""
        mapping = {
            'error': IssueSeverity.CRITICAL,
            'fatal': IssueSeverity.CRITICAL,
            'warning': IssueSeverity.HIGH,
            'refactor': IssueSeverity.MEDIUM,
            'convention': IssueSeverity.LOW,
            'info': IssueSeverity.INFO
        }
        return mapping.get(pylint_type.lower(), IssueSeverity.INFO)

class JavaScriptESLintAnalyzer(BaseStaticAnalyzer):
    """ESLint analyzer for JavaScript/TypeScript code."""

    def _setup_analyzer(self) -> None:
        """Setup ESLint-specific configuration."""
        self.supported_languages = {'javascript', 'typescript'}
        self.tool_command = ['eslint', '--format=json', '--no-eslintrc', '--config', '{}']

    def get_tool_name(self) -> str:
        return "eslint"

    async def _execute_analysis(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
        """Execute ESLint analysis."""
        extension = '.js' if language == 'javascript' else '.ts'
        with tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False) as temp_file:
            temp_file.write(content)
            temp_file.flush()

            try:
                # Create basic ESLint config
                config = {
                    "env": {"es6": True, "node": True},
                    "extends": ["eslint:recommended"],
                    "parserOptions": {"ecmaVersion": 2020, "sourceType": "module"}
                }

                if language == 'typescript':
                    config["parser"] = "@typescript-eslint/parser"
                    config["plugins"] = ["@typescript-eslint"]

                config_str = json.dumps(config)
                command = [cmd.replace('{}', config_str) if '{}' in cmd else cmd for cmd in self.tool_command]
                command.append(temp_file.name)

                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                return {
                    'output': stdout.decode('utf-8'),
                    'error': stderr.decode('utf-8'),
                    'return_code': process.returncode
                }
            finally:
                os.unlink(temp_file.name)

    def _parse_results(self, raw_output: str, language: str) -> List[AnalysisIssue]:
        """Parse ESLint JSON output."""
        issues = []
        try:
            if raw_output.strip():
                eslint_results = json.loads(raw_output)
                for file_result in eslint_results:
                    for message in file_result.get('messages', []):
                        severity = self._map_eslint_severity(message.get('severity', 1))
                        issues.append(AnalysisIssue(
                            file_path=file_result.get('filePath', ''),
                            line_number=message.get('line', 0),
                            column=message.get('column'),
                            severity=severity,
                            category=message.get('ruleId', 'unknown'),
                            message=message.get('message', ''),
                            rule_id=message.get('ruleId'),
                            suggestion=message.get('fix', {}).get('text') if message.get('fix') else None
                        ))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse ESLint output: {raw_output[:100]}...")

        return issues

    def _map_eslint_severity(self, eslint_severity: int) -> IssueSeverity:
        """Map ESLint severity levels to our severity levels."""
        mapping = {
            2: IssueSeverity.HIGH,    # Error
            1: IssueSeverity.MEDIUM,  # Warning
            0: IssueSeverity.INFO     # Off/Info
        }
        return mapping.get(eslint_severity, IssueSeverity.INFO)

# ============================================================================
# ANALYSIS ORCHESTRATOR (Single Responsibility + Dependency Inversion)
# ============================================================================

class StaticAnalysisOrchestrator:
    """Orchestrates static analysis across multiple tools and languages."""

    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.language_detector = FileExtensionLanguageDetector()
        self.analyzers: List[BaseStaticAnalyzer] = []
        self.state_tracker = AnalysisStateTracker()
        self._setup_analyzers()

    def _setup_analyzers(self) -> None:
        """Initialize available analyzers."""
        try:
            self.analyzers.append(PythonPylintAnalyzer(self.config))
        except Exception as e:
            logger.warning(f"Failed to initialize Pylint analyzer: {e}")

        try:
            self.analyzers.append(JavaScriptESLintAnalyzer(self.config))
        except Exception as e:
            logger.warning(f"Failed to initialize ESLint analyzer: {e}")

    def add_analyzer(self, analyzer: BaseStaticAnalyzer) -> None:
        """Add a custom analyzer (Open/Closed Principle)."""
        self.analyzers.append(analyzer)

    async def analyze_repository(self, repository_info: Dict[str, Any]) -> RepositoryAnalysisResult:
        """Analyze an entire repository."""
        analysis_id = self._generate_analysis_id(repository_info)
        repository_url = repository_info.get('url', 'unknown')

        logger.info(f"Starting repository analysis: {analysis_id}")

        # Initialize result structure
        result = RepositoryAnalysisResult(
            repository_url=repository_url,
            analysis_id=analysis_id,
            timestamp=datetime.now().isoformat()
        )

        # Track analysis start
        self.state_tracker.start_analysis(analysis_id, repository_info)

        try:
            # Get files from repository info
            files = self._extract_files_from_repository(repository_info)

            # Group files by language
            language_files = self._group_files_by_language(files)
            result.languages_detected = set(language_files.keys())

            # Analyze each language
            for language, file_list in language_files.items():
                logger.info(f"Analyzing {len(file_list)} {language} files")

                language_result = await self._analyze_language_files(
                    language, file_list, analysis_id
                )
                result.language_results[language] = language_result

            # Calculate overall metrics
            result.overall_metrics = self._calculate_overall_metrics(result)
            result.execution_summary = self.state_tracker.get_analysis_summary(analysis_id)

            # Track analysis completion
            self.state_tracker.complete_analysis(analysis_id, result)

            logger.info(f"Repository analysis completed: {analysis_id}")
            return result

        except Exception as e:
            logger.error(f"Repository analysis failed: {analysis_id}, error: {e}")
            self.state_tracker.fail_analysis(analysis_id, str(e))
            raise

    async def _analyze_language_files(
        self,
        language: str,
        files: List[Dict[str, Any]],
        analysis_id: str
    ) -> LanguageAnalysisResult:
        """Analyze files for a specific language."""
        language_result = LanguageAnalysisResult(
            language=language,
            file_count=len(files)
        )

        # Get applicable analyzers for this language
        applicable_analyzers = [
            analyzer for analyzer in self.analyzers
            if analyzer.supports_language(language)
        ]

        if not applicable_analyzers:
            logger.warning(f"No analyzers available for language: {language}")
            return language_result

        # Track language analysis start
        self.state_tracker.start_language_analysis(analysis_id, language, len(files))

        # Analyze with each applicable tool
        for analyzer in applicable_analyzers:
            tool_name = analyzer.get_tool_name()
            logger.info(f"Running {tool_name} analysis for {language}")

            # Track tool execution start
            self.state_tracker.start_tool_execution(analysis_id, language, tool_name)

            try:
                # Analyze all files with this tool
                tool_issues = []
                for file_info in files:
                    file_result = await analyzer.analyze(
                        file_info['path'],
                        file_info['content'],
                        language
                    )
                    tool_issues.extend(file_result.issues)

                # Create aggregated tool result
                tool_result = ToolAnalysisResult(
                    tool_name=tool_name,
                    language=language,
                    status=AnalysisStatus.SUCCESS,
                    issues=tool_issues,
                    metrics={'files_analyzed': len(files), 'total_issues': len(tool_issues)}
                )

                language_result.tool_results.append(tool_result)

                # Track tool execution completion
                self.state_tracker.complete_tool_execution(
                    analysis_id, language, tool_name, tool_result
                )

            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name} for {language}, error: {e}")

                # Create failed tool result
                failed_result = ToolAnalysisResult(
                    tool_name=tool_name,
                    language=language,
                    status=AnalysisStatus.FAILED,
                    error_message=str(e)
                )
                language_result.tool_results.append(failed_result)

                # Track tool execution failure
                self.state_tracker.fail_tool_execution(analysis_id, language, tool_name, str(e))

        # Calculate language-level metrics
        language_result.aggregated_metrics = self._calculate_language_metrics(language_result)
        language_result.total_issues = sum(len(tr.issues) for tr in language_result.tool_results)

        # Track language analysis completion
        self.state_tracker.complete_language_analysis(analysis_id, language, language_result)

        return language_result

    def _generate_analysis_id(self, repository_info: Dict[str, Any]) -> str:
        """Generate unique analysis ID."""
        repo_url = repository_info.get('url', 'unknown')
        timestamp = datetime.now().isoformat()
        content = f"{repo_url}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _extract_files_from_repository(self, repository_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract file information from repository data."""
        files = []
        repo_files = repository_info.get('files', [])

        for file_info in repo_files:
            if isinstance(file_info, dict):
                file_path = file_info.get('name', file_info.get('path', ''))
                if self.config.should_analyze_file(file_path):
                    files.append({
                        'path': file_path,
                        'content': file_info.get('content', ''),
                        'size': len(file_info.get('content', ''))
                    })

        return files

    def _group_files_by_language(self, files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group files by detected programming language."""
        language_files = {}

        for file_info in files:
            language = self.language_detector.detect_language(
                file_info['path'],
                file_info['content']
            )

            if language:
                if language not in language_files:
                    language_files[language] = []
                language_files[language].append(file_info)

        return language_files

    def _calculate_overall_metrics(self, result: RepositoryAnalysisResult) -> Dict[str, Any]:
        """Calculate repository-wide metrics."""
        total_files = sum(lr.file_count for lr in result.language_results.values())
        total_issues = sum(lr.total_issues for lr in result.language_results.values())

        languages_analyzed = len(result.language_results)
        tools_executed = sum(len(lr.tool_results) for lr in result.language_results.values())

        return {
            'total_files_analyzed': total_files,
            'total_issues_found': total_issues,
            'languages_analyzed': languages_analyzed,
            'tools_executed': tools_executed,
            'analysis_timestamp': datetime.now().isoformat()
        }

    def _calculate_language_metrics(self, language_result: LanguageAnalysisResult) -> Dict[str, Any]:
        """Calculate language-specific metrics."""
        total_issues = sum(len(tr.issues) for tr in language_result.tool_results)
        successful_tools = sum(1 for tr in language_result.tool_results if tr.status == AnalysisStatus.SUCCESS)

        return {
            'total_issues': total_issues,
            'successful_tools': successful_tools,
            'failed_tools': len(language_result.tool_results) - successful_tools,
            'files_analyzed': language_result.file_count
        }

# ============================================================================
# STATE TRACKING FOR DEBUGGING (Single Responsibility Principle)
# ============================================================================

class AnalysisStateTracker:
    """Tracks analysis execution state for debugging and monitoring."""

    def __init__(self):
        self.analysis_states: Dict[str, Dict[str, Any]] = {}
        self.execution_log: List[Dict[str, Any]] = []

    def start_analysis(self, analysis_id: str, repository_info: Dict[str, Any]) -> None:
        """Track analysis start."""
        self.analysis_states[analysis_id] = {
            'status': 'started',
            'repository_info': repository_info,
            'start_time': datetime.now().isoformat(),
            'languages': {},
            'tools': {},
            'events': []
        }
        self._log_event(analysis_id, 'analysis_started', {'repository_url': repository_info.get('url')})

    def start_language_analysis(self, analysis_id: str, language: str, file_count: int) -> None:
        """Track language analysis start."""
        if analysis_id in self.analysis_states:
            self.analysis_states[analysis_id]['languages'][language] = {
                'status': 'started',
                'file_count': file_count,
                'start_time': datetime.now().isoformat(),
                'tools': {}
            }
        self._log_event(analysis_id, 'language_analysis_started', {'language': language, 'files': file_count})

    def start_tool_execution(self, analysis_id: str, language: str, tool_name: str) -> None:
        """Track tool execution start."""
        if analysis_id in self.analysis_states:
            lang_state = self.analysis_states[analysis_id]['languages'].get(language, {})
            lang_state.setdefault('tools', {})[tool_name] = {
                'status': 'running',
                'start_time': datetime.now().isoformat()
            }
        self._log_event(analysis_id, 'tool_execution_started', {'language': language, 'tool': tool_name})

    def complete_tool_execution(
        self,
        analysis_id: str,
        language: str,
        tool_name: str,
        result: ToolAnalysisResult
    ) -> None:
        """Track tool execution completion."""
        if analysis_id in self.analysis_states:
            lang_state = self.analysis_states[analysis_id]['languages'].get(language, {})
            tool_state = lang_state.get('tools', {}).get(tool_name, {})
            tool_state.update({
                'status': 'completed',
                'end_time': datetime.now().isoformat(),
                'issues_found': len(result.issues),
                'execution_time': result.execution_time
            })
        self._log_event(analysis_id, 'tool_execution_completed', {
            'language': language,
            'tool': tool_name,
            'issues': len(result.issues)
        })

    def fail_tool_execution(self, analysis_id: str, language: str, tool_name: str, error: str) -> None:
        """Track tool execution failure."""
        if analysis_id in self.analysis_states:
            lang_state = self.analysis_states[analysis_id]['languages'].get(language, {})
            tool_state = lang_state.get('tools', {}).get(tool_name, {})
            tool_state.update({
                'status': 'failed',
                'end_time': datetime.now().isoformat(),
                'error': error
            })
        self._log_event(analysis_id, 'tool_execution_failed', {
            'language': language,
            'tool': tool_name,
            'error': error
        })

    def complete_language_analysis(
        self,
        analysis_id: str,
        language: str,
        result: LanguageAnalysisResult
    ) -> None:
        """Track language analysis completion."""
        if analysis_id in self.analysis_states:
            lang_state = self.analysis_states[analysis_id]['languages'].get(language, {})
            lang_state.update({
                'status': 'completed',
                'end_time': datetime.now().isoformat(),
                'total_issues': result.total_issues,
                'tools_executed': len(result.tool_results)
            })
        self._log_event(analysis_id, 'language_analysis_completed', {
            'language': language,
            'issues': result.total_issues
        })

    def complete_analysis(self, analysis_id: str, result: RepositoryAnalysisResult) -> None:
        """Track analysis completion."""
        if analysis_id in self.analysis_states:
            self.analysis_states[analysis_id].update({
                'status': 'completed',
                'end_time': datetime.now().isoformat(),
                'total_issues': result.overall_metrics.get('total_issues_found', 0),
                'languages_analyzed': len(result.language_results)
            })
        self._log_event(analysis_id, 'analysis_completed', {
            'total_issues': result.overall_metrics.get('total_issues_found', 0)
        })

    def fail_analysis(self, analysis_id: str, error: str) -> None:
        """Track analysis failure."""
        if analysis_id in self.analysis_states:
            self.analysis_states[analysis_id].update({
                'status': 'failed',
                'end_time': datetime.now().isoformat(),
                'error': error
            })
        self._log_event(analysis_id, 'analysis_failed', {'error': error})

    def get_analysis_summary(self, analysis_id: str) -> Dict[str, Any]:
        """Get analysis execution summary."""
        return self.analysis_states.get(analysis_id, {})

    def _log_event(self, analysis_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """Log an analysis event."""
        event = {
            'analysis_id': analysis_id,
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.execution_log.append(event)
        logger.debug(f"Analysis event: {event_type} for {analysis_id}")

# ============================================================================
# FACTORY FOR CREATING ANALYZERS (Factory Pattern)
# ============================================================================

class AnalyzerFactory:
    """Factory for creating static analysis tools."""

    @staticmethod
    def create_analyzer(tool_name: str, config: AnalysisConfig) -> Optional[BaseStaticAnalyzer]:
        """Create an analyzer by name."""
        analyzers = {
            'pylint': PythonPylintAnalyzer,
            'eslint': JavaScriptESLintAnalyzer,
        }

        analyzer_class = analyzers.get(tool_name.lower())
        if analyzer_class:
            try:
                return analyzer_class(config)
            except Exception as e:
                logger.error(f"Failed to create {tool_name} analyzer: {e}")
                return None

        logger.warning(f"Unknown analyzer: {tool_name}")
        return None

    @staticmethod
    def get_available_analyzers() -> List[str]:
        """Get list of available analyzer names."""
        return ['pylint', 'eslint']
