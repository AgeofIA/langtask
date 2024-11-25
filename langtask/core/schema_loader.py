"""YAML Schema Loader

Converts YAML schema definitions to Pydantic models for data validation.
Supports JSON Schema types and enums with comprehensive error reporting.

Public Functions:
    load_yaml_schema: Loads and converts YAML schema to Pydantic model
"""

import time
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, create_model, ValidationError

from .exceptions import SchemaValidationError, FileSystemError
from .file_reader import read_yaml_file
from .logger import get_logger

logger = get_logger(__name__)


# Standard type mappings for schema conversion
TYPE_MAPPING = {
    'string': str,
    'integer': int,
    'number': float,
    'boolean': bool,
    'array': list[Any],
    'object': dict[str, Any],
}


def load_yaml_schema(file_path: str | Path, request_id: str | None = None):
    """Load and convert a YAML schema into a Pydantic model.

    Provides schema validation with:
    - Type checking and conversion
    - Enum support
    - Performance monitoring
    - Comprehensive error handling

    Args:
        file_path: Path to the YAML schema file. Can be either a string path
            or a Path object.
        request_id: Optional identifier for tracing and logging purposes.

    Returns:
        Optional[BaseModel]: Pydantic model class for data validation.
        Returns None if schema is empty.

    Raises:
        SchemaValidationError: When:
            - Schema structure is invalid
            - Field definitions are incorrect
            - Type conversion fails
            - Enum values are invalid
        FileSystemError: When schema file cannot be accessed

    Logs:
        - Schema loading start (INFO)
        - Empty schema detection (INFO)
        - Successful conversion with metrics (SUCCESS)
        - Validation and conversion errors (ERROR)

    Example:
        >>> try:
        ...     model = load_yaml_schema("user_schema.yaml")
        ...     if model:
        ...         user_data = model(name="John", age=30)
        ... except SchemaValidationError as e:
        ...     print(f"Schema error: {e.message}")
    """
    start_time = time.time()
    path = Path(file_path)
    
    try:
        logger.info(
            "Loading YAML schema",
            file_path=str(path),
            request_id=request_id
        )
        
        yaml_schema = read_yaml_file(path)
        if not yaml_schema:
            logger.info(
                "No schema defined",
                file_path=str(path),
                request_id=request_id
            )
            return None
        
        # Validate overall schema structure
        if not isinstance(yaml_schema, dict):
            raise SchemaValidationError(
                message=f"Schema must be a YAML dictionary. Found: {type(yaml_schema).__name__}",
                schema_type="yaml",
                field=path.stem,
                constraints={"type": "object"}
            )

        # Validate and create model
        _validate_schema(yaml_schema)
        pydantic_model = _create_pydantic_model(yaml_schema)
        
        duration_ms = (time.time() - start_time) * 1000
        logger.success(
            "Schema loaded and converted",
            file_path=str(path),
            duration_ms=round(duration_ms, 2),
            field_count=len(yaml_schema),
            request_id=request_id
        )
        
        return pydantic_model
        
    except FileSystemError:
        raise
        
    except SchemaValidationError:
        raise
        
    except ValidationError as e:
        logger.error(
            "Pydantic model creation failed",
            file_path=str(path),
            errors=e.errors(),
            request_id=request_id
        )
        raise SchemaValidationError(
            message=f"Invalid model definition. Check field types and constraints: {e.errors()[0]['msg']}",
            schema_type="pydantic",
            constraints={"validation_errors": e.errors()}
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error loading schema",
            file_path=str(path),
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id
        )
        raise SchemaValidationError(
            message=f"Failed to load schema. Verify file format and field definitions.",
            schema_type="unknown",
            field=path.stem
        )


def _validate_schema(schema: dict[str, Any]) -> None:
    """Validate schema structure and field definitions."""
    for field_name, field_def in schema.items():
        # Validate field definition structure
        if not isinstance(field_def, dict):
            raise SchemaValidationError(
                message=f"Field '{field_name}' must be a dictionary defining type and constraints.",
                schema_type="field",
                field=field_name,
                constraints={"expected_type": "object"}
            )
            
        # Validate required type field
        if 'type' not in field_def:
            raise SchemaValidationError(
                message=f"Field '{field_name}' missing 'type'. Specify one of: {', '.join(TYPE_MAPPING.keys())}",
                schema_type="field",
                field=field_name,
                constraints={"required_attribute": "type"}
            )
            
        # Validate type value
        field_type = field_def.get('type')
        if field_type not in TYPE_MAPPING and 'enum' not in field_def:
            raise SchemaValidationError(
                message=f"Field '{field_name}' has invalid type: {field_type}",
                schema_type="type",
                field=field_name,
                constraints={
                    "invalid_type": field_type,
                    "allowed_types": list(TYPE_MAPPING.keys())
                }
            )
            
        # Validate enum values if present
        if 'enum' in field_def:
            enum_values = field_def['enum']
            if not isinstance(enum_values, list) or not enum_values:
                raise SchemaValidationError(
                    message=f"Field '{field_name}' has invalid enum definition",
                    schema_type="enum",
                    field=field_name,
                    constraints={"requirement": "non-empty list of values"}
                )

def _create_pydantic_model(schema: dict[str, Any]):
    """Create Pydantic model from validated schema dictionary."""
    try:
        fields = {}
        for field_name, field_def in schema.items():
            # Convert field names to lowercase
            field_type, field_info = _convert_to_pydantic_field(field_name.lower(), field_def)
            fields[field_name.lower()] = (field_type, field_info)

        return create_model('DynamicModel', **fields)
        
    except Exception as e:
        logger.error(
            "Model creation failed",
            error=str(e),
            fields=list(schema.keys())
        )
        raise SchemaValidationError(
            message="Failed to create Pydantic model",
            schema_type="model",
            constraints={"error": str(e)}
        )

def _convert_to_pydantic_field(
    field_name: str,
    field_def: dict[str, Any]
) -> tuple[Any, Field]:
    """Convert schema field definition to Pydantic field tuple."""
    try:
        field_type = _get_field_type(field_name, field_def)
        
        # Create field with metadata
        field_info = Field(
            default=field_def.get('default'),
            description=field_def.get('description', ''),
            title=field_def.get('title')
        )
        
        return field_type, field_info
        
    except Exception as e:
        raise SchemaValidationError(
            message=f"Failed to convert field '{field_name}': {str(e)}",
            schema_type="field",
            field=field_name,
            constraints={"definition": field_def}
        )

def _get_field_type(field_name: str, field_def: dict[str, Any]) -> Any:
    """Determine Python type for schema field, including enums."""
    # Handle enum fields
    if 'enum' in field_def:
        try:
            return Enum(
                f"{field_name.capitalize()}Enum",
                {v: v for v in field_def['enum']}
            )
        except Exception as e:
            raise SchemaValidationError(
                message=f"Invalid enum for '{field_name}'. Values must be unique and hashable.",
                schema_type="enum",
                field=field_name,
                constraints={"values": field_def['enum']}
            )
    
    # Handle standard types
    schema_type = field_def.get('type')
    if schema_type in TYPE_MAPPING:
        return TYPE_MAPPING[schema_type]
    
    # Fallback for unknown types    
    logger.warning(
        "Unknown schema type",
        field=field_name,
        type=schema_type
    )
    return Any