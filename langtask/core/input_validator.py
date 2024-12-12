"""Input Parameter Validator

Validates input parameters against schemas or prompt variables with structured
error reporting. Supports both Pydantic model validation and variable checking.

Public Functions:
    validate_prompt_input: Validate input parameters using schema or variables
"""

import time
from typing import Type
from pydantic import BaseModel, ValidationError

from .exceptions import DataValidationError, SchemaValidationError
from .logger import get_logger

logger = get_logger(__name__)


def validate_prompt_input(
    input_schema: Type[BaseModel] | None,
    input_params: dict | None,
    prompt_variables: list[str],
    request_id: str
) -> dict:
    """Validate input parameters using schema or prompt variables.

    Performs validation with:
    - Schema-based validation using Pydantic models
    - Required variable checking
    - Performance monitoring
    - Structured error reporting
    - Case-insensitive matching

    Args:
        input_schema: Optional Pydantic model class for validation
        input_params: Dictionary of input parameters to validate
        prompt_variables: List of required prompt variable names
        request_id: Request identifier for tracing

    Returns:
        Dict: Validated parameter dictionary with canonical field names

    Raises:
        DataValidationError: When:
            - Required parameters are missing
            - Parameters fail schema validation
        SchemaValidationError: When schema validation system fails

    Logs:
        DEBUG: Starting input validation with parameters
        INFO: Input validation completion with duration and fields
        ERROR: Unexpected validation errors with details
    """
    start_time = time.time()
    
    logger.debug(
        "Starting input validation",
        request_id=request_id,
        has_schema=bool(input_schema),
        param_count=len(input_params or {}),
        required_vars=prompt_variables
    )
    
    try:
        if input_schema and isinstance(input_schema, type) and issubclass(input_schema, BaseModel):
            result = _validate_with_schema(input_schema, input_params, request_id)
        else:
            result = _validate_without_schema(input_params or {}, prompt_variables, request_id)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Input validation successful",
            request_id=request_id,
            duration_ms=round(duration_ms, 2),
            validated_fields=list(result.keys())
        )
        return result
        
    except (DataValidationError, SchemaValidationError):
        raise
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Unexpected validation error",
            request_id=request_id,
            error=str(e),
            duration_ms=round(duration_ms, 2),
            error_type=type(e).__name__
        )
        raise SchemaValidationError(
            message=f"Schema validation failed. Check input types and required fields: {str(e)}",
            schema_type="input",
            field=None,
            constraints={"error_type": type(e).__name__}
        )


def _validate_with_schema(
    input_schema: Type[BaseModel],
    input_params: dict | None,
    request_id: str
) -> dict:
    """Validate input parameters against Pydantic schema model."""
    if not input_params:
        input_params = {}

    try:
        lowercase_params = {
            k.lower(): v for k, v in input_params.items()
        }
        
        validated = input_schema(**lowercase_params)
        result = validated.model_dump()
        
        logger.debug(
            "Schema validation successful",
            request_id=request_id,
            schema=input_schema.__name__,
            field_count=len(result)
        )
        return result
        
    except ValidationError as e:
        error_details = []
        constraints = {}
        
        for error in e.errors():
            field = error["loc"][0]
            error_type = error["type"]
            
            # Map Pydantic error types to user-friendly messages
            error_message = {
                "literal_error": "Invalid option",
                "missing": "Required field",
                "type_error": "Invalid type",
                "value_error": "Invalid value",
                "list_type": "Invalid list value",
                "greater_than": "Value too small",
                "less_than": "Value too large",
                "string_pattern_match": "Invalid format",
                "string_too_short": "Value too short",
                "string_too_long": "Value too long",
            }.get(error_type, error["msg"])
            
            error_details.append((field, error_message))
            constraints[field] = {
                "error_type": error_type,
                "message": error["msg"]
            }
        
        logger.error(
            "Schema validation failed",
            request_id=request_id,
            schema=input_schema.__name__,
            validation_errors=error_details
        )
        
        main_field = error_details[0][0] if error_details else None
        error_messages = [f"{field}: {msg}" for field, msg in error_details]
        
        raise DataValidationError(
            message=f"Invalid input parameters: {', '.join(error_messages)}",
            data_type="schema_input",
            constraint="field_validation",
            value=main_field
        )


def _validate_without_schema(
    input_params: dict,
    prompt_variables: list[str],
    request_id: str
) -> dict:
    """Validate input parameters against required prompt variables list."""
    # Convert everything to lowercase for comparison
    input_vars = {k.lower(): v for k, v in input_params.items()}
    required_vars = {v.lower() for v in prompt_variables}
    
    # Check for missing variables
    missing_vars = required_vars - input_vars.keys()
    
    if missing_vars:
        logger.error(
            "Missing required parameters",
            request_id=request_id,
            missing_params=list(missing_vars)
        )
        
        first_missing = next(iter(missing_vars))
        raise DataValidationError(
            message=f"Missing required input parameters: {', '.join(missing_vars)}. Check prompt template for required fields.",
            data_type="prompt_input",
            constraint="required_field",
            value=first_missing
        )

    # Build result and track unknown parameters
    result = {}
    unknown_params = set()
    
    for input_key, value in input_params.items():
        input_key_lower = input_key.lower()
        if input_key_lower in required_vars:
            result[input_key_lower] = value
        else:
            unknown_params.add(input_key)

    # Log warning if unknown parameters were provided
    if unknown_params:
        logger.warning(
            "Unknown parameters received",
            request_id=request_id,
            unknown_params=list(unknown_params)
        )

    logger.debug(
        "Variable validation successful",
        request_id=request_id,
        valid_params=list(result.keys())
    )
    return result