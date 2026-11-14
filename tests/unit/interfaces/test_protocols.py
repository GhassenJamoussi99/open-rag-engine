"""The fakes satisfy every Protocol (checked by mypy) and compose into a working pipeline."""

import asyncio
from uuid import uuid4

import pytest

from open_rag_engine.domain import Chunk, Document, PipelineState
from open_rag_engine.interfaces import (
    LLM,
    Chunker,
    DocumentRepository,
    EmbeddedChunk,
    Embedder,
    LLMRequest,
    Parser,
    Retriever,
    SourceFile,
    Stage,
    StreamEnd,
    TextDelta,
    VectorStore,
)
from tests.factories import CONTRACT_TEXT, make_context, make_query
from tests.fakes import (
    FakeChunker,
    FakeDenseRetriever,
    FakeEmbedder,
    FakeParser,
    InMemoryStore,
    RetrieveStage,
    ScriptedLLM,
)


async def _ingest(
    store: InMemoryStore,
    embedder: Embedder,
    tenant: str,
    uri: str = "contracts/msa.txt",
    access_tags: tuple[str, ...] = (),
) -> Document:
    parser: Parser = FakeParser()
    chunker: Chunker = FakeChunker(size=60)
    repository: DocumentRepository = store

    parsed = parser.parse(
        SourceFile(source_uri=uri, content=CONTRACT_TEXT.encode(), doc_type="contract")
    )
    document = Document(
        id=uuid4(),
        source_uri=parsed.source_uri,
        content_hash=parsed.content_hash,
        doc_type=parsed.doc_type,
        title=parsed.title,
        tenant_id=tenant,
        access_tags=access_tags,
        page_count=parsed.page_count,
    )
    drafts = chunker.chunk(parsed)
    chunks = [
        Chunk.from_draft(
            draft, document_id=document.id, embedding_model=embedder.model_name, chunker="fake"
        )
        for draft in drafts
    ]
    vectors = embedder.embed_passages([chunk.text for chunk in chunks])
    await repository.replace(
        document,
        [EmbeddedChunk(chunk=c, vector=v) for c, v in zip(chunks, vectors, strict=True)],
    )
    assert all(parsed.text_at(chunk.span) == chunk.text for chunk in chunks)
    return document


def _query_state(tenant: str, question: str, access_tags: tuple[str, ...] = ()) -> PipelineState:
    context = make_context(tenant_id=tenant, access_tags=access_tags)
    return PipelineState(query=make_query(question), context=context)


def test_ingest_then_retrieve_returns_the_relevant_chunk() -> None:
    store = InMemoryStore()
    embedder = FakeEmbedder()
    asyncio.run(_ingest(store, embedder, tenant="acme"))
    vector_store: VectorStore = store
    retriever: Retriever = FakeDenseRetriever(embedder, store)
    stage: Stage = RetrieveStage(retriever)

    state = asyncio.run(stage.run(_query_state("acme", "governed by the laws of which state")))

    assert vector_store is store
    assert state.candidates
    assert "Delaware" in state.candidates[0].chunk.text
    assert state.candidates[0].source == "dense"


def test_tenant_filter_hides_other_tenants_documents() -> None:
    store = InMemoryStore()
    embedder = FakeEmbedder()
    asyncio.run(_ingest(store, embedder, tenant="acme"))
    stage = RetrieveStage(FakeDenseRetriever(embedder, store))

    state = asyncio.run(stage.run(_query_state("globex", "governing law")))

    assert state.candidates == ()


def test_replace_swaps_chunks_and_delete_removes_them() -> None:
    store = InMemoryStore()
    embedder = FakeEmbedder()
    first = asyncio.run(_ingest(store, embedder, tenant="acme"))
    second = asyncio.run(_ingest(store, embedder, tenant="acme"))
    stage = RetrieveStage(FakeDenseRetriever(embedder, store))

    hits = asyncio.run(stage.run(_query_state("acme", "Delaware"))).candidates
    assert {hit.chunk.document_id for hit in hits} == {second.id}
    assert asyncio.run(store.get_by_uri("acme", first.source_uri)) == second

    asyncio.run(store.delete("acme", second.id))

    assert asyncio.run(store.get_by_uri("acme", second.source_uri)) is None
    assert asyncio.run(stage.run(_query_state("acme", "Delaware"))).candidates == ()


def test_same_path_in_two_tenants_is_two_separate_documents() -> None:
    store = InMemoryStore()
    embedder = FakeEmbedder()
    acme = asyncio.run(_ingest(store, embedder, tenant="acme"))
    globex = asyncio.run(_ingest(store, embedder, tenant="globex"))

    assert asyncio.run(store.get_by_uri("acme", acme.source_uri)) == acme
    assert asyncio.run(store.get_by_uri("globex", globex.source_uri)) == globex


def test_delete_ignores_documents_of_other_tenants() -> None:
    store = InMemoryStore()
    acme = asyncio.run(_ingest(store, FakeEmbedder(), tenant="acme"))

    asyncio.run(store.delete("globex", acme.id))

    assert asyncio.run(store.get_by_uri("acme", acme.source_uri)) == acme


@pytest.mark.parametrize(
    ("document_tags", "user_tags", "visible"),
    [
        ((), (), True),
        (("legal",), ("legal", "hr"), True),
        (("legal",), ("hr",), False),
        (("legal",), (), False),
    ],
)
def test_access_tags_hide_documents_the_user_cannot_read(
    document_tags: tuple[str, ...], user_tags: tuple[str, ...], visible: bool
) -> None:
    store = InMemoryStore()
    embedder = FakeEmbedder()
    asyncio.run(_ingest(store, embedder, tenant="acme", access_tags=document_tags))
    stage = RetrieveStage(FakeDenseRetriever(embedder, store))

    state = asyncio.run(stage.run(_query_state("acme", "Delaware", access_tags=user_tags)))

    assert bool(state.candidates) is visible


def test_llm_generates_and_streams_the_same_text() -> None:
    llm: LLM = ScriptedLLM("Delaware law governs [1].")
    request = LLMRequest(system="Answer from the context.", prompt="[1] governed by Delaware")

    async def collect() -> tuple[str, str]:
        response = await llm.generate(request)
        events = [event async for event in llm.stream(request)]
        assert isinstance(events[-1], StreamEnd)
        streamed = "".join(e.text for e in events if isinstance(e, TextDelta))
        return response.text, streamed.strip()

    generated, streamed = asyncio.run(collect())

    assert generated == streamed == "Delaware law governs [1]."
