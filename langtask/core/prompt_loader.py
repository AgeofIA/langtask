"""Prompt Template Loader

Loads and configures chat prompt templates from files with schema validation.
Handles variable extraction and format instruction management.

Public Functions:
    load_prompt: Loads prompt files and creates chat template
    check_input_params_in_instructions: Checks for template variables
"""

import re
import time
from pathlib import Path
from typing import Any, Type
from pydantic import BaseModel

from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from .exceptions import (
    ExecutionError,
    FileSystemError,
    PromptValidationError,
    SchemaValidationError
)
from .file_reader import read_text_file
from .logger import get_logger, DEFAULT_REQUEST_ID
from .schema_loader import load_yaml_schema, StructuredResponse

logger = get_logger(__name__)


def load_prompt(
    prompt_id: str,
    prompt_config: dict[str, Any],
    request_id: str | None = None
) -> tuple[ChatPromptTemplate, Type[StructuredResponse] | None, Type[BaseModel] | None]:
    """Load and configure a chat prompt template from files.

    Creates a template with:
    - Instruction loading and validation
    - Schema-based input/output validation
    - Variable extraction and verification
    - Format instruction management

    Args:
        prompt_id: Unique identifier for the prompt
        prompt_config: Configuration containing file paths and LLM settings
        request_id: Optional identifier for tracing and logging

    Returns:
        A tuple containing:
        - Configured prompt template
        - Response schema class if defined
        - Input schema class if defined

    Raises:
        ExecutionError: When prompt processing fails
        FileSystemError: When file operations fail
        PromptValidationError: When prompt validation fails
        SchemaValidationError: When schema validation fails

    Logs:
        - Prompt loading start (INFO)
        - File loading operations (DEBUG)
        - Schema loading status (DEBUG)
        - LLM configurations (DEBUG)
        - Success metrics (SUCCESS)
        - Processing errors (ERROR)

    Example:
        >>> try:
        ...     template, out_schema, in_schema = load_prompt(
        ...         "user-prompt",
        ...         {"files": {"instructions.md": "path/to/file"}}
        ...     )
        ... except PromptValidationError as e:
        ...     print(f"Validation error: {e.message}")
    """
    request_id = request_id or DEFAULT_REQUEST_ID
    start_time = time.time()
    
    try:
        logger.info(
            "Loading prompt",
            prompt_id=prompt_id,
            request_id=request_id
        )
        
        files = prompt_config['files']
        prompt_path = Path(files['instructions.md']).parent
        
        # Validate required instruction file
        if 'instructions.md' not in files:
            raise PromptValidationError(
                message="Missing instructions.md file. Required in prompt directory.",
                prompt_path=str(prompt_path),
                validation_type="file_structure"
            )
            
        # Load instructions
        try:
            logger.debug(
                "Loading instruction file",
                prompt_id=prompt_id,
                file=files['instructions.md'],
                request_id=request_id
            )
            instructions_content = read_text_file(files['instructions.md'])
            
        except FileSystemError as e:
            raise PromptValidationError(
                message=f"Cannot read instructions.md. Verify file exists and has read permissions.",
                prompt_path=str(prompt_path),
                validation_type="instructions"
            )
        
        # Load schemas if they exist
        output_schema = None
        input_schema = None
        
        if 'output_schema.yaml' in files:
            logger.debug(
                "Loading output schema",
                prompt_id=prompt_id,
                file=files['output_schema.yaml'],
                request_id=request_id
            )
            output_schema = load_yaml_schema(
                files['output_schema.yaml'],
                request_id=request_id
            )
            
        if 'input_schema.yaml' in files:
            logger.debug(
                "Loading input schema",
                prompt_id=prompt_id,
                file=files['input_schema.yaml'],
                request_id=request_id
            )
            input_schema = load_yaml_schema(
                files['input_schema.yaml'],
                request_id=request_id
            )
        
        # Create prompt template
        prompt_template = _create_prompt_template(
            instructions_content,
            output_schema,
            input_schema,
            request_id
        )
        
        duration_ms = (time.time() - start_time) * 1000
        logger.success(
            "Prompt loaded successfully",
            prompt_id=prompt_id,
            duration_ms=round(duration_ms, 2),
            has_input_schema=bool(input_schema),
            has_output_schema=bool(output_schema),
            request_id=request_id
        )
        
        # Log LLM configurations
        for i, llm_config in enumerate(prompt_config['config'].llm):
            logger.debug(
                "LLM configuration",
                prompt_id=prompt_id,
                config_index=i,
                provider=llm_config.provider,
                model=llm_config.model,
                request_id=request_id
            )
            
        return prompt_template, output_schema, input_schema
        
    except (FileSystemError, PromptValidationError, SchemaValidationError):
        raise
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Failed to load prompt",
            prompt_id=prompt_id,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2),
            request_id=request_id
        )
        raise ExecutionError(
            message=f"Failed to load prompt '{prompt_id}'. Verify all required files exist and are valid.",
            operation="prompt_loading"
        )


def check_input_params_in_instructions(instructions_content: str) -> bool:
    """Check if instructions contain any input parameters.

    Args:
        instructions_content: Raw instruction template text

    Returns:
        bool: True if parameters are found, False otherwise

    Logs:
        - Parameter check results at DEBUG level
    """
    variables = _extract_template_variables(instructions_content)
    logger.debug(
        "Checked for input parameters",
        has_parameters=bool(variables),
        parameter_count=len(variables),
        request_id=DEFAULT_REQUEST_ID
    )
    return bool(variables)


def _create_prompt_template(
    instructions_content: str,
    output_schema: Type[StructuredResponse] | None,
    input_schema: Type[BaseModel] | None,
    request_id: str = DEFAULT_REQUEST_ID
) -> ChatPromptTemplate:
    """Create chat template from instructions and schemas with variable handling."""
    try:
        start_time = time.time()
        
        # Extract variables from instructions
        extracted_variables = _extract_template_variables(instructions_content)
        logger.debug(
            "Extracted template variables",
            variable_count=len(extracted_variables),
            variables=list(extracted_variables),
            request_id=request_id
        )
        
        # Determine input variables
        if input_schema:
            input_variables = set(input_schema.model_fields.keys())
            _validate_template_variables(
                extracted_variables,
                input_variables,
                request_id
            )
        else:
            input_variables = extracted_variables
            if input_variables:
                logger.info(
                    "Using variables from instructions",
                    variables=list(input_variables),
                    request_id=request_id
                )
        
        # Convert template format while preserving regular brackets
        template_content = _convert_template_format(instructions_content)
        
        # Add format instructions for structured output
        if output_schema:
            template_content += (
                f"\n\nFormat your response as a valid {output_schema.__name__} with "
                f"the following fields: {', '.join(output_schema.model_fields.keys())}. "
                f"Use proper types for each field."
            )
        
        template = ChatPromptTemplate(
            messages=[
                HumanMessagePromptTemplate.from_template(template_content)
            ],
            input_variables=list(input_variables)
        )
        
        duration_ms = (time.time() - start_time) * 1000
        logger.debug(
            "Prompt template created",
            variable_count=len(input_variables),
            has_format_instructions=bool(output_schema),
            duration_ms=round(duration_ms, 2),
            request_id=request_id
        )
        
        return template
        
    except Exception:
        raise PromptValidationError(
            message="Failed to create template. Check variable usage matches schema and format {{variable}}.",
            prompt_path="template_creation",
            validation_type="template"
        )


def _extract_template_variables(content: str) -> set[str]:
    """Extract unique variable names from template content using {{variable}} format.
    
    Returns:
        Set[str]: Set of lowercase variable names for internal use
    """
    pattern = r'\{\{([A-Za-z_]+)\}\}'
    matches = re.findall(pattern, content)
    
    # Convert all variables to lowercase
    variables = {var.lower() for var in matches}
    
    return variables


def _validate_template_variables(
    template_vars: set[str],
    schema_vars: set[str],
    request_id: str = DEFAULT_REQUEST_ID
) -> None:
    """Compare template and schema variables for consistency."""
    # Variables are already lowercase from _extract_template_variables
    # and schema_loader, so we can compare directly
    extra_vars = template_vars - schema_vars
    missing_vars = schema_vars - template_vars
    
    if extra_vars:
        logger.warning(
            f"Template uses undefined variables: {', '.join(extra_vars)}. Add to input schema or remove.",
            extra_vars=list(extra_vars),
            request_id=request_id
        )
    
    if missing_vars:
        logger.warning(
            f"Schema variables not used in template: {', '.join(missing_vars)}. Add to template or remove from schema.",
            missing_vars=list(missing_vars),
            request_id=request_id
        )


def _convert_template_format(content: str) -> str:
    """Convert double-bracketed template variables to single brackets.
    
    First escapes any existing single brackets in the content, then converts
    double-bracketed variables to single brackets. Variables are converted to lowercase.
    
    Args:
        content: Original template content with double brackets
    
    Returns:
        str: Template content with escaped single brackets and converted template variables
    """
    # First, escape any single brackets that aren't part of a double-bracket pair
    def _escape_singles(text: str) -> str:
        result = ""
        i = 0
        while i < len(text):
            # Skip double brackets
            if i + 1 < len(text) and text[i:i+2] == '{{':
                result += '{{'
                i += 2
            elif i + 1 < len(text) and text[i:i+2] == '}}':
                result += '}}'
                i += 2
            # Escape single brackets
            elif text[i] == '{':
                result += r'\{'
                i += 1
            elif text[i] == '}':
                result += r'\}'
                i += 1
            else:
                result += text[i]
                i += 1
        return result
    
    # Escape existing single brackets
    escaped_content = _escape_singles(content)
    
    # Convert double-bracketed variables to single brackets and lowercase
    def _replace_var(match):
        var = match.group(1).lower()
        return '{' + var + '}'
    
    pattern = r'\{\{([A-Za-z_]+)\}\}'
    return re.sub(pattern, _replace_var, escaped_content)