"""YAML Schema Loader

Converts YAML schema definitions to Pydantic models for data validation.
Supports JSON Schema types, literals, and nested objects.

Fields are required by default unless explicitly marked with required: false.
Nested objects are supported up to 4 levels deep.

Public Functions:
    load_yaml_schema: Loads and converts YAML schema to Pydantic model
"""

import time
from pathlib import Path
from typing import Any, Literal, Type

from pydantic import BaseModel, Field, create_model, ValidationError

from .exceptions import SchemaValidationError, FileSystemError
from .file_reader import read_yaml_file
from .logger import get_logger

logger = get_logger(__name__)


class StructuredResponse(BaseModel):
    """Base class for all structured LLM responses."""
    
    model_config = {
        "frozen": True,  # Make instances immutable
        "str_strip_whitespace": True,  # Clean up string outputs
        "validate_default": True  # Ensure defaults match field types
    }
    
    def __str__(self) -> str:
        """Create a readable string representation of the response."""
        return self._format_value(self.model_dump(), indent_level=0, is_root=True)
    
    def _format_value(self, value: Any, indent_level: int, is_root: bool = False) -> str:
        """Recursively format values with proper indentation."""
        indent = "    " * indent_level
        next_indent = "    " * (indent_level + 1)
        
        if isinstance(value, dict):
            if not value:
                return "{}"
                
            items = []
            for k, v in value.items():
                formatted_value = self._format_value(v, indent_level + 1)
                items.append(f"{next_indent}{k}={formatted_value}")
                
            dict_content = ',\n'.join(items)
            if is_root:
                class_name = self.__class__.__name__
                return f"{class_name}(\n{dict_content}\n{indent})"
            return "{\n" + dict_content + f"\n{indent}}}"
            
        elif isinstance(value, list):
            if not value:
                return "[]"
                
            items = []
            for item in value:
                formatted_item = self._format_value(item, indent_level + 1)
                items.append(f"{next_indent}{formatted_item}")
                
            return "[\n" + ',\n'.join(items) + f"\n{indent}]"
            
        elif isinstance(value, (str, int, float, bool)):
            return repr(value)
            
        return str(value)
    
    def __repr__(self) -> str:
        """Use the same format for repr as str for consistency."""
        return self.__str__()


# Standard type mappings for schema conversion
TYPE_MAPPING = {
    'string': str,
    'integer': int,
    'number': float,
    'boolean': bool,
    'array': list[Any],  # TODO: Add support for typed arrays in future
    'object': dict[str, Any],  # Placeholder - objects use nested models
}

# Types that support options lists
OPTION_COMPATIBLE_TYPES = {'string', 'integer', 'number'}

# Maximum allowed nesting depth for object types
MAX_NESTING_DEPTH = 4

# Cache for created schema classes
_schema_cache: dict[str, Type[StructuredResponse]] = {}


def load_yaml_schema(file_path: str | Path, request_id: str | None = None) -> Type[StructuredResponse] | None:
    """Load and convert a YAML schema into a Pydantic response class.

    Args:
        file_path: Path to the YAML schema file. Can be either a string path
            or a Path object.
        request_id: Optional identifier for tracing and logging purposes.

    Returns:
        Either:
            - Response class for validation
            - None if schema is empty

    Raises:
        SchemaValidationError: When:
            - Schema structure is invalid
            - Field definitions are incorrect
            - Type conversion fails
            - Option values are invalid
            - Nested object depth exceeds MAX_NESTING_DEPTH
        FileSystemError: When schema file cannot be accessed

    Notes:
        - All fields are required by default unless marked with required: false
        - Nested objects must define their fields in a 'properties' key
        - Maximum nesting depth is 4 levels
        - Field names are converted to lowercase internally
        - Options are only supported for string, integer, and number types

    Example:
        >>> try:
        ...     schema_class = load_yaml_schema("schema.yaml")
        ...     if schema_class:
        ...         # Fields are required by default
        ...         response = schema_class(
        ...             required_field="value",
        ...             metadata={  # Nested object
        ...                 "required_nested": "value",
        ...                 "optional_nested": "value"  # If marked required: false
        ...             }
        ...         )
        ... except SchemaValidationError as e:
        ...     print(f"Schema error: {e.message}")
    """
    start_time = time.time()
    path = Path(file_path)
    
    try:
        # Check cache first
        if str(path) in _schema_cache:
            return _schema_cache[str(path)]
            
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
        response_class = _create_pydantic_model(yaml_schema, path.stem)
        
        # Cache the created class
        _schema_cache[str(path)] = response_class
        
        duration_ms = (time.time() - start_time) * 1000
        logger.success(
            "Schema loaded and converted",
            file_path=str(path),
            duration_ms=round(duration_ms, 2),
            field_count=len(yaml_schema),
            request_id=request_id
        )
        
        return response_class
        
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
            message=f"Invalid schema definition. Check field types and constraints: {e.errors()[0]['msg']}",
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


def _validate_schema(schema: dict[str, Any], field_path: str = "", depth: int = 0) -> None:
    """Validate schema structure and field definitions recursively."""
    for field_name, field_def in schema.items():
        current_path = f"{field_path}.{field_name}" if field_path else field_name
        
        # Validate field definition structure
        if not isinstance(field_def, dict):
            raise SchemaValidationError(
                message=f"Field '{current_path}' must be a dictionary defining type and constraints.",
                schema_type="field",
                field=current_path,
                constraints={"expected_type": "object"}
            )
            
        # Validate required type field
        if 'type' not in field_def:
            raise SchemaValidationError(
                message=f"Field '{current_path}' missing 'type'. Specify one of: {', '.join(TYPE_MAPPING.keys())}",
                schema_type="field",
                field=current_path,
                constraints={"required_attribute": "type"}
            )
            
        # Validate type value
        field_type = field_def.get('type')
        if field_type not in TYPE_MAPPING:
            raise SchemaValidationError(
                message=f"Field '{current_path}' has invalid type: {field_type}",
                schema_type="type",
                field=current_path,
                constraints={
                    "invalid_type": field_type,
                    "allowed_types": list(TYPE_MAPPING.keys())
                }
            )
        
        # Handle nested object validation
        if field_type == 'object':
            if depth >= MAX_NESTING_DEPTH:
                raise SchemaValidationError(
                    message=f"Field '{current_path}' exceeds maximum nesting depth of {MAX_NESTING_DEPTH}",
                    schema_type="nesting",
                    field=current_path,
                    constraints={"max_depth": MAX_NESTING_DEPTH}
                )
                
            if 'properties' not in field_def:
                raise SchemaValidationError(
                    message=f"Object field '{current_path}' must define 'properties'",
                    schema_type="object",
                    field=current_path,
                    constraints={"required_attribute": "properties"}
                )
                
            _validate_schema(field_def['properties'], current_path, depth + 1)
            
        # Validate options if present
        if 'options' in field_def:
            # First validate that the field type supports options
            if field_type not in OPTION_COMPATIBLE_TYPES:
                raise SchemaValidationError(
                    message=f"Field '{current_path}' has type '{field_type}' which does not support options. Options are only "
                           f"supported for: {', '.join(OPTION_COMPATIBLE_TYPES)}",
                    schema_type="options",
                    field=current_path,
                    constraints={"allowed_types": list(OPTION_COMPATIBLE_TYPES)}
                )
            
            # Then validate the options list structure
            option_values = field_def['options']
            if not isinstance(option_values, list) or not option_values:
                raise SchemaValidationError(
                    message=f"Field '{current_path}' has invalid options definition. Must be a non-empty list.",
                    schema_type="options",
                    field=current_path,
                    constraints={"requirement": "non-empty list of values"}
                )
            
            # Validate option value types match the field type
            expected_type = TYPE_MAPPING[field_type]
            if not all(isinstance(v, expected_type) for v in option_values):
                raise SchemaValidationError(
                    message=f"Field '{current_path}' options must all be of type {field_type}",
                    schema_type="options",
                    field=current_path,
                    constraints={"expected_type": field_type}
                )


def _create_pydantic_model(schema: dict[str, Any], schema_name: str) -> Type[StructuredResponse]:
    """Create Pydantic response class from validated schema dictionary."""
    try:
        fields = {}
        for field_name, field_def in schema.items():
            # Convert field names to lowercase
            field_type, field_info = _convert_to_pydantic_field(field_name.lower(), field_def)
            fields[field_name.lower()] = (field_type, field_info)

        # Create class with meaningful name
        class_name = f"{schema_name.title().replace('_', '')}Response"
        return create_model(
            class_name,
            __base__=StructuredResponse,
            **fields
        )
        
    except Exception as e:
        logger.error(
            "Response class creation failed",
            error=str(e),
            fields=list(schema.keys())
        )
        raise SchemaValidationError(
            message="Failed to create response class",
            schema_type="model",
            constraints={"error": str(e)}
        )


def _convert_to_pydantic_field(
    field_name: str,
    field_def: dict[str, Any],
    parent_path: str = ""
) -> tuple[Any, Field]:
    """Convert schema field definition to Pydantic field tuple."""
    try:
        field_type = _get_field_type(field_name, field_def, parent_path)
        
        # Fields are required by default in Pydantic
        # Only set default if field is optional or has explicit default
        field_kwargs = {
            "description": field_def.get('description', ''),
            "title": field_def.get('title')
        }
        
        if not field_def.get('required', True):
            field_kwargs["default"] = field_def.get('default', None)
        elif 'default' in field_def:
            field_kwargs["default"] = field_def['default']
            
        return field_type, Field(**field_kwargs)
        
    except Exception as e:
        current_path = f"{parent_path}.{field_name}" if parent_path else field_name
        raise SchemaValidationError(
            message=f"Failed to convert field '{current_path}': {str(e)}",
            schema_type="field",
            field=current_path,
            constraints={"definition": field_def}
        )


def _get_field_type(field_name: str, field_def: dict[str, Any], parent_path: str = "") -> Any:
    """Determine Python type for schema field, including literals and nested objects."""
    current_path = f"{parent_path}.{field_name}" if parent_path else field_name
    
    # Handle fields with options using Literal types
    if 'options' in field_def:
        try:
            option_values = tuple(field_def['options'])  # Convert to tuple for Literal
            return Literal[option_values]  # type: ignore
        except Exception as e:
            raise SchemaValidationError(
                message=f"Invalid options for '{current_path}'. Values must be hashable.",
                schema_type="options",
                field=current_path,
                constraints={"values": field_def['options']}
            )
    
    schema_type = field_def.get('type')
    
    # Handle nested objects
    if schema_type == 'object' and 'properties' in field_def:
        # Create nested fields
        nested_fields = {}
        for prop_name, prop_def in field_def['properties'].items():
            nested_type, nested_info = _convert_to_pydantic_field(
                prop_name.lower(),
                prop_def,
                current_path
            )
            nested_fields[prop_name.lower()] = (nested_type, nested_info)
        
        # Create nested model with descriptive name and proper inheritance
        model_name = f"{current_path.title().replace('.', '_')}Model"
        return create_model(
            model_name,
            __base__=BaseModel,
            **nested_fields,
            __module__=StructuredResponse.__module__
        )
    
    # Handle standard types
    if schema_type in TYPE_MAPPING:
        return TYPE_MAPPING[schema_type]
    
    # Fallback for unknown types    
    logger.warning(
        "Unknown schema type",
        field=current_path,
        type=schema_type
    )
    return Any