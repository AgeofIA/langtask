"""File and Directory Validation Module

Validates file system paths by checking existence, accessibility, and permissions.
Used throughout the application as a pre-check before file operations to ensure
proper error handling and user feedback.

Public Functions:
    validate_file: Validates existence and accessibility of a file
    validate_directory: Validates existence and accessibility of a directory
"""

from pathlib import Path

from .exceptions import FileSystemError
from .logger import get_logger

logger = get_logger(__name__)


def validate_file(file_path: str | Path, required: bool = True) -> bool:
    """Validate that a file exists and is accessible.
    
    Performs full validation of a file's existence and accessibility including:
    - Path resolution (handling relative paths and symlinks)
    - Existence verification
    - Read permission checking
    
    Args:
        file_path: Path to the file to validate. Can be either a string path
            or a Path object. Relative paths are resolved to absolute paths.
        required: If True, raises FileSystemError when file doesn't exist.
            If False, returns False for missing files without raising errors.
        
    Returns:
        bool: True if file exists and is accessible, False if file doesn't exist
            and required=False. Always raises exceptions for other error conditions.
        
    Raises:
        FileSystemError: In the following cases:
            - File does not exist (only if required=True)
            - Path exists but is not a file
            - Permission denied when accessing file
            - Other OS-level access errors
            - Unexpected errors during validation
            
    Logs:
        WARNING: Required file not found
        ERROR: Permission denied with details
        ERROR: File system errors with details
        ERROR: Unexpected errors during validation
            
    Example:
        >>> try:
        ...     # Required file validation
        ...     validate_file("config.yaml")
        ...     # File is valid, proceed with operations
        ...     
        ...     # Optional file validation
        ...     if validate_file("optional.yaml", required=False):
        ...         # Process optional file
        ...     else:
        ...         # Skip optional file processing
        ... except FileSystemError as e:
        ...     if e.operation == "read":
        ...         # Handle permission errors
        ...     elif "exist" in e.message:
        ...         # Handle missing required file
        ...     print(f"Validation failed: {e.message}")
    """
    try:
        path = Path(file_path).resolve()
        
        if not path.is_file():
            if not required:
                return False
                
            logger.warning("Required file not found", path=str(path))
            raise FileSystemError(
                message=f"File not found: '{path}'. Verify path is correct and file exists.",
                path=str(path),
                operation="access"
            )
            
        # Test read access by opening file
        with path.open('r'):
            pass
            
        return True
            
    except PermissionError as e:
        logger.error(
            "Permission denied",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"Cannot read '{path}'. Check file permissions and ownership.",
            path=str(path),
            operation="read",
            error_code=getattr(e, 'errno', None)
        )
        
    except FileSystemError:
        raise
        
    except OSError as e:
        logger.error(
            "File system error",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"File system error for '{path}'. {str(e)}",
            path=str(path),
            operation="access",
            error_code=getattr(e, 'errno', None)
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"Unexpected error with '{path}'. System error: {str(e)}",
            path=str(path),
            operation="access"
        )


def validate_directory(dir_path: str | Path) -> None:
    """Validate that a directory exists and is accessible.
    
    Performs full validation of a directory's existence and accessibility including:
    - Path resolution (handling relative paths and symlinks)
    - Existence verification
    - Read permission checking
    - Basic traversal testing
    
    Args:
        dir_path: Path to the directory to validate. Can be either a string path
            or a Path object. Relative paths are resolved to absolute paths.
        
    Raises:
        FileSystemError: In the following cases:
            - Directory does not exist
            - Path exists but is not a directory
            - Permission denied when accessing directory
            - Other OS-level access errors
            - Unexpected errors during validation
            
    Logs:
        WARNING: Directory not found
        ERROR: Permission denied with details
        ERROR: Directory access errors with details
        ERROR: Unexpected errors during validation

    Note:
        The function tests basic directory traversal by attempting to get the
        first directory entry, which verifies both existence and read permissions
        in a single operation.
            
    Example:
        >>> try:
        ...     validate_directory("data/configs/")
        ...     # Directory is valid, proceed with operations
        ... except FileSystemError as e:
        ...     if e.operation == "read":
        ...         # Handle permission errors
        ...     elif "exist" in e.message:
        ...         # Handle missing directory
        ...     print(f"Validation failed: {e.message}")
    """
    try:
        path = Path(dir_path).resolve()
        
        if not path.is_dir():
            logger.warning("Directory not found", path=str(path))
            raise FileSystemError(
                message=f"Directory not found: '{path}'. Verify path is correct and directory exists.",
                path=str(path),
                operation="access"
            )
            
        # Test read access by listing directory
        try:
            next(path.iterdir(), None)
        except StopIteration:
            # Empty directory is valid
            pass
        
    except PermissionError as e:
        logger.error(
            "Permission denied",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"Cannot access directory '{path}'. Check directory permissions and ownership.",
            path=str(path),
            operation="read",
            error_code=getattr(e, 'errno', None)
        )
        
    except OSError as e:
        logger.error(
            "Directory access error",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"Directory access error for '{path}'. {str(e)}",
            path=str(path),
            operation="access",
            error_code=getattr(e, 'errno', None)
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error",
            path=str(path),
            error=str(e)
        )
        raise FileSystemError(
            message=f"Unexpected error with directory '{path}'. System error: {str(e)}",
            path=str(path),
            operation="access"
        )