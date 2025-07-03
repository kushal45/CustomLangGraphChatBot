"""
Logging utilities for tools in CustomLangGraphChatBot.

This module provides:
- Logging decorators for tool execution
- Base logging functionality for all tools
- Performance monitoring and error tracking
- Structured logging for tool operations
"""

import time
import functools
import json
from typing import Any, Dict, Optional, Callable
from logging_config import get_logger
from monitoring import monitoring
from error_tracking import error_tracker


def log_tool_execution(func: Callable) -> Callable:
    """
    Decorator to log tool execution with performance metrics and error handling.
    
    This decorator automatically logs:
    - Tool execution start/end
    - Input parameters (sanitized)
    - Execution time
    - Success/failure status
    - Error details if execution fails
    - Result summary
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        # Get logger for the tool
        logger = get_logger(f"tools.{self.__class__.__name__}")
        
        # Extract tool name and input
        tool_name = getattr(self, 'name', self.__class__.__name__)
        input_data = args[0] if args else kwargs.get('query', kwargs.get('code', 'No input'))
        
        # Sanitize input for logging (truncate if too long)
        sanitized_input = _sanitize_input_for_logging(input_data)
        
        # Generate execution ID for tracking
        execution_id = f"{tool_name}_{int(time.time() * 1000)}"
        
        # Log execution start
        logger.info(f"Tool execution started", extra={
            "tool_name": tool_name,
            "execution_id": execution_id,
            "input_type": type(input_data).__name__,
            "input_size": len(str(input_data)) if input_data else 0,
            "input_preview": sanitized_input,
            "function": func.__name__
        })
        
        start_time = time.time()
        
        try:
            # Execute the tool
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time
            
            # Analyze result
            result_summary = _analyze_result(result)
            
            # Log successful execution
            logger.info(f"Tool execution completed successfully", extra={
                "tool_name": tool_name,
                "execution_id": execution_id,
                "execution_time_seconds": round(execution_time, 4),
                "result_type": type(result).__name__,
                "result_summary": result_summary,
                "success": True
            })

            # Record monitoring metrics
            monitoring.record_tool_execution(
                tool_name=tool_name,
                execution_time=execution_time,
                success=True
            )

            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log execution failure
            error_type = type(e).__name__
            error_message = str(e)

            logger.error(f"Tool execution failed", extra={
                "tool_name": tool_name,
                "execution_id": execution_id,
                "execution_time_seconds": round(execution_time, 4),
                "error_type": error_type,
                "error_message": error_message,
                "success": False
            }, exc_info=True)

            # Record monitoring metrics
            monitoring.record_tool_execution(
                tool_name=tool_name,
                execution_time=execution_time,
                success=False,
                error_type=error_type
            )

            # Track error for alerting and analysis
            error_tracker.track_error(
                error_type=error_type,
                error_message=error_message,
                source=f"tools.{tool_name}",
                context={
                    "execution_id": execution_id,
                    "execution_time_seconds": round(execution_time, 4),
                    "input_preview": _sanitize_input_for_logging(str(input_data)[:200]) if input_data else None
                },
                stack_trace=None  # Could add stack trace if needed
            )

            # Re-raise the exception
            raise
    
    return wrapper


def log_api_call(provider: str = "unknown", log_request_body: bool = False, log_response_body: bool = False):
    """
    Enhanced decorator to log API calls with detailed request/response information.

    Args:
        provider: Name of the API provider (e.g., "github", "groq", "openai")
        log_request_body: Whether to log request body (be careful with sensitive data)
        log_response_body: Whether to log response body (be careful with large responses)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            logger = get_logger(f"tools.api.{provider}")

            # Generate API call ID for correlation
            api_call_id = f"{provider}_{int(time.time() * 1000)}_{id(self)}"

            # Extract request details
            url = kwargs.get('url', args[0] if args else 'unknown')
            method = kwargs.get('method', 'GET')
            headers = kwargs.get('headers', {})
            params = kwargs.get('params', {})
            data = kwargs.get('data', kwargs.get('json', {}))

            # Prepare request logging data
            request_log_data = {
                "provider": provider,
                "api_call_id": api_call_id,
                "method": method,
                "url": _sanitize_url_for_logging(url),
                "function": func.__name__,
                "has_headers": bool(headers),
                "has_params": bool(params),
                "has_data": bool(data)
            }

            # Add request body if requested (sanitized)
            if log_request_body and data:
                request_log_data["request_body_preview"] = _sanitize_input_for_logging(str(data)[:500])
                request_log_data["request_body_size"] = len(str(data))

            # Log API call start
            logger.info(f"API call started", extra=request_log_data)

            start_time = time.time()

            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time

                # Prepare response logging data
                response_log_data = {
                    "provider": provider,
                    "api_call_id": api_call_id,
                    "execution_time_seconds": round(execution_time, 4),
                    "response_type": type(result).__name__,
                    "success": True
                }

                # Add response analysis
                if isinstance(result, dict):
                    response_log_data["response_keys"] = list(result.keys())[:10]  # First 10 keys
                    response_log_data["response_size"] = len(str(result))

                    # Add response body if requested (sanitized)
                    if log_response_body:
                        response_log_data["response_body_preview"] = str(result)[:500]

                elif isinstance(result, (list, tuple)):
                    response_log_data["response_length"] = len(result)
                    response_log_data["response_size"] = len(str(result))

                elif isinstance(result, str):
                    response_log_data["response_length"] = len(result)
                    if log_response_body:
                        response_log_data["response_body_preview"] = result[:500]

                # Log successful API call
                logger.info(f"API call completed successfully", extra=response_log_data)

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # Enhanced error logging
                error_log_data = {
                    "provider": provider,
                    "api_call_id": api_call_id,
                    "execution_time_seconds": round(execution_time, 4),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "success": False
                }

                # Add HTTP-specific error details if available
                if hasattr(e, 'response'):
                    error_log_data["http_status_code"] = getattr(e.response, 'status_code', None)
                    error_log_data["http_reason"] = getattr(e.response, 'reason', None)

                # Log API call failure
                logger.error(f"API call failed", extra=error_log_data, exc_info=True)

                raise

        return wrapper
    return decorator


def log_github_api_call(func: Callable) -> Callable:
    """Specialized decorator for GitHub API calls with rate limiting tracking."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        logger = get_logger("tools.api.github")

        # Generate GitHub API call ID
        api_call_id = f"github_{int(time.time() * 1000)}_{id(self)}"

        # Extract GitHub-specific details
        url = kwargs.get('url', args[0] if args else 'unknown')
        headers = kwargs.get('headers', {})

        # Log GitHub API call with rate limiting info
        logger.info("GitHub API call started", extra={
            "provider": "github",
            "api_call_id": api_call_id,
            "url": _sanitize_url_for_logging(url),
            "function": func.__name__,
            "has_auth": "Authorization" in headers
        })

        start_time = time.time()

        try:
            result = func(self, *args, **kwargs)
            execution_time = time.time() - start_time

            # Extract rate limiting info if available
            rate_limit_info = {}
            if hasattr(result, 'headers'):
                rate_limit_info = {
                    "rate_limit_remaining": result.headers.get('X-RateLimit-Remaining'),
                    "rate_limit_reset": result.headers.get('X-RateLimit-Reset'),
                    "rate_limit_used": result.headers.get('X-RateLimit-Used')
                }

            logger.info("GitHub API call completed", extra={
                "provider": "github",
                "api_call_id": api_call_id,
                "execution_time_seconds": round(execution_time, 4),
                "success": True,
                **rate_limit_info
            })

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # Enhanced GitHub error logging
            error_data = {
                "provider": "github",
                "api_call_id": api_call_id,
                "execution_time_seconds": round(execution_time, 4),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "success": False
            }

            # Add GitHub-specific error details
            if hasattr(e, 'response') and e.response:
                error_data["github_status_code"] = e.response.status_code
                error_data["github_message"] = e.response.text[:200] if hasattr(e.response, 'text') else None

            logger.error("GitHub API call failed", extra=error_data, exc_info=True)
            raise

    return wrapper


def log_ai_api_call(provider: str):
    """Specialized decorator for AI provider API calls with token usage tracking."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            logger = get_logger(f"tools.api.ai.{provider}")

            # Generate AI API call ID
            api_call_id = f"ai_{provider}_{int(time.time() * 1000)}_{id(self)}"

            # Extract AI-specific details
            prompt = kwargs.get('prompt', args[0] if args else '')
            model = getattr(self, 'model', 'unknown') if hasattr(self, 'model') else 'unknown'

            logger.info(f"AI API call started", extra={
                "provider": provider,
                "api_call_id": api_call_id,
                "function": func.__name__,
                "model": model,
                "prompt_length": len(str(prompt)),
                "prompt_preview": str(prompt)[:100] if prompt else None
            })

            start_time = time.time()

            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time

                # Extract AI-specific response details
                response_data = {
                    "provider": provider,
                    "api_call_id": api_call_id,
                    "execution_time_seconds": round(execution_time, 4),
                    "model": model,
                    "success": True
                }

                # Add response analysis
                if isinstance(result, str):
                    response_data["response_length"] = len(result)
                    response_data["response_preview"] = result[:200]
                elif isinstance(result, dict):
                    response_data["response_keys"] = list(result.keys())
                    if 'usage' in result:
                        response_data["token_usage"] = result['usage']

                logger.info(f"AI API call completed", extra=response_data)

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.error(f"AI API call failed", extra={
                    "provider": provider,
                    "api_call_id": api_call_id,
                    "execution_time_seconds": round(execution_time, 4),
                    "model": model,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "success": False
                }, exc_info=True)

                raise

        return wrapper
    return decorator


def _sanitize_input_for_logging(input_data: Any) -> str:
    """
    Sanitize input data for logging by truncating and removing sensitive information.
    
    Args:
        input_data: Input data to sanitize
        
    Returns:
        Sanitized string representation of input
    """
    if input_data is None:
        return "None"
    
    # Convert to string
    input_str = str(input_data)
    
    # Truncate if too long
    max_length = 200
    if len(input_str) > max_length:
        input_str = input_str[:max_length] + "... (truncated)"
    
    # Remove potential sensitive information
    sensitive_patterns = [
        "token", "key", "password", "secret", "auth", "credential"
    ]
    
    # Simple sanitization - replace potential sensitive values
    for pattern in sensitive_patterns:
        if pattern.lower() in input_str.lower():
            # This is a basic approach - in production, use more sophisticated sanitization
            input_str = input_str.replace(pattern, "[REDACTED]")
    
    return input_str


def _sanitize_url_for_logging(url: str) -> str:
    """
    Sanitize URL for logging by removing query parameters that might contain sensitive data.
    
    Args:
        url: URL to sanitize
        
    Returns:
        Sanitized URL
    """
    if not isinstance(url, str):
        return str(url)
    
    # Remove query parameters that might contain tokens
    if '?' in url:
        base_url = url.split('?')[0]
        return f"{base_url}?[QUERY_PARAMS_REDACTED]"
    
    return url


def _analyze_result(result: Any) -> Dict[str, Any]:
    """
    Analyze tool execution result to create a summary for logging.
    
    Args:
        result: Tool execution result
        
    Returns:
        Dictionary with result analysis
    """
    summary = {
        "type": type(result).__name__,
        "size": len(str(result)) if result else 0
    }
    
    if isinstance(result, dict):
        summary.update({
            "keys": list(result.keys())[:10],  # First 10 keys
            "has_error": "error" in result,
            "has_data": any(key not in ["error", "warning"] for key in result.keys()) if result else False
        })
        
        # Check for specific result patterns
        if "error" in result:
            summary["error_type"] = "tool_error"
        elif "issues" in result:
            summary["issues_count"] = len(result.get("issues", []))
        elif "functions" in result:
            summary["functions_count"] = len(result.get("functions", []))
    
    elif isinstance(result, list):
        summary.update({
            "length": len(result),
            "item_types": list(set(type(item).__name__ for item in result[:5]))  # Types of first 5 items
        })
    
    elif isinstance(result, str):
        summary.update({
            "length": len(result),
            "is_json": result.strip().startswith('{') or result.strip().startswith('[')
        })
    
    return summary


class LoggedBaseTool:
    """
    Base class for tools that provides automatic logging functionality.

    Tools can inherit from this class to get automatic logging of execution,
    performance metrics, and error tracking.
    """

    def __init__(self):
        # Use object.__setattr__ to bypass Pydantic's field validation
        object.__setattr__(self, '_logger', get_logger(f"tools.{self.__class__.__name__}"))

    @property
    def logger(self):
        """Get the logger instance."""
        if not hasattr(self, '_logger'):
            object.__setattr__(self, '_logger', get_logger(f"tools.{self.__class__.__name__}"))
        return self._logger

    def log_info(self, message: str, **extra):
        """Log info message with tool context."""
        self.logger.info(message, extra={
            "tool_name": getattr(self, 'name', self.__class__.__name__),
            **extra
        })

    def log_warning(self, message: str, **extra):
        """Log warning message with tool context."""
        self.logger.warning(message, extra={
            "tool_name": getattr(self, 'name', self.__class__.__name__),
            **extra
        })

    def log_error(self, message: str, **extra):
        """Log error message with tool context."""
        self.logger.error(message, extra={
            "tool_name": getattr(self, 'name', self.__class__.__name__),
            **extra
        })

    def log_debug(self, message: str, **extra):
        """Log debug message with tool context."""
        self.logger.debug(message, extra={
            "tool_name": getattr(self, 'name', self.__class__.__name__),
            **extra
        })
