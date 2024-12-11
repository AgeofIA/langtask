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
- [Configuration Reference](#configuration-reference)
  - [Global Configuration](#global-configuration)
  - [Prompt Configuration](#prompt-configuration)
  - [Schema Definitions](#schema-definitions)
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
    "model": "claude-3-opus-20240229",
    "temperature": 0.7,
    "max_tokens": 2000
})

# Multiple providers with fallback
lt.set_global_config([
    {
        "provider": "anthropic",
        "model": "claude-3-opus-20240229",
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
    "model": "claude-3-opus-20240229"
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


## Configuration Reference

### Global Configuration

Global configuration options that can be set using `set_global_config()`:

```yaml
# Single provider
provider: "anthropic"
model: "claude-3-opus-20240229"
temperature: 0.7
max_tokens: 2000

# Multiple providers (as list)
- provider: "anthropic"
  model: "claude-3-opus-20240229"
  temperature: 0.7
- provider: "openai"
  model: "gpt-4"
  temperature: 0.5
  max_tokens: 1000
```

### Prompt Configuration

Structure of `config.yaml` for individual prompts:

```yaml
# Required fields
id: "prompt-id"
llm:
  provider: "anthropic"
  model: "claude-3-opus-20240229"
  temperature: 0.7

# Optional fields
display_name: "Human Readable Name"
description: "Description of what this prompt does"

# Multiple providers
llm:
  - provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.7
  - provider: "openai"
    model: "gpt-4"
    temperature: 0.5
```

### Schema Definitions

#### Input Schema (`input_schema.yaml`)

All field names in schemas are stored internally as lowercase. Use `required: false` to mark optional fields. The `options` field can be used with string, number, and integer types to restrict allowed values:

```yaml
# String options
style:
  type: string
  description: "Writing style"
  options: ["formal", "casual", "technical"]

# Integer options
priority:
  type: integer
  description: "Task priority level"
  options: [1, 2, 3]

# Number (float) options
confidence_threshold:
  type: number
  description: "Processing confidence level"
  options: [0.25, 0.5, 0.75, 0.95]

# Regular fields without options
name:
  type: string
  description: "User's name"

is_urgent:
  type: boolean
  description: "Whether the task is urgent"

additional_context:
  type: string
  description: "Any additional context for the message"
  required: false
```

#### Output Schema (`output_schema.yaml`)

When an output schema is defined, responses are returned as Pydantic models with dot notation access:

```yaml
# Required fields (default)
message:
  type: string
  description: "Generated message"
  
status:
  type: string
  description: "Processing status"
  options: ["complete", "partial", "failed"]

priority_level:
  type: integer
  description: "Output priority"
  options: [1, 2, 3, 4, 5]

confidence:
  type: number
  description: "Confidence score"
  options: [0.2, 0.4, 0.6, 0.8, 1.0]

is_final:
  type: boolean
  description: "Whether this is the final version"

# Optional fields
metadata:
  type: object
  description: "Additional message metadata"
  required: false
  properties:
    tone:
      type: string
      description: "Detected tone of the message"
      options: ["formal", "casual", "playful"]
    word_count:
      type: integer
      description: "Number of words in the message"
```

Accessing structured responses in code:

```python
response = lt.run("analyze-text", {"text": "Sample input"})

# Direct field access with dot notation
print(response.message)
print(response.status)          # Will be one of: "complete", "partial", "failed"
print(response.priority_level)  # Will be one of: 1, 2, 3, 4, 5
print(response.confidence)      # Will be one of: 0.2, 0.4, 0.6, 0.8, 1.0
print(response.is_final)        # true or false

if hasattr(response, 'metadata'):
    print(response.metadata.tone)
    print(response.metadata.word_count)

# Convert to dictionary if needed
data = response.model_dump()
```

Key features of structured responses:
- Type-safe field access
- IDE autocompletion support
- Immutable response objects
- Automatic type conversion
- Clear error messages for invalid access

### Creating Custom Prompts

Each prompt in your prompt directory should follow this structure:

```
prompts/
└── your-prompt/
    ├── config.yaml          # LLM and prompt configuration
    ├── instructions.md      # Prompt template
    ├── input_schema.yaml    # Input validation schema
    └── output_schema.yaml   # Output validation schema (optional)
```

### Prompt Template Guidelines

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

### Config File Structure

The `config.yaml` file supports both single and multiple LLM configurations:

```yaml
# Basic configuration
id: "greeting-prompt"
display_name: "Greeting Generator"
description: "Generates customized greetings"
llm:
  provider: "anthropic"
  model: "claude-3-opus-20240229"
  temperature: 0.7
  max_tokens: 1000

# Multiple providers with fallback
id: "analysis-prompt"
display_name: "Text Analyzer"
description: "Analyzes text content"
llm:
  - provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.1
  - provider: "openai"
    model: "gpt-4"
    temperature: 0.1
```

### Schema Examples

Input schema (`input_schema.yaml`):
```yaml
name:
  type: string
  description: "Recipient's name"

style:
  type: string
  description: "Message style"
  options: ["formal", "casual", "professional"]

priority:
  type: integer
  description: "Message priority"
  options: [1, 2, 3]

is_draft:
  type: boolean
  description: "Whether this is a draft message"

topic:
  type: string
  description: "Message topic"
  required: false
```

Output schema (`output_schema.yaml`):
```yaml
message:
  type: string
  description: "Generated message"

content_type:
  type: string
  description: "Type of content generated"
  options: ["greeting", "farewell", "announcement"]

quality_score:
  type: number
  description: "Quality assessment score"
  options: [0.25, 0.5, 0.75, 1.0]

is_approved:
  type: boolean
  description: "Whether the content is approved"

metadata:
  type: object
  description: "Additional message metadata"
  required: false
  properties:
    tone:
      type: string
      description: "Detected tone of the message"
      options: ["formal", "casual", "playful"]
    word_count:
      type: integer
      description: "Number of words in the message"
```

### Variable Name Handling

LangTask uses case-insensitive matching throughout the system:

1. Template Variables:
   - Variables in `instructions.md` like `{{name}}`, `{{NAME}}`, or `{{Name}}` are treated as identical
   - All variables are converted to lowercase internally

2. Input Parameters:
   - Parameter names in `run()` calls are matched case-insensitively
   - `{"name": "Alice"}`, `{"NAME": "Alice"}`, and `{"Name": "Alice"}` are equivalent

3. Schema Definitions:
   - Field names in schema files are stored as lowercase
   - All comparisons and validations are done case-insensitively

This approach simplifies variable handling while maintaining flexibility for users.


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
| `lt.SchemaValidationError` | Schema validation failures |
| `lt.DataValidationError` | Input data validation failures |
| `lt.PromptValidationError` | Prompt-related validation issues |

### Basic Error Handling

```python
try:
    response = lt.run("analyze-text", input_params)
except lt.ValidationError as e:
    # All exceptions provide detailed error messages
    print(str(e))
    # Access additional context if needed
    print(e.details)
except lt.ProviderError as e:
    print(str(e))
    # Provider errors include provider information
    if isinstance(e, lt.ProviderQuotaError):
        print(f"Retry after {e.retry_after} seconds")
except lt.LangTaskError as e:
    print(str(e))
```

### Exception Details

Each exception provides contextual data through their attributes:

1. `FileSystemError`
```python
try:
    lt.register("./nonexistent/prompts")
except lt.FileSystemError as e:
    # e.message -> "Directory not found: './nonexistent/prompts'. Verify path is correct and directory exists."
    print(str(e))  # Prints the message
    print(e.path)  # './nonexistent/prompts'
    print(e.operation)  # 'access'
```

2. `ProviderAuthenticationError`
```python
try:
    response = lt.run("my-prompt", {"text": "Hello"})
except lt.ProviderAuthenticationError as e:
    # e.message -> "Anthropic authentication failed. Verify key format (sk-ant-...) and account status at console.anthropic.com"
    print(str(e))
    print(e.provider)  # 'anthropic'
    print(e.auth_type)  # 'api_key'
```

3. `SchemaValidationError`
```python
try:
    response = lt.run("translate", {})
except lt.SchemaValidationError as e:
    # e.message -> "Missing required field 'text'. Update the prompt to ensure all required fields are included in the response."
    print(str(e))
    print(e.schema_type)  # 'input'
    print(e.field)  # 'text'
    print(e.constraints)  # {'error_type': 'missing', ...}
```

4. `ProviderQuotaError`
```python
try:
    response = lt.run("analyze", {"text": "Sample"})
except lt.ProviderQuotaError as e:
    # e.message -> "Rate limit exceeded for provider 'anthropic'. Try again in 30 seconds."
    print(str(e))
    print(e.provider)  # 'anthropic'
    print(e.limit_type)  # 'rate_limit'
    print(e.retry_after)  # 30
```

### Error Attributes

Each exception type includes the following attributes:

1. `LangTaskError` (Base class)
   - `message`: Detailed error description
   - `details`: Dictionary of error context

2. `FileSystemError`
   - `path`: Affected file/directory path
   - `operation`: Operation that failed ('read', 'write', 'access', etc.)
   - `error_code`: Optional system error code

3. `ProviderError` subclasses
   - `provider`: LLM provider name ('openai', 'anthropic')
   - `ProviderAPIError`: Additional `status_code` and `response`
   - `ProviderQuotaError`: Additional `limit_type` and `retry_after`
   - `ProviderAuthenticationError`: Additional `auth_type` and `scope`

4. Validation Errors
   - `SchemaValidationError`: `schema_type`, `field`, `constraints`
   - `DataValidationError`: `data_type`, `constraint`, `value`
   - `PromptValidationError`: `prompt_path`, `validation_type`


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