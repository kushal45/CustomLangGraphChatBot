from typing import TypedDict, List, Optional, Dict, Any, Union
from langchain_core.messages import BaseMessage
from enum import Enum


class ReviewStatus(Enum):
    """Status of the review process."""
    INITIALIZING = "initializing"
    FETCHING_REPOSITORY = "fetching_repository"
    ANALYZING_CODE = "analyzing_code"
    RUNNING_STATIC_ANALYSIS = "running_static_analysis"
    RUNNING_AI_ANALYSIS = "running_ai_analysis"
    GENERATING_REPORT = "generating_report"
    SENDING_NOTIFICATIONS = "sending_notifications"
    COMPLETED = "completed"
    FAILED = "failed"


class RepositoryInfo(TypedDict):
    """Information about the repository being analyzed."""
    url: str
    name: str
    full_name: str
    description: Optional[str]
    language: Optional[str]
    stars: int
    forks: int
    size: int
    default_branch: str
    topics: List[str]
    file_structure: List[Dict[str, Any]]
    recent_commits: List[Dict[str, Any]]


class ToolResult(TypedDict):
    """Result from a tool execution."""
    tool_name: str
    success: bool
    result: Dict[str, Any]
    error_message: Optional[str]
    execution_time: float
    timestamp: str


class AnalysisResults(TypedDict):
    """Comprehensive analysis results."""
    static_analysis: Dict[str, ToolResult]
    ai_analysis: Dict[str, ToolResult]
    security_analysis: Dict[str, ToolResult]
    complexity_analysis: Optional[ToolResult]
    overall_score: Optional[float]
    summary: Optional[str]
    recommendations: List[str]


class ReviewState(TypedDict):
    """Enhanced state for the code review workflow."""
    # Core workflow state
    messages: List[BaseMessage]
    current_step: str
    status: ReviewStatus
    error_message: Optional[str]

    # Repository information
    repository_url: str
    repository_info: Optional[RepositoryInfo]
    repository_type: Optional[str]

    # Tool execution tracking
    enabled_tools: List[str]
    tool_results: Dict[str, ToolResult]
    failed_tools: List[str]

    # Analysis results
    analysis_results: Optional[AnalysisResults]
    files_analyzed: List[str]
    total_files: int

    # Configuration and metadata
    review_config: Dict[str, Any]
    start_time: Optional[str]
    end_time: Optional[str]

    # Communication and reporting
    notifications_sent: List[Dict[str, Any]]
    report_generated: bool
    final_report: Optional[Dict[str, Any]]