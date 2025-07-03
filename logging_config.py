"""
Centralized logging configuration for CustomLangGraphChatBot.

This module provides comprehensive logging setup with:
- Structured logging with JSON format
- Multiple log levels and handlers
- File rotation and retention policies
- Performance and error tracking
- Configurable log destinations
"""

import logging
import logging.config
import logging.handlers
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
import traceback


class LogLevel(Enum):
    """Available log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Available log formats."""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if enabled
        if self.include_extra:
            extra_fields = {}
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    extra_fields[key] = value
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class LoggingConfig:
    """Centralized logging configuration manager."""
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "detailed",
        log_dir: Optional[str] = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_json_logging: bool = False
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Log format type (simple, detailed, json)
            log_dir: Directory for log files (defaults to ./logs)
            enable_file_logging: Whether to enable file logging
            enable_console_logging: Whether to enable console logging
            max_file_size: Maximum size of log files before rotation
            backup_count: Number of backup files to keep
            enable_json_logging: Whether to use JSON structured logging
        """
        self.log_level = log_level.upper()
        self.log_format = log_format.lower()
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_json_logging = enable_json_logging
        
        # Create log directory if it doesn't exist
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def get_formatter(self, format_type: str = None) -> logging.Formatter:
        """Get appropriate formatter based on configuration."""
        format_type = format_type or self.log_format
        
        if format_type == "json" or self.enable_json_logging:
            return StructuredFormatter()
        elif format_type == "simple":
            return logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:  # detailed
            return logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
    
    def setup_logging(self) -> None:
        """Setup comprehensive logging configuration."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Set root logger level
        root_logger.setLevel(getattr(logging, self.log_level))
        
        handlers = []
        
        # Console handler
        if self.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level))
            console_handler.setFormatter(self.get_formatter("simple"))  # Use simple format for console
            handlers.append(console_handler)
        
        # File handlers
        if self.enable_file_logging:
            # Main application log
            app_log_file = self.log_dir / "app.log"
            app_handler = logging.handlers.RotatingFileHandler(
                app_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            app_handler.setLevel(getattr(logging, self.log_level))
            app_handler.setFormatter(self.get_formatter())
            handlers.append(app_handler)
            
            # Error log (ERROR and CRITICAL only)
            error_log_file = self.log_dir / "error.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(self.get_formatter())
            handlers.append(error_handler)
            
            # Tool execution log
            tools_log_file = self.log_dir / "tools.log"
            tools_handler = logging.handlers.RotatingFileHandler(
                tools_log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            tools_handler.setLevel(logging.INFO)
            tools_handler.setFormatter(self.get_formatter())
            
            # Add filter to only log tool-related messages
            tools_handler.addFilter(lambda record: 'tools.' in record.name or 'tool_execution' in record.name)
            handlers.append(tools_handler)
        
        # Add all handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)
        
        # Log the configuration
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {self.log_level}, Format: {self.log_format}")
        logger.info(f"Log directory: {self.log_dir.absolute()}")
        logger.info(f"Handlers: Console={self.enable_console_logging}, File={self.enable_file_logging}")


def setup_logging_from_env() -> LoggingConfig:
    """Setup logging configuration from environment variables."""
    config = LoggingConfig(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "detailed"),
        log_dir=os.getenv("LOG_DIR", "logs"),
        enable_file_logging=os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true",
        enable_console_logging=os.getenv("ENABLE_CONSOLE_LOGGING", "true").lower() == "true",
        max_file_size=int(os.getenv("MAX_LOG_FILE_SIZE", str(10 * 1024 * 1024))),
        backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        enable_json_logging=os.getenv("ENABLE_JSON_LOGGING", "false").lower() == "true"
    )
    
    config.setup_logging()
    return config


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def initialize_logging(config: Optional[LoggingConfig] = None) -> LoggingConfig:
    """Initialize global logging configuration."""
    global _logging_config
    
    if config is None:
        config = setup_logging_from_env()
    else:
        config.setup_logging()
    
    _logging_config = config
    return config


def get_logging_config() -> Optional[LoggingConfig]:
    """Get the current logging configuration."""
    return _logging_config
