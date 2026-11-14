"""Searchable pieces of a document, before and after they are stored."""

from typing import Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.span import Span
from open_rag_engine.domain.types import NonBlankStr, Offset, PageNumber, StrictCount


class _ChunkContent(DomainModel):
    """Text and exact position shared by drafts and stored chunks.

    The span must slice the document's text back to exactly `text`. The constructor
    checks the lengths; chunker property tests check the content against the document.
    """

    ordinal: Offset
    text: NonBlankStr
    span: Span
    page_start: PageNumber
    page_end: PageNumber
    section_path: tuple[NonBlankStr, ...] = ()
    token_count: StrictCount

    @model_validator(mode="after")
    def _check_position(self) -> Self:
        if self.span.length != len(self.text):
            raise ValueError(
                f"span length {self.span.length} does not match text length {len(self.text)}"
            )
        if self.page_end < self.page_start:
            raise ValueError(f"page_end {self.page_end} is before page_start {self.page_start}")
        return self


class ChunkDraft(_ChunkContent):
    """What a chunker produces: text and position, without identity yet."""


class Chunk(_ChunkContent):
    """A stored chunk: content plus its identity and the components that produced it."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    parent_id: UUID | None = None
    embedding_model: NonBlankStr
    chunker: NonBlankStr

    @model_validator(mode="after")
    def _check_parent(self) -> Self:
        if self.parent_id == self.id:
            raise ValueError("a chunk cannot be its own parent")
        return self

    @classmethod
    def from_draft(
        cls,
        draft: ChunkDraft,
        *,
        document_id: UUID,
        embedding_model: str,
        chunker: str,
        parent_id: UUID | None = None,
    ) -> Self:
        """Give a draft its identity. Always creates a new chunk id."""
        return cls.model_validate(
            {
                **dict(draft),
                "document_id": document_id,
                "embedding_model": embedding_model,
                "chunker": chunker,
                "parent_id": parent_id,
            }
        )
