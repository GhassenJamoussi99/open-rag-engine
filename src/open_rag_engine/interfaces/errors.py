"""One error hierarchy for the whole system. Fallbacks catch specific types, never Exception."""


class RagError(Exception):
    """Base class for every error open-rag-engine raises on purpose."""


class ConfigError(RagError):
    """The configuration is invalid; raised at startup."""


class ParseError(RagError):
    """A source file could not be parsed. Ingestion logs it and moves on."""

    def __init__(self, source_uri: str, reason: str) -> None:
        super().__init__(f"{source_uri}: {reason}")
        self.source_uri = source_uri
        self.reason = reason


class DependencyError(RagError):
    """An external dependency (store, model provider) failed."""


class StoreUnavailable(DependencyError):
    """The vector or keyword store timed out or is down."""


class LLMError(DependencyError):
    """The LLM provider failed."""


class LLMTimeout(LLMError):
    """The provider did not answer in time."""


class LLMRateLimited(LLMError):
    """The provider is throttling requests."""


class LLMBadResponse(LLMError):
    """The provider answered with output that can't be used."""
