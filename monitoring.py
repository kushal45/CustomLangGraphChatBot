"""Comprehensive monitoring and metrics collection for the CustomLangGraphChatBot."""

import time
import json
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class APIMetrics:
    """Metrics for API endpoint performance."""
    endpoint: str
    method: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    error_count_by_type: Dict[str, int] = None
    status_code_counts: Dict[int, int] = None
    
    def __post_init__(self):
        if self.error_count_by_type is None:
            self.error_count_by_type = defaultdict(int)
        if self.status_code_counts is None:
            self.status_code_counts = defaultdict(int)
    
    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0.0


@dataclass
class ToolMetrics:
    """Metrics for tool execution performance."""
    tool_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    last_execution_time: Optional[datetime] = None
    error_count_by_type: Dict[str, int] = None
    
    def __post_init__(self):
        if self.error_count_by_type is None:
            self.error_count_by_type = defaultdict(int)
    
    @property
    def average_execution_time(self) -> float:
        """Calculate average execution time."""
        return self.total_execution_time / self.total_executions if self.total_executions > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful_executions / self.total_executions * 100) if self.total_executions > 0 else 0.0


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    start_time: datetime
    total_requests: int = 0
    total_errors: int = 0
    active_requests: int = 0
    peak_active_requests: int = 0
    total_tools_executed: int = 0
    unique_clients: set = None
    
    def __post_init__(self):
        if self.unique_clients is None:
            self.unique_clients = set()
    
    @property
    def uptime_seconds(self) -> float:
        """Calculate system uptime in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate requests per minute."""
        uptime_minutes = self.uptime_seconds / 60
        return self.total_requests / uptime_minutes if uptime_minutes > 0 else 0.0


class MonitoringSystem:
    """Comprehensive monitoring system for tracking API and tool performance."""
    
    def __init__(self, max_recent_events: int = 1000):
        self.api_metrics: Dict[str, APIMetrics] = {}
        self.tool_metrics: Dict[str, ToolMetrics] = {}
        self.system_metrics = SystemMetrics(start_time=datetime.now())
        self.recent_events = deque(maxlen=max_recent_events)
        self.lock = threading.Lock()
        
        logger.info("Monitoring system initialized", extra={
            "start_time": self.system_metrics.start_time.isoformat(),
            "max_recent_events": max_recent_events
        })
    
    def record_api_request(self, endpoint: str, method: str, status_code: int, 
                          response_time: float, client_ip: str = None, error_type: str = None):
        """Record API request metrics."""
        with self.lock:
            key = f"{method}:{endpoint}"
            
            if key not in self.api_metrics:
                self.api_metrics[key] = APIMetrics(endpoint=endpoint, method=method)
            
            metrics = self.api_metrics[key]
            metrics.total_requests += 1
            metrics.total_response_time += response_time
            metrics.min_response_time = min(metrics.min_response_time, response_time)
            metrics.max_response_time = max(metrics.max_response_time, response_time)
            metrics.last_request_time = datetime.now()
            metrics.status_code_counts[status_code] += 1
            
            if 200 <= status_code < 400:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
                if error_type:
                    metrics.error_count_by_type[error_type] += 1
            
            # Update system metrics
            self.system_metrics.total_requests += 1
            if status_code >= 400:
                self.system_metrics.total_errors += 1
            if client_ip:
                self.system_metrics.unique_clients.add(client_ip)
            
            # Record recent event
            self.recent_events.append({
                "timestamp": datetime.now().isoformat(),
                "type": "api_request",
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time": response_time,
                "client_ip": client_ip,
                "error_type": error_type
            })
    
    def record_tool_execution(self, tool_name: str, execution_time: float, 
                            success: bool, error_type: str = None):
        """Record tool execution metrics."""
        with self.lock:
            if tool_name not in self.tool_metrics:
                self.tool_metrics[tool_name] = ToolMetrics(tool_name=tool_name)
            
            metrics = self.tool_metrics[tool_name]
            metrics.total_executions += 1
            metrics.total_execution_time += execution_time
            metrics.min_execution_time = min(metrics.min_execution_time, execution_time)
            metrics.max_execution_time = max(metrics.max_execution_time, execution_time)
            metrics.last_execution_time = datetime.now()
            
            if success:
                metrics.successful_executions += 1
            else:
                metrics.failed_executions += 1
                if error_type:
                    metrics.error_count_by_type[error_type] += 1
            
            # Update system metrics
            self.system_metrics.total_tools_executed += 1
            
            # Record recent event
            self.recent_events.append({
                "timestamp": datetime.now().isoformat(),
                "type": "tool_execution",
                "tool_name": tool_name,
                "execution_time": execution_time,
                "success": success,
                "error_type": error_type
            })
    
    def get_api_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of API metrics."""
        with self.lock:
            return {
                endpoint: {
                    "endpoint": metrics.endpoint,
                    "method": metrics.method,
                    "total_requests": metrics.total_requests,
                    "success_rate": round(metrics.success_rate, 2),
                    "average_response_time": round(metrics.average_response_time, 4),
                    "min_response_time": round(metrics.min_response_time, 4),
                    "max_response_time": round(metrics.max_response_time, 4),
                    "last_request": metrics.last_request_time.isoformat() if metrics.last_request_time else None,
                    "status_codes": dict(metrics.status_code_counts),
                    "error_types": dict(metrics.error_count_by_type)
                }
                for endpoint, metrics in self.api_metrics.items()
            }
    
    def get_tool_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of tool metrics."""
        with self.lock:
            return {
                tool_name: {
                    "tool_name": metrics.tool_name,
                    "total_executions": metrics.total_executions,
                    "success_rate": round(metrics.success_rate, 2),
                    "average_execution_time": round(metrics.average_execution_time, 4),
                    "min_execution_time": round(metrics.min_execution_time, 4),
                    "max_execution_time": round(metrics.max_execution_time, 4),
                    "last_execution": metrics.last_execution_time.isoformat() if metrics.last_execution_time else None,
                    "error_types": dict(metrics.error_count_by_type)
                }
                for tool_name, metrics in self.tool_metrics.items()
            }
    
    def get_system_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of system metrics."""
        with self.lock:
            return {
                "start_time": self.system_metrics.start_time.isoformat(),
                "uptime_seconds": round(self.system_metrics.uptime_seconds, 2),
                "total_requests": self.system_metrics.total_requests,
                "total_errors": self.system_metrics.total_errors,
                "error_rate": round((self.system_metrics.total_errors / self.system_metrics.total_requests * 100) 
                                 if self.system_metrics.total_requests > 0 else 0, 2),
                "requests_per_minute": round(self.system_metrics.requests_per_minute, 2),
                "active_requests": self.system_metrics.active_requests,
                "peak_active_requests": self.system_metrics.peak_active_requests,
                "total_tools_executed": self.system_metrics.total_tools_executed,
                "unique_clients_count": len(self.system_metrics.unique_clients)
            }
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events."""
        with self.lock:
            return list(self.recent_events)[-limit:]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        with self.lock:
            system_summary = self.get_system_metrics_summary()
            
            # Determine health status based on error rates and performance
            error_rate = system_summary["error_rate"]
            uptime = system_summary["uptime_seconds"]
            
            if error_rate > 10:
                status = "unhealthy"
            elif error_rate > 5:
                status = "degraded"
            else:
                status = "healthy"
            
            return {
                "status": status,
                "error_rate": error_rate,
                "uptime_seconds": uptime,
                "total_requests": system_summary["total_requests"],
                "active_requests": system_summary["active_requests"],
                "timestamp": datetime.now().isoformat()
            }


# Global monitoring instance
monitoring = MonitoringSystem()
