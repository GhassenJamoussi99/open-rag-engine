import pytest

from open_rag_engine.interfaces import (
    ConfigError,
    DependencyError,
    LLMBadResponse,
    LLMError,
    LLMRateLimited,
    LLMTimeout,
    ParseError,
    RagError,
    StoreUnavailable,
)


@pytest.mark.parametrize(
    ("error", "parent"),
    [
        (ConfigError, RagError),
        (ParseError, RagError),
        (DependencyError, RagError),
        (StoreUnavailable, DependencyError),
        (LLMError, DependencyError),
        (LLMTimeout, LLMError),
        (LLMRateLimited, LLMError),
        (LLMBadResponse, LLMError),
    ],
)
def test_hierarchy(error: type[RagError], parent: type[RagError]) -> None:
    assert issubclass(error, parent)


def test_parse_error_names_the_file() -> None:
    error = ParseError("contracts/msa.pdf", "no text layer")

    assert error.source_uri == "contracts/msa.pdf"
    assert str(error) == "contracts/msa.pdf: no text layer"
