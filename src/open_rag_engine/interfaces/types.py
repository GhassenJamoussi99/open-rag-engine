"""Boundary types: what components exchange that isn't part of the domain vocabulary."""

import hashlib
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import Field

from open_rag_engine.domain import Chunk, DomainModel, NonBlankStr, Slug

Vector = tuple[float, ...]
"""An embedding. Tuples keep vectors immutable like the rest of the domain."""


class SourceFile(DomainModel):
    """Raw bytes of a file to ingest, plus the document type it is filed under."""

    source_uri: NonBlankStr
    content: Annotated[bytes, Field(min_length=1)]
    doc_type: Slug

    @property
    def suffix(self) -> str:
        return PurePosixPath(self.source_uri).suffix.lower()

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


class EmbeddedChunk(DomainModel):
    """A chunk paired with its vector, as written to the store in one transaction."""

    chunk: Chunk
    vector: Annotated[Vector, Field(min_length=1)]
