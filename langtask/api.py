"""Public API Module

Provides the main public interface for text generation and configuration management.
Handles prompt registration, execution, and global settings.

Note: Prompt directories must be explicitly registered using register() before use.

Public Functions:
    register: Register prompt directory for template discovery
    list_directories: Get list of registered prompt directories
    list_prompts: Get dictionary of registered prompts and configurations
    get_prompt: Get configuration for a specific prompt
    run: Generate text using specified prompt
    set_global_config: Set or update global configuration
    get_global_config: Get current global configuration
    set_logs: Configure logging settings and location
"""

from pathlib import Path
from typing import Any

from .core.config_loader import (
    get_global_config as _get_global_config,
    set_global_config as _set_global_config
)
from .core.exceptions import (
    ConfigurationError,
    FileSystemError,
    PromptValidationError,
    PromptValidationError as CorePromptValidationError
)
from .core.llm_processor import process_llm_request
from .core.logger import get_logger, configure_logging, LogLevel
from .core.prompt_registrar import (
    register_prompt_directory,
    get_directories_list,
    get_prompts_list,
    get_prompt_info
)
from .core.schema_loader import StructuredResponse

logger = get_logger(__name__)


def register(directory: str | Path) -> None:
    """Register a prompt directory.

    Args:
        directory: Path to directory containing prompt templates

    Raises:
        FileSystemError: When directory access fails
        InitializationError: When prompt registration fails

    Example:
        >>> register("./my_prompts")
        >>> response = run("translate-text", {"text": "Hello", "language": "Spanish"})
    """
    register_prompt_directory(directory)


def list_directories() -> list[str]:
    """Get list of registered prompt directory paths.

    Returns:
        List[str]: List of directory paths that have been registered

    Example:
        >>> dirs = list_directories()
        >>> print(f"Registered directories: {dirs}")
    """
    return get_directories_list()


def list_prompts() -> dict[str, dict[str, Any]]:
    """Get dictionary of registered prompts with basic information.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping prompt IDs to basic information:
            {
                "prompt-id": {
                    "display_name": str,        # Optional display name
                    "description": str,         # Optional description
                    "has_llm_config": bool,     # Whether prompt has LLM settings
                    "has_input_schema": bool,   # Whether input schema exists
                    "has_output_schema": bool   # Whether output schema exists
                }
            }
            
    Notes:
        This method returns lightweight prompt information suitable for listing and
        discovery. For detailed configuration including schemas and complete LLM
        settings, use get_prompt(prompt_id).

    Example:
        >>> prompts = list_prompts()
        >>> for id, info in prompts.items():
        ...     print(f"Prompt: {id}")
        ...     if info['description']:
        ...         print(f"  Description: {info['description']}")
        ...     if info['has_llm_config']:
        ...         print("  LLM settings configured")
    """
    return get_prompts_list()


def get_prompt(prompt_id: str) -> dict[str, Any]:
    """Get configuration information for a specific prompt.

    Args:
        prompt_id: ID of the prompt to retrieve information for

    Returns:
        Dictionary containing prompt configuration:
            - llm: List of LLM configurations with:
                - provider: str
                - model: str
                - temperature: float
                - max_tokens: int
            - schemas: Schema information:
                - input:
                    - exists: True if schema exists
                    - content: Schema content if exists
                - output:
                    - exists: True if schema exists
                    - content: Schema content if exists
            - display_name: Optional display name (if present)
            - description: Optional prompt description (if present)
            - instructions: Content of instructions.md template

    Raises:
        PromptValidationError: When requested prompt doesn't exist or no directories registered
        FileSystemError: When prompt files cannot be read

    Example:
        >>> info = get_prompt("translate-text")
        >>> print(f"Model: {info['llm'][0]['model']}")
        >>> if info['schemas']['input']['exists']:
        ...     print("Required fields:", info['schemas']['input']['content']['required'])
        >>> print(f"Prompt Template:\\n{info['instructions']}")
    """
    try:
        return get_prompt_info(prompt_id)
    except CorePromptValidationError as e:
        if "No prompt directories have been registered" in str(e):
            raise PromptValidationError(
                message="No prompt directories registered. Use register() to add a prompt directory.",
                prompt_path=e.prompt_path,
                validation_type=e.validation_type
            )
        raise


def run(prompt_id: str, input_params: dict[str, Any] | None = None) -> str | StructuredResponse:
    """Generate a response using the specified prompt.

    Args:
        prompt_id: ID of the registered prompt to use
        input_params: Optional parameters required by the prompt template

    Returns:
        Either:
            - Raw text response when no schema is defined
            - Structured response object with fields accessible via
              dot notation when an output schema is defined

    Raises:
        ExecutionError: For processing and runtime failures
        ProviderAPIError: For LLM provider communication issues
        DataValidationError: For input validation failures
        SchemaValidationError: For schema validation failures
        PromptValidationError: When prompt not found or no directories registered

    Example:
        >>> # Simple text response
        >>> response = run("translate-text", {"text": "Hello", "language": "Spanish"})
        >>> print(response)  # Prints: "Hola"
        
        >>> # Structured response with schema
        >>> response = run("analyze-sentiment", {"text": "Great product!"})
        >>> print(response.sentiment)  # Access fields directly
        positive
        >>> print(response.confidence:.2f)  # Access numeric fields
        0.95
    """
    try:
        return process_llm_request(prompt_id, input_params)
    except CorePromptValidationError as e:
        if "No prompt directories have been registered" in str(e):
            raise PromptValidationError(
                message="No prompt directories registered. Use register() to add a prompt directory.",
                prompt_path=e.prompt_path,
                validation_type=e.validation_type
            )
        raise


def set_global_config(
    config: str | dict[str, Any] | list[dict[str, Any]] | None = None,
    override_local_config: bool = False
) -> None:
    """Set or reset the global configuration for LLM settings.

    Args:
        config: Configuration source, which can be:
            - None: Reset to default configuration
            - str: Path to YAML configuration file
            - dict: Single LLM configuration
            - list: Multiple LLM configurations in priority order
        override_local_config: If True, global settings override prompt-specific ones

    Raises:
        ConfigurationError: Invalid configuration structure
        FileSystemError: Configuration file access failure
        SchemaValidationError: Configuration validation failure

    Example:
        >>> set_global_config({
        ...     "provider": "anthropic",
        ...     "model": "claude-3-opus-20240229",
        ...     "temperature": 0.7
        ... })
    """
    _set_global_config(config, override_local_config)


def get_global_config() -> dict[str, Any]:
    """Get the current global configuration.

    Returns:
        Dict[str, Any]: Current global LLM configuration settings

    Example:
        >>> config = get_global_config()
        >>> print(config["llm"]["provider"])
        "anthropic"
    """
    return _get_global_config()


def set_logs(
    path: str | Path | None = None,
    console_level: LogLevel = 'INFO',
    file_level: LogLevel = 'DEBUG',
    rotation: str = '10 MB',
    retention: str = '1 week'
) -> None:
    """Set logging configuration for LangTask.

    Args:
        path: Directory for log files. Can be string or Path object.
            If None, resets to default './logs' directory.
        console_level: Minimum level for console logging.
            Default: 'INFO'
        file_level: Minimum level for file logging.
            Default: 'DEBUG'
        rotation: When to rotate log files. Size-based (e.g., '10 MB', '1 GB')
            or time-based (e.g., '1 day', '1 week'). Default: '10 MB'
        retention: How long to keep old log files. Time-based duration
            (e.g., '1 week', '1 month'). Default: '1 week'

    Raises:
        FileSystemError: When specified directory cannot be accessed or created
        ConfigurationError: When log settings are invalid

    Example:
        >>> # Basic usage with custom path
        >>> set_logs("./my_logs")
        >>> 
        >>> # Detailed configuration
        >>> set_logs(
        ...     path="./logs",
        ...     console_level="WARNING",  # Less console output
        ...     file_level="DEBUG",       # Detailed file logs
        ...     rotation="100 MB",        # Larger log files
        ...     retention="1 month"       # Keep logs longer
        ... )
        >>> 
        >>> # Reset to defaults
        >>> set_logs()
    """
    try:
        if path is not None:
            path = Path(path)
        configure_logging(
            log_dir=path,
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