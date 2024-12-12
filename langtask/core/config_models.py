"""Configuration Models

Defines Pydantic models for managing LLM provider settings, global configurations,
and prompt-specific settings. Enforces validation rules with clear error reporting.

Public Classes:
    LLMConfig: Configuration for specific LLM provider instances
    GlobalConfig: Global LLM configuration settings
    PromptConfig: Prompt-specific configuration and metadata
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .exceptions import ConfigurationError


# Default configuration values
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_TOKENS = 4096
ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9-_]*$')


class LLMConfig(BaseModel):
    """Configuration settings for a specific LLM provider instance.
    
    Validates and enforces parameter ranges for temperature and token limits.
    Automatically applies default values when parameters are unspecified.
    
    Args:
        provider: LLM provider name ('openai' or 'anthropic')
        model: Model identifier string
        temperature: Sampling temperature (0.0 to 1.0)
        max_tokens: Maximum tokens to generate (>0)
    
    Raises:
        ConfigurationError: If temperature or max_tokens are outside valid ranges
    
    Example:
        >>> config = LLMConfig(
        ...     provider='anthropic',
        ...     model='claude-3-5-haiku-20241022',
        ...     temperature=0.7,
        ...     max_tokens=1000
        ... )
    """
    provider: Literal['openai', 'anthropic']
    model: str
    temperature: float | None = Field(default=DEFAULT_TEMPERATURE)
    max_tokens: int | None = Field(default=DEFAULT_MAX_TOKENS)
    
    @model_validator(mode='after')
    def set_defaults_for_none(self) -> 'LLMConfig':
        """Set defaults for None values."""
        if self.temperature is None:
            self.temperature = DEFAULT_TEMPERATURE
        if self.max_tokens is None:
            self.max_tokens = DEFAULT_MAX_TOKENS
        return self

    @model_validator(mode='after')
    def validate_ranges(self) -> 'LLMConfig':
        """Validate parameter ranges for temperature and max_tokens."""
        if not 0.0 <= self.temperature <= 1.0:
            raise ConfigurationError(
                message=f"Temperature {self.temperature} invalid: must be between 0.0 and 1.0",
                config_key="temperature",
                source="llm_config"
            )
            
        if self.max_tokens <= 0:
            raise ConfigurationError(
                message=f"Max tokens {self.max_tokens} invalid: must be greater than 0",
                config_key="max_tokens",
                source="llm_config"
            )
        return self


class GlobalConfig(BaseModel):
    """Global LLM configuration settings.
    
    Manages single or multiple LLM configurations in priority order.
    When multiple configs are provided, they are tried in sequence
    until successful completion.
    
    Args:
        llm: Single LLMConfig or list of configs in priority order
    
    Example:
        # Single config
        >>> config = GlobalConfig(llm=LLMConfig(...))
        
        # Multiple configs with fallback
        >>> config = GlobalConfig(llm=[
        ...     LLMConfig(provider='anthropic', ...),
        ...     LLMConfig(provider='openai', ...)
        ... ])
    """
    llm: LLMConfig | list[LLMConfig] = Field(default_factory=list)


class PromptConfig(BaseModel):
    """Prompt-specific configuration and metadata.
    
    Manages prompt configurations with flexible LLM settings specification.
    Supports both direct dictionary configuration and prioritized config lists.
    
    Args:
        id: Unique identifier for the prompt (lowercase alphanumeric with - and _)
        display_name: Optional human-friendly name for display purposes
        description: Optional description of the prompt's purpose
        llm: LLM configuration as dict or list of LLMConfig objects
    
    Raises:
        ConfigurationError: If configuration is invalid or cannot be parsed
    
    Example:
        >>> config = PromptConfig(
        ...     id="greeting-prompt",
        ...     display_name="Personalized Greeting Generator",
        ...     description="Generates personalized greetings",
        ...     llm=[LLMConfig(...), LLMConfig(...)]
        ... )
    """
    id: str
    display_name: str | None = None
    description: str | None = None
    llm: list[LLMConfig] | dict[str, str | float | int]

    @model_validator(mode='after')
    def validate_id_format(self) -> 'PromptConfig':
        """Validate id format and case."""
        if not ID_PATTERN.match(self.id):
            raise ConfigurationError(
                message=(
                    f"Invalid prompt id '{self.id}'. Must start with letter/number "
                    "and contain only lowercase letters, numbers, hyphens, or underscores"
                ),
                config_key="id",
                source="prompt_config"
            )
        return self

    @model_validator(mode='after')
    def validate_and_convert_llm(self) -> 'PromptConfig':
        """Convert dict config to list format."""
        try:
            if isinstance(self.llm, dict):
                self.llm = [LLMConfig(**self.llm)]
            elif not isinstance(self.llm, list):
                raise ConfigurationError(
                    message="LLM config must be a dictionary or list of provider settings",
                    config_key="llm",
                    source="prompt_config"
                )
            return self
            
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
                
            if "type_error" in str(e).lower():
                raise ConfigurationError(
                    message="Invalid LLM config format. Required: provider (openai/anthropic) and model name",
                    config_key="llm",
                    source="prompt_config"
                )
            
            raise ConfigurationError(
                message=f"Invalid LLM config: {str(e)}. Check provider and model settings",
                config_key="llm",
                source="prompt_config"
            )