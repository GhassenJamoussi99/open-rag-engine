"""Citations and final answers."""

from collections import Counter
from typing import Literal, Self
from uuid import UUID

from pydantic import model_validator

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.span import Span
from open_rag_engine.domain.types import NonBlankStr, PageNumber, StrictCount

Verdict = Literal["supported", "partial", "unsupported"]
"""The citation verifier's judgement (Phase 2)."""


class Citation(DomainModel):
    """One `[n]` marker in an answer, resolved to the exact place in the source."""

    marker: StrictCount
    chunk_id: UUID
    document_id: UUID
    title: str | None = None
    span: Span
    page_start: PageNumber
    page_end: PageNumber
    quote: NonBlankStr
    verdict: Verdict | None = None

    @model_validator(mode="after")
    def _check_pages(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError(f"page_end {self.page_end} is before page_start {self.page_start}")
        if len(self.quote) > self.span.length:
            raise ValueError(
                f"quote has {len(self.quote)} characters but its span covers {self.span.length}"
            )
        return self


class Answer(DomainModel):
    """The final answer. A refusal has no citations; an uncited answer is flagged."""

    text: NonBlankStr
    refused: bool
    citations: tuple[Citation, ...] = ()
    degraded: tuple[NonBlankStr, ...] = ()
    trace_id: NonBlankStr

    @model_validator(mode="after")
    def _check_citations(self) -> Self:
        if self.refused and self.citations:
            raise ValueError("a refused answer cannot have citations")
        counts = Counter(citation.marker for citation in self.citations)
        duplicates = sorted(marker for marker, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate citation markers: {duplicates}")
        return self

    @property
    def uncited(self) -> bool:
        """True when the system answered but could not point to any evidence."""
        return not self.refused and not self.citations
