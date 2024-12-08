# Changelog

All notable changes to LangTask will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-03-22

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