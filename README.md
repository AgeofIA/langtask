# LangTask

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-pre--alpha-red)

LangTask is a lightweight Python library for rapidly setting up and managing LLM prompts with structured input/output validation. It provides a clean, type-safe interface for working with language models while enforcing schema validation and proper error handling.

> ⚠️ **Note**: This is a pre-alpha, work-in-progress project used internally for client work. It is not yet stable for production use and the API may change significantly.

## Features

- 🔍 **Schema Validation**: Type-safe input and output validation using Pydantic models with dot notation access
- 🔄 **Provider Flexibility**: Support for multiple LLM providers (currently OpenAI and Anthropic)
- 📝 **Prompt Management**: Simple directory-based prompt organization and discovery
- ⚡ **Easy Integration**: Clean API for registering and running prompts
- 🛠️ **Error Handling**: Comprehensive error hierarchy with detailed feedback
- 📊 **Logging**: Structured logging with request tracing and performance monitoring

## Installation

```bash
pip install langtask
```

## Quick Start

First, import the library (we'll use this import in all following examples):
```python
import langtask as lt
```

1. Create a prompt directory structure:

```
prompts/
└── greeting/
    ├── config.yaml           # LLM configuration
    ├── instructions.md       # Prompt template
    ├── input_schema.yaml     # Input validation schema
    └── output_schema.yaml    # Output validation schema (optional)
```

2. Configure your prompt:

```yaml
# config.yaml
id: greeting
display_name: "Greeting Generator"
description: "Generates personalized greetings"
llm:
  provider: "anthropic"
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.7
```

3. Define input schema:

```yaml
# input_schema.yaml
name:
  type: string
  description: "Name of the person to greet"
style:
  type: string
  description: "Style of greeting (formal/casual)"
  enum: ["formal", "casual"]
```

4. Create prompt instructions:

```markdown
# Note: Variable names are case-insensitive
Generate a {{STYLE}} greeting for {{Name}}.
# Will work the same as:
Generate a {{style}} greeting for {{name}}.
```

5. Use in your code:

```python
# Register prompt directory
lt.register("./prompts")

# For simple text responses (no output schema)
response = lt.run("greeting", {
    "NAME": "Alice",  # Will work
    "style": "casual" # Will also work
})
print(response)  # "Hey Alice! How's it going?"

# For structured responses (with output schema)
response = lt.run("analyze-sentiment", {
    "text": "Great product!"
})
print(response.sentiment)      # "positive"
print(response.confidence)     # 0.95
print(response.word_count)     # 2
```

## Variable Naming

LangTask handles variable names case-insensitively throughout the system:
- Template variables like `{{NAME}}`, `{{name}}`, or `{{Name}}` are treated as identical
- Input parameters can use any case (e.g., `"NAME"`, `"name"`, `"Name"`)
- Schema definitions use lowercase internally
- All comparisons and validations are case-insensitive

This makes the system more flexible and less error-prone when dealing with variable names.

## Example Prompt Structure

LangTask uses a directory-based approach for organizing prompts:

```
prompts/
├── greeting/
│   ├── config.yaml
│   ├── instructions.md
│   └── input_schema.yaml
└── sentiment/
    ├── config.yaml
    ├── instructions.md
    ├── input_schema.yaml
    └── output_schema.yaml
```

Each prompt requires:
- `config.yaml`: LLM provider settings and prompt metadata
- `instructions.md`: The actual prompt template with variable placeholders
- `input_schema.yaml`: Schema defining expected input parameters
- `output_schema.yaml`: Schema for structured output validation (required for dot notation access)

## Configuration

Set global defaults for all prompts:

```python
lt.set_global_config({
    "provider": "anthropic",
    "model": "claude-3-opus-20240229",
    "temperature": 0.1
})
```

Or use provider-specific settings per prompt in `config.yaml`:

```yaml
llm:
  - provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.7
  - provider: "openai"
    model: "gpt-4"
    temperature: 0.5
    max_tokens: 1000
```

## Structured Responses

When using output schemas, responses are returned as Pydantic models with dot notation access:

```yaml
# Define output schema (output_schema.yaml):
sentiment:
  type: string
  description: "Detected sentiment"
  enum: ["positive", "negative", "neutral"]
confidence:
  type: number
  description: "Confidence score"
word_count:
  type: integer
  description: "Number of words analyzed"
```

```python
# Access in code:
result = lt.run("analyze-sentiment", {"text": "Great product!"})

# Access fields with dot notation
print(result.sentiment)    # "positive"
print(result.confidence)   # 0.95
print(f"Analysis based on {result.word_count} words")

# Convert to dictionary if needed
data = result.model_dump()
```

Key benefits:
- Type-safe field access
- IDE autocompletion support
- Immutable response objects
- Automatic type conversion
- Clear error messages for invalid access

## Logging

LangTask provides comprehensive logging with configurable settings for both console and file output:

### Features
- Colored console output with configurable level
- File logging with automatic rotation
- Request ID tracking for operation tracing
- Performance metrics for monitoring
- Structured formatting for easy parsing

### Configuration
Use `set_logs()` to configure logging behavior:

```python
# Basic usage - just set log directory
lt.set_logs("./my_logs")

# Detailed configuration
lt.set_logs(
    path="./app/logs",              # Custom log directory
    console_level="WARNING",        # Less console output
    file_level="DEBUG",            # Detailed file logs
    rotation="100 MB",             # Larger log files
    retention="1 month"            # Keep logs longer
)

# Reset to defaults (logs/ directory with standard settings)
lt.set_logs()
```

### Configuration Options
- `path`: Directory for log files (default: './logs')
- `console_level`: Console logging level (default: 'INFO')
  - Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
- `file_level`: File logging level (default: 'DEBUG')
  - Options: Same as console_level
- `rotation`: When to rotate log files (default: '10 MB')
  - Size-based: '10 MB', '1 GB', etc.
  - Time-based: '1 day', '1 week', etc.
- `retention`: How long to keep old logs (default: '1 week')
  - '1 week', '1 month', '90 days', etc.

### Default Behavior
- Console: INFO level with color-coded output
- File: DEBUG level for detailed troubleshooting
- Location: `./logs/langtask.log`
- Rotation: 10 MB file size
- Retention: 1 week

### Fallback Behavior
If the specified log directory cannot be created or accessed:
- Custom path: Raises FileSystemError
- Default path: Falls back to console-only logging with warning

### Example Log Output
```
2024-03-22 10:15:30 | req-123 | INFO    | prompt_loader  | Loading prompt | prompt_id=greeting
2024-03-22 10:15:30 | req-123 | WARNING | schema_loader  | Unknown field detected | field=custom_param
2024-03-22 10:15:31 | req-123 | SUCCESS | llm_processor  | Request processed | duration_ms=523.45
```

## Environment Setup

LangTask supports multiple ways to configure your API keys:

1. Direct environment variables:
```bash
# For Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# For OpenAI
export OPENAI_API_KEY=sk-...
```

2. Using `.env` file (recommended for development):
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Then in your code:
```python
from dotenv import load_dotenv
load_dotenv()
```

3. Setting in your deployment environment (recommended for production)

Remember to add `.env` to your `.gitignore` to protect your API keys.

## Development Status

This project is in pre-alpha stage and is actively being developed. Current limitations:
- API may change without notice
- Limited provider support (OpenAI and Anthropic only)
- Basic error recovery
- Limited documentation

## Requirements

- Python 3.10 or higher
- Dependencies:
  - pydantic >= 2.0
  - langchain >= 0.1.0
  - langchain-openai >= 0.0.2
  - langchain-anthropic >= 0.1.1
  - pyyaml >= 6.0
  - python-dotenv >= 0.19.0
  - loguru >= 0.7.0

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to submit an issue or pull request.