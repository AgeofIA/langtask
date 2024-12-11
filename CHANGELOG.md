# Changelog

All notable changes to LangTask will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.1] - Unreleased

### Changed
- Switched response format from dictionaries to immutable Pydantic models
- Changed `optional: true` to `required: false` in schema definitions for better alignment with industry standards
- Improved handling of optional input schema files to properly support prompts without input validation
- Replaced `enum` with `options` in schema definitions for more intuitive field restrictions
- Switched from Python Enums to Pydantic Literals for better type safety and simpler value handling
- Limited options to string, integer, and number types only

### Added
- Dot notation access for response fields (e.g., `response.field` instead of `response["field"]`)
- Response immutability to prevent accidental modifications
- Human-readable string representation when printing full response objects
- `model_dump()` method for converting responses to dictionaries
- Support for nested objects in schemas (up to 4 levels deep)
- Support for options on string, integer, and number fields with strict type validation

### Fixed
- Resolved an error that occurred when using prompts without input_schema.yaml files
- Corrected logger parameter handling for optional schema warnings


## [0.1.0] - 2024-11-25

### Added
- Initial release with core functionality
- Directory-based prompt management system
- Case-insensitive variable handling throughout the system
- Support for OpenAI and Anthropic LLM providers
- Comprehensive logging system with file and console output
- Schema validation using Pydantic models
- Multiple provider configurations with fallback support

#### Core Features
- Prompt registration and discovery system
- Input/output schema validation
- Template variable interpolation
- Global and per-prompt configuration
- Structured error hierarchy
- Request ID tracking for operations
- Performance monitoring and metrics

#### Configuration
- Global LLM settings management
- Provider-specific configurations
- Flexible logging configuration
- Environment variable support
- `.env` file integration

#### Logging
- Configurable console and file logging
- Log rotation and retention policies
- Color-coded console output
- Structured log formatting
- Performance metric tracking
- Request tracing support

#### Error Handling
- Comprehensive exception hierarchy
- Detailed error context
- Provider-specific error handling
- Validation error reporting
- File system error management

### Dependencies
- Python 3.10+
- pydantic >= 2.0
- langchain >= 0.1.0
- langchain-openai >= 0.0.2
- langchain-anthropic >= 0.1.1
- pyyaml >= 6.0
- python-dotenv >= 0.19.0
- loguru >= 0.7.0

[0.1.0]: https://github.com/AgeofIA/langtask/releases/tag/v0.1.0





Yes, we should update it to reflect the recent changes. The changelog currently has a few inaccuracies, particularly around which types support options. Here's how we should update the Changed and Added sections:

### Changed
- Structured responses now use Pydantic models with dot notation access instead of dictionaries
- Response objects are now immutable to prevent accidental modifications
- Changed `optional: true` to `required: false` in schema definitions for better alignment with industry standards
- Improved handling of optional input schema files to properly support prompts without input validation
- Replaced `enum` with `options` in schema definitions for more intuitive field restrictions
- Switched from Python Enums to Pydantic Literals for better type safety and simpler value handling
- Limited options to string, integer, and number types only for better semantic clarity

### Added
- Type hints for structured responses in IDE
- Automatic field type conversion in responses
- Clear error messages for invalid field access
- `model_dump()` method for converting responses to dictionaries
- Support for options on string, integer, and number fields with strict type validation

Key changes:
1. Removed boolean from supported options types in the Added section
2. Added an explicit Changed entry about limiting options to specific types
3. Made the options support entry more specific about which types are supported

Would you like me to make any other adjustments to the changelog?