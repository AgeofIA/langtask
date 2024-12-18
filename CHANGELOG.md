# Changelog

All notable changes to LangTask will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.2] - Unreleased

### Changed
- Removed redundant output schema format instructions from prompt templates since LangChain's `with_structured_output()` handles this natively

### Added
- Included full response output in debug logs

### Fixed
- Fixed schema validation where `required: false` was not working correctly, causing all fields to be treated as required regardless of setting
- Optional status (`required: false`) now properly cascades to child fields in nested objects

### Maintenence
- Improved output validation to better handle pre-validated responses, JSON strings, and invalid response types with clearer error messages


## [0.1.1] - 2024-12-12

### Changed
- Switched response format from dictionaries to immutable Pydantic models
- Changed `optional: true` to `required: false` in schema definitions for better alignment with industry standards
- Replaced `enum` with `options` in schema definitions for more intuitive field restrictions
- Limited options to string, integer, and number types
- Removed 'array' type in favor of new `list` attribute for more intuitive array definitions
- Adjusted logging levels across request lifecycle for cleaner console output

### Added
- Dot notation access for response fields (e.g., `response.field` instead of `response["field"]`)
- Response immutability to prevent accidental modifications
- Human-readable string representation when printing full response objects
- `model_dump()` method for converting responses to dictionaries
- Support for nested objects in schemas (up to 4 levels deep)
- Support for options on string, integer, and number fields with strict type validation
- Support for list fields with size constraints using the `list` attribute:
  - `list: true` for unconstrained lists
  - `list: n` for exactly n items
  - `list: n-m` for between n and m items
  - `list: n+` for n or more items
- List validation support for both primitive types and objects
- Support for string field constraints using:
  - min_characters: Minimum string length
  - max_characters: Maximum string length
  - pattern: Regular expression pattern
- Support for numeric field constraints using:
  - min: Minimum value (inclusive)
  - max: Maximum value (inclusive)
  - exclusive_min: Minimum value (exclusive)
  - exclusive_max: Maximum value (exclusive)
  - multiple_of: Value must be multiple of this number

### Fixed
- Resolved an error that occurred when using prompts without input_schema.yaml files
- Corrected logger parameter handling for optional schema warnings
- Enhanced field validation error messages by properly mapping Pydantic errors to user-friendly descriptions in input and output validators
- Updated prompt registration to reinitialize prompts when directories are re-registered, ensuring updates to existing prompts are captured
- Fixed request ID propagation through file reading operations to maintain consistent request tracing in logs
- Fixed incorrect OutputParserException import path and restored proper LangChain parsing error handling

### Maintenence
- Switched from Python Enums to Pydantic Literals for better type safety and simpler value handling
- Improved separation of concerns between LLM processing and output validation by moving provider interaction code from output_validator.py to llm_processor.py
- Improved API documentation structure to include "Creating Custom Prompts" and "Working with Responses" sections


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


[0.1.2]: https://github.com/AgeofIA/langtask/releases/tag/v0.1.2
[0.1.1]: https://github.com/AgeofIA/langtask/releases/tag/v0.1.1
[0.1.0]: https://github.com/AgeofIA/langtask/releases/tag/v0.1.0