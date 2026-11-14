from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from open_rag_engine.domain import Chunk, ChunkDraft, Span
from tests.factories import make_chunk, make_chunk_draft


class TestChunkDraft:
    def test_builds_valid_draft(self) -> None:
        draft = make_chunk_draft(section_path=["Article 2", "2.1 Governing Law"])

        assert draft.section_path == ("Article 2", "2.1 Governing Law")

    @pytest.mark.parametrize("text", ["", "  \n "])
    def test_rejects_blank_text(self, text: str) -> None:
        with pytest.raises(ValidationError, match="text"):
            make_chunk_draft(text, span=Span(char_start=0, char_end=max(len(text), 1)))

    def test_rejects_span_that_does_not_match_text_length(self) -> None:
        with pytest.raises(ValidationError, match="span length"):
            make_chunk_draft("abc", span=Span(char_start=0, char_end=4))

    def test_rejects_reversed_page_range(self) -> None:
        with pytest.raises(ValidationError, match="page_end"):
            make_chunk_draft(page_start=3, page_end=2)

    @pytest.mark.parametrize(("field", "value"), [("token_count", 0), ("ordinal", -1)])
    def test_rejects_out_of_range_numbers(self, field: str, value: int) -> None:
        overrides: dict[str, Any] = {field: value}

        with pytest.raises(ValidationError, match=field):
            make_chunk_draft(**overrides)


class TestChunk:
    def test_builds_valid_chunk(self) -> None:
        chunk = make_chunk()

        assert chunk.parent_id is None
        assert chunk.text == "governed by the laws of Delaware"

    def test_rejects_chunk_that_is_its_own_parent(self) -> None:
        chunk = make_chunk()

        with pytest.raises(ValidationError, match="own parent"):
            make_chunk(id=chunk.id, parent_id=chunk.id)

    @pytest.mark.parametrize("field", ["embedding_model", "chunker"])
    def test_requires_provenance(self, field: str) -> None:
        overrides: dict[str, Any] = {field: ""}

        with pytest.raises(ValidationError, match=field):
            make_chunk(**overrides)

    def test_from_draft_keeps_position_and_adds_identity(self) -> None:
        draft = make_chunk_draft()
        document_id = uuid4()

        chunk = Chunk.from_draft(
            draft, document_id=document_id, embedding_model="bge-small", chunker="recursive"
        )

        assert chunk.document_id == document_id
        assert (chunk.text, chunk.span, chunk.ordinal) == (draft.text, draft.span, draft.ordinal)
        assert chunk.embedding_model == "bge-small"

    def test_stored_chunk_is_not_a_draft(self) -> None:
        assert not isinstance(make_chunk(), ChunkDraft)

    def test_inherits_draft_invariants(self) -> None:
        with pytest.raises(ValidationError, match="span length"):
            make_chunk(span=Span(char_start=0, char_end=3))
