"""Custom Exceptions

Defines the structured exception hierarchy used throughout LangTask.
Each exception includes relevant contextual information to aid in debugging
and error handling.

Exception Hierarchy:
    LangTaskError
    ├── SystemError
    │   ├── FileSystemError
    │   ├── ConfigurationError 
    │   └── EnvironmentError
    ├── ValidationError
    │   ├── SchemaValidationError
    │   ├── PromptValidationError
    │   └── DataValidationError
    ├── ProviderError
    │   ├── ProviderAPIError
    │   ├── ProviderQuotaError
    │   └── ProviderAuthenticationError
    └── ProcessingError
        ├── InitializationError
        └── ExecutionError
"""

from typing import Any


# Base Package Exception

class LangTaskError(Exception):
    """Base exception for all LangTask errors."""
    
    def __init__(self, message: str, **kwargs):
        self.details: dict[str, Any] = kwargs
        super().__init__(message)


# Level 1: Core Error Categories

class SystemError(LangTaskError):
    """Base for system-level errors including file system, configuration, and environment issues."""
    pass

class ValidationError(LangTaskError):
    """Base for validation and verification errors."""
    pass

class ProviderError(LangTaskError):
    """Base for LLM provider-related errors."""
    pass

class ProcessingError(LangTaskError):
    """Base for processing-related errors."""
    pass


# Level 2: System Errors

class FileSystemError(SystemError):
    """File system operation errors."""
    def __init__(self, message: str, path: str, operation: str, error_code: int | None = None):
        self.path = path
        self.operation = operation
        self.error_code = error_code
        super().__init__(message, path=path, operation=operation, error_code=error_code)

class ConfigurationError(SystemError):
    """Configuration-related errors."""
    def __init__(self, message: str, config_key: str | None = None, source: str | None = None):
        self.config_key = config_key
        self.source = source
        super().__init__(message, config_key=config_key, source=source)

class EnvironmentError(SystemError):
    """Environment setup and access errors."""
    def __init__(self, message: str, variable: str | None = None, required: bool = True):
        self.variable = variable
        self.required = required
        super().__init__(message, variable=variable, required=required)


# Level 2: Validation Errors

class SchemaValidationError(ValidationError):
    """Schema definition and validation errors."""
    def __init__(self, message: str, schema_type: str, field: str | None = None, constraints: dict | None = None):
        self.schema_type = schema_type
        self.field = field
        self.constraints = constraints or {}
        super().__init__(message, schema_type=schema_type, field=field, constraints=self.constraints)

class PromptValidationError(ValidationError):
    """Prompt structure and content validation errors."""
    def __init__(self, message: str, prompt_path: str, validation_type: str):
        self.prompt_path = prompt_path
        self.validation_type = validation_type
        super().__init__(message, prompt_path=prompt_path, validation_type=validation_type)

class DataValidationError(ValidationError):
    """Data content validation errors."""
    def __init__(self, message: str, data_type: str, constraint: str | None = None, value: Any = None):
        self.data_type = data_type
        self.constraint = constraint
        self.value = value
        super().__init__(message, data_type=data_type, constraint=constraint, value=value)


# Level 2: Provider Errors

class ProviderAPIError(ProviderError):
    """LLM provider API interaction errors."""
    def __init__(self, message: str, provider: str, status_code: int | None = None, response: Any = None):
        self.provider = provider
        self.status_code = status_code
        self.response = response
        super().__init__(message, provider=provider, status_code=status_code, response=response)

class ProviderQuotaError(ProviderError):
    """Provider quota and rate limit errors."""
    def __init__(self, message: str, provider: str, limit_type: str, retry_after: int | None = None, quota_info: dict | None = None):
        self.provider = provider
        self.limit_type = limit_type
        self.retry_after = retry_after
        self.quota_info = quota_info or {}
        super().__init__(message, provider=provider, limit_type=limit_type, retry_after=retry_after, quota_info=self.quota_info)

class ProviderAuthenticationError(ProviderError):
    """Provider authentication and authorization errors."""
    def __init__(self, message: str, provider: str, auth_type: str, scope: str | None = None):
        self.provider = provider
        self.auth_type = auth_type
        self.scope = scope
        super().__init__(message, provider=provider, auth_type=auth_type, scope=scope)


# Level 2: Processing Errors

class InitializationError(ProcessingError):
    """Component initialization errors."""
    def __init__(self, message: str, component: str, state: str | None = None, dependencies: list | None = None):
        self.component = component
        self.state = state
        self.dependencies = dependencies or []
        super().__init__(message, component=component, state=state, dependencies=self.dependencies)

class ExecutionError(ProcessingError):
    """Execution and runtime processing errors."""
    def __init__(self, message: str, operation: str, details: dict | None = None):
        self.operation = operation
        self.details = details or {}
        super().__init__(message, operation=operation, details=self.details)