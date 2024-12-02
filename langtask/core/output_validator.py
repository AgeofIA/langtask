"""Output Validation Module

Validates LLM outputs against schema definitions with detailed error reporting.
Handles common validation scenarios and provides actionable error messages.

Public Functions:
    validate_llm_output: Validate LLM response against output schema
    handle_structured_output: Process and validate structured LLM output
"""

from typing import Any, Type

from langchain_core.output_parsers import BaseOutputParser
from langchain_core.outputs import ChatGeneration, Generation
from pydantic import ValidationError

from .exceptions import SchemaValidationError, ProviderAPIError
from .logger import get_logger
from .schema_loader import StructuredResponse

logger = get_logger(__name__)


def handle_structured_output(
    provider: Any,
    messages: Any,
    output_schema: Type[StructuredResponse],
    request_id: str
) -> StructuredResponse:
    """Process LLM response with structured output schema validation.

    Handles structured output processing with:
    - Provider output formatting
    - Schema validation
    - Error categorization
    - Detailed error reporting

    Args:
        provider: LLM provider instance (ChatOpenAI or ChatAnthropic)
        messages: Formatted prompt messages to send to LLM
        output_schema: Response schema class defining expected structure
        request_id: Request identifier for tracing

    Returns:
        StructuredResponse: Validated response object with field access via dot notation

    Raises:
        SchemaValidationError: When:
            - Response doesn't match schema
            - Required fields are missing
            - Field types don't match
            - Response format is invalid
        ProviderAPIError: When provider communication or processing fails

    Logs:
        - Validation failures with details (ERROR)
        - Processing errors with context (ERROR)
        - Success metrics (DEBUG)

    Example:
        >>> schema = SentimentResponse
        >>> response = handle_structured_output(
        ...     provider=llm_provider,
        ...     messages=formatted_prompt,
        ...     output_schema=schema,
        ...     request_id="123"
        ... )
        >>> print(response.sentiment)  # Access fields with dot notation
    """
    try:
        structured_provider = provider.with_structured_output(output_schema)
        response = structured_provider.invoke(messages.to_messages())
        return validate_llm_output(response, output_schema, request_id)
        
    except SchemaValidationError:
        raise
        
    except ValidationError as e:
        logger.error(
            "Output validation failed",
            request_id=request_id,
            error=str(e),
            schema=output_schema.__name__
        )
        raise SchemaValidationError(
            message=(
                "LLM response format validation failed. The response was returned as a string "
                "instead of structured data. Update the prompt to ensure the LLM returns properly "
                "structured output that matches your schema."
            ),
            schema_type="output",
            field=output_schema.__name__,
            constraints={"validation_errors": e.errors()}
        )
        
    except Exception as e:
        is_parsing_error = (
            isinstance(e, BaseOutputParser.OutputParserException) or
            (hasattr(e, '__cause__') and isinstance(e.__cause__, ValidationError))
        )
        
        logger.error(
            "Structured output processing failed",
            request_id=request_id,
            error=str(e),
            error_type=type(e).__name__,
            schema=output_schema.__name__,
            is_parsing_error=is_parsing_error
        )
        
        if is_parsing_error:
            raise SchemaValidationError(
                message=f"Failed to parse LLM response into expected schema format. Review output_schema.yaml and prompt instructions.",
                schema_type="output",
                field=output_schema.__name__,
                constraints={"error": str(e)}
            )
            
        raise ProviderAPIError(
            message=f"Failed to process structured output. Check provider status and API limits.",
            provider=provider.__class__.__name__,
            response=getattr(e, 'response', None)
        )


def validate_llm_output(
    output_data: Any,
    output_schema: Type[StructuredResponse],
    request_id: str
) -> StructuredResponse:
    """Validate LLM output against schema definition.

    Performs validation with:
    - Schema compliance checking
    - Type validation and conversion
    - Required field verification
    - Detailed error reporting

    Args:
        output_data: Raw output from LLM to validate
        output_schema: Response schema class defining expected structure
        request_id: Request identifier for tracing

    Returns:
        StructuredResponse: Validated response object with field access via dot notation

    Raises:
        SchemaValidationError: When:
            - Output format doesn't match schema
            - Required fields are missing
            - Field types don't match
            - JSON parsing fails

    Logs:
        - Validation failures with details (ERROR)
        - Type conversion attempts (DEBUG)
        - Success metrics (DEBUG)

    Example:
        >>> schema = SentimentResponse
        >>> data = {"sentiment": "positive", "confidence": 0.95}
        >>> result = validate_llm_output(data, schema, "123")
        >>> print(result.sentiment)  # Access fields with dot notation
    """
    try:
        if isinstance(output_data, (ChatGeneration, Generation)):
            output_data = output_data.text
            
        if isinstance(output_data, StructuredResponse):
            return output_data
            
        return output_schema(**output_data)
        
    except ValidationError as e:
        error_details = e.errors()[0] if e.errors() else {}
        error_loc = ' -> '.join(str(x) for x in error_details.get('loc', []))
        error_type = error_details.get('type', 'unknown')
        input_value = error_details.get('input', '')
        
        if isinstance(input_value, str) and len(input_value) > 100:
            input_preview = input_value[:100] + '...'
        else:
            input_preview = str(input_value)
        
        logger.error(
            "Output validation failed",
            request_id=request_id,
            error=str(e),
            schema=output_schema.__name__,
            error_location=error_loc,
            error_type=error_type,
            input_preview=input_preview
        )
        
        if error_type == 'dict_type' and isinstance(input_value, str) and input_value.strip().startswith('{'):
            message = (
                f"Schema validation failed at '{error_loc}': The LLM returned a string containing JSON "
                f"instead of structured data. Received: '{input_preview}'. "
                f"This usually means the LLM needs clearer instructions to return structured data. "
                f"Try updating the prompt to explicitly request a structured response format."
            )
        elif error_type == 'missing':
            message = (
                f"Required field '{error_loc}' is missing from LLM output. "
                f"Update the prompt to ensure all required fields are included in the response."
            )
        elif error_type == 'type_error':
            message = (
                f"Invalid type at '{error_loc}': Expected {error_details.get('expected', 'unknown')}, "
                f"got {type(input_value).__name__}. Value: '{input_preview}'. "
                f"Ensure the prompt clearly specifies the expected data types."
            )
        else:
            message = (
                f"Schema validation failed at '{error_loc}': {error_details.get('msg', str(e))}. "
                f"The LLM response format doesn't match the schema definition. "
                f"Error type: {error_type}. Received: '{input_preview}'. "
                f"Review output_schema.yaml and ensure the LLM is prompted correctly."
            )
        
        raise SchemaValidationError(
            message=message,
            schema_type="output",
            field=error_loc or output_schema.__name__,
            constraints={
                "error_type": error_type,
                "validation_errors": e.errors(),
                "input_preview": input_preview
            }
        )