"""Logging Module

Provides structured logging with request tracing, standardized formatting,
and comprehensive error handling. Implements loguru wrapper for consistent
logging behavior.

Public Components:
    LoggerWrapper: Consistent logging with context and error handling
    get_logger: Creates contextualized logger instances
    configure_logging: Configures logging settings and handlers
"""

import sys
from pathlib import Path
from typing import Literal, Any

from loguru import logger

from .exceptions import (
    ConfigurationError,
    ExecutionError,
    FileSystemError
)


# Type definitions
LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
DEFAULT_REQUEST_ID = "----------"


def _normalize_request_id(request_id: Any) -> str:
    """Convert request_id to string format, using default if None."""
    if request_id is None:
        return DEFAULT_REQUEST_ID
    return str(request_id)


class LoggerWrapper:
    """Wrapper around loguru logger providing consistent logging behavior.

    Provides logging with:
    - Request ID tracking
    - Extra field formatting
    - Duration tracking
    - Error handling

    Args:
        logger_instance: Base loguru logger instance to wrap

    Example:
        >>> logger = LoggerWrapper(logger.bind(name="my_module"))
        >>> logger.info("Process started", request_id="123")
        >>> logger.success("Process complete", duration_ms=150)
    """
    
    def __init__(self, logger_instance: Any) -> None:
        self._logger = logger_instance
        self._request_id = DEFAULT_REQUEST_ID
        
    def bind(self, **kwargs) -> 'LoggerWrapper':
        """Create new logger instance with bound context.

        Args:
            **kwargs: Context key-value pairs to bind

        Returns:
            LoggerWrapper: New logger instance with bound context

        Raises:
            ExecutionError: If binding fails
        """
        try:
            new_logger = LoggerWrapper(self._logger.bind(**kwargs))
            if 'request_id' in kwargs:
                new_logger._request_id = _normalize_request_id(kwargs['request_id'])
            return new_logger
        except Exception as e:
            raise ExecutionError(
                message=f"Invalid logger context values. Ensure all values are serializable.",
                operation="logger_bind"
            )

    def _format_extra(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Format extra arguments for consistent log output."""
        try:
            # Extract request_id and duration if present
            request_id = _normalize_request_id(kwargs.pop('request_id', self._request_id))
            duration_ms = kwargs.pop('duration_ms', None)
            
            # Remove standard fields from extras
            exclude = {'name', 'clean_name'}
            extras = {k: v for k, v in kwargs.items() if k not in exclude}
            
            # Return formatted extras with request_id
            return {
                'request_id': request_id,
                'duration_ms': duration_ms,
                **extras
            }
        except Exception as e:
            raise ExecutionError(
                message="Failed to format log extras. Check for invalid or non-serializable values.",
                operation="format_extras"
            )

    def __getattr__(self, name):
        if name in ('debug', 'info', 'warning', 'error', 'critical', 'success'):
            def log_method(message, **kwargs):
                try:
                    extras = self._format_extra(kwargs)
                    request_id = extras.pop('request_id')
                    duration_ms = extras.pop('duration_ms', None)
                    
                    # Format message with duration for success logs
                    if name == 'success' and duration_ms is not None:
                        message = f"{message} ({duration_ms:.2f}ms)"
                    
                    # Format extra fields
                    extra_str = ' | '.join(f"{k}={str(v)}" for k, v in extras.items())
                    final_message = f"{message} | {extra_str}" if extra_str else message
                    
                    # Create bound logger with request_id
                    bound_logger = self._logger.bind(request_id=request_id)
                    return getattr(bound_logger, name)(final_message)
                except Exception as e:
                    raise ExecutionError(
                        message=f"Failed to log {name} message. Verify message and extra fields are valid.",
                        operation="log_message",
                        details={"level": name}
                    )
            return log_method
        return getattr(self._logger, name)


def get_logger(name: str) -> LoggerWrapper:
    """Get a contextualized logger for the given module.

    Args:
        name: Module name for context (typically __name__)

    Returns:
        LoggerWrapper: Configured logger instance with module context

    Raises:
        ConfigurationError: If logger initialization fails

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting process", request_id="123")
    """
    try:
        logger_instance = logger.bind(
            name=name,
            clean_name=_clean_module_name(name),
            request_id=DEFAULT_REQUEST_ID
        )
        return LoggerWrapper(logger_instance)
    except Exception as e:
        raise ConfigurationError(
            message=f"Invalid logger name '{name}'. Use valid module name string.",
            source="logger_init",
            config_key=name
        )


def configure_logging(
    log_dir: Path | None = None,
    console_level: LogLevel = 'INFO',
    file_level: LogLevel = 'DEBUG',
    rotation: str = '10 MB',
    retention: str = '1 week'
) -> None:
    """Configure logging settings with validation.

    Args:
        log_dir: Optional custom log directory path. If provided, this location will
            be used instead of the default './logs' directory.
        console_level: Minimum level for console logging.
            Default: 'INFO'
        file_level: Minimum level for file logging.
            Default: 'DEBUG'
        rotation: When to rotate log files. Size-based (e.g., '10 MB', '1 GB')
            or time-based (e.g., '1 day', '1 week'). Default: '10 MB'
        retention: How long to keep old log files. Time-based duration.
            Default: '1 week'

    Raises:
        FileSystemError: If custom log directory specified but cannot be accessed
        ConfigurationError: If logger configuration fails
    """
    try:
        # Validate log levels
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if console_level not in valid_levels:
            raise ConfigurationError(
                message=f"Invalid console_level: {console_level}. Must be one of: {', '.join(valid_levels)}",
                config_key="console_level"
            )
        if file_level not in valid_levels:
            raise ConfigurationError(
                message=f"Invalid file_level: {file_level}. Must be one of: {', '.join(valid_levels)}",
                config_key="file_level"
            )

        # Initialize logging with validated parameters
        _initialize_logging(
            log_dir=log_dir,
            console_level=console_level,
            file_level=file_level,
            rotation=rotation,
            retention=retention
        )

    except (FileSystemError, ConfigurationError):
        raise
    except Exception as e:
        raise ConfigurationError(
            message=f"Failed to configure logging: {str(e)}",
            source="logging",
            config_key="configuration"
        )


def _clean_module_name(name: str) -> str:
    """Strip 'langtask.core.' prefix from module name."""
    return name.replace('langtask.core.', '')


def _initialize_logging(
    log_dir: Path | None = None,
    console_level: LogLevel = 'INFO',
    file_level: LogLevel = 'DEBUG',
    rotation: str = '10 MB',
    retention: str = '1 week'
) -> None:
    """Internal function to initialize logging handlers.

    All parameters should be pre-validated before calling this function.
    """
    base_logger = LoggerWrapper(logger.bind(
        request_id=DEFAULT_REQUEST_ID,
        clean_name="logger",
        name="langtask.core.logger"
    ))

    try:
        # Remove default handler
        logger.remove()
        
        # Add console handler
        try:
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                       "<yellow>{extra[request_id]:<12}</yellow> | "
                       "<level>{level: <8}</level> | "
                       "<cyan>{extra[clean_name]}</cyan> | "
                       "{message}",
                colorize=True,
                level=console_level
            )
        except Exception as e:
            raise ConfigurationError(
                message="Failed to configure console logging",
                source="console_handler",
                config_key="format"
            )
        
        # Determine log directory - either user-specified or default to ./logs
        target_dir = log_dir if log_dir is not None else Path.cwd() / 'logs'
        
        # Attempt to create and verify log directory
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            # Test write permissions
            test_file = target_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError) as e:
            # If user specified a directory but we can't use it, that's an error
            if log_dir is not None:
                raise FileSystemError(
                    message=f"Cannot create or write to specified log directory: {str(e)}",
                    path=str(log_dir),
                    operation="create"
                )
            # For default directory, fall back to console-only with warning
            base_logger.warning(
                "Could not create log directory './logs'. Falling back to console-only logging. "
                "Either create a writable 'logs' directory or specify a custom log location."
            )
            return
            
        # Add file handler
        log_file = target_dir / "langtask.log"
        try:
            logger.add(
                str(log_file),
                format="{time:YYYY-MM-DD HH:mm:ss} | "
                       "{extra[request_id]:<12} | "
                       "{level: <8} | "
                       "{extra[clean_name]} | "
                       "{message}",
                rotation=rotation,
                retention=retention,
                level=file_level
            )
            
            base_logger.info(f"Logging initialized. Log file: {log_file}")
            
        except Exception as e:
            if log_dir is not None:
                raise FileSystemError(
                    message=f"Failed to initialize log file: {str(e)}",
                    path=str(log_file),
                    operation="create"
                )
            base_logger.warning(
                f"Could not create log file. Falling back to console-only logging: {str(e)}"
            )
            
    except (FileSystemError, ConfigurationError):
        raise
    except Exception as e:
        raise ExecutionError(
            message="Failed to initialize logging system. Verify directory and file permissions.",
            operation="logging_init"
        )


# Initialize logging with defaults when module is imported
try:
    configure_logging()
except Exception as e:
    logger.add(sys.stderr, format="{message}")
    # Use raw logger for fallback error since wrapper might not be working
    logger.error("Logging initialization failed. Falling back to basic stderr logging.")