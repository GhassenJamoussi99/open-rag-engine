"""Protocols for the ingestion side: parse, chunk, embed, store."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from open_rag_engine.domain import ChunkDraft, Document, ParsedDocument
from open_rag_engine.interfaces.types import EmbeddedChunk, SourceFile, Vector


class Parser(Protocol):
    @property
    def supported_types(self) -> frozenset[str]:
        """File suffixes this parser handles, lowercase with the dot, such as `.pdf`."""
        ...

    def parse(self, source: SourceFile) -> ParsedDocument:
        """Extract text, pages and headings. Raises `ParseError` on unreadable files."""
        ...


class Chunker(Protocol):
    @property
    def name(self) -> str: ...

    def chunk(self, document: ParsedDocument) -> list[ChunkDraft]: ...


class Embedder(Protocol):
    """Synchronous and CPU bound. Async callers run it with `asyncio.to_thread`."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_passages(self, texts: Sequence[str]) -> list[Vector]: ...

    def embed_query(self, text: str) -> Vector: ...


class DocumentRepository(Protocol):
    """Documents are identified by `(tenant_id, source_uri)`; every call is tenant scoped."""

    async def get_by_uri(self, tenant_id: str, source_uri: str) -> Document | None: ...

    async def replace(self, document: Document, chunks: Sequence[EmbeddedChunk]) -> None:
        """Write the document and all its chunks in one transaction, dropping old chunks.

        Replaces the existing document with the same tenant and source URI, if any.
        """
        ...

    async def delete(self, tenant_id: str, document_id: UUID) -> None:
        """Delete a document and its chunks. A document of another tenant is left alone."""
        ...
