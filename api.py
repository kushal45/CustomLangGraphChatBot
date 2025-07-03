from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Any, Dict
from workflow import create_review_workflow
from state import ReviewState
import asyncio
import time
import uuid
from fastapi.middleware.cors import CORSMiddleware
from logging_config import get_logger, initialize_logging
from monitoring import monitoring
from error_tracking import error_tracker

# Initialize logging
initialize_logging()
logger = get_logger(__name__)

app = FastAPI(title="CustomLangGraphChatBot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses."""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Log request
    logger.info("HTTP request received", extra={
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "content_type": request.headers.get("content-type")
    })

    try:
        # Track active requests
        monitoring.system_metrics.active_requests += 1
        monitoring.system_metrics.peak_active_requests = max(
            monitoring.system_metrics.peak_active_requests,
            monitoring.system_metrics.active_requests
        )

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        logger.info("HTTP response sent", extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time_seconds": round(process_time, 4),
            "response_size": response.headers.get("content-length")
        })

        # Record metrics
        monitoring.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time=process_time,
            client_ip=request.client.host if request.client else None
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        process_time = time.time() - start_time
        error_type = type(e).__name__

        logger.error("HTTP request failed", extra={
            "request_id": request_id,
            "error": str(e),
            "error_type": error_type,
            "process_time_seconds": round(process_time, 4)
        }, exc_info=True)

        # Record error metrics
        monitoring.record_api_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=500,  # Internal server error
            response_time=process_time,
            client_ip=request.client.host if request.client else None,
            error_type=error_type
        )

        # Track error for alerting and analysis
        error_tracker.track_error(
            error_type=error_type,
            error_message=str(e),
            source=f"api.{request.url.path}",
            context={
                "request_id": request_id,
                "method": request.method,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
                "process_time_seconds": round(process_time, 4)
            }
        )

        raise
    finally:
        # Decrease active requests counter
        monitoring.system_metrics.active_requests -= 1

class ReviewRequest(BaseModel):
    repository_url: str

class ReviewResponse(BaseModel):
    report: Dict[str, Any]

@app.post("/review", response_model=ReviewResponse)
async def review_endpoint(request: ReviewRequest):
    """Execute code review workflow for a given repository."""
    request_id = str(uuid.uuid4())

    logger.info("Code review request started", extra={
        "request_id": request_id,
        "repository_url": request.repository_url,
        "endpoint": "/review"
    })

    try:
        # Initialize state
        logger.debug("Initializing workflow state", extra={
            "request_id": request_id,
            "repository_url": request.repository_url
        })

        from state import ReviewStatus

        state = ReviewState(
            messages=[],
            current_step="start_review",
            status=ReviewStatus.INITIALIZING,
            error_message=None,
            repository_url=request.repository_url,
            repository_info=None,
            repository_type=None,
            enabled_tools=[],
            tool_results={},
            failed_tools=[],
            analysis_results=None,
            files_analyzed=[],
            total_files=0,
            review_config={},
            start_time=None,
            end_time=None,
            notifications_sent=[],
            report_generated=False,
            final_report=None
        )

        # Create workflow
        logger.debug("Creating workflow", extra={"request_id": request_id})
        workflow_graph = create_review_workflow()

        # Compile the workflow graph
        logger.debug("Compiling workflow", extra={"request_id": request_id})
        workflow = workflow_graph.compile()

        # Run workflow asynchronously and get the final state
        logger.info("Starting workflow execution", extra={
            "request_id": request_id,
            "initial_state": state.get("current_step")
        })

        start_time = time.time()
        final_state = await workflow.ainvoke(state)
        execution_time = time.time() - start_time

        logger.info("Workflow execution completed", extra={
            "request_id": request_id,
            "execution_time_seconds": round(execution_time, 4),
            "final_step": final_state.get("current_step"),
            "has_results": bool(final_state.get("analysis_results")),
            "has_error": bool(final_state.get("error_message"))
        })

        # Return the analysis results from the final state
        result = {"report": final_state.get("analysis_results", {})}

        logger.info("Code review request completed successfully", extra={
            "request_id": request_id,
            "result_keys": list(result["report"].keys()) if result["report"] else []
        })

        return result

    except Exception as e:
        logger.error("Code review request failed", extra={
            "request_id": request_id,
            "repository_url": request.repository_url,
            "error": str(e),
            "error_type": type(e).__name__
        }, exc_info=True)

        raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with system status."""
    logger.debug("Health check requested")
    health_status = monitoring.get_health_status()

    return {
        "status": health_status["status"],
        "timestamp": time.time(),
        "service": "CustomLangGraphChatBot API",
        "error_rate": health_status["error_rate"],
        "uptime_seconds": health_status["uptime_seconds"],
        "total_requests": health_status["total_requests"],
        "active_requests": health_status["active_requests"]
    }


@app.get("/metrics")
async def get_metrics():
    """Get comprehensive system metrics."""
    logger.debug("Metrics endpoint accessed")

    return {
        "system": monitoring.get_system_metrics_summary(),
        "api": monitoring.get_api_metrics_summary(),
        "tools": monitoring.get_tool_metrics_summary(),
        "timestamp": time.time()
    }


@app.get("/metrics/api")
async def get_api_metrics():
    """Get API-specific metrics."""
    logger.debug("API metrics endpoint accessed")
    return monitoring.get_api_metrics_summary()


@app.get("/metrics/tools")
async def get_tool_metrics():
    """Get tool execution metrics."""
    logger.debug("Tool metrics endpoint accessed")
    return monitoring.get_tool_metrics_summary()


@app.get("/metrics/system")
async def get_system_metrics():
    """Get system-wide metrics."""
    logger.debug("System metrics endpoint accessed")
    return monitoring.get_system_metrics_summary()


@app.get("/events/recent")
async def get_recent_events(limit: int = 100):
    """Get recent system events."""
    logger.debug("Recent events endpoint accessed", extra={"limit": limit})
    return {
        "events": monitoring.get_recent_events(limit),
        "timestamp": time.time()
    }


@app.get("/errors/summary")
async def get_error_summary(hours: int = 24):
    """Get error summary for the specified time period."""
    logger.debug("Error summary endpoint accessed", extra={"hours": hours})
    return {
        "summary": error_tracker.get_error_summary(hours),
        "timestamp": time.time()
    }


@app.get("/errors/patterns")
async def get_error_patterns(min_count: int = 3):
    """Get error patterns."""
    logger.debug("Error patterns endpoint accessed", extra={"min_count": min_count})
    return {
        "patterns": error_tracker.get_error_patterns(min_count),
        "timestamp": time.time()
    }


@app.get("/errors/recent")
async def get_recent_errors(limit: int = 100, severity: str = None):
    """Get recent errors."""
    logger.debug("Recent errors endpoint accessed", extra={"limit": limit, "severity": severity})

    # Convert severity string to enum if provided
    severity_enum = None
    if severity:
        try:
            from error_tracking import ErrorSeverity
            severity_enum = ErrorSeverity(severity.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    return {
        "errors": error_tracker.get_recent_errors(limit, severity_enum),
        "timestamp": time.time()
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    logger.debug("Root endpoint accessed")
    return {
        "message": "CustomLangGraphChatBot API",
        "version": "1.0.0",
        "endpoints": {
            "review": "/review",
            "health": "/health",
            "metrics": "/metrics",
            "api_metrics": "/metrics/api",
            "tool_metrics": "/metrics/tools",
            "system_metrics": "/metrics/system",
            "recent_events": "/events/recent",
            "error_summary": "/errors/summary",
            "error_patterns": "/errors/patterns",
            "recent_errors": "/errors/recent",
            "docs": "/docs"
        }
    }