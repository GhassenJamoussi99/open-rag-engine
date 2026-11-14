"""Small working implementations of every Phase 1 Protocol, used instead of mocks."""

import asyncio
import hashlib
import math
import re
from collections.abc import AsyncIterator, Sequence
from uuid import UUID

from open_rag_engine.domain import (
    ChunkDraft,
    Document,
    PageSpan,
    ParsedDocument,
    PipelineState,
    Query,
    ScoredChunk,
    Span,
    evolve,
)
from open_rag_engine.interfaces import (
    EmbeddedChunk,
    LLMEvent,
    LLMRequest,
    LLMResponse,
    Retriever,
    SearchFilters,
    SourceFile,
    StreamEnd,
    TextDelta,
    Vector,
    build_filters,
)

_WORD = re.compile(r"[a-z0-9]+")


class FakeParser:
    """Parses UTF-8 text files as a single page; the first line is the title."""

    supported_types = frozenset({".txt"})

    def parse(self, source: SourceFile) -> ParsedDocument:
        text = source.content.decode("utf-8")
        return ParsedDocument(
            source_uri=source.source_uri,
            content_hash=source.content_hash,
            doc_type=source.doc_type,
            title=text.splitlines()[0].strip() or None,
            text=text,
            pages=(PageSpan(page=1, char_start=0, char_end=len(text)),),
        )


class FakeChunker:
    """Fixed windows of `size` characters, skipping windows that are only whitespace."""

    name = "fake-fixed"

    def __init__(self, size: int = 60) -> None:
        self._size = size

    def chunk(self, document: ParsedDocument) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for start in range(0, len(document.text), self._size):
            span = Span(char_start=start, char_end=min(start + self._size, len(document.text)))
            text = document.text_at(span)
            if not text.strip():
                continue
            page_start, page_end = document.pages_for_span(span)
            drafts.append(
                ChunkDraft(
                    ordinal=len(drafts),
                    text=text,
                    span=span,
                    page_start=page_start,
                    page_end=page_end,
                    token_count=max(len(text.split()), 1),
                )
            )
        return drafts


class FakeEmbedder:
    """Bag-of-words hashing embedder: deterministic, and texts sharing words score higher."""

    model_name = "fake-bow"
    dimension = 64

    def embed_passages(self, texts: Sequence[str]) -> list[Vector]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> Vector:
        return self._embed(text)

    def _embed(self, text: str) -> Vector:
        counts = [0.0] * self.dimension
        for word in _WORD.findall(text.lower()):
            bucket = int(hashlib.sha256(word.encode()).hexdigest(), 16) % self.dimension
            counts[bucket] += 1.0
        norm = math.sqrt(sum(c * c for c in counts)) or 1.0
        return tuple(c / norm for c in counts)


class InMemoryStore:
    """Implements both DocumentRepository and VectorStore, like the Postgres adapter will."""

    def __init__(self) -> None:
        self._documents: dict[tuple[str, str], Document] = {}
        self._chunks: dict[UUID, tuple[EmbeddedChunk, ...]] = {}

    async def get_by_uri(self, tenant_id: str, source_uri: str) -> Document | None:
        return self._documents.get((tenant_id, source_uri))

    async def replace(self, document: Document, chunks: Sequence[EmbeddedChunk]) -> None:
        if any(item.chunk.document_id != document.id for item in chunks):
            raise ValueError("every chunk must belong to the document being replaced")
        key = (document.tenant_id, document.source_uri)
        previous = self._documents.get(key)
        if previous is not None:
            self._chunks.pop(previous.id, None)
        self._documents[key] = document
        self._chunks[document.id] = tuple(chunks)

    async def delete(self, tenant_id: str, document_id: UUID) -> None:
        match = next((key for key, doc in self._documents.items() if doc.id == document_id), None)
        if match is None or match[0] != tenant_id:
            return
        del self._documents[match]
        self._chunks.pop(document_id, None)

    async def search(self, vector: Vector, k: int, filters: SearchFilters) -> list[ScoredChunk]:
        visible = [doc for doc in self._documents.values() if _matches(doc, filters)]
        hits = [
            ScoredChunk(chunk=item.chunk, score=_dot(vector, item.vector), source="dense")
            for doc in visible
            for item in self._chunks.get(doc.id, ())
        ]
        return sorted(hits, key=lambda hit: hit.score, reverse=True)[:k]


class FakeDenseRetriever:
    def __init__(self, embedder: FakeEmbedder, store: InMemoryStore) -> None:
        self.name = "dense"
        self._embedder = embedder
        self._store = store

    async def retrieve(self, query: Query, filters: SearchFilters, k: int) -> list[ScoredChunk]:
        vector = await asyncio.to_thread(self._embedder.embed_query, query.text)
        return await self._store.search(vector, k, filters)


class ScriptedLLM:
    """Returns a fixed reply; streams it word by word, then one StreamEnd event."""

    model_name = "scripted"

    def __init__(self, reply: str) -> None:
        self._reply = reply

    async def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=self._reply,
            model=self.model_name,
            input_tokens=len(request.prompt.split()),
            output_tokens=len(self._reply.split()),
        )

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMEvent]:
        for word in self._reply.split(" "):
            yield TextDelta(text=word + " ")
        yield StreamEnd(response=await self.generate(request))


class RetrieveStage:
    name = "retrieve"

    def __init__(self, retriever: Retriever) -> None:
        self._retriever = retriever

    async def run(self, state: PipelineState) -> PipelineState:
        filters = build_filters(state.context, state.query)
        hits = await self._retriever.retrieve(state.query, filters, state.query.options.top_k)
        return evolve(state, candidates=hits)


def _matches(document: Document, filters: SearchFilters) -> bool:
    if document.tenant_id != filters.tenant_id:
        return False
    if filters.doc_types and document.doc_type not in filters.doc_types:
        return False
    return not document.access_tags or bool(set(document.access_tags) & set(filters.access_tags))


def _dot(left: Vector, right: Vector) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
