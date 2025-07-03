"""Error tracking and alerting system for CustomLangGraphChatBot."""

import time
import json
import threading
from collections import defaultdict, deque
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from logging_config import get_logger

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    API_ERROR = "api_error"
    TOOL_ERROR = "tool_error"
    SYSTEM_ERROR = "system_error"
    VALIDATION_ERROR = "validation_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorEvent:
    """Represents a single error event."""
    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    source: str  # API endpoint, tool name, etc.
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    resolved: bool = False
    resolution_notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "source": self.source,
            "context": self.context,
            "stack_trace": self.stack_trace,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes
        }


@dataclass
class ErrorPattern:
    """Represents a pattern of recurring errors."""
    pattern_id: str
    error_type: str
    source: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    sample_messages: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "error_type": self.error_type,
            "source": self.source,
            "count": self.count,
            "first_occurrence": self.first_occurrence.isoformat(),
            "last_occurrence": self.last_occurrence.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "sample_messages": self.sample_messages[:5]  # Limit to 5 samples
        }


class ErrorTracker:
    """Comprehensive error tracking and alerting system."""
    
    def __init__(self, max_events: int = 10000, pattern_threshold: int = 3):
        self.errors: deque = deque(maxlen=max_events)
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.severity_counts: Dict[ErrorSeverity, int] = defaultdict(int)
        self.category_counts: Dict[ErrorCategory, int] = defaultdict(int)
        self.pattern_threshold = pattern_threshold
        self.lock = threading.Lock()
        self.alert_thresholds = {
            ErrorSeverity.CRITICAL: 1,  # Alert immediately
            ErrorSeverity.HIGH: 3,      # Alert after 3 occurrences
            ErrorSeverity.MEDIUM: 10,   # Alert after 10 occurrences
            ErrorSeverity.LOW: 50       # Alert after 50 occurrences
        }
        
        logger.info("Error tracking system initialized", extra={
            "max_events": max_events,
            "pattern_threshold": pattern_threshold,
            "alert_thresholds": {k.value: v for k, v in self.alert_thresholds.items()}
        })
    
    def classify_error(self, error_type: str, error_message: str, source: str) -> tuple[ErrorSeverity, ErrorCategory]:
        """Classify error based on type, message, and source."""
        error_message_lower = error_message.lower()
        error_type_lower = error_type.lower()
        
        # Determine category
        if "timeout" in error_message_lower or "timeout" in error_type_lower:
            category = ErrorCategory.TIMEOUT_ERROR
        elif "rate limit" in error_message_lower or "429" in error_message:
            category = ErrorCategory.RATE_LIMIT_ERROR
        elif "auth" in error_message_lower or "401" in error_message or "403" in error_message:
            category = ErrorCategory.AUTHENTICATION_ERROR
        elif "validation" in error_message_lower or "400" in error_message:
            category = ErrorCategory.VALIDATION_ERROR
        elif source.startswith("tools."):
            category = ErrorCategory.TOOL_ERROR
        elif source.startswith("api.") or "api" in source:
            category = ErrorCategory.API_ERROR
        elif "external" in error_message_lower or "connection" in error_message_lower:
            category = ErrorCategory.EXTERNAL_SERVICE_ERROR
        elif "system" in error_message_lower or "internal" in error_message_lower:
            category = ErrorCategory.SYSTEM_ERROR
        else:
            category = ErrorCategory.UNKNOWN_ERROR
        
        # Determine severity
        if any(keyword in error_message_lower for keyword in ["critical", "fatal", "crash", "corruption"]):
            severity = ErrorSeverity.CRITICAL
        elif any(keyword in error_message_lower for keyword in ["error", "failed", "exception"]):
            if category in [ErrorCategory.AUTHENTICATION_ERROR, ErrorCategory.EXTERNAL_SERVICE_ERROR]:
                severity = ErrorSeverity.HIGH
            elif category in [ErrorCategory.TOOL_ERROR, ErrorCategory.API_ERROR]:
                severity = ErrorSeverity.MEDIUM
            else:
                severity = ErrorSeverity.LOW
        elif any(keyword in error_message_lower for keyword in ["warning", "deprecated"]):
            severity = ErrorSeverity.LOW
        else:
            severity = ErrorSeverity.MEDIUM
        
        return severity, category
    
    def track_error(self, error_type: str, error_message: str, source: str, 
                   context: Dict[str, Any] = None, stack_trace: str = None) -> str:
        """Track a new error event."""
        with self.lock:
            # Generate unique error ID
            error_id = f"err_{int(time.time() * 1000)}_{len(self.errors)}"
            
            # Classify error
            severity, category = self.classify_error(error_type, error_message, source)
            
            # Create error event
            error_event = ErrorEvent(
                id=error_id,
                timestamp=datetime.now(),
                error_type=error_type,
                error_message=error_message,
                severity=severity,
                category=category,
                source=source,
                context=context or {},
                stack_trace=stack_trace
            )
            
            # Add to error collection
            self.errors.append(error_event)
            
            # Update counters
            self.error_counts[f"{error_type}:{source}"] += 1
            self.severity_counts[severity] += 1
            self.category_counts[category] += 1
            
            # Check for patterns
            self._update_error_patterns(error_event)
            
            # Check for alerts
            self._check_alert_thresholds(error_event)
            
            # Log the error tracking
            logger.info("Error tracked", extra={
                "error_id": error_id,
                "error_type": error_type,
                "severity": severity.value,
                "category": category.value,
                "source": source
            })
            
            return error_id
    
    def _update_error_patterns(self, error_event: ErrorEvent):
        """Update error patterns for recurring issues."""
        pattern_key = f"{error_event.error_type}:{error_event.source}"
        
        if pattern_key in self.error_patterns:
            pattern = self.error_patterns[pattern_key]
            pattern.count += 1
            pattern.last_occurrence = error_event.timestamp
            if len(pattern.sample_messages) < 5:
                pattern.sample_messages.append(error_event.error_message)
        else:
            self.error_patterns[pattern_key] = ErrorPattern(
                pattern_id=f"pattern_{len(self.error_patterns)}",
                error_type=error_event.error_type,
                source=error_event.source,
                count=1,
                first_occurrence=error_event.timestamp,
                last_occurrence=error_event.timestamp,
                severity=error_event.severity,
                category=error_event.category,
                sample_messages=[error_event.error_message]
            )
    
    def _check_alert_thresholds(self, error_event: ErrorEvent):
        """Check if error should trigger an alert."""
        threshold = self.alert_thresholds.get(error_event.severity, 10)
        error_key = f"{error_event.error_type}:{error_event.source}"
        
        if self.error_counts[error_key] >= threshold:
            self._trigger_alert(error_event, self.error_counts[error_key])
    
    def _trigger_alert(self, error_event: ErrorEvent, count: int):
        """Trigger an alert for the error."""
        logger.warning("Error alert triggered", extra={
            "error_id": error_event.id,
            "error_type": error_event.error_type,
            "severity": error_event.severity.value,
            "source": error_event.source,
            "count": count,
            "alert_reason": f"Error count ({count}) exceeded threshold"
        })
        
        # Here you could integrate with external alerting systems
        # like Slack, email, PagerDuty, etc.
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]
            
            return {
                "time_period_hours": hours,
                "total_errors": len(recent_errors),
                "errors_by_severity": {
                    severity.value: len([e for e in recent_errors if e.severity == severity])
                    for severity in ErrorSeverity
                },
                "errors_by_category": {
                    category.value: len([e for e in recent_errors if e.category == category])
                    for category in ErrorCategory
                },
                "top_error_sources": self._get_top_sources(recent_errors),
                "error_rate_per_hour": len(recent_errors) / hours if hours > 0 else 0
            }
    
    def _get_top_sources(self, errors: List[ErrorEvent], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top error sources."""
        source_counts = defaultdict(int)
        for error in errors:
            source_counts[error.source] += 1
        
        return [
            {"source": source, "count": count}
            for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        ]
    
    def get_error_patterns(self, min_count: int = None) -> List[Dict[str, Any]]:
        """Get error patterns."""
        with self.lock:
            min_count = min_count or self.pattern_threshold
            patterns = [
                pattern.to_dict()
                for pattern in self.error_patterns.values()
                if pattern.count >= min_count
            ]
            return sorted(patterns, key=lambda x: x["count"], reverse=True)
    
    def get_recent_errors(self, limit: int = 100, severity: ErrorSeverity = None) -> List[Dict[str, Any]]:
        """Get recent errors."""
        with self.lock:
            errors = list(self.errors)
            if severity:
                errors = [e for e in errors if e.severity == severity]
            
            # Sort by timestamp (most recent first)
            errors.sort(key=lambda x: x.timestamp, reverse=True)
            
            return [error.to_dict() for error in errors[:limit]]


# Global error tracker instance
error_tracker = ErrorTracker()
