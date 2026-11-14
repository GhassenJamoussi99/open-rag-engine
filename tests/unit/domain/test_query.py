import pytest
from pydantic import ValidationError

from open_rag_engine.domain import QueryOptions, RequestContext
from tests.factories import make_context, make_query


class TestQuery:
    def test_strips_surrounding_whitespace(self) -> None:
        assert make_query("  Which law governs?\n").text == "Which law governs?"

    @pytest.mark.parametrize("text", ["", "   "])
    def test_rejects_blank_question(self, text: str) -> None:
        with pytest.raises(ValidationError, match="text"):
            make_query(text)

    def test_rejects_overlong_question(self) -> None:
        with pytest.raises(ValidationError, match="text"):
            make_query("x" * 2001)

    def test_defaults_to_no_filters_and_default_options(self) -> None:
        query = make_query()

        assert query.doc_types == ()
        assert query.options == QueryOptions()

    def test_rejects_invalid_doc_type_filter(self) -> None:
        with pytest.raises(ValidationError, match="doc_types"):
            make_query(doc_types=["NDA agreements"])

    @pytest.mark.parametrize("top_k", [0, 51])
    def test_rejects_top_k_out_of_range(self, top_k: int) -> None:
        with pytest.raises(ValidationError, match="top_k"):
            QueryOptions(top_k=top_k)


class TestRequestContext:
    def test_requires_tenant(self) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            RequestContext()  # type: ignore[call-arg]

    def test_rejects_blank_tenant(self) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            make_context(tenant_id=" ")

    def test_generates_distinct_request_and_trace_ids(self) -> None:
        first, second = make_context(), make_context()

        assert first.request_id != second.request_id
        assert first.trace_id != second.trace_id

    def test_debug_is_off_by_default(self) -> None:
        assert make_context().debug is False
