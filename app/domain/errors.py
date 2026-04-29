from __future__ import annotations


class SalesTrainerError(Exception):
    """Base class for controlled application errors."""


class SessionNotFoundError(SalesTrainerError):
    """Raised when a session cannot be found."""


class SessionNotActiveError(SalesTrainerError):
    """Raised when an operation requires an active session."""


class UnknownScenarioError(SalesTrainerError):
    """Raised when a scenario_id is unknown."""


class UnknownPersonaError(SalesTrainerError):
    """Raised when a persona_id is unknown."""


class LLMProviderConfigurationError(SalesTrainerError):
    """Raised when LLM provider configuration or policy is invalid."""


class RepositoryUnavailableError(SalesTrainerError):
    """Raised when the configured repository backend cannot be used."""
