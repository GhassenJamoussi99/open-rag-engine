import pytest
from pydantic import ValidationError

from open_rag_engine.domain import Span


def test_length_is_end_minus_start() -> None:
    assert Span(char_start=10, char_end=40).length == 30


@pytest.mark.parametrize(("start", "end"), [(5, 5), (10, 3)])
def test_rejects_empty_or_reversed_range(start: int, end: int) -> None:
    with pytest.raises(ValidationError, match="invalid span"):
        Span(char_start=start, char_end=end)


def test_rejects_negative_start() -> None:
    with pytest.raises(ValidationError):
        Span(char_start=-1, char_end=5)


def test_is_frozen() -> None:
    span = Span(char_start=0, char_end=5)

    with pytest.raises(ValidationError, match="frozen"):
        span.char_end = 6  # type: ignore[misc]


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="extra"):
        Span(char_start=0, char_end=5, length=5)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [(10, 20, True), (10, 100, True), (5, 20, False), (90, 101, False)],
)
def test_contains(start: int, end: int, expected: bool) -> None:
    outer = Span(char_start=10, char_end=100)

    assert outer.contains(Span(char_start=start, char_end=end)) is expected


@pytest.mark.parametrize("start", [True, "5", 5.0])
def test_rejects_non_integer_offsets(start: object) -> None:
    with pytest.raises(ValidationError, match="char_start"):
        Span.model_validate({"char_start": start, "char_end": 10})
