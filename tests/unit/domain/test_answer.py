import math

import pytest
from pydantic import ValidationError

from tests.factories import make_answer, make_citation, make_scored_chunk


class TestScoredChunk:
    @pytest.mark.parametrize("source", ["dense", "bm25", "fused", "reranked"])
    def test_accepts_known_sources(self, source: str) -> None:
        assert make_scored_chunk(source=source).source == source

    def test_rejects_unknown_source(self) -> None:
        with pytest.raises(ValidationError, match="source"):
            make_scored_chunk(source="magic")

    @pytest.mark.parametrize("score", [math.nan, math.inf])
    def test_rejects_non_finite_score(self, score: float) -> None:
        with pytest.raises(ValidationError, match="score"):
            make_scored_chunk(score=score)


class TestCitation:
    def test_rejects_marker_below_one(self) -> None:
        with pytest.raises(ValidationError, match="marker"):
            make_citation(marker=0)

    def test_rejects_reversed_page_range(self) -> None:
        with pytest.raises(ValidationError, match="page_end"):
            make_citation(page_start=4, page_end=3)

    def test_rejects_blank_quote(self) -> None:
        with pytest.raises(ValidationError, match="quote"):
            make_citation(quote=" ")

    def test_verdict_is_unset_until_verified(self) -> None:
        assert make_citation().verdict is None


class TestAnswer:
    def test_cited_answer_is_not_flagged(self) -> None:
        assert make_answer().uncited is False

    def test_answer_without_citations_is_flagged_uncited(self) -> None:
        assert make_answer(citations=()).uncited is True

    def test_refusal_is_not_flagged_uncited(self) -> None:
        answer = make_answer(text="The documents don't say.", refused=True, citations=())

        assert answer.uncited is False

    def test_rejects_refusal_with_citations(self) -> None:
        with pytest.raises(ValidationError, match="refused answer"):
            make_answer(refused=True)

    def test_rejects_duplicate_markers(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            make_answer(citations=(make_citation(1), make_citation(1)))

    def test_rejects_blank_text(self) -> None:
        with pytest.raises(ValidationError, match="text"):
            make_answer(text="")


def test_citation_rejects_quote_longer_than_its_span() -> None:
    with pytest.raises(ValidationError, match="quote"):
        make_citation(quote="x" * 33)
