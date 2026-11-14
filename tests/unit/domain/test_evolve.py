import pytest
from pydantic import ValidationError

from open_rag_engine.domain import Span, evolve
from tests.factories import make_chunk


def test_returns_new_object_and_leaves_original_unchanged() -> None:
    span = Span(char_start=0, char_end=10)

    moved = evolve(span, char_end=20)

    assert moved == Span(char_start=0, char_end=20)
    assert span.char_end == 10


def test_revalidates_the_result() -> None:
    span = Span(char_start=5, char_end=10)

    with pytest.raises(ValidationError, match="invalid span"):
        evolve(span, char_end=5)


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra"):
        evolve(Span(char_start=0, char_end=10), lenght=3)


def test_keeps_nested_objects_without_copying() -> None:
    chunk = make_chunk()

    renumbered = evolve(chunk, ordinal=7)

    assert renumbered.ordinal == 7
    assert renumbered.span is chunk.span
