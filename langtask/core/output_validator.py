"""Output Validation Module

Validates LLM outputs against schema definitions with detailed error reporting.
Handles common validation scenarios and provides actionable error messages.

Public Functions:
    validate_llm_output: Validate LLM response against output schema
    handle_structured_output: Process and validate structured LLM output
"""

from typing import Any, Type
from pydantic import ValidationError

from .exceptions import SchemaValidationError
from .logger import get_logger
from .schema_loader import StructuredResponse

logger = get_logger(__name__)


def handle_structured_output(
    response_data: Any,
    output_schema: Type[StructuredResponse],
    request_id: str
) -> StructuredResponse:
    """Process and validate structured LLM output.

    Performs validation with:
    - Schema compliance checking
    - Type validation and conversion
    - Required field verification
    - Detailed error reporting

    Args:
        response_data: Raw response data from LLM to validate
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

    Logs:
        ERROR: Validation failures with details
        ERROR: Processing errors with context

    Example:
        >>> schema = SentimentResponse
        >>> data = {"sentiment": "positive", "confidence": 0.95}
        >>> response = handle_structured_output(data, schema, "123")
        >>> print(response.sentiment)  # Access fields with dot notation
    """
    try:
        # If response is already a valid StructuredResponse, return it
        if isinstance(response_data, output_schema):
            logger.debug(
                "Response already validated",
                request_id=request_id,
                schema=output_schema.__name__
            )
            return response_data
            
        # If response is a dict, validate it
        if isinstance(response_data, dict):
            return validate_llm_output(response_data, output_schema, request_id)
            
        # Handle potential JSON string responses
        if isinstance(response_data, str) and response_data.strip().startswith('{'):
            raise SchemaValidationError(
                message=(
                    "The LLM returned a JSON string instead of structured data. "
                    f"Received: '{response_data[:100]}...'. "
                    "Update the prompt to return direct structured output."
                ),
                schema_type="output",
                field=output_schema.__name__,
                constraints={"input_preview": response_data[:100]}
            )
            
        # Handle other invalid response types
        raise SchemaValidationError(
            message=(
                f"Invalid response type: {type(response_data).__name__}. "
                "Expected structured data matching the output schema."
            ),
            schema_type="output",
            field=output_schema.__name__,
            constraints={"response_type": type(response_data).__name__}
        )
        
    except ValidationError as e:
        logger.error(
            "Output validation failed",
            request_id=request_id,
            error=str(e),
            schema=output_schema.__name__
        )
        raise SchemaValidationError(
            message=(
                "LLM response format validation failed. The response structure "
                "does not match the expected schema. Update the prompt to ensure "
                "the LLM returns properly structured output."
            ),
            schema_type="output",
            field=output_schema.__name__,
            constraints={"validation_errors": e.errors()}
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
            - Options validation fails
            - List constraints aren't met

    Logs:
        DEBUG: Output validation successful with field count
        ERROR: Output validation failures with error details

    Example:
        >>> schema = SentimentResponse
        >>> data = {"sentiment": "positive", "confidence": 0.95}
        >>> result = validate_llm_output(data, schema, "123")
        >>> print(result.sentiment)  # Access fields with dot notation
    """
    try:
        if isinstance(output_data, StructuredResponse):
            return output_data
            
        validated = output_schema(**output_data)
        
        logger.debug(
            "Output validation successful",
            request_id=request_id,
            schema=output_schema.__name__,
            field_count=len(validated.model_dump())
        )
        
        return validated
        
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

        # Map common validation errors to user-friendly messages
        error_messages = {
            'dict_type': (
                f"The LLM returned an invalid format at '{error_loc}'. "
                f"Expected a structured object but received: '{input_preview}'. "
                f"Update the prompt to ensure proper response structure."
            ),
            'missing': (
                f"Required field '{error_loc}' is missing from LLM output. "
                f"Update the prompt to ensure all required fields are included."
            ),
            'type_error': (
                f"Invalid type at '{error_loc}': Expected {error_details.get('expected', 'unknown')}, "
                f"got {type(input_value).__name__}. Value: '{input_preview}'. "
                f"Ensure the prompt specifies the correct data types."
            ),
            'literal_error': (
                f"Invalid option at '{error_loc}'. Value '{input_preview}' is not one of the allowed options. "
                f"Update the prompt to specify valid choices."
            ),
            'list_type': (
                f"Invalid list value at '{error_loc}': {error_details.get('msg')}. "
                f"Ensure the prompt specifies the correct list format."
            ),
            'greater_than': (
                f"Value too small at '{error_loc}': {error_details.get('msg')}. "
                f"Update the prompt to specify valid value ranges."
            ),
            'less_than': (
                f"Value too large at '{error_loc}': {error_details.get('msg')}. "
                f"Update the prompt to specify valid value ranges."
            ),
            'string_pattern_match': (
                f"Invalid format at '{error_loc}': {error_details.get('msg')}. "
                f"Ensure the prompt specifies the required format."
            ),
            'string_too_short': (
                f"Value too short at '{error_loc}': {error_details.get('msg')}. "
                f"Update the prompt to specify minimum length requirements."
            ),
            'string_too_long': (
                f"Value too long at '{error_loc}': {error_details.get('msg')}. "
                f"Update the prompt to specify maximum length requirements."
            )
        }

        message = error_messages.get(error_type, (
            f"Schema validation failed at '{error_loc}': {error_details.get('msg', str(e))}. "
            f"The LLM response doesn't match the schema. Error type: {error_type}. "
            f"Received: '{input_preview}'. Review the schema and prompt instructions."
        ))
        
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