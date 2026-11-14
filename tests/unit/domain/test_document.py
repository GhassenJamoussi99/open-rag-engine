from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from open_rag_engine.domain import Heading, PageSpan, ParsedDocument, Span
from tests.factories import make_document, make_parsed_document


def _pages(*bounds: tuple[int, int]) -> tuple[PageSpan, ...]:
    return tuple(
        PageSpan(page=number, char_start=start, char_end=end)
        for number, (start, end) in enumerate(bounds, start=1)
    )


def _two_page_document(**overrides: Any) -> ParsedDocument:
    text = "a" * 100 + "b" * 50
    fields: dict[str, Any] = {"pages": _pages((0, 100), (100, 150))} | overrides
    return make_parsed_document(text, **fields)


class TestParsedDocument:
    def test_counts_pages(self) -> None:
        assert _two_page_document().page_count == 2

    @pytest.mark.parametrize(("offset", "page"), [(0, 1), (99, 1), (100, 2), (149, 2)])
    def test_maps_offset_to_page(self, offset: int, page: int) -> None:
        assert _two_page_document().page_for_offset(offset) == page

    @pytest.mark.parametrize("offset", [-1, 150])
    def test_rejects_offset_outside_text(self, offset: int) -> None:
        with pytest.raises(ValueError, match="outside"):
            _two_page_document().page_for_offset(offset)

    def test_maps_span_across_page_break(self) -> None:
        span = Span(char_start=90, char_end=110)

        assert _two_page_document().pages_for_span(span) == (1, 2)

    def test_span_ending_at_page_boundary_stays_on_that_page(self) -> None:
        span = Span(char_start=90, char_end=100)

        assert _two_page_document().pages_for_span(span) == (1, 1)

    def test_slices_text_by_span(self) -> None:
        document = _two_page_document()

        assert document.text_at(Span(char_start=98, char_end=102)) == "aabb"

    def test_rejects_span_past_end_of_text(self) -> None:
        with pytest.raises(ValueError, match="past the text"):
            _two_page_document().text_at(Span(char_start=140, char_end=151))

    def test_rejects_page_that_ends_before_it_starts(self) -> None:
        with pytest.raises(ValidationError, match="ends before it starts"):
            PageSpan(page=1, char_start=10, char_end=5)

    def test_leading_empty_page_maps_offset_zero_to_next_page(self) -> None:
        document = make_parsed_document("a" * 10, pages=_pages((0, 0), (0, 10)))

        assert document.page_for_offset(0) == 2

    def test_allows_empty_page(self) -> None:
        text = "a" * 10 + "b" * 10
        document = make_parsed_document(text, pages=_pages((0, 10), (10, 10), (10, 20)))

        assert document.page_count == 3
        assert document.page_for_offset(10) == 3

    @pytest.mark.parametrize(
        ("bounds", "message"),
        [
            (((5, 100), (100, 150)), "start at offset 0"),
            (((0, 90), (100, 150)), "gap or overlap"),
            (((0, 110), (100, 150)), "gap or overlap"),
            (((0, 100), (100, 140)), "end at the text length"),
        ],
    )
    def test_rejects_pages_that_do_not_tile_the_text(
        self, bounds: tuple[tuple[int, int], ...], message: str
    ) -> None:
        with pytest.raises(ValidationError, match=message):
            _two_page_document(pages=_pages(*bounds))

    def test_rejects_non_consecutive_page_numbers(self) -> None:
        pages = (
            PageSpan(page=1, char_start=0, char_end=100),
            PageSpan(page=3, char_start=100, char_end=150),
        )

        with pytest.raises(ValidationError, match="numbered 1, 2, 3"):
            _two_page_document(pages=pages)

    def test_rejects_heading_outside_text(self) -> None:
        heading = Heading(level=1, title="Annex", char_offset=500)

        with pytest.raises(ValidationError, match="heading"):
            _two_page_document(headings=(heading,))

    def test_rejects_headings_out_of_order(self) -> None:
        headings = (
            Heading(level=1, title="Second", char_offset=50),
            Heading(level=1, title="First", char_offset=10),
        )

        with pytest.raises(ValidationError, match="heading"):
            _two_page_document(headings=headings)

    @pytest.mark.parametrize("text", ["", "   \n\t"])
    def test_rejects_blank_text(self, text: str) -> None:
        with pytest.raises(ValidationError):
            make_parsed_document(text, pages=_pages((0, max(len(text), 1))))

    def test_rejects_malformed_content_hash(self) -> None:
        with pytest.raises(ValidationError, match="content_hash"):
            make_parsed_document(content_hash="not-a-sha256")

    def test_rejects_invalid_doc_type(self) -> None:
        with pytest.raises(ValidationError, match="doc_type"):
            make_parsed_document(doc_type="Master Agreement")

    def test_stores_collections_as_tuples(self) -> None:
        text = "a" * 10
        document = make_parsed_document(text, pages=[PageSpan(page=1, char_start=0, char_end=10)])

        assert isinstance(document.pages, tuple)


@given(st.lists(st.integers(min_value=0, max_value=40), min_size=1, max_size=12))
def test_every_offset_maps_to_the_page_that_contains_it(page_lengths: list[int]) -> None:
    if sum(page_lengths) == 0:
        page_lengths = [*page_lengths, 1]
    bounds: list[tuple[int, int]] = []
    start = 0
    for length in page_lengths:
        bounds.append((start, start + length))
        start += length
    document = make_parsed_document("x" * start, pages=_pages(*bounds))

    for offset in range(start):
        page = document.pages[document.page_for_offset(offset) - 1]
        assert page.char_start <= offset < page.char_end


class TestDocument:
    def test_builds_valid_document(self) -> None:
        document = make_document(access_tags=["legal", "finance"])

        assert document.access_tags == ("legal", "finance")

    @pytest.mark.parametrize("tenant", ["", "   "])
    def test_rejects_blank_tenant(self, tenant: str) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            make_document(tenant_id=tenant)

    def test_rejects_zero_pages(self) -> None:
        with pytest.raises(ValidationError, match="page_count"):
            make_document(page_count=0)
