"""Builders for valid domain objects. Tests override only the field under test."""

import hashlib
from typing import Any
from uuid import UUID, uuid4

from open_rag_engine.domain import (
    Answer,
    Chunk,
    ChunkDraft,
    Citation,
    Document,
    PageSpan,
    ParsedDocument,
    Query,
    RequestContext,
    ScoredChunk,
    Span,
)

CONTRACT_TEXT = (
    "MASTER SERVICES AGREEMENT\n"
    "1. Term. This agreement starts on the effective date.\n"
    "2. Governing Law. This agreement is governed by the laws of Delaware.\n"
)
TENANT = "acme"


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def make_parsed_document(text: str = CONTRACT_TEXT, **overrides: Any) -> ParsedDocument:
    fields: dict[str, Any] = {
        "source_uri": "contracts/msa.pdf",
        "content_hash": sha256_hex(text),
        "doc_type": "contract",
        "title": "Master Services Agreement",
        "text": text,
    }
    if "pages" not in overrides:
        fields["pages"] = (PageSpan(page=1, char_start=0, char_end=len(text)),)
    return ParsedDocument(**(fields | overrides))


def make_document(**overrides: Any) -> Document:
    fields: dict[str, Any] = {
        "id": uuid4(),
        "source_uri": "contracts/msa.pdf",
        "content_hash": sha256_hex(CONTRACT_TEXT),
        "doc_type": "contract",
        "title": "Master Services Agreement",
        "tenant_id": TENANT,
        "page_count": 1,
    }
    return Document(**(fields | overrides))


def make_chunk_draft(
    text: str = "governed by the laws of Delaware", **overrides: Any
) -> ChunkDraft:
    fields: dict[str, Any] = {
        "ordinal": 0,
        "text": text,
        "page_start": 1,
        "page_end": 1,
        "section_path": ("2. Governing Law",),
        "token_count": 6,
    }
    if "span" not in overrides:
        fields["span"] = Span(char_start=100, char_end=100 + len(text))
    return ChunkDraft(**(fields | overrides))


def make_chunk(
    text: str = "governed by the laws of Delaware",
    *,
    document_id: UUID | None = None,
    **overrides: Any,
) -> Chunk:
    draft = make_chunk_draft(text)
    fields: dict[str, Any] = dict(draft) | {
        "id": uuid4(),
        "document_id": document_id or uuid4(),
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "chunker": "recursive",
    }
    return Chunk(**(fields | overrides))


def make_scored_chunk(score: float = 0.83, **overrides: Any) -> ScoredChunk:
    fields: dict[str, Any] = {"chunk": make_chunk(), "score": score, "source": "dense"}
    return ScoredChunk(**(fields | overrides))


def make_citation(marker: int = 1, **overrides: Any) -> Citation:
    fields: dict[str, Any] = {
        "marker": marker,
        "chunk_id": uuid4(),
        "document_id": uuid4(),
        "title": "Master Services Agreement",
        "span": Span(char_start=100, char_end=132),
        "page_start": 1,
        "page_end": 1,
        "quote": "governed by the laws of Delaware",
    }
    return Citation(**(fields | overrides))


def make_answer(**overrides: Any) -> Answer:
    fields: dict[str, Any] = {
        "text": "The agreement is governed by the laws of Delaware [1].",
        "refused": False,
        "citations": (make_citation(),),
        "trace_id": "trace-1",
    }
    return Answer(**(fields | overrides))


def make_query(text: str = "Which law governs the agreement?", **overrides: Any) -> Query:
    return Query(text=text, **overrides)


def make_context(**overrides: Any) -> RequestContext:
    fields: dict[str, Any] = {"tenant_id": TENANT}
    return RequestContext(**(fields | overrides))
