from typing import Dict, Any, Optional, Protocol
from dataclasses import dataclass
from state import ReviewState, ReviewStatus
from logging_config import get_logger
from tools.registry import get_tool_registry
from debug.repository_debugging import repo_debugger
from debug.visual_flow_tracker import track_debug_flow, print_complete_debug_flow, FlowStage

logger = get_logger(__name__)

# ============================================================================
# SOLID PRINCIPLE IMPLEMENTATION: Dependency Inversion & Interface Segregation
# ============================================================================

class RepositoryValidator(Protocol):
    """Protocol for repository URL validation (Interface Segregation)."""
    def validate_url(self, url: Optional[str]) -> Dict[str, Any]:
        ...

class ToolRegistryProvider(Protocol):
    """Protocol for tool registry operations (Interface Segregation)."""
    def get_registry(self) -> Any:
        ...
    def get_github_tool(self, registry: Any) -> Optional[Any]:
        ...

class RepositoryFetcher(Protocol):
    """Protocol for repository data fetching (Interface Segregation)."""
    async def fetch_repository_data(self, tool: Any, url: str) -> Dict[str, Any]:
        ...

class RepositoryProcessor(Protocol):
    """Protocol for repository data processing (Interface Segregation)."""
    def process_repository_info(self, repo_result: Dict[str, Any]) -> Dict[str, Any]:
        ...

class ToolSelector(Protocol):
    """Protocol for tool selection (Interface Segregation)."""
    def select_tools(self, registry: Any, repository_info: Dict[str, Any]) -> Dict[str, Any]:
        ...

# ============================================================================
# SOLID PRINCIPLE IMPLEMENTATION: Single Responsibility Principle
# ============================================================================

@dataclass
class ValidationResult:
    """Value object for validation results."""
    is_valid: bool
    url: Optional[str] = None
    error_message: Optional[str] = None
    inspection_data: Optional[Dict[str, Any]] = None

@dataclass
class RepositoryData:
    """Value object for repository data."""
    success: bool
    repository_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    response_inspection: Optional[Dict[str, Any]] = None

@dataclass
class ToolSelectionResult:
    """Value object for tool selection results."""
    repository_type: str
    enabled_tools: list
    file_extensions: list
    total_files: int

class RepositoryUrlValidator:
    """Single responsibility: Validate repository URLs."""

    def validate_url(self, url: Optional[str]) -> ValidationResult:
        """Validate repository URL with comprehensive inspection."""
        track_debug_flow(
            "URL Validation Starting",
            FlowStage.URL_VALIDATION,
            {"repository_url": url},
            {"validation_step": "starting"},
            "IN_PROGRESS"
        )

        if not url:
            error_msg = "No repository URL provided in state"
            logger.error("Repository URL validation failed", extra={
                "error": error_msg,
                "validation_step": "url_presence_check"
            })

            track_debug_flow(
                "URL Validation Failed",
                FlowStage.ERROR_HANDLING,
                {"repository_url": url},
                {"error": error_msg, "validation_step": "repository_url"},
                "FAILED"
            )

            repo_debugger.debug_breakpoint(
                "url_validation_failure",
                {"repository_url": url},
                {"error": error_msg, "validation_step": "url_presence_check"}
            )

            return ValidationResult(
                is_valid=False,
                error_message=error_msg
            )

        # Perform URL inspection
        url_inspection = repo_debugger.inspect_repository_url(url)

        track_debug_flow(
            "URL Validation Success",
            FlowStage.URL_VALIDATION,
            {"repository_url": url},
            {"repository_url": url, "validation_result": "success"},
            "COMPLETED"
        )

        repo_debugger.debug_breakpoint(
            "url_validation_success",
            {"repository_url": url},
            {
                "repository_url": url,
                "url_inspection": url_inspection,
                "step": "Repository URL validated successfully"
            }
        )

        logger.info("Repository URL validation passed", extra={
            "repository_url": url,
            "validation_step": "url_inspection_complete"
        })

        return ValidationResult(
            is_valid=True,
            url=url,
            inspection_data=url_inspection
        )

class ToolRegistryManager:
    """Single responsibility: Manage tool registry operations."""

    def get_registry(self) -> Any:
        """Get tool registry instance."""
        logger.info("Initializing tool registry", extra={
            "step": "tool_registry_init"
        })

        registry = get_tool_registry()

        track_debug_flow(
            "Tool Registry Initialization",
            FlowStage.TOOL_REGISTRY,
            {"registry_status": "initialized"},
            {"available_tools": registry.get_tool_names(), "registry_status": "initialized"},
            "COMPLETED"
        )

        repo_debugger.debug_breakpoint(
            "tool_registry_init",
            {"registry_status": "initialized"},
            {
                "available_tools": registry.get_tool_names(),
                "step": "Tool registry initialized"
            }
        )

        return registry

    def get_github_tool(self, registry: Any) -> Optional[Any]:
        """Get GitHub repository tool from registry."""
        github_tool = registry.get_tool("github_repository")

        if not github_tool:
            error_msg = "GitHub repository tool not available"
            logger.error("GitHub tool availability check failed", extra={
                "error": error_msg,
                "available_tools": registry.get_tool_names()
            })

            repo_debugger.debug_breakpoint(
                "github_tool_unavailable",
                {"available_tools": registry.get_tool_names()},
                {
                    "error": error_msg,
                    "available_tools": registry.get_tool_names(),
                    "step": "GitHub repository tool not found"
                }
            )

            return None

        return github_tool

class RepositoryDataFetcher:
    """Single responsibility: Fetch repository data from GitHub."""

    async def fetch_repository_data(self, tool: Any, url: str) -> RepositoryData:
        """Fetch repository data using GitHub tool."""
        logger.info("Executing GitHub repository tool", extra={
            "step": "github_tool_execution",
            "tool_name": "github_repository",
            "repository_url": url
        })

        track_debug_flow(
            "GitHub API Call - Starting",
            FlowStage.GITHUB_API_CALL,
            {"repository_url": url},
            {"tool_name": "github_repository", "repository_url": url, "api_stage": "starting"},
            "IN_PROGRESS"
        )

        repo_debugger.debug_breakpoint(
            "before_github_api_call",
            {"repository_url": url},
            {
                "tool_name": "github_repository",
                "repository_url": url,
                "step": "About to execute GitHub repository tool"
            }
        )

        # Execute GitHub API call
        repo_result = await tool._arun(url)

        # Process API response
        api_success = repo_result.get("success", False)
        response_inspection = repo_debugger.inspect_github_response(repo_result)

        track_debug_flow(
            "GitHub API Call - Completed",
            FlowStage.GITHUB_API_CALL,
            {"repository_url": url},
            {
                "api_success": api_success,
                "api_stage": "completed",
                "has_result": "result" in repo_result
            },
            "COMPLETED" if api_success else "FAILED"
        )

        repo_debugger.debug_breakpoint(
            "after_github_api_call",
            {"repository_url": url},
            {
                "repo_result": repo_result,
                "response_inspection": response_inspection,
                "step": "GitHub repository tool execution completed"
            }
        )

        if not api_success:
            error_msg = f"Failed to fetch repository information: {repo_result.get('error_message', 'Unknown error')}"
            logger.error("Repository information fetch failed", extra={
                "error": error_msg,
                "github_result": repo_result
            })

            repo_debugger.debug_breakpoint(
                "repository_fetch_failure",
                {"repository_url": url},
                {
                    "error_msg": error_msg,
                    "repo_result": repo_result,
                    "response_inspection": response_inspection,
                    "step": "Repository information fetch failed"
                }
            )

            return RepositoryData(
                success=False,
                error_message=error_msg
            )

        repository_info = repo_result.get("result", {})

        return RepositoryData(
            success=True,
            repository_info=repository_info,
            response_inspection=response_inspection
        )

class RepositoryInfoProcessor:
    """Single responsibility: Process and analyze repository information."""

    def process_repository_info(self, repo_data: RepositoryData) -> Dict[str, Any]:
        """Process repository information and extract metadata."""
        repository_info = repo_data.repository_info

        # Inspect repository information quality
        repo_info_inspection = repo_debugger.inspect_repository_info(repository_info)

        track_debug_flow(
            "Repository Information Processing",
            FlowStage.DATA_PROCESSING,
            {"repository_info_keys": list(repository_info.keys()) if repository_info else []},
            {
                "repository_info": repository_info,
                "repo_info_inspection": repo_info_inspection,
                "step": "Repository information extracted and analyzed"
            },
            "COMPLETED"
        )

        repo_debugger.debug_breakpoint(
            "repository_info_extraction",
            {"repository_info": repository_info},
            {
                "repository_info": repository_info,
                "repo_info_inspection": repo_info_inspection,
                "step": "Repository information extracted and analyzed"
            }
        )

        logger.info("Repository information extracted successfully", extra={
            "step": "repository_info_extraction",
            "repo_name": repository_info.get("name") if repository_info else None,
            "repo_language": repository_info.get("language") if repository_info else None,
            "repo_size": repository_info.get("size") if repository_info else None,
            "repo_stars": repository_info.get("stars") if repository_info else None
        })

        return {
            "repository_info": repository_info,
            "repo_info_inspection": repo_info_inspection
        }

class RepositoryToolSelector:
    """Single responsibility: Select appropriate tools based on repository type."""

    def select_tools(self, registry: Any, repository_info: Dict[str, Any]) -> ToolSelectionResult:
        """Select tools based on repository characteristics."""
        # Extract file extensions for repository type detection
        file_extensions = []
        if repository_info and "files" in repository_info:
            for file_info in repository_info["files"]:
                if "name" in file_info and "." in file_info["name"]:
                    ext = file_info["name"].split(".")[-1]
                    if ext not in file_extensions:
                        file_extensions.append(f".{ext}")

        # Detect repository type and get enabled tools
        repository_type = registry.detect_repository_type(file_extensions)
        enabled_tools = registry.get_tools_for_repository(repository_type)
        tool_names = [tool.name for tool in enabled_tools]

        track_debug_flow(
            "Tool Selection",
            FlowStage.TOOL_SELECTION,
            {"repository_type": repository_type.value},
            {
                "repository_type": repository_type.value,
                "file_extensions": file_extensions[:10],
                "enabled_tools": tool_names,
                "enabled_tool_count": len(enabled_tools),
                "step": "Tool selection completed - ready for next step"
            },
            "COMPLETED"
        )

        repo_debugger.debug_breakpoint(
            "tool_selection_final",
            {"repository_type": repository_type.value},
            {
                "repository_type": repository_type.value,
                "file_extensions": file_extensions[:10],
                "enabled_tools": tool_names,
                "enabled_tool_count": len(enabled_tools),
                "step": "Tool selection completed - ready for next step"
            }
        )

        logger.info("Tools enabled for repository type", extra={
            "step": "tool_selection",
            "repository_type": repository_type.value,
            "enabled_tool_count": len(enabled_tools),
            "enabled_tools": tool_names
        })

        return ToolSelectionResult(
            repository_type=repository_type.value,
            enabled_tools=tool_names,
            file_extensions=file_extensions,
            total_files=len(file_extensions)
        )

# ============================================================================
# SOLID PRINCIPLE IMPLEMENTATION: Dependency Injection & Orchestration
# ============================================================================

class StartReviewOrchestrator:
    """
    Orchestrator class that coordinates the start review process.
    Follows Dependency Injection principle for testability and flexibility.
    """

    def __init__(
        self,
        url_validator: RepositoryValidator = None,
        tool_manager: ToolRegistryProvider = None,
        data_fetcher: RepositoryFetcher = None,
        info_processor: RepositoryProcessor = None,
        tool_selector: ToolSelector = None
    ):
        # Dependency Injection with sensible defaults (DIP)
        self.url_validator = url_validator or RepositoryUrlValidator()
        self.tool_manager = tool_manager or ToolRegistryManager()
        self.data_fetcher = data_fetcher or RepositoryDataFetcher()
        self.info_processor = info_processor or RepositoryInfoProcessor()
        self.tool_selector = tool_selector or RepositoryToolSelector()

    async def execute_start_review(self, state: ReviewState) -> Dict[str, Any]:
        """
        Execute the start review process using composed dependencies.
        Single responsibility: Orchestrate the workflow steps.
        """
        # Log initial state
        logger.info("Starting review process - INPUT STATE", extra={
            "workflow_step": "start_review",
            "state_keys": list(state.keys()) if state else [],
            "repository_url": state.get("repository_url"),
            "current_step": state.get("current_step"),
            "status": state.get("status")
        })

        try:
            # Initialize workflow tracking
            track_debug_flow(
                "Workflow Initialization",
                FlowStage.INITIALIZATION,
                state,
                {"step": "Starting start_review_node execution", "session_start": True},
                "IN_PROGRESS"
            )

            repo_debugger.debug_breakpoint(
                "initial_state_validation",
                state,
                {"step": "Validating initial state and repository URL"}
            )

            # Step 1: Validate repository URL (SRP)
            validation_result = self.url_validator.validate_url(state.get("repository_url"))
            if not validation_result.is_valid:
                return self._create_error_response(validation_result.error_message)

            # Step 2: Initialize tool registry (SRP)
            tool_registry = self.tool_manager.get_registry()
            github_tool = self.tool_manager.get_github_tool(tool_registry)
            if not github_tool:
                return self._create_error_response("GitHub repository tool not available")

            # Step 3: Fetch repository data (SRP)
            repo_data = await self.data_fetcher.fetch_repository_data(github_tool, validation_result.url)
            if not repo_data.success:
                return self._create_error_response(repo_data.error_message)

            # Step 4: Process repository information (SRP)
            processed_info = self.info_processor.process_repository_info(repo_data)

            # Step 5: Select appropriate tools (SRP)
            tool_selection = self.tool_selector.select_tools(tool_registry, repo_data.repository_info)

            # Step 6: Create final result
            return self._create_success_response(
                processed_info["repository_info"],
                tool_selection
            )

        except Exception as e:
            error_msg = f"Unexpected error in start_review_node: {str(e)}"
            logger.error("start_review_node execution failed", extra={
                "workflow_step": "start_review",
                "error": error_msg,
                "exception_type": type(e).__name__,
                "state_keys": list(state.keys()) if state else [],
                "repository_url": state.get("repository_url")
            })
            return self._create_error_response(error_msg)

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "current_step": "error_handler",
            "error_message": error_message,
            "status": ReviewStatus.FAILED
        }

    def _create_success_response(
        self,
        repository_info: Dict[str, Any],
        tool_selection: ToolSelectionResult
    ) -> Dict[str, Any]:
        """Create standardized success response."""
        result = {
            "current_step": "analyze_code",
            "status": ReviewStatus.FETCHING_REPOSITORY,
            "repository_info": repository_info,
            "repository_type": tool_selection.repository_type,
            "enabled_tools": tool_selection.enabled_tools,
            "total_files": tool_selection.total_files,
            "file_extensions": tool_selection.file_extensions[:10]
        }

        # Final workflow tracking
        track_debug_flow(
            "Workflow Completion",
            FlowStage.COMPLETION,
            result,
            {
                "workflow_completed": True,
                "next_step": "analyze_code",
                "repository_type": result.get("repository_type"),
                "enabled_tools_count": len(result.get("enabled_tools", []))
            },
            "COMPLETED"
        )

        repo_debugger.debug_breakpoint(
            "final_success_state",
            result,
            {
                "workflow_completed": True,
                "next_step": "analyze_code",
                "debug_session_summary": f"Session {repo_debugger.debug_session_id} completed successfully",
                "step": "start_review_node completed successfully"
            }
        )

        logger.info("Review process started successfully - OUTPUT RESULT", extra={
            "workflow_step": "start_review",
            "result_keys": list(result.keys()),
            "next_step": result.get("current_step"),
            "repository_type": result.get("repository_type"),
            "enabled_tools_count": len(result.get("enabled_tools", [])),
            "total_files": result.get("total_files")
        })

        # Print comprehensive debugging summaries
        print("\n" + "="*80)
        print("🔍 DEBUGGING SESSION COMPLETE")
        print("="*80)

        repo_debugger.print_debug_summary()
        print_complete_debug_flow()

        return result

# ============================================================================
# SOLID PRINCIPLE IMPLEMENTATION: Main Entry Point with Dependency Injection
# ============================================================================

async def start_review_node(state: ReviewState) -> Dict[str, Any]:
    """
    SOLID-compliant start review process entry point.

    This function now follows SOLID principles:
    - Single Responsibility: Only orchestrates the workflow
    - Open/Closed: Extensible through dependency injection
    - Liskov Substitution: Uses protocols for type safety
    - Interface Segregation: Small, focused interfaces
    - Dependency Inversion: Depends on abstractions, not concretions
    """
    orchestrator = StartReviewOrchestrator()
    return await orchestrator.execute_start_review(state)



async def analyze_code_node(state: ReviewState) -> Dict[str, Any]:
    """
    Analyze the repository code using language-agnostic static analysis tools.

    This node performs comprehensive code analysis including:
    - Language-agnostic static analysis (Pylint, ESLint, etc.)
    - Code quality metrics across multiple languages
    - Security vulnerability detection
    - Architecture and maintainability analysis
    - Comprehensive state tracking and debugging

    The implementation follows SOLID principles and supports extensibility
    for new programming languages and analysis tools.

    Args:
        state: Current review state containing repository information

    Returns:
        Updated state with comprehensive analysis results
    """
    from tools.static_analysis_integration import analyze_repository_with_static_analysis
    from debug.repository_debugging import repo_debugger

    logger.info("Starting language-agnostic code analysis", extra={
        "workflow_step": "analyze_code",
        "current_step": state.get("current_step"),
        "state_keys": list(state.keys()) if state else [],
        "repository_url": state.get("repository_url", ""),
        "analysis_type": "language_agnostic_static_analysis"
    })

    # 🔍 DEBUG BREAKPOINT: Analysis Start
    repo_debugger.debug_breakpoint(
        "code_analysis_start",
        state,
        {
            "step": "Starting comprehensive static analysis",
            "repository_url": state.get("repository_url", ""),
            "repository_files": len((state.get("repository_info") or {}).get("files", [])),
            "analysis_type": "language_agnostic_static_analysis"
        }
    )

    try:
        # Get repository information for validation
        repository_info = state.get("repository_info", {})
        repository_url = state.get("repository_url", "")

        # 🔍 DEBUG BREAKPOINT: Repository Info Validation
        repo_debugger.debug_breakpoint(
            "repository_validation",
            state,
            {
                "step": "Validating repository information for analysis",
                "repository_url": repository_url,
                "has_repository_info": bool(repository_info),
                "file_count": len(repository_info.get("files", [])),
                "repository_language": repository_info.get("language", "unknown")
            }
        )

        # Validate that we have repository information
        if not repository_info or not repository_info.get("files"):
            error_msg = "No repository information or files available for analysis"
            logger.error(error_msg, extra={
                "workflow_step": "analyze_code",
                "error": error_msg,
                "repository_info_available": bool(repository_info)
            })

            # 🔍 DEBUG BREAKPOINT: Validation Error
            repo_debugger.debug_breakpoint(
                "validation_error",
                state,
                {
                    "step": "Repository validation failed",
                    "error": error_msg,
                    "repository_info_keys": list(repository_info.keys()) if repository_info else []
                }
            )

            return {
                "current_step": "error_handler",
                "error": error_msg,
                "error_type": "validation_error"
            }

        # 🔍 DEBUG BREAKPOINT: Before Static Analysis
        repo_debugger.debug_breakpoint(
            "before_static_analysis",
            state,
            {
                "step": "Initiating language-agnostic static analysis",
                "files_to_analyze": len(repository_info.get("files", [])),
                "analysis_framework": "static_analysis_framework",
                "integration_layer": "static_analysis_integration"
            }
        )

        # Execute comprehensive static analysis using our language-agnostic framework
        logger.info("Executing language-agnostic static analysis...", extra={
            "workflow_step": "analyze_code",
            "files_count": len(repository_info.get("files", [])),
            "repository_language": repository_info.get("language", "unknown")
        })

        updated_state = await analyze_repository_with_static_analysis(state)

        # 🔍 DEBUG BREAKPOINT: After Static Analysis
        repo_debugger.debug_breakpoint(
            "after_static_analysis",
            updated_state,
            {
                "step": "Static analysis completed",
                "analysis_successful": "analysis_results" in updated_state,
                "next_step": updated_state.get("current_step", "unknown"),
                "total_issues": updated_state.get("analysis_results", {}).get("static_analysis", {}).get("summary", {}).get("total_issues", 0),
                "languages_analyzed": updated_state.get("analysis_results", {}).get("static_analysis", {}).get("summary", {}).get("languages_analyzed", 0)
            }
        )

        # Check if analysis was successful
        if updated_state.get("current_step") == "error_handler":
            logger.error("Static analysis failed", extra={
                "workflow_step": "analyze_code",
                "error": updated_state.get("error", {}).get("message", "Unknown error")
            })
            return updated_state

        # Extract results for logging
        analysis_summary = updated_state.get("analysis_results", {}).get("static_analysis", {}).get("summary", {})

        # 🔍 DEBUG BREAKPOINT: Analysis Success
        repo_debugger.debug_breakpoint(
            "analysis_success",
            updated_state,
            {
                "step": "Code analysis completed successfully",
                "analysis_summary": analysis_summary,
                "next_step": updated_state.get("current_step"),
                "status": updated_state.get("status")
            }
        )

        logger.info("Language-agnostic code analysis completed successfully", extra={
            "workflow_step": "analyze_code",
            "total_issues": analysis_summary.get("total_issues", 0),
            "languages_analyzed": analysis_summary.get("languages_analyzed", 0),
            "tools_executed": analysis_summary.get("tools_executed", 0),
            "next_step": updated_state.get("current_step")
        })

        # ====================================================================
        # AI Code Review
        # ====================================================================
        logger.info("Starting AI code review", extra={"workflow_step": "analyze_code"})

        from tools.ai_analysis_tools import code_review_tool
        from tools.github_tools import github_file_content_tool
        import json

        ai_analysis_results = {}
        files_to_analyze = []
        if repository_info and "contents" in repository_info:
            for file_info in repository_info["contents"]:
                if file_info["type"] == "file" and file_info["name"].endswith(".py"): # Simple filter for now
                    files_to_analyze.append(file_info["path"])

        for file_path in files_to_analyze:
            logger.info(f"Analyzing file with AI: {file_path}", extra={"workflow_step": "analyze_code"})

            # Fetch file content
            file_content_query = json.dumps({
                "repository_url": repository_url,
                "file_path": file_path
            })
            file_content_result = await github_file_content_tool._arun(file_content_query)

            if "error" in file_content_result:
                logger.error(f"Failed to fetch content for {file_path}: {file_content_result['error']}", extra={"workflow_step": "analyze_code"})
                continue

            file_content = file_content_result.get("content", "")
            if not file_content:
                logger.warning(f"File content is empty for {file_path}", extra={"workflow_step": "analyze_code"})
                continue

            # Perform AI code review
            ai_review_query = json.dumps({
                "code": file_content,
                "language": "python" # Should be dynamic
            })
            review_result = await code_review_tool._arun(ai_review_query)
            ai_analysis_results[file_path] = review_result

        # Update state with AI analysis results
        if "analysis_results" not in updated_state:
            updated_state["analysis_results"] = {}
        if "ai_analysis" not in updated_state["analysis_results"]:
            updated_state["analysis_results"]["ai_analysis"] = {}
        updated_state["analysis_results"]["ai_analysis"] = ai_analysis_results
        logger.info("AI code review completed", extra={"workflow_step": "analyze_code", "files_analyzed": len(ai_analysis_results)})


        # Return the result in the expected format
        result = {
            "current_step": updated_state.get("current_step", "generate_report"),
            "analysis_results": updated_state.get("analysis_results", {}),
            "analysis_metadata": updated_state.get("analysis_metadata", {}),
            "status": updated_state.get("status", "analyzing_code")
        }

        return result

    except Exception as e:
        error_msg = f"Code analysis failed: {str(e)}"
        logger.error(error_msg, extra={
            "workflow_step": "analyze_code",
            "error": error_msg,
            "exception_type": type(e).__name__,
            "repository_url": state.get("repository_url", "")
        })

        # 🔍 DEBUG BREAKPOINT: Analysis Error
        repo_debugger.debug_breakpoint(
            "analysis_error",
            state,
            {
                "step": "Code analysis failed with exception",
                "error": error_msg,
                "exception_type": type(e).__name__,
                "repository_url": state.get("repository_url", "")
            }
        )

        return {
            "current_step": "error_handler",
            "error": error_msg,
            "error_type": "analysis_exception"
        }

async def generate_report_node(state: ReviewState) -> Dict[str, Any]:
    """Generate a code review report."""
    logger.info("Starting report generation", extra={
        "workflow_step": "generate_report",
        "current_step": state.get("current_step"),
        "state_keys": list(state.keys()) if state else []
    })

    from tools.ai_analysis_tools import code_review_tool
    import json

    analysis_results = state.get("analysis_results", {})
    static_analysis = analysis_results.get("static_analysis", {})
    ai_analysis = analysis_results.get("ai_analysis", {})

    # 1. Format the results into a single string
    report_content = "## Code Review Report\n\n"

    report_content += "### Static Analysis Summary\n"
    if static_analysis and static_analysis.get("summary"):
        summary = static_analysis["summary"]
        report_content += f"- Total Issues: {summary.get('total_issues', 0)}\n"
        report_content += f"- Issues by Severity: {summary.get('issues_by_severity', {})}\n"

    report_content += "\n### AI Analysis Summary\n"
    if ai_analysis:
        for file_path, review in ai_analysis.items():
            report_content += f"#### File: {file_path}\n"
            if "review" in review:
                review_data = review["review"]
                report_content += f"- Overall Score: {review_data.get('overall_score', 'N/A')}\n"
                report_content += f"- Summary: {review_data.get('summary', 'N/A')}\n"
                if "issues" in review_data:
                    report_content += "- Issues:\n"
                    for issue in review_data["issues"]:
                        report_content += f"  - [{issue.get('severity')}] {issue.get('description')} (Suggestion: {issue.get('suggestion')})\n"

    # 2. Use an AI tool to generate a summary
    summary_prompt = f"""
    Based on the following code analysis report, please provide a high-level summary.
    Focus on the most critical issues and provide actionable recommendations.

    Report:
    {report_content}
    """

    ai_summary_query = json.dumps({
        "code": "", # No code, just context
        "context": summary_prompt
    })

    summary_result = await code_review_tool._arun(ai_summary_query)

    final_report = {
        "summary": summary_result.get("review", {}).get("summary", "Could not generate summary."),
        "details": analysis_results
    }

    logger.info("Report generation completed", extra={
        "workflow_step": "generate_report"
    })

    return {
        "current_step": "complete",
        "status": ReviewStatus.COMPLETED,
        "final_report": final_report,
        "report_generated": True
    }

async def error_handler_node(state: ReviewState) -> Dict[str, Any]:
    """Handle errors in the workflow."""
    error_message = state.get("error_message", "Unknown error occurred")
    logger.error("Workflow error occurred", extra={
        "workflow_step": "error_handler",
        "error_message": error_message,
        "state_keys": list(state.keys()) if state else [],
        "current_step": state.get("current_step")
    })
    result = {"current_step": "error_handled", "error_handled": True}
    logger.info("Error handled successfully", extra={
        "workflow_step": "error_handler",
        "result": result
    })
    return result