"""Prompt Registry Module

Manages prompt template discovery and registration from registered directories.
Provides centralized prompt access with validation and error handling.

Public Functions:
    register_prompt_directory: Register a prompt directory
    get_prompt: Get specific prompt by id
    get_directories_list: Get list of registered directories
    get_prompts_list: Get list of registered prompts with basic information
    get_prompt_info: Get full formatted information for a specific prompt
"""

import time
from pathlib import Path
from typing import Any

from .exceptions import (
    FileSystemError,
    InitializationError, 
    PromptValidationError,
    SchemaValidationError
)
from .file_validator import validate_directory
from .logger import get_logger
from .prompt_discoverer import discover_prompts_in_directories
from .schema_loader import load_yaml_schema

logger = get_logger(__name__)


# Registry data
_prompts: dict[str, Any] = {}
_dirs: list[str] = []
_initialized: bool = False


def register_prompt_directory(directory: str | Path) -> None:
    """Register a prompt directory for template discovery.
    
    Args:
        directory: Path to directory containing prompt templates
        
    Raises:
        FileSystemError: When directory access fails
        InitializationError: When prompt registration fails
        
    Logs:
        - Directory registration (INFO)
        - Duplicate directory warnings (WARNING)
        - Registration failures (ERROR)
    """
    global _dirs, _initialized
    
    try:
        directory_path = Path(directory)
        
        # Validate directory existence and accessibility
        validate_directory(directory_path)
            
        if str(directory_path) in _dirs:
            logger.warning(
                "Directory already registered",
                directory=str(directory_path)
            )
            return
            
        _dirs.append(str(directory_path))
        _initialized = False
        
        logger.info(
            "Registered prompt directory",
            directory=str(directory_path)
        )
        
        _initialize_prompts()
        
    except FileSystemError:
        raise
        
    except Exception as e:
        logger.error(
            "Failed to register prompt directory",
            directory=str(directory),
            error=str(e),
            error_type=type(e).__name__
        )
        raise InitializationError(
            message=f"Failed to register '{directory}'. Ensure directory exists and contains valid prompt templates.",
            component="prompt_registry",
            state="registration",
            dependencies=[str(directory)]
        )


def get_prompt_config(prompt_id: str) -> dict[str, Any] | None:
    """Get a prompt's configuration for LLM execution.
    
    Args:
        prompt_id: Identifier of the prompt to retrieve
        
    Returns:
        Optional[Dict]: Prompt configuration if found, containing:
            - config: LLM and prompt settings
            - files: Associated template and schema files
        
    Raises:
        PromptValidationError: When requested prompt doesn't exist
        InitializationError: When prompts cannot be initialized
        
    Logs:
        - Prompt not found errors (ERROR)
    """
    if not _initialized:
        _initialize_prompts()
    
    prompt = _prompts.get(prompt_id)
    if not prompt:
        if not _dirs:
            error_msg = "No prompt directories registered. Register a directory before requesting prompts."
        else:
            registered = ", ".join(_prompts.keys())
            error_msg = f"Prompt '{prompt_id}' not found. Available prompts: {registered}"
            
        logger.error(
            "Prompt not found",
            prompt_id=prompt_id,
            registered_dirs=len(_dirs)
        )
        raise PromptValidationError(
            message=error_msg,
            prompt_path=str(_dirs[0]) if _dirs else "<no directories registered>",
            validation_type="existence"
        )
        
    return prompt


def get_directories_list() -> list[str]:
    """Get list of registered prompt directories.
    
    Returns:
        List[str]: List of directory paths as strings
        
    Note:
        Returns empty list if no directories are registered
        
    Example:
        >>> dirs = get_directories_info()
        >>> print(dirs)
        ['/path/to/prompts1', '/path/to/prompts2']
    """
    return _dirs.copy()


def get_prompts_list() -> dict[str, dict[str, Any]]:
    """Get simplified list of registered prompts.
    
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping prompt IDs to basic information:
            {
                "prompt-id": {
                    "display_name": str,        # Optional display name 
                    "description": str,         # Optional description
                    "has_llm_config": bool,           # Whether prompt has LLM settings
                    "has_input_schema": bool,   # Whether input schema exists
                    "has_output_schema": bool   # Whether output schema exists
                }
            }
    
    Note:
        Returns lightweight prompt information suitable for listing and discovery.
        For detailed configuration including schemas and complete LLM settings,
        use get_prompt_info().
        
    Example:
        >>> prompts = get_prompts_list()
        >>> for id, info in prompts.items():
        ...     print(f"{info['display_name']}: {info['description']}")
        ...     if info['has_llm_config']:
        ...         print("LLM settings configured")
    """
    if not _initialized:
        _initialize_prompts()
        
    return {
        prompt_id: {
            "display_name": info['config'].display_name or prompt_id,
            "description": info['config'].description or "",
            "has_llm_config": bool(info['config'].llm),
            "has_input_schema": 'input_schema.yaml' in info['files'],
            "has_output_schema": 'output_schema.yaml' in info['files']
        }
        for prompt_id, info in _prompts.items()
    }


def get_prompt_info(prompt_id: str) -> dict[str, Any]:
    """Get configuration information for a specific prompt.
    
    Args:
        prompt_id: ID of the prompt to retrieve info for
        
    Returns:
        Dict[str, Any]: Dictionary containing prompt configuration:
            - llm: List[Dict] - List of LLM configurations with:
                - provider: str
                - model: str
                - temperature: float
                - max_tokens: int
            - schemas: Dict - Schema information:
                - input: Dict
                    - exists: bool - True if schema exists
                    - content: Optional[Dict] - Schema content if exists
                - output: Dict
                    - exists: bool - True if schema exists
                    - content: Optional[Dict] - Schema content if exists
            - display_name: str - Optional display name (if present)
            - description: str - Optional prompt description (if present)
            - instructions: str - Content of instructions.md template
                
    Raises:
        PromptValidationError: When requested prompt doesn't exist
        InitializationError: When prompts cannot be initialized
        FileSystemError: When prompt files cannot be read
        
    Example:
        >>> info = get_prompt_info("translate-text")
        >>> print(f"Description: {info['description']}")
        >>> if info['schemas']['input']['exists']:
        ...     print(f"Input Schema: {info['schemas']['input']['content']}")
        >>> print(f"Prompt Template: {info['instructions']}")
    """
    if not _initialized:
        _initialize_prompts()
    
    prompt = _prompts.get(prompt_id)
    if not prompt:
        if not _dirs:
            error_msg = "No prompt directories registered. Register a directory before requesting prompts."
        else:
            registered = ", ".join(_prompts.keys())
            error_msg = f"Prompt '{prompt_id}' not found. Available prompts: {registered}"
            
        logger.error(
            "Prompt not found",
            prompt_id=prompt_id,
            registered_dirs=len(_dirs)
        )
        raise PromptValidationError(
            message=error_msg,
            prompt_path=str(_dirs[0]) if _dirs else "<no directories registered>",
            validation_type="existence"
        )
    
    return _format_prompt_info(prompt)


def _initialize_prompts() -> None:
    """Initialize prompts from all registered directories."""
    global _prompts, _initialized
    
    if _initialized:
        logger.info("Prompts already initialized")
        return
        
    try:
        start_time = time.time()
        
        if not _dirs:
            logger.info("No prompt directories registered")
            _prompts = {}
            _initialized = True
            return
        
        logger.info(
            "Initializing prompts",
            directory_count=len(_dirs)
        )
        
        _prompts = discover_prompts_in_directories(_dirs)
        _initialized = True
        
        duration_ms = (time.time() - start_time) * 1000
        logger.success(
            "Prompts initialized successfully",
            prompt_count=len(_prompts),
            directory_count=len(_dirs),
            duration_ms=round(duration_ms, 2)
        )
        
    except FileSystemError:
        raise
        
    except Exception as e:
        logger.error(
            "Failed to initialize prompts",
            error=str(e),
            error_type=type(e).__name__
        )
        raise InitializationError(
            message="Failed to initialize prompts. Check directory permissions and prompt template formats.",
            component="prompt_registry",
            state="initialization",
            dependencies=_dirs
        )


def _format_prompt_info(prompt_data: dict[str, Any]) -> dict[str, Any]:
    """Format raw prompt data into standardized info dictionary."""
    # Format LLM configs
    llm_configs = []
    config_llms = prompt_data['config'].llm if isinstance(prompt_data['config'].llm, list) else [prompt_data['config'].llm]
    for llm in config_llms:
        llm_configs.append({
            "provider": llm.provider,
            "model": llm.model,
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens
        })
        
    # Process schemas with content
    schemas = {
        "input": {"exists": False, "content": None},
        "output": {"exists": False, "content": None}
    }
    
    # Load input schema if present
    if 'input_schema.yaml' in prompt_data['files']:
        schemas['input']['exists'] = True
        try:
            schema = load_yaml_schema(prompt_data['files']['input_schema.yaml'])
            if schema:
                schemas['input']['content'] = schema.model_json_schema()
        except SchemaValidationError as e:
            logger.warning(
                "Failed to load input schema",
                prompt_id=prompt_data['config'].id,
                error=str(e)
            )
    
    # Load output schema if present
    if 'output_schema.yaml' in prompt_data['files']:
        schemas['output']['exists'] = True
        try:
            schema = load_yaml_schema(prompt_data['files']['output_schema.yaml'])
            if schema:
                schemas['output']['content'] = schema.model_json_schema()
        except SchemaValidationError as e:
            logger.warning(
                "Failed to load output schema",
                prompt_id=prompt_data['config'].id,
                error=str(e)
            )
    
    # Build base response with required fields
    response = {
        "llm": llm_configs,
        "schemas": schemas
    }
    
    # Include optional display-related fields if present
    if display_name := prompt_data['config'].display_name:
        response["display_name"] = display_name
        
    if description := prompt_data['config'].description:
        response["description"] = description
        
    # Add instructions content - read_text_file already raises FileSystemError appropriately
    try:
        from .file_reader import read_text_file
        response["instructions"] = read_text_file(prompt_data['files']['instructions.md'])
    except FileSystemError:
        raise
        
    return response