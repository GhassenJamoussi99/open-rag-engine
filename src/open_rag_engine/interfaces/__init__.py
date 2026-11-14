"""Contracts between components. See docs/architecture/05-interfaces.md."""

from open_rag_engine.interfaces.errors import (
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
from open_rag_engine.interfaces.filters import SearchFilters, build_filters
from open_rag_engine.interfaces.ingestion import Chunker, DocumentRepository, Embedder, Parser
from open_rag_engine.interfaces.llm import LLMEvent, LLMRequest, LLMResponse, StreamEnd, TextDelta
from open_rag_engine.interfaces.query import LLM, Retriever, Stage, VectorStore
from open_rag_engine.interfaces.types import EmbeddedChunk, SourceFile, Vector

__all__ = [
    "LLM",
    "Chunker",
    "ConfigError",
    "DependencyError",
    "DocumentRepository",
    "EmbeddedChunk",
    "Embedder",
    "LLMBadResponse",
    "LLMError",
    "LLMEvent",
    "LLMRateLimited",
    "LLMRequest",
    "LLMResponse",
    "LLMTimeout",
    "ParseError",
    "Parser",
    "RagError",
    "Retriever",
    "SearchFilters",
    "SourceFile",
    "Stage",
    "StoreUnavailable",
    "StreamEnd",
    "TextDelta",
    "Vector",
    "VectorStore",
    "build_filters",
]
