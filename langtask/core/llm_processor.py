"""LLM Request Processing Module

Handles the complete lifecycle of Language Model (LLM) requests from prompt
preparation through response processing. Provides a robust interface for
executing LLM operations with proper validation, error handling, and logging.

Public Functions:
    process_llm_request: Process an LLM request with complete lifecycle handling
"""

import time
import uuid
from typing import Any, Type

from langchain.prompts import ChatPromptTemplate

from .exceptions import (
    DataValidationError,
    ExecutionError,
    PromptValidationError,
    ProviderAPIError,
    SchemaValidationError
)
from .input_validator import validate_prompt_input
from .output_validator import handle_structured_output
from .llm_connector import initialize_provider
from .logger import get_logger
from .prompt_loader import load_prompt
from .prompt_registrar import get_prompt_config
from .schema_loader import StructuredResponse

logger = get_logger(__name__)


def process_llm_request(prompt_id: str, input_params: dict[str, Any] | None = None) -> str | StructuredResponse:
    """Process an LLM request with complete lifecycle handling.

    Manages request processing with:
    - Prompt loading and validation
    - Input parameter validation
    - LLM interaction
    - Response processing

    Args:
        prompt_id: ID of the registered prompt to use
        input_params: Optional parameters required by the prompt template

    Returns:
        Either:
            - Raw text response when no schema is specified
            - Object with field access when schema is defined

    Raises:
        ExecutionError: For processing and runtime failures
        ProviderAPIError: For LLM provider communication issues
        DataValidationError: For input validation failures
        SchemaValidationError: For schema validation failures
        PromptValidationError: When prompt not found or no directories registered

    Logs:
        - Request start with ID (INFO)
        - Request completion with metrics (SUCCESS)
        - Validation and provider errors (ERROR)
        - Unexpected failures (ERROR)

    Example:
        >>> # Simple text response
        >>> result = process_llm_request("greeting-prompt", {"name": "Alice"})
        >>> print(result)
        Hello, Alice! How are you today?

        >>> # Structured response with schema
        >>> result = process_llm_request("analyze-sentiment", {"text": "Great day!"})
        >>> print(result.sentiment)  # Access fields directly
        positive
        >>> print(result.confidence:.2f)  # Access numeric fields
        0.95
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    try:
        logger.info(
            "Starting request processing",
            request_id=request_id,
            prompt_id=prompt_id
        )
        
        # Load Prompt and Configuration
        prompt_config = get_prompt_config(prompt_id)
        prompt_template, output_schema, input_schema = load_prompt(
            prompt_id, 
            prompt_config,
            request_id
        )
        
        # Initialize Provider and Validate Input
        provider = initialize_provider(prompt_config['config'].llm, request_id=request_id)
        validated_params = validate_prompt_input(
            input_schema, 
            input_params, 
            prompt_template.input_variables,
            request_id
        )

        # Process Request
        response = _process_llm_call(
            provider,
            prompt_template,
            validated_params,
            output_schema,
            request_id
        )

        logger.success(
            "Request processed successfully",
            request_id=request_id,
            prompt_id=prompt_id,
            duration_ms=_get_duration_ms(start_time),
            has_schema=bool(output_schema),
            params_count=len(validated_params or {})
        )
        
        return response

    except (DataValidationError, PromptValidationError, ProviderAPIError, SchemaValidationError):
        logger.error(
            "Request failed with validation or provider error",
            request_id=request_id,
            prompt_id=prompt_id,
            duration_ms=_get_duration_ms(start_time)
        )
        raise
        
    except Exception as e:
        logger.error(
            "Request failed with unexpected error",
            request_id=request_id,
            prompt_id=prompt_id,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=_get_duration_ms(start_time)
        )
        raise ExecutionError(
            message=f"Request processing failed. Check prompt configuration and LLM provider status.",
            operation="request_processing"
        )


def _process_llm_call(
    provider: Any,
    prompt: ChatPromptTemplate,
    params: dict[str, Any],
    output_schema: Type[StructuredResponse] | None,
    request_id: str
) -> str | StructuredResponse:
    """Handle core LLM interaction with error handling and response processing."""
    start_time = time.time()
    provider_name = provider.__class__.__name__
    
    try:
        # Prepare and Send Request
        messages = prompt.format_prompt(**params)
        
        # Log request initiation at INFO level
        logger.info(
            "Initiating LLM request",
            request_id=request_id,
            provider=provider_name
        )
        
        # Log detailed message content at DEBUG level
        logger.debug(
            "Sending prompt to LLM",
            request_id=request_id,
            messages=messages.to_string(),
            provider=provider_name
        )

        # Process Response
        if output_schema:
            response = handle_structured_output(
                provider,
                messages,
                output_schema,
                request_id
            )
        else:
            response = provider.invoke(messages.to_messages())
            response = response.content

        logger.debug(
            "LLM response received",
            request_id=request_id,
            duration_ms=_get_duration_ms(start_time),
            response_type=type(response).__name__
        )
        
        return response

    except (SchemaValidationError, ProviderAPIError):
        raise
        
    except Exception as e:
        logger.error(
            "LLM call failed",
            request_id=request_id,
            error=str(e),
            duration_ms=_get_duration_ms(start_time),
            provider=provider_name
        )
        raise ProviderAPIError(
            message=f"LLM request failed ({provider_name}). Check API status and rate limits.",
            provider=provider_name,
            response=getattr(e, 'response', None)
        )


def _get_duration_ms(start_time: float) -> float:
    """Calculate duration in milliseconds from start time."""
    return round((time.time() - start_time) * 1000, 2)