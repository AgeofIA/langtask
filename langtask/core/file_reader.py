"""File Reading Module

Reads and parses text and YAML files with UTF-8 encoding. Handles file size
limits, logging, and structured error reporting for configuration and schema
file operations.

Public Functions:
    read_text_file: Reads and decodes text files
    read_yaml_file: Reads and parses YAML files with validation
"""

import time
import yaml
from pathlib import Path
from typing import Any

from .exceptions import FileSystemError, SchemaValidationError
from .file_validator import validate_file
from .logger import get_logger

logger = get_logger(__name__)


# Maximum allowed file size (10MB) to prevent memory issues
MAX_FILE_SIZE = 10 * 1024 * 1024


def read_text_file(
    file_path: str | Path,
    max_size: int | None = MAX_FILE_SIZE,
    request_id: str | None = None
) -> str:
    """Read the content of a text file with UTF-8 encoding.

    Provides robust text file reading with:
    - UTF-8 encoding
    - Optional size validation
    - Performance monitoring
    - Comprehensive error handling

    Args:
        file_path: Path to the file to read. Can be either a string path
            or a Path object. Relative paths are resolved to absolute paths.
        max_size: Maximum allowed file size in bytes. Set to None to disable
            size checking. Defaults to MAX_FILE_SIZE (10MB).
        request_id: Optional identifier for tracing and logging purposes.

    Returns:
        str: Complete content of the file as a string.

    Raises:
        FileSystemError: In the following cases:
            - File access errors (see file_validator.validate_file)
            - File size exceeds max_size limit
            - UTF-8 encoding errors
            - Other unexpected read errors
            
    Logs:
        - All read operations are logged with timing information
        - Successful reads logged at DEBUG level with file size and duration
        - Read failures logged at ERROR level with error context

    Notes:
        - Files are read entirely into memory
        - File size is checked before reading to prevent memory issues
        - Consider memory availability when setting max_size
        - Assumes all files are UTF-8 encoded

    Example:
        >>> try:
        ...     # Basic usage
        ...     content = read_text_file("config.txt")
        ...     
        ...     # With custom size limit
        ...     content = read_text_file(
        ...         "large_file.txt",
        ...         max_size=50 * 1024 * 1024  # 50MB
        ...     )
        ...     
        ...     # No size limit
        ...     content = read_text_file("huge_file.txt", max_size=None)
        ... except FileSystemError as e:
        ...     if "size" in e.message:
        ...         print("File too large")
        ...     elif "encoding" in e.message:
        ...         print("Encoding error")
        ...     else:
        ...         print(f"Read error: {e.message}")
    """
    start_time = time.time()
    path = Path(file_path)
    
    try:
        validate_file(path)
        
        # Check file size if limit specified
        if max_size is not None:
            size = path.stat().st_size
            if size > max_size:
                readable_max = f"{max_size / (1024*1024):.1f}MB"
                readable_size = f"{size / (1024*1024):.1f}MB"
                raise FileSystemError(
                    message=f"File too large ({readable_size}). Maximum size: {readable_max}",
                    path=str(path),
                    operation="read"
                )
        
        content = path.read_text(encoding='utf-8')
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            "File read successfully",
            path=str(path),
            size_bytes=path.stat().st_size,
            duration_ms=round(duration_ms, 2),
            request_id=request_id
        )
        return content
        
    except UnicodeError as e:
        logger.error(
            "UTF-8 encoding error",
            path=str(path),
            error=str(e),
            request_id=request_id
        )
        raise FileSystemError(
            message="File must be UTF-8 encoded. Check file encoding and try again.",
            path=str(path),
            operation="read"
        )
        
    except FileSystemError:
        raise
        
    except Exception as e:
        logger.error(
            "Unexpected error reading file",
            path=str(path),
            error=str(e),
            request_id=request_id
        )
        raise FileSystemError(
            message=f"Cannot read file. Verify file exists and has read permissions.",
            path=str(path),
            operation="read"
        )


def read_yaml_file(
    file_path: str | Path,
    max_size: int | None = MAX_FILE_SIZE,
    request_id: str | None = None
) -> dict[str, Any]:
    """Read and parse a YAML file with validation.

    Provides robust YAML file reading with:
    - Automatic text file reading (via read_text_file)
    - YAML parsing and validation
    - Structured error reporting
    - Performance monitoring

    Args:
        file_path: Path to the YAML file to read. Can be either a string path
            or a Path object. Relative paths are resolved to absolute paths.
        max_size: Maximum allowed file size in bytes. Set to None to disable
            size checking. Defaults to MAX_FILE_SIZE (10MB).
        request_id: Optional identifier for tracing and logging purposes.

    Returns:
        Dict[str, Any]: Parsed YAML content as a dictionary. Returns an empty
        dictionary if the file is empty or contains only comments.

    Raises:
        FileSystemError: If file access fails (via read_text_file)
        SchemaValidationError: In the following cases:
            - Invalid YAML syntax (with line number if available)
            - Non-dictionary YAML structure
            - Other YAML parsing errors
            
    Logs:
        - All YAML operations are logged with timing information
        - Successful parses logged at DEBUG level with item count and duration
        - Parsing failures logged at ERROR level with line numbers when available

    Notes:
        - Files are read entirely into memory
        - Large YAML files may have significant parsing overhead
        - Consider memory usage for both file content and parsed structure

    Example:
        >>> try:
        ...     # Basic usage
        ...     config = read_yaml_file("config.yaml")
        ...     
        ...     # Handle empty or comment-only files
        ...     data = read_yaml_file("empty.yaml")
        ...     if not data:
        ...         print("No configuration found")
        ...     
        ...     # With custom size limit
        ...     data = read_yaml_file("large_config.yaml", max_size=5_000_000)
        ... except FileSystemError as e:
        ...     print(f"File error: {e.message}")
        ... except SchemaValidationError as e:
        ...     if e.field:  # Line number available
        ...         print(f"YAML error on {e.field}: {e.message}")
        ...     else:
        ...         print(f"YAML error: {e.message}")
    """
    start_time = time.time()
    path = Path(file_path)
    
    try:
        content = read_text_file(path, max_size, request_id)
        yaml_content = yaml.safe_load(content) or {}
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            "YAML parsed successfully",
            path=str(path),
            items=len(yaml_content) if isinstance(yaml_content, dict) else 0,
            duration_ms=round(duration_ms, 2),
            request_id=request_id
        )
        return yaml_content
        
    except yaml.YAMLError as e:
        logger.error(
            "YAML parsing error",
            path=str(path),
            error=str(e),
            request_id=request_id
        )
        error_info = {
            "line": getattr(e, 'problem_mark', None) and e.problem_mark.line + 1,
            "problem": getattr(e, 'problem', str(e))
        }
        error_location = f" at line {error_info['line']}" if error_info['line'] else ""
        raise SchemaValidationError(
            message=f"Invalid YAML syntax{error_location}. {error_info['problem']}",
            schema_type="yaml",
            field=f"line {error_info['line']}" if error_info['line'] else None
        )
        
    except FileSystemError:
        raise
        
    except Exception as e:
        logger.error(
            "Unexpected error parsing YAML",
            path=str(path),
            error=str(e)
        )
        raise SchemaValidationError(
            message="Failed to parse YAML file. Verify file contains valid YAML syntax.",
            schema_type="yaml"
        )