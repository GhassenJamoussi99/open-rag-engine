"""Parsed source files and the stored document records they become."""

from bisect import bisect_right
from collections.abc import Sequence
from itertools import pairwise
from typing import Annotated, Self
from uuid import UUID

from pydantic import Field, model_validator

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.span import Span
from open_rag_engine.domain.types import NonBlankStr, Offset, PageNumber, Sha256Hex, Slug


class PageSpan(DomainModel):
    """The character range of one page. Blank pages have an empty range."""

    page: PageNumber
    char_start: Offset
    char_end: Offset

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.char_end < self.char_start:
            raise ValueError(f"page {self.page} ends before it starts")
        return self


class Heading(DomainModel):
    """A heading found by the parser, positioned by the offset where it starts."""

    level: Annotated[int, Field(ge=1, le=6)]
    title: NonBlankStr
    char_offset: Offset


class ParsedDocument(DomainModel):
    """A file's full extracted text, its page table and its headings.

    The page spans tile the text exactly, so every character offset belongs to
    exactly one page. That is what lets a citation name its page.
    """

    source_uri: NonBlankStr
    content_hash: Sha256Hex
    doc_type: Slug
    title: str | None = None
    text: NonBlankStr
    pages: Annotated[tuple[PageSpan, ...], Field(min_length=1)]
    headings: tuple[Heading, ...] = ()

    @model_validator(mode="after")
    def _check_layout(self) -> Self:
        _check_pages_tile_text(self.pages, len(self.text))
        _check_headings(self.headings, len(self.text))
        return self

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page_for_offset(self, offset: int) -> int:
        """Return the page number that contains the character at `offset`."""
        if not 0 <= offset < len(self.text):
            raise ValueError(f"offset {offset} is outside the text (length {len(self.text)})")
        starts = [page.char_start for page in self.pages]
        return self.pages[bisect_right(starts, offset) - 1].page

    def pages_for_span(self, span: Span) -> tuple[int, int]:
        """Return the first and last page that `span` touches."""
        return self.page_for_offset(span.char_start), self.page_for_offset(span.char_end - 1)

    def text_at(self, span: Span) -> str:
        """Return the exact text covered by `span`."""
        if span.char_end > len(self.text):
            raise ValueError(
                f"span ends at {span.char_end}, past the text (length {len(self.text)})"
            )
        return self.text[span.char_start : span.char_end]


class Document(DomainModel):
    """The stored record of one source file. Its text lives in its chunks."""

    id: UUID
    source_uri: NonBlankStr
    content_hash: Sha256Hex
    doc_type: Slug
    title: str | None = None
    tenant_id: NonBlankStr
    access_tags: tuple[Slug, ...] = ()
    page_count: PageNumber


def _check_pages_tile_text(pages: Sequence[PageSpan], text_length: int) -> None:
    if [page.page for page in pages] != list(range(1, len(pages) + 1)):
        raise ValueError("pages must be numbered 1, 2, 3, ... in order")
    if pages[0].char_start != 0:
        raise ValueError("pages must start at offset 0")
    for previous, current in pairwise(pages):
        if current.char_start != previous.char_end:
            raise ValueError(f"gap or overlap between page {previous.page} and page {current.page}")
    last_end = pages[-1].char_end
    if last_end != text_length:
        raise ValueError(f"pages must end at the text length {text_length}, not at {last_end}")


def _check_headings(headings: Sequence[Heading], text_length: int) -> None:
    for heading in headings:
        if heading.char_offset >= text_length:
            raise ValueError(
                f"heading {heading.title!r} at offset {heading.char_offset} is outside the text"
            )
    offsets = [heading.char_offset for heading in headings]
    if offsets != sorted(offsets):
        raise ValueError("headings must be in text order")
