"""Domain objects: the data the whole system speaks. See docs/architecture/06-domain-model.md."""

from open_rag_engine.domain.answer import Answer, Citation, Verdict
from open_rag_engine.domain.base import DomainModel, evolve
from open_rag_engine.domain.chunk import Chunk, ChunkDraft
from open_rag_engine.domain.document import Document, Heading, PageSpan, ParsedDocument
from open_rag_engine.domain.pipeline import PipelineState, StageTiming
from open_rag_engine.domain.query import Query, QueryOptions, RequestContext
from open_rag_engine.domain.retrieval import ScoredChunk, ScoreSource
from open_rag_engine.domain.span import Span
from open_rag_engine.domain.types import NonBlankStr, Offset, PageNumber, Sha256Hex, Slug

__all__ = [
    "Answer",
    "Chunk",
    "ChunkDraft",
    "Citation",
    "Document",
    "DomainModel",
    "Heading",
    "NonBlankStr",
    "Offset",
    "PageNumber",
    "PageSpan",
    "ParsedDocument",
    "PipelineState",
    "Query",
    "QueryOptions",
    "RequestContext",
    "ScoreSource",
    "ScoredChunk",
    "Sha256Hex",
    "Slug",
    "Span",
    "StageTiming",
    "Verdict",
    "evolve",
]
