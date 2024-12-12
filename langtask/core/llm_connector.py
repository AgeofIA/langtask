"""LLM Connector Module

Manages connections to Language Learning Model (LLM) providers with unified
interface, authentication handling, and automatic fallback support.

Public Functions:
    initialize_provider: Initialize connection to first available LLM provider
"""

import os
import time

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from .config_loader import LLMConfig
from .exceptions import (
    ConfigurationError,
    EnvironmentError,
    ProviderAuthenticationError
)
from .logger import get_logger

logger = get_logger(__name__)


def initialize_provider(
    llm_configs: list[LLMConfig],
    request_id: str | None = None
) -> ChatOpenAI | ChatAnthropic:
    """Initialize connection to the first available LLM provider.

    Args:
        llm_configs: List of LLMConfig objects defining provider settings
        request_id: Optional identifier for tracing and logging

    Returns:
        Initialized provider connection to either OpenAI or Anthropic

    Raises:
        ConfigurationError: When configuration structure is invalid
        EnvironmentError: When required API keys are missing
        ProviderAuthenticationError: When all provider connections fail

    Logs:
        INFO: Attempting provider connection with details
        INFO: Provider initialized with duration
        WARNING: Unsupported provider detection
        ERROR: No LLM configurations provided
        ERROR: Unexpected initialization errors with details
        ERROR: All provider initializations failed with count and duration
    """
    if not llm_configs:
        logger.error(
            "No LLM configurations provided",
            request_id=request_id
        )
        raise ConfigurationError(
            message="At least one LLM configuration is required",
            source="provider_initialization"
        )
    
    connection_errors = []
    start_time = time.time()
    
    for config in llm_configs:
        try:
            logger.info(
                "Attempting provider connection",
                request_id=request_id,
                provider=config.provider,
                model=config.model
            )
            
            if config.provider == 'openai':
                connection = _connect_openai(
                    config.model,
                    config.temperature,
                    config.max_tokens
                )
            elif config.provider == 'anthropic':
                connection = _connect_anthropic(
                    config.model,
                    config.temperature,
                    config.max_tokens
                )
            else:
                logger.warning(
                    "Unsupported provider",
                    request_id=request_id,
                    provider=config.provider
                )
                connection_errors.append(f"Unsupported provider: {config.provider}")
                continue
                
            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "Provider initialized",
                request_id=request_id,
                provider=config.provider,
                model=config.model,
                duration_ms=round(duration_ms, 2)
            )
            return connection
                
        except (EnvironmentError, ProviderAuthenticationError):
            connection_errors.append(f"{config.provider}: Connection failed")
            continue
            
        except Exception as e:
            logger.error(
                "Unexpected initialization error",
                request_id=request_id,
                provider=config.provider,
                model=config.model,
                error=str(e),
                error_type=type(e).__name__
            )
            connection_errors.append(f"{config.provider}: {str(e)}")
    
    duration_ms = (time.time() - start_time) * 1000
    logger.error(
        "All provider initializations failed",
        request_id=request_id,
        error_count=len(connection_errors),
        duration_ms=round(duration_ms, 2)
    )
    
    raise ProviderAuthenticationError(
        message="No valid LLM provider available",
        provider="multiple",
        auth_type="initialization",
        scope=", ".join(connection_errors)
    )


def _connect_openai(
    model_name: str,
    temperature: float,
    max_tokens: int
) -> ChatOpenAI:
    """Initialize and authenticate OpenAI API connection."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise EnvironmentError(
            message="OpenAI API key missing. Get key from https://platform.openai.com/api-keys and set OPENAI_API_KEY env variable.",
            variable='OPENAI_API_KEY',
            required=True
        )
    
    try:
        return ChatOpenAI(
            temperature=temperature,
            model=model_name,
            max_tokens=max_tokens
        )
        
    except Exception as e:
        if "auth" in str(e).lower() or "key" in str(e).lower():
            raise ProviderAuthenticationError(
                message=f"OpenAI authentication failed. Verify key format (sk-...) and account status at platform.openai.com: {str(e)}",
                provider="openai",
                auth_type="api_key"
            )
        raise ProviderAuthenticationError(
            message=f"OpenAI initialization failed. Check model '{model_name}' availability and account access.",
            provider="openai",
            auth_type="initialization"
        )


def _connect_anthropic(
    model_name: str,
    temperature: float,
    max_tokens: int
) -> ChatAnthropic:
    """Initialize and authenticate Anthropic API connection."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise EnvironmentError(
            message="Anthropic API key missing. Get key from https://console.anthropic.com and set ANTHROPIC_API_KEY env variable.",
            variable='ANTHROPIC_API_KEY',
            required=True
        )
    
    try:
        return ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
    except Exception as e:
        if "auth" in str(e).lower() or "key" in str(e).lower():
            raise ProviderAuthenticationError(
                message=f"Anthropic authentication failed. Verify key format (sk-ant-...) and account status at console.anthropic.com: {str(e)}",
                provider="anthropic",
                auth_type="api_key"
            )
        raise ProviderAuthenticationError(
            message=f"Anthropic initialization failed. Check model '{model_name}' availability and account access.",
            provider="anthropic",
            auth_type="initialization"
        )