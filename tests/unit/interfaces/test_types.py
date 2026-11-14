from typing import Any

import pytest
from pydantic import ValidationError

from open_rag_engine.interfaces import (
    EmbeddedChunk,
    LLMRequest,
    LLMResponse,
    SearchFilters,
    SourceFile,
    StreamEnd,
    TextDelta,
    build_filters,
)
from tests.factories import make_chunk, make_context, make_query, sha256_hex


class TestBuildFilters:
    def test_always_carries_tenant_and_access_tags_from_context(self) -> None:
        context = make_context(tenant_id="acme", access_tags=["legal"])

        filters = build_filters(context, make_query(doc_types=["nda"]))

        assert filters == SearchFilters(
            tenant_id="acme", access_tags=("legal",), doc_types=("nda",)
        )

    def test_search_filters_require_tenant(self) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            SearchFilters(tenant_id="")


class TestSourceFile:
    def test_exposes_suffix_and_content_hash(self) -> None:
        source = SourceFile(
            source_uri="contracts/MSA.PDF", content=b"%PDF-1.7", doc_type="contract"
        )

        assert source.suffix == ".pdf"
        assert source.content_hash == sha256_hex("%PDF-1.7")

    def test_rejects_empty_content(self) -> None:
        with pytest.raises(ValidationError, match="content"):
            SourceFile(source_uri="a.pdf", content=b"", doc_type="contract")


class TestEmbeddedChunk:
    def test_rejects_empty_vector(self) -> None:
        with pytest.raises(ValidationError, match="vector"):
            EmbeddedChunk(chunk=make_chunk(), vector=())


class TestLLMTypes:
    def test_request_defaults_to_deterministic_sampling(self) -> None:
        request = LLMRequest(system="Answer from the context.", prompt="[1] ...")

        assert request.temperature == 0.0
        assert request.max_tokens > 0

    @pytest.mark.parametrize(("field", "value"), [("max_tokens", 0), ("temperature", 2.5)])
    def test_request_rejects_out_of_range_settings(self, field: str, value: float) -> None:
        overrides: dict[str, Any] = {field: value}

        with pytest.raises(ValidationError, match=field):
            LLMRequest(system="s", prompt="p", **overrides)

    def test_stream_events_are_tagged(self) -> None:
        response = LLMResponse(text="Delaware [1].", model="fake", input_tokens=10, output_tokens=3)

        assert TextDelta(text="Dela").type == "text_delta"
        assert StreamEnd(response=response).type == "end"
