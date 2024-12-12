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


def register_prompt_directory(directory: str | Path) -> None:
    """Register or refresh a prompt directory for template discovery.
    
    Registers a new directory or refreshes an existing one, ensuring all prompt
    templates are up to date. Any changes to prompt files in registered directories
    will be detected and loaded.
    
    Args:
        directory: Path to directory containing prompt templates
        
    Raises:
        FileSystemError: When directory access fails
        InitializationError: When prompt registration fails
        
    Logs:
        INFO: New directory registration
        INFO: Existing directory refresh
        ERROR: Directory processing failures
    """
    global _dirs
    
    try:
        directory_path = Path(directory)
        str_path = str(directory_path)
        
        # Validate directory existence and accessibility
        validate_directory(directory_path)
        
        # Add to directories if new
        if str_path not in _dirs:
            _dirs.append(str_path)
            logger.info(
                "Registered new directory",
                directory=str_path,
                directory_count=len(_dirs)
            )
        else:
            logger.info(
                "Refreshing existing directory",
                directory=str_path,
                directory_count=len(_dirs)
            )
        
        # Force reinitialization to pick up any changes
        _initialize_prompts()
        
    except Exception as e:
        logger.error(
            "Failed to process directory",
            directory=str_path,
            error=str(e),
            error_type=type(e).__name__
        )
        raise InitializationError(
            message=f"Failed to process directory '{directory}'. Ensure directory exists and contains valid prompt templates.",
            component="prompt_registry",
            state="registration",
            dependencies=[str_path]
        )


def get_prompt_config(prompt_id: str) -> dict[str, Any] | None:
    """Get a prompt's configuration for LLM execution.
    
    Args:
        prompt_id: Identifier of the prompt to retrieve
        
    Returns:
        Either:
            - Prompt configuration containing LLM settings and associated files
            - None if prompt is not found
        
    Raises:
        PromptValidationError: When requested prompt doesn't exist
        InitializationError: When prompts cannot be initialized
        
    Logs:
        ERROR: Prompt not found errors
    """
    if not _prompts:
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
                    "has_llm_config": bool,     # Whether prompt has LLM settings
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
    if not _prompts:
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
        Dictionary containing prompt configuration:
            - llm: List of LLM configurations with:
                - provider: Provider name
                - model: Model identifier
                - temperature: Temperature setting
                - max_tokens: Maximum tokens limit
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
        PromptValidationError: When requested prompt doesn't exist
        InitializationError: When prompts cannot be initialized
        FileSystemError: When prompt files cannot be read
        
    Logs:
        ERROR: Prompt not found errors
        WARNING: Failed schema loading
        
    Example:
        >>> info = get_prompt_info("translate-text")
        >>> print(f"Description: {info['description']}")
        >>> if info['schemas']['input']['exists']:
        ...     print(f"Input Schema: {info['schemas']['input']['content']}")
        >>> print(f"Prompt Template: {info['instructions']}")
    """
    if not _prompts:
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
    """Initialize or refresh prompts from all registered directories.
    
    Loads all prompts from registered directories, either for initial loading
    or refreshing existing prompts to pick up any changes.
    """
    global _prompts
    
    try:
        start_time = time.time()
        
        if not _dirs:
            logger.info("No prompt directories registered")
            _prompts = {}
            return
        
        # Load all prompts
        new_prompts = discover_prompts_in_directories(_dirs)
        
        if _prompts:
            # Calculate differences
            added = set(new_prompts) - set(_prompts)
            removed = set(_prompts) - set(new_prompts)
            updated = {k for k in set(_prompts) & set(new_prompts) 
                      if new_prompts[k] != _prompts[k]}
            
            # Update prompts
            _prompts = new_prompts
            
            logger.success(
                "Prompts refreshed",
                prompt_count=len(_prompts),
                directory_count=len(_dirs),
                added=len(added),
                removed=len(removed),
                updated=len(updated),
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
            
            # Log detailed changes if any occurred
            if added or removed or updated:
                logger.info(
                    "Changes detected",
                    added=list(added) if added else None,
                    removed=list(removed) if removed else None,
                    updated=list(updated) if updated else None
                )
        else:
            # Initial load
            _prompts = new_prompts
            
            logger.success(
                "Prompts initialized",
                prompt_count=len(_prompts),
                directory_count=len(_dirs),
                duration_ms=round((time.time() - start_time) * 1000, 2)
            )
        
    except Exception as e:
        logger.error(
            "Failed to load prompts",
            error=str(e),
            error_type=type(e).__name__,
            directory_count=len(_dirs)
        )
        raise InitializationError(
            message="Failed to load prompts. Check directory permissions and prompt template formats.",
            component="prompt_registry",
            state="loading",
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