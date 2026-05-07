from __future__ import annotations


class SalesTrainerError(Exception):
    """Base class for controlled application errors."""


class SessionNotFoundError(SalesTrainerError):
    """Raised when a session cannot be found."""


class SessionNotActiveError(SalesTrainerError):
    """Raised when an operation requires an active session."""


class StateVersionConflictError(SalesTrainerError):
    """Raised when a stale session update would overwrite newer state."""


class UnknownScenarioError(SalesTrainerError):
    """Raised when a scenario_id is unknown."""


class UnknownPersonaError(SalesTrainerError):
    """Raised when a persona_id is unknown."""


class LLMProviderConfigurationError(SalesTrainerError):
    """Raised when LLM provider configuration or policy is invalid."""


class PersonaGenerationError(SalesTrainerError):
    """Raised when persona generation cannot produce a valid profile."""


class RepositoryUnavailableError(SalesTrainerError):
    """Raised when the configured repository backend cannot be used."""


class SpeechToTextConfigurationError(SalesTrainerError):
    """Raised when speech-to-text backend configuration is invalid."""


class SpeechTranscriptionError(SalesTrainerError):
    """Raised when speech transcription cannot be completed."""


class SpeechUploadTooLargeError(SalesTrainerError):
    """Raised when an uploaded audio payload exceeds the configured size limit."""


class UnsupportedAudioTypeError(SalesTrainerError):
    """Raised when an uploaded audio payload uses an unsupported content type."""


class SpeechConcurrencyLimitError(SalesTrainerError):
    """Raised when the speech backend is already processing another request."""
