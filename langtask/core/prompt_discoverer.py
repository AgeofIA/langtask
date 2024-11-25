"""Prompt Discovery Module

Discovers and validates prompt configurations across multiple directories.
Handles file structure validation, config loading, and error reporting.

Public Functions:
    discover_prompts_in_directories: Discover and validate prompts from directories
"""

import time
from pathlib import Path

from .config_loader import load_config
from .exceptions import FileSystemError, PromptValidationError
from .file_reader import read_text_file
from .file_validator import validate_directory, validate_file
from .logger import get_logger
from .prompt_loader import check_input_params_in_instructions

logger = get_logger(__name__)


# File structure requirements
REQUIRED_FILES: set[str] = {'config.yaml', 'instructions.md'}
OPTIONAL_FILES: set[str] = {'input_schema.yaml', 'output_schema.yaml'}


def discover_prompts_in_directories(directories: list[str | Path]) -> dict[str, dict]:
    """Discover and validate all prompts from the provided directories.

    Performs directory scanning with:
    - File structure validation
    - Config loading and validation
    - Duplicate prompt detection
    - Performance monitoring

    Args:
        directories: List of paths to directories containing prompts.
            Accepts both string paths and Path objects.

    Returns:
        Dict[str, Dict]: Mapping of prompt IDs to their configurations
            and metadata. Each entry contains:
            - config: Prompt configuration
            - files: Paths to prompt files
            - source_directory: Original directory path

    Raises:
        FileSystemError: When directory access fails
        PromptValidationError: When:
            - Required files are missing
            - Config validation fails
            - Duplicate prompts are found
            - File processing fails

    Logs:
        - Discovery start with directory count (INFO)
        - Individual prompt discovery (INFO)
        - Duplicate prompt warnings (WARNING)
        - Processing errors (ERROR)
        - Completion metrics (SUCCESS)
    """
    start_time = time.time()
    discovered_prompts: dict[str, dict] = {}
    
    try:
        logger.info(
            "Starting prompt discovery",
            directory_count=len(directories)
        )
        
        # Validate and process each directory
        for directory in directories:
            dir_path = Path(directory).resolve()
            validate_directory(dir_path)
            
            logger.debug(
                "Processing directory",
                directory=str(dir_path)
            )
            
            _discover_prompts_in_directory(dir_path, discovered_prompts)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.success(
            "Prompt discovery completed",
            prompt_count=len(discovered_prompts),
            duration_ms=round(duration_ms, 2)
        )
        
        return discovered_prompts
        
    except (FileSystemError, PromptValidationError):
        raise
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Prompt discovery failed",
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2)
        )
        raise PromptValidationError(
            message="Failed to discover prompts. Check directory permissions and structure: prompts/{id}/{config.yaml,instructions.md}",
            validation_type="discovery",
            prompt_path="multiple_directories"
        )


def _discover_prompts_in_directory(
    directory: Path,
    discovered_prompts: dict
) -> None:
    """Process single directory and update discovered_prompts dict."""
    logger.info(
        "Scanning directory for prompts",
        directory=str(directory)
    )
    
    try:
        # Scan directory
        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith('__'):
                continue
                
            try:
                prompt_files = _validate_prompt_files(item)
                config = load_config(prompt_files['config.yaml'])
                
                # Validate prompt id
                if not config.id:
                    logger.error(
                        "Missing prompt ID in config",
                        path=str(item)
                    )
                    raise PromptValidationError(
                        message="Config must have 'id' field in config.yaml",
                        validation_type="config",
                        prompt_path=str(item)
                    )
                
                # Check for duplicate prompt ids
                if config.id in discovered_prompts:
                    logger.warning(
                        "Duplicate prompt ID found",
                        prompt_id=config.id,
                        original_path=str(discovered_prompts[config.id]['source_directory']),
                        duplicate_path=str(directory)
                    )
                
                # Store prompt configuration
                discovered_prompts[config.id] = {
                    'config': config,
                    'files': prompt_files,
                    'source_directory': directory
                }
                
                logger.info(
                    "Discovered prompt",
                    prompt_id=config.id,
                    directory=str(directory),
                    llm_count=len(config.llm)
                )
                
            except (FileSystemError, PromptValidationError):
                raise
                
            except Exception as e:
                logger.error(
                    "Failed to process prompt",
                    path=str(item),
                    error=str(e),
                    error_type=type(e).__name__
                )
                raise PromptValidationError(
                    message=f"Invalid prompt in {item.name}. Verify config.yaml formatting and required fields.",
                    validation_type="processing",
                    prompt_path=str(item)
                )
                
    except FileSystemError:
        raise
        
    except PromptValidationError:
        raise
        
    except Exception as e:
        logger.error(
            "Error scanning directory",
            directory=str(directory),
            error=str(e),
            error_type=type(e).__name__
        )
        raise PromptValidationError(
            message=f"Cannot scan {directory.name}. Check directory permissions and contents.",
            validation_type="directory",
            prompt_path=str(directory)
        )


def _validate_prompt_files(prompt_path: Path) -> dict[str, Path]:
    """Validate prompt directory structure and return mapping of valid file paths."""
    prompt_files: dict[str, Path] = {}
    
    try:
        # Validate required files
        missing_files = []
        for file in REQUIRED_FILES:
            file_path = prompt_path / file
            if not validate_file(file_path, required=True):
                missing_files.append(file)
            else:
                prompt_files[file] = file_path
                
        if missing_files:
            raise PromptValidationError(
                message=f"Prompt {prompt_path.name} missing required files: {', '.join(missing_files)}. Each prompt needs config.yaml and instructions.md",
                validation_type="required_files",
                prompt_path=str(prompt_path),
                constraints={"missing_files": missing_files}
            )
        
        # Check optional files
        for file in OPTIONAL_FILES:
            file_path = prompt_path / file
            if validate_file(file_path, required=False):
                prompt_files[file] = file_path
        
        # Validate input parameters usage
        try:
            instructions_content = read_text_file(prompt_files['instructions.md'])
            input_params_used = check_input_params_in_instructions(instructions_content)
            
            if input_params_used and 'input_schema.yaml' not in prompt_files:
                logger.warning(
                    "Input parameters used without schema",
                    prompt_path=str(prompt_path),
                    message="Input validation will be skipped"
                )
                
        except FileSystemError as e:
            raise PromptValidationError(
                message=f"Cannot read instructions.md in {prompt_path.name}. Check file permissions and content.",
                validation_type="instructions",
                prompt_path=str(prompt_path),
                constraints={"error": str(e)}
            )
        
        return prompt_files
        
    except (FileSystemError, PromptValidationError):
        raise
        
    except Exception as e:
        logger.error(
            "Unexpected error validating prompt files",
            prompt_path=str(prompt_path),
            error=str(e)
        )
        raise PromptValidationError(
            message=f"Invalid prompt structure in {prompt_path.name}. Ensure all required files exist and are properly formatted.",
            validation_type="validation",
            prompt_path=str(prompt_path)
        )