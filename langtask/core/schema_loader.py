"""YAML Schema Loader

Converts YAML schema definitions to Pydantic models for data validation.
Supports JSON Schema types, literals, and nested objects.

Fields are required by default unless explicitly marked with required: false.
Nested objects are supported up to 4 levels deep.
List fields are supported with size constraints using the 'list' attribute.

Public Functions:
    load_yaml_schema: Loads and converts YAML schema to Pydantic model
"""

import re
import time
from pathlib import Path
from typing import Any, Literal, Type, get_args, get_origin

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
            return f"{{\n{dict_content}\n{indent}}}"
            
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
    'object': dict[str, Any],  # Listed for validation - implementation uses nested Pydantic models
}

# Types that support options lists
OPTION_COMPATIBLE_TYPES = {'string', 'integer', 'number'}

# Maximum allowed nesting depth for object types
MAX_NESTING_DEPTH = 4

# Regular expression for validating list specifications
LIST_SPEC_PATTERN = re.compile(r'^(?:(\d+)-(\d+)|(\d+)\+)$')


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

    Logs:
        DEBUG: Loading YAML schema with file path
        DEBUG: No schema defined in file
        DEBUG: Schema loaded with duration and field count
        ERROR: Pydantic model creation failures with errors
        ERROR: Unexpected loading errors with details

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
        logger.debug(
            "Loading YAML schema",
            file_path=str(path),
            request_id=request_id
        )
        
        yaml_schema = read_yaml_file(path, request_id=request_id)
        if not yaml_schema:
            logger.debug(
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
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
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
            
        # Validate list specification if present
        if 'list' in field_def:
            try:
                _parse_list_spec(field_def['list'])
            except SchemaValidationError as e:
                raise SchemaValidationError(
                    message=f"Invalid list specification for field '{current_path}': {e.message}",
                    schema_type="list",
                    field=current_path,
                    constraints=e.constraints
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
        
        # Handle list constraints if present
        if 'list' in field_def:
            min_items, max_items = _parse_list_spec(field_def['list'])
            if min_items is not None:
                field_kwargs["min_length"] = min_items
            if max_items is not None:
                field_kwargs["max_length"] = max_items
        
        # Handle optional fields and defaults
        if not field_def.get('required', True):
            field_kwargs["default"] = field_def.get('default', None)
        elif 'default' in field_def:
            field_kwargs["default"] = field_def['default']

        # Handle string constraints
        if field_def.get('type') == 'string':
            if 'min_characters' in field_def:
                if not isinstance(field_def['min_characters'], int) or field_def['min_characters'] < 0:
                    raise SchemaValidationError(
                        message=f"Field '{current_path}' min_characters must be a positive integer",
                        schema_type="field",
                        field=current_path,
                        constraints={"min_characters": field_def['min_characters']}
                    )
                field_kwargs["min_length"] = field_def['min_characters']
                
            if 'max_characters' in field_def:
                if not isinstance(field_def['max_characters'], int) or field_def['max_characters'] < 1:
                    raise SchemaValidationError(
                        message=f"Field '{current_path}' max_characters must be a positive integer",
                        schema_type="field",
                        field=current_path,
                        constraints={"max_characters": field_def['max_characters']}
                    )
                field_kwargs["max_length"] = field_def['max_characters']
                
            if 'min_characters' in field_def and 'max_characters' in field_def:
                if field_def['min_characters'] > field_def['max_characters']:
                    raise SchemaValidationError(
                        message=f"Field '{current_path}' min_characters cannot be greater than max_characters",
                        schema_type="field",
                        field=current_path,
                        constraints={
                            "min_characters": field_def['min_characters'],
                            "max_characters": field_def['max_characters']
                        }
                    )
                    
            if 'pattern' in field_def:
                try:
                    re.compile(field_def['pattern'])
                    field_kwargs["pattern"] = field_def['pattern']
                except re.error as e:
                    raise SchemaValidationError(
                        message=f"Field '{current_path}' has invalid regex pattern: {str(e)}",
                        schema_type="field",
                        field=current_path,
                        constraints={"pattern": field_def['pattern']}
                    )
            
        # Handle numeric constraints
        if field_def.get('type') in ('integer', 'number'):
            # Check for contradictory constraints
            if 'min' in field_def and 'exclusive_min' in field_def:
                raise SchemaValidationError(
                    message=f"Field '{current_path}' cannot have both 'min' and 'exclusive_min' constraints",
                    schema_type="field",
                    field=current_path,
                    constraints={"conflicting_rules": ["min", "exclusive_min"]}
                )
            
            if 'max' in field_def and 'exclusive_max' in field_def:
                raise SchemaValidationError(
                    message=f"Field '{current_path}' cannot have both 'max' and 'exclusive_max' constraints",
                    schema_type="field",
                    field=current_path,
                    constraints={"conflicting_rules": ["max", "exclusive_max"]}
                )

            # Handle inclusive bounds
            if 'min' in field_def:
                field_kwargs["ge"] = field_def['min']
            if 'max' in field_def:
                field_kwargs["le"] = field_def['max']
            
            # Handle exclusive bounds
            if 'exclusive_min' in field_def:
                field_kwargs["gt"] = field_def['exclusive_min']
            if 'exclusive_max' in field_def:
                field_kwargs["lt"] = field_def['exclusive_max']
            
            if 'multiple_of' in field_def:
                field_kwargs["multiple_of"] = field_def['multiple_of']
        
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
    base_type = None
    
    # Get parent's required status - defaults to True if not specified
    is_required = field_def.get('required', True)
    
    # Handle fields with options using Literal types
    if 'options' in field_def:
        try:
            option_values = tuple(field_def['options'])  # Convert to tuple for Literal
            base_type = Literal[option_values]  # type: ignore
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
            # If parent is optional, property inherits this unless explicitly overridden
            if not is_required:
                prop_def = prop_def.copy()  # Create copy to avoid modifying original
                prop_def.setdefault('required', False)
                
            nested_type, nested_info = _convert_to_pydantic_field(
                prop_name.lower(),
                prop_def,
                current_path
            )
            nested_fields[prop_name.lower()] = (nested_type, nested_info)
            
        # Create nested model with descriptive name and proper inheritance
        model_name = f"{current_path.title().replace('.', '_')}Model"
        base_type = create_model(
            model_name,
            __base__=BaseModel,
            **nested_fields,
            __module__=StructuredResponse.__module__
        )
    
    # Handle standard types if no options defined
    if base_type is None and schema_type in TYPE_MAPPING:
        base_type = TYPE_MAPPING[schema_type]
    
    # Wrap in list if specified
    if 'list' in field_def:
        return list[base_type] if base_type is not None else list
        
    # Make type optional if required=false
    if not is_required and base_type is not None:
        if get_origin(base_type) is not None and get_origin(base_type) is Literal:
            existing_args = get_args(base_type)
            if type(None) not in existing_args:
                base_type = Literal[existing_args + (None,)]  # type: ignore
        else:
            base_type = base_type | None
    
    return base_type or Any  # Fallback to Any for unknown types


def _parse_list_spec(value: Any) -> tuple[int | None, int | None]:
    """Parse list specification into (min, max) counts."""
    if value is True:
        return None, None
    
    if isinstance(value, int):
        if value < 1:
            raise SchemaValidationError(
                message=f"List count must be positive, got {value}",
                schema_type="list",
                constraints={"min_value": 1}
            )
        return value, value
        
    if isinstance(value, str):
        match = LIST_SPEC_PATTERN.match(value)
        if not match:
            raise SchemaValidationError(
                message=f"Invalid list specification '{value}'. Use format: '1-3' for range or '3+' for minimum",
                schema_type="list",
                constraints={"pattern": "n-m or n+"}
            )
            
        # Get all groups and determine which format matched
        range_min, range_max, min_only = match.groups()
        
        if range_min and range_max:  # n-m format
            min_val = int(range_min)
            max_val = int(range_max)
            if min_val > max_val:
                raise SchemaValidationError(
                    message=f"Invalid range: minimum ({min_val}) greater than maximum ({max_val})",
                    schema_type="list",
                    constraints={"min": min_val, "max": max_val}
                )
            return min_val, max_val
            
        if min_only:  # n+ format
            return int(min_only), None
            
    raise SchemaValidationError(
        message=f"Invalid list specification type: {type(value)}. Expected bool, int, or string",
        schema_type="list",
        constraints={"allowed_types": ["bool", "int", "str"]}
    )