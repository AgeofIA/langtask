# LangTask API Documentation

This document provides detailed API documentation for the LangTask library.

First, import the library (we'll use this import in all following examples):
```python
import langtask as lt
```

## Table of Contents
- [Core Functions](#core-functions)
  - [register()](#register)
  - [run()](#run)
  - [list_directories()](#list_directories)
  - [list_prompts()](#list_prompts)
  - [get_prompt()](#get_prompt)
  - [set_global_config()](#set_global_config)
  - [get_global_config()](#get_global_config)
  - [set_logs()](#set_logs)
- [Creating Custom Prompts](#creating-custom-prompts)
  - [Directory Structure](#directory-structure)
  - [Prompt Instructions](#prompt-instructions-instructionsmd)
  - [Configuration](#configuration-configyaml)
  - [Schema Reference](#schema-reference)
    - [Basic Schema Structure](#basic-schema-structure)
    - [Field Types & Properties](#field-types--properties)
    - [Field Options & Constraints](#field-options--constraints)
    - [List Fields](#list-fields)
    - [Optional Fields and Defaults](#optional-fields-and-defaults)
- [Working with Responses](#working-with-responses)
  - [Response Format](#response-format)
  - [Field Access](#field-access)
  - [Response Features](#response-features)
- [Error Handling](#error-handling)
- [Logging](#logging)


## Core Functions

### register()

Registers a directory containing prompt templates for use with LangTask.

```python
def register(directory: str | Path) -> None
```

**Parameters:**
- `directory`: Path to directory containing prompt templates. Can be string or Path object.

**Raises:**
- `FileSystemError`: When directory access fails or required files are missing
- `InitializationError`: When prompt registration fails due to invalid configurations

**Example:**
```python
# Register single directory
lt.register("./prompts")

# Register with Path object
from pathlib import Path
lt.register(Path("./client_prompts"))

# Multiple directories can be registered
lt.register("./prompts/common")
lt.register("./prompts/specialized")
```

### run()

Generates a response using a registered prompt with optional input parameters.

```python
def run(
    prompt_id: str,
    input_params: Dict[str, Any] | None = None
) -> str | StructuredResponse
```

**Parameters:**
- `prompt_id`: ID of the registered prompt to use
- `input_params`: Optional dictionary of parameters required by the prompt template

**Returns:**
- `str`: Raw text response when no output schema is defined
- `StructuredResponse`: Pydantic model instance with dot notation access when output schema is defined

**Raises:**
- `ExecutionError`: Processing or runtime failures
- `ProviderAPIError`: LLM provider communication issues
- `DataValidationError`: Input parameter validation failures
- `SchemaValidationError`: Output schema validation failures
- `PromptValidationError`: When prompt not found or no directories registered

**Examples:**

Basic usage:
```python
# Simple text generation (no output schema)
response = lt.run("greeting", {"name": "Alice", "style": "casual"})
print(response)  # "Hey Alice! What's up?"

# With structured output
result = lt.run("analyze-sentiment", {"text": "I love this product!"})
print(result.sentiment)      # "positive"
print(result.confidence)     # 0.95
print(result.word_count)     # 2

# Convert to dictionary if needed
data = result.model_dump()
```

Error handling:
```python
try:
    response = lt.run("analyze-text", {"text": user_input})
except lt.DataValidationError as e:
    print(f"Invalid input: {e.message}")
except lt.ProviderAPIError as e:
    print(f"LLM provider error: {e.message}")
except lt.SchemaValidationError as e:
    print(f"Schema validation failed: {e.message}")
```

### list_directories()

Retrieves information about registered directories.

```python
def list_directories() -> List[str]
```

**Returns:**
List of registered directory paths

**Examples:**
```python
# List registered directories
dirs = lt.list_directories()
print(f"Registered directories: {dirs}")
```

### list_prompts()

Retrieves information about registered prompts.

```python
def list_prompts() -> List[str]
```

**Returns:**
List of registered prompt IDs

**Examples:**
```python
# List registered prompts
prompts = lt.list_prompts()
print(f"Registered prompts: {prompts}")
```

### get_prompt()

Retrieves information about a specific prompt.

```python
def get_prompt(
    id: str,
    what: Literal["directories", "prompts"] | None = None
) -> Dict[str, Any] | List[str]
```

**Parameters:**
- `id`: ID of the prompt to retrieve
- `what`: Type of information to retrieve:
  - `"directories"`: List of directory paths
  - `"prompts"`: Dictionary of prompt configurations
  - `None`: Complete prompt information

**Returns:**
Various return types based on parameters:
- With `what="directories"`: List of directory paths
- With `what="prompts"`: Dictionary of prompt configurations
- With `what=None`: Complete prompt information

**Examples:**
```python
# Get prompt configurations
prompts = lt.get_prompt("translate-text", "prompts")
print(f"\nPrompt: translate-text")
print(f"Display Name: {prompts.get('display_name', 'translate-text')}")
print(f"Provider: {prompts['llm'][0]['provider']}")
print(f"Has Input Schema: {prompts['schemas']['input']['exists']}")
print(f"Has Output Schema: {prompts['schemas']['output']['exists']}")

# Get specific prompt information
info = lt.get_prompt("translate-text", "prompts")
if info['schemas']['input']['exists']:
    print("Required Input Fields:")
    schema = info['schemas']['input']['content']
    for field, details in schema['properties'].items():
        print(f"- {field}: {details['type']}")
```

### set_global_config()

Sets or resets the global configuration for LLM settings.

```python
def set_global_config(
    config: str | Dict[str, Any] | List[Dict[str, Any]] | None = None,
    override_local_config: bool = False
) -> None
```

**Parameters:**
- `config`: Configuration source:
  - `None`: Reset to default configuration
  - `str`: Path to YAML configuration file
  - `dict`: Single LLM configuration
  - `list`: Multiple LLM configurations in priority order
- `override_local_config`: If True, global settings override prompt-specific ones

**Examples:**
```python
# Single provider configuration
lt.set_global_config({
    "provider": "anthropic",
    "model": "claude-3-5-haiku-20241022",
    "temperature": 0.7,
    "max_tokens": 2000
})

# Multiple providers with fallback
lt.set_global_config([
    {
        "provider": "anthropic",
        "model": "claude-3-5-haiku-20241022",
        "temperature": 0.7
    },
    {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.5
    }
])

# Load from file
lt.set_global_config("config/llm_settings.yaml")

# Reset to defaults
lt.set_global_config(None)

# Override local configs
lt.set_global_config({
    "provider": "anthropic",
    "model": "claude-3-5-haiku-20241022"
}, override_local_config=True)
```

### get_global_config()

Retrieves current global configuration settings.

```python
def get_global_config() -> Dict[str, Any]
```

**Returns:**
Dictionary containing current global LLM configuration

**Example:**
```python
config = lt.get_global_config()
print(f"Provider: {config['llm']['provider']}")
print(f"Model: {config['llm']['model']}")
print(f"Temperature: {config['llm']['temperature']}")
```

### set_logs()

Configure logging settings and output handlers.

```python
def set_logs(
    path: str | Path | None = None,
    console_level: LogLevel = 'INFO',
    file_level: LogLevel = 'DEBUG',
    rotation: str = '10 MB',
    retention: str = '1 week'
) -> None
```

**Parameters:**
- `path`: Directory for log files. Can be string or Path object. Set to None to use default './logs' directory.
- `console_level`: Minimum level for console logging (default: 'INFO')
  - Valid levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
- `file_level`: Minimum level for file logging (default: 'DEBUG')
  - Valid levels: same as console_level
- `rotation`: When to rotate log files (default: '10 MB')
  - Size-based: '10 MB', '1 GB', etc.
  - Time-based: '1 day', '1 week', etc.
- `retention`: How long to keep old logs (default: '1 week')
  - Examples: '1 week', '1 month', '90 days'

**Raises:**
- `FileSystemError`: When specified directory cannot be accessed or created
- `ConfigurationError`: When log settings are invalid (e.g., invalid log level)

**Examples:**

Basic usage:
```python
# Use custom log directory
lt.set_logs("./my_logs")

# Use Path object
from pathlib import Path
lt.set_logs(Path("/var/log/myapp"))

# Reset to defaults
lt.set_logs()
```

Advanced configuration:
```python
# Detailed configuration
lt.set_logs(
    path="./app/logs",         # Custom directory
    console_level="WARNING",   # Less console output
    file_level="DEBUG",        # Detailed file logs
    rotation="100 MB",         # Larger log files
    retention="1 month"        # Keep logs longer
)

# Production settings
lt.set_logs(
    path="/var/log/myapp",
    console_level="ERROR",     # Minimal console output
    file_level="INFO",         # Standard file logging
    rotation="1 GB",           # Large log files
    retention="90 days"        # Extended retention
)
```

Error handling:
```python
try:
    lt.set_logs("/path/to/logs", console_level="DEBUG")
except lt.FileSystemError as e:
    print(f"Log directory error: {e.message}")
except lt.ConfigurationError as e:
    print(f"Configuration error: {e.message}")
```

## Creating Custom Prompts

### Directory Structure

Each prompt in your prompt directory should follow this structure:

```
prompts/
└── your-prompt/
    ├── config.yaml          # LLM and prompt configuration
    ├── instructions.md      # Prompt template
    ├── input_schema.yaml    # Input validation schema (optional)
    └── output_schema.yaml   # Output validation schema (optional)
```

### Prompt Instructions (instructions.md)

The `instructions.md` file supports variable interpolation using double curly braces. Variable names are case-insensitive:

```markdown
Write a {{style}} message for {{name}} about {{topic}}.
# These are equivalent:
Write a {{STYLE}} message for {{NAME}} about {{TOPIC}}.
Write a {{Style}} message for {{Name}} about {{Topic}}.

The message should be:
1. Appropriate for the given style
2. Personalized using the name
3. Focused on the specified topic
```

### Configuration (config.yaml)

Structure of `config.yaml` for individual prompts:

```yaml
# Required fields
id: "prompt-id"

# Optional fields
display_name: Human Readable Name
description: Description of what this prompt does

# Optional LLM settings (will use global config if not specified)
llm:
  provider: anthropic
  model: claude-3-5-haiku-20241022
  temperature: 0.7

# Optional multiple providers
llm:
  - provider: anthropic
    model: claude-3-5-haiku-20241022
    temperature: 0.7
  - provider: openai
    model: gpt-4o-mini
    temperature: 0.5
```

### Schema Reference

#### Basic Schema Structure

Both input (`input_schema.yaml`) and output (`output_schema.yaml`) schemas follow the same rules and syntax. All field names are stored internally as lowercase. 

```yaml
field_name:
  type: string         # Required - type of the field
  description: ...   # Optional - field description
  required: false      # Optional - defaults to true
  options: [...]       # Optional - restrict allowed values (for string, integer, and number types)
  list: ...            # Optional - make field a list
  default: ...         # Optional - default value if field missing
```

#### Field Types & Properties

```yaml
# String fields with constraints
name:
  type: string
  description: User's name
  min_characters: 2        # Minimum string length
  max_characters: 100      # Maximum string length
  pattern: ^[a-zA-Z ]+$    # Regex pattern for validation

# Numeric fields with constraints
# type: integer for whole numbers, number for float/decimal values
score:
  type: number
  description: "Score value"
  min: 0                # Minimum value (inclusive)
  max: 100              # Maximum value (inclusive)
  exclusive_min: 0      # Minimum value (exclusive)
  exclusive_max: 100    # Maximum value (exclusive)
  multiple_of: 0.5      # Must be multiple of this value

# Note: min/exclusive_min and max/exclusive_max cannot be used together

# Boolean fields
is_active:
  type: boolean
  description: "Whether the item is active"

# Object fields with nested properties
metadata:
  type: object
  description: Additional metadata
  properties:
    name:
      type: string
    count:
      type: integer
```

#### Field Options & Constraints

```yaml
# String options
status:
  type: string
  description: Processing status
  options: ["complete", "partial", "failed"]

# Integer options
priority:
  type: integer
  description: Task priority level
  options: [1, 2, 3]

# Number (float) options
confidence:
  type: number
  description: Processing confidence
  options: [0.25, 0.5, 0.75, 1.0]
```

#### List Fields

```yaml
# Unconstrained list
tags:
  type: string
  list: true
  description: Tag list

# Exact count
required_scores:
  type: number
  list: 3
  options: [1, 2, 3, 4, 5]
  description: Must provide exactly 3 scores

# Range of items
categories:
  type: string
  list: 1-3
  options: ["A", "B", "C"]
  description: Between 1 and 3 categories

# Minimum items
products:
  type: object
  list: 3+
  description: At least 3 products
  properties:
    name:
      type: string
    price:
      type: number
```

List specifications:
- `list: true` - Any number of items
- `list: n` - Exactly n items
- `list: n-m` - Between n and m items
- `list: n+` - n or more items

#### Optional Fields and Defaults

```yaml
# Optional field with default
format:
  type: string
  options: ["short", "long"]
  required: false
  default: short
  description: Output format

# Optional field without default (will be null if not provided)
notes:
  type: string
  required: false
  description: Additional notes

# Optional nested object
metadata:
  type: object
  required: false
  properties:
    created_at:
      type: string
    author:
      type: string
```


## Working with Responses

When using output schemas, responses from `lt.run()` are returned as immutable Pydantic models with dot notation access. This section explains how to work with these structured responses effectively.

### Response Format

```python
response = lt.run("analyze-text", {"text": "Sample input"})

# Print full response with clean formatting
print(response)
# OutputSchemaResponse(
#     message='This is a detailed analysis...',
#     status='complete',
#     priority_level=2,
#     confidence=0.8,
#     is_final=true,
#     metadata={
#         'tone': 'formal',
#         'word_count': 42,
#         'timestamps': {
#             'started': '2024-03-22T10:15:30',
#             'completed': '2024-03-22T10:15:31'
#         }
#     }
# )
```

### Field Access

#### Basic Fields
```python
# Direct field access with dot notation
print(response.message)         # Basic string field
print(response.status)          # Field with options: "complete", "partial", "failed"
print(response.priority_level)  # Integer field with options: 1, 2, 3, 4, 5
print(response.confidence)      # Number field with options: 0.2, 0.4, 0.6, 0.8, 1.0
print(response.is_final)        # Boolean field: true or false
```

#### List Fields
```python
# Access single-type lists
for tag in response.tags:
    print(tag)  # Each tag is a string

# Access lists of objects
for product in response.products:
    print(f"Name: {product.name}")
    print(f"Price: {product.price}")
    
# List length validation is automatic
response.categories  # Will have between 1-3 items if specified in schema
response.products    # Will have 3+ items if specified in schema
```

#### Nested Fields
```python
# Access nested objects up to 4 levels deep
print(response.metadata.author)                    # Two levels
print(response.analysis.details.tone)              # Three levels
print(response.analysis.details.metrics.accuracy)  # Four levels
```

#### Optional Fields

There are two ways to handle optional fields:

```python
# 1. Using try/except
try:
    print(response.metadata.tone)  # Will raise AttributeError if metadata or tone is missing
except AttributeError:
    print("Could not access response.metadata.tone")

# 2. Using hasattr check (recommended)
if hasattr(response, 'metadata'):
    print(response.metadata.tone)
    print(response.metadata.word_count)
```

#### Converting to Dictionary
```python
# Convert entire response to dictionary
data = response.model_dump()

# Access converted data
print(data['metadata']['tone'])  # Dictionary access instead of dot notation
```

### Response Features

#### Type Safety & Validation
- Automatic type-checking and option enforcement
- List constraints and nested object validation
- Immutable objects prevent accidental modifications

#### Best Practices
1. Use `hasattr()` for optional field checking
2. Access nested fields with dot notation (e.g., `response.metadata.author`)
3. Use `model_dump()` only when dictionary format is required
4. Catch specific exceptions for optional fields
5. Let validation errors propagate for required fields


## Error Handling

LangTask provides a comprehensive exception hierarchy for detailed error handling. All exceptions are available directly from the package root:

| Exception Type | Description |
|---------------|-------------|
| **Base Exceptions** | |
| `lt.LangTaskError` | Base exception for all library errors |
| `lt.ValidationError` | Base for validation-related errors |
| `lt.ProviderError` | Base for LLM provider-related errors |
| `lt.SystemError` | Base for system-level errors |
| **Specific Exceptions** | |
| `lt.FileSystemError` | File/directory access issues |
| `lt.ConfigurationError` | Configuration-related errors |
| `lt.ProviderAPIError` | LLM provider API issues |
| `lt.ProviderQuotaError` | Rate limiting and quota issues |
| `lt.ProviderAuthenticationError` | API key and auth issues |
| `lt.SchemaValidationError` | Schema definition, structure, and response validation failures |
| `lt.DataValidationError` | Input parameter validation failures |
| `lt.PromptValidationError` | Prompt template validation issues |

### Common Error Handling

```python
try:
    response = lt.run("analyze-text", input_params)
except lt.SchemaValidationError as e:
    # Schema or response validation error
    print(f"Schema error: {e.message}")
    print(f"Field: {e.field}")
    print(f"Constraints: {e.constraints}")
except lt.ProviderError as e:
    # Provider-related errors
    print(f"Provider error: {e.message}")
    if isinstance(e, lt.ProviderQuotaError):
        print(f"Retry after {e.retry_after} seconds")
except lt.LangTaskError as e:
    # Catch-all for other library errors
    print(f"Error: {e.message}")
```

### Error Attributes

Each exception type includes the following attributes:

#### `LangTaskError` (Base class)
   - `message`: Detailed error description
   - `details`: Dictionary of error context

#### `FileSystemError`
   - `path`: Affected file/directory path
   - `operation`: Operation that failed ('read', 'write', 'access', etc.)
   - `error_code`: Optional system error code

#### `ProviderError` subclasses
   - `provider`: LLM provider name ('openai', 'anthropic')
   - `ProviderAPIError`: Additional `status_code` and `response`
   - `ProviderQuotaError`: Additional `limit_type` and `retry_after`
   - `ProviderAuthenticationError`: Additional `auth_type` and `scope`

#### Validation Errors
   - `SchemaValidationError`: `schema_type`, `field`, `constraints`
     - For lists: `constraints` includes `min`, `max`, and `actual` count
     - For options: `constraints` includes `allowed_values` and `received_value`
     - For types: `constraints` includes `expected_type` and `actual_type`
   - `DataValidationError`: `data_type`, `constraint`, `value`
   - `PromptValidationError`: `prompt_path`, `validation_type`

### Exception Details

Each exception provides contextual data through attributes. Here are common scenarios you'll encounter and how to handle them:

#### File System Operations
```python
try:
    lt.register("./nonexistent/prompts")
except lt.FileSystemError as e:
    # "Directory not found: './nonexistent/prompts'"
    print(e.path)        # './nonexistent/prompts'
    print(e.operation)   # 'access'
```

#### Authentication Issues
```python
try:
    response = lt.run("my-prompt", {"text": "Hello"})
except lt.ProviderAuthenticationError as e:
    # "Anthropic authentication failed. Verify API key..."
    print(e.provider)    # 'anthropic'
    print(e.auth_type)   # 'api_key'
```

#### Schema Validation - Missing Fields
```python
try:
    response = lt.run("translate", {})
except lt.SchemaValidationError as e:
    # "Missing required field 'text'"
    print(e.schema_type) # 'input'
    print(e.field)       # 'text'
    print(e.constraints) # {'error_type': 'missing', ...}
```

#### Schema Validation - List Constraints
```python
try:
    response = lt.run("analyze", {"categories": ["A", "B", "C", "D"]})
except lt.SchemaValidationError as e:
    # "List validation failed: Field 'categories' expects 1-3 items, got 4"
    print(e.schema_type) # 'list'
    print(e.field)       # 'categories'
    print(e.constraints) # {'min': 1, 'max': 3, 'actual': 4}
```

#### Rate Limiting
```python
try:
    response = lt.run("analyze", {"text": "Sample"})
except lt.ProviderQuotaError as e:
    # "Rate limit exceeded for provider 'anthropic'. Try again in 30 seconds"
    print(e.provider)     # 'anthropic'
    print(e.retry_after)  # 30
```


## Logging

LangTask's logging system offers configurable outputs with structured formatting and comprehensive error tracking.

### Core Features
- Console and file logging with separate log levels
- Automatic log rotation and retention
- Request ID tracking for operation correlation
- Performance metrics and duration tracking
- Structured output format for easy parsing
- Color-coded console output for readability

### Log Format
Each log entry includes:
- Timestamp
- Request ID (for tracking related operations)
- Log level
- Module name
- Main message
- Additional context fields

### Console Output
Color-coded output (configurable level, default INFO):
```
2024-03-22 10:15:30 | req-123 | INFO    | prompt_loader  | Loading prompt | prompt_id=greeting
2024-03-22 10:15:31 | req-123 | SUCCESS | llm_processor  | Request processed | duration_ms=523.45
```

### File Output
Detailed output (configurable level, default DEBUG):
```
2024-03-22 10:15:30 | req-123 | DEBUG   | schema_loader  | Schema validation starting | schema_type=input
2024-03-22 10:15:31 | req-123 | SUCCESS | llm_processor  | Request processed | provider=anthropic duration_ms=523.45
```

### Log Levels
Supported levels in order of verbosity:
- `DEBUG`: Detailed debugging information
- `INFO`: General operational messages
- `WARNING`: Issues that need attention but don't prevent operation
- `ERROR`: Operation-specific failures
- `CRITICAL`: System-level failures

### Performance Tracking
Automatic performance metrics:
- Operation duration in milliseconds
- Resource usage indicators
- Success/failure status

Example performance tracking:
```python
# Configure logging with performance tracking
lt.set_logs(
    path="./logs",
    console_level="INFO",
    file_level="DEBUG"
)

# Performance metrics are automatically logged
response = lt.run("analyze-text", {"text": "Sample input"})

# Console output example:
# 2024-03-22 10:15:31 | INFO    | Request started  | prompt_id=analyze-text
# 2024-03-22 10:15:32 | SUCCESS | Request complete | duration_ms=523.45
```

### Default Configuration
If not explicitly configured:
- Console: INFO level with colors
- File: DEBUG level for troubleshooting
- Location: ./logs/langtask.log
- Rotation: 10 MB maximum file size
- Retention: 1 week

### Error Handling
The logging system has two fallback levels:
1. Default directory (`./logs`): Falls back to console-only logging with warning
2. Custom directory: Raises appropriate error with details