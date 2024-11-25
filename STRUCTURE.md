# LangTask Project Structure

This document provides an overview of the LangTask project structure.

```
project_root/
│
├── langtask/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── logger.py
│   │   ├── file_validator.py
│   │   ├── file_reader.py
│   │   ├── prompt_discoverer.py
│   │   ├── prompt_registrar.py
│   │   ├── config_models.py
│   │   ├── config_loader.py
│   │   ├── global_config.py
│   │   ├── llm_connector.py
│   │   ├── input_validator.py
│   │   ├── llm_processor.py
│   │   ├── schema_loader.py
│   │   └── prompt_loader.py
│   │
│   └── api.py
│
├── pyproject.toml
├── MANIFEST.in
├── requirements.txt
├── README.md
├── STRUCTURE.md
├── API.md
└── LICENSE
```

## Directory and File Descriptions

### langtask/
The main package directory containing all the core functionality.

- `__init__.py`: Package initialization file.
- `api.py`: The directory of methods available for the package.

#### core/
Contains the core components of the LangTask package.

- `logger.py`: Logging utility for the entire package.
- `exceptions.py`: Custom exceptions for the entire package.
- `file_validator.py`: Utility functions for validating file existence and accessibility.
- `file_reader.py`: Utility functions for reading and parsing text and YAML files.
- `prompt_registrar.py`: Manages prompt registration and initialization.
- `prompt_discoverer.py`: Handles discovery and validation of prompt files.
- `config_models.py`: Defines Pydantic models for configuration management (LLM, global, and prompt-specific configs)
- `config_loader.py`: Handles loading and management of configurations at both global and prompt-specific levels
- `global_config.py`: Manages global configuration settings for the package.
- `llm_connector.py`: Handles initialization of LLM providers and model configuration.
- `input_validator.py`: Validates input parameters against schemas.
- `llm_processor.py`: Processes LLM request to generate responses.
- `schema_loader.py`: Loads and parses schema files.
- `prompt_loader.py`: Loads and prepares prompts for LLMs.

### Other Files
- `pyproject.toml`: Project configuration and build settings using modern Python packaging standards.
- `MANIFEST.in`: Specifies additional files to include in the package distribution.
- `requirements.txt`: List of Python dependencies.
- `README.md`: Main documentation file with usage instructions.
- `STRUCTURE.md`: This file, describing the project structure.
- `API.md`: Detailed API documentation including function references and examples.
- `LICENSE`: The license file for the project.

#### Custom Prompt Directory Structure
- `config.yaml`: Configuration for the prompt.
- `input_schema.yaml`: Schema defining the expected input.
- `output_schema.yaml`: Schema defining the expected output.
- `instructions.md`: Instructions/prompt for the LLM.