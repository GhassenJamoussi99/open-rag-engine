"""Character ranges inside a document's full parsed text."""

from typing import Self

from pydantic import model_validator

from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.types import Offset


class Span(DomainModel):
    """A half-open character range `[char_start, char_end)`; never empty.

    Offsets count Unicode code points (Python `str` indexing), not bytes or UTF-16 units.
    """

    char_start: Offset
    char_end: Offset

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        if self.char_start >= self.char_end:
            raise ValueError(
                f"invalid span [{self.char_start}, {self.char_end}): end must be after start"
            )
        return self

    @property
    def length(self) -> int:
        return self.char_end - self.char_start

    def contains(self, other: "Span") -> bool:
        return self.char_start <= other.char_start and other.char_end <= self.char_end
