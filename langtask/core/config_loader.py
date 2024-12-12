"""Configuration Loading Module

Manages Language Model (LLM) configurations at global and prompt-specific levels,
supporting multiple providers and configuration sources with validation.

Public Functions:
    set_global_config: Set or reset global LLM configuration
    get_global_config: Retrieve current global configuration
    get_llm_provider_globals: Get settings for specific LLM provider
    get_default_llm_provider: Get default LLM provider name
    should_override_local_config: Check global config override status
    load_config: Load and validate prompt configuration from file
"""

from typing import Any
from pathlib import Path

from pydantic import ValidationError

from .config_models import GlobalConfig, LLMConfig, PromptConfig
from .exceptions import ConfigurationError, FileSystemError, SchemaValidationError
from .file_reader import read_yaml_file
from .logger import get_logger

logger = get_logger(__name__)


# Global state
_global_config: GlobalConfig = GlobalConfig()
_override_local_config: bool = False


def set_global_config(
    config: str | dict[str, Any] | list[dict[str, Any]] | None = None,
    override_local_config: bool = False
) -> None:
    """Set or reset the global LLM configuration.
    
    Establishes global configuration settings that can either serve as defaults
    or override local prompt-specific configurations.
    
    Args:
        config: Configuration source, which can be:
            - None: Resets to default configuration
            - str: Path to YAML configuration file
            - dict: Single LLM configuration
            - list: Multiple LLM configurations in priority order
        override_local_config: If True, global settings override prompt-specific ones
    
    Raises:
        ConfigurationError: Invalid configuration structure
        FileSystemError: Configuration file access failure
        SchemaValidationError: Configuration validation failure
        
    Logs:
        INFO: Global configuration updates with config count
        ERROR: Configuration validation failures with details
        ERROR: Unexpected configuration errors
    """
    global _global_config, _override_local_config
    
    try:
        if config is None:
            _reset_global_config()
            return

        llm_config = _parse_config_input(config)
        _global_config = GlobalConfig(llm=llm_config)
        _override_local_config = override_local_config
        
        logger.info(
            "Global configuration updated",
            config_count=len(llm_config) if isinstance(llm_config, list) else 1,
            override_local=override_local_config
        )
        
    except ValidationError as e:
        logger.error(
            "Configuration validation failed",
            errors=e.errors()
        )
        raise SchemaValidationError(
            message=f"Invalid config schema. Check provider, model, temperature (0-1), and max_tokens fields: {e.errors()[0]['msg']}",
            schema_type="config",
            constraints={"validation_errors": e.errors()}
        )
        
    except (FileSystemError, SchemaValidationError):
        raise
        
    except Exception as e:
        logger.error(
            "Unexpected configuration error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise ConfigurationError(
            message=f"Failed to set config. Ensure valid LLM provider settings and try again.",
            source="global"
        )


def get_global_config() -> dict[str, Any]:
    """Get the current global configuration settings."""
    return _global_config.model_dump()


def get_llm_provider_globals(llm_provider: str) -> dict[str, Any] | None:
    """Get configuration settings for a specific LLM provider.

    Args:
        llm_provider: Provider identifier (e.g., 'anthropic', 'openai')

    Returns:
        Provider configuration settings if found, None otherwise
    """
    llm_configs = _global_config.llm if isinstance(_global_config.llm, list) else [_global_config.llm]
    for config in llm_configs:
        if config.provider == llm_provider:
            return config.model_dump()
    return None


def get_default_llm_provider() -> str | None:
    """Get the default LLM provider from global configuration."""
    llm_configs = _global_config.llm if isinstance(_global_config.llm, list) else [_global_config.llm]
    return llm_configs[0].provider if llm_configs else None


def should_override_local_config() -> bool:
    """Check if global config should override local configs."""
    return _override_local_config


def load_config(file_path: str | Path) -> PromptConfig:
    """Load and validate a prompt configuration from a YAML file.
    
    Processes prompt-specific configurations with optional inheritance from
    global settings based on override settings.
    
    Args:
        file_path: Path to the YAML configuration file. Can be string or Path object.
    
    Returns:
        PromptConfig: Validated configuration object with resolved settings
    
    Raises:
        ConfigurationError: Invalid configuration structure
        FileSystemError: Configuration file access failure
        SchemaValidationError: Configuration validation failure
        
    Logs:
        DEBUG: Successful configuration loads with prompt ID and path
        ERROR: Validation failures with detailed error context
        ERROR: General load failures with error details
    """
    path = Path(file_path)
    config_key = path.stem
    
    try:
        config_dict = read_yaml_file(file_path)
        
        if not isinstance(config_dict, dict):
            raise SchemaValidationError(
                message=f"Config file must be a YAML dictionary, found {type(config_dict).__name__}",
                schema_type="config",
                field=config_key
            )
            
        config = PromptConfig.model_validate(config_dict)
        
        if should_override_local_config() or not config.llm:
            _apply_global_defaults(config)
            
        logger.debug(
            "Configuration loaded successfully",
            prompt_id=config.id,
            file_path=str(path)
        )
        
        return config
        
    except ValidationError as e:
        prompt_id = config_dict.get('id', 'unknown') if isinstance(config_dict, dict) else 'unknown'
        logger.error(
            "Configuration validation failed",
            prompt_id=prompt_id,
            file_path=str(path),
            errors=e.errors()
        )
        raise SchemaValidationError(
            message=f"Invalid config in {path.name}. Required fields: id, llm provider/model. Error: {e.errors()[0]['msg']}",
            schema_type="config",
            field=prompt_id,
            constraints={"validation_errors": e.errors()}
        )
        
    except (FileSystemError, SchemaValidationError):
        raise
        
    except Exception as e:
        logger.error(
            "Failed to load configuration",
            file_path=str(path),
            error=str(e)
        )
        raise ConfigurationError(
            message=f"Failed to load configuration: {str(e)}",
            config_key=config_key,
            source=str(path)
        )


def _reset_global_config() -> None:
    """Reset global configuration to defaults."""
    global _global_config, _override_local_config
    _global_config = GlobalConfig()
    _override_local_config = False
    logger.info("Global configuration reset to defaults")


def _parse_config_input(
    config: str | dict[str, Any] | list[dict[str, Any]]
) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse and validate configuration input from various sources.
    
    Handles file paths, direct dictionaries, and configuration lists while
    ensuring proper structure and presence of required keys.
    """
    if isinstance(config, str):
        data = read_yaml_file(config)
        if not isinstance(data, dict):
            raise ConfigurationError(
                message="Config file must be a YAML dictionary with LLM settings.",
                source=config
            )
        if 'llm' not in data:
            raise ConfigurationError(
                message="Missing required 'llm' key in config. Define provider and model settings.",
                config_key='llm',
                source=config
            )
        return data['llm']
        
    return [config] if isinstance(config, dict) else config


def _apply_global_defaults(config: PromptConfig) -> None:
    """Apply global LLM defaults to prompt configuration.
    
    Updates prompt config with global provider settings when appropriate,
    respecting override settings and maintaining default values.
    """
    default_provider = get_default_llm_provider()
    if not default_provider:
        return
        
    globals = get_llm_provider_globals(default_provider)
    if globals:
        default_llm = LLMConfig(
            provider=default_provider,
            model=globals.get('model', ''),
            temperature=globals.get('temperature', LLMConfig.model_fields['temperature'].default),
            max_tokens=globals.get('max_tokens', LLMConfig.model_fields['max_tokens'].default)
        )
        config.llm = [default_llm]