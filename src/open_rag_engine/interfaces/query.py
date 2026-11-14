"""Protocols for the query side: search, retrieve, generate, and pipeline stages."""

from collections.abc import AsyncIterator
from typing import Protocol

from open_rag_engine.domain import PipelineState, Query, ScoredChunk
from open_rag_engine.interfaces.filters import SearchFilters
from open_rag_engine.interfaces.llm import LLMEvent, LLMRequest, LLMResponse
from open_rag_engine.interfaces.types import Vector


class VectorStore(Protocol):
    async def search(self, vector: Vector, k: int, filters: SearchFilters) -> list[ScoredChunk]: ...


class Retriever(Protocol):
    @property
    def name(self) -> str: ...

    async def retrieve(self, query: Query, filters: SearchFilters, k: int) -> list[ScoredChunk]: ...


class LLM(Protocol):
    @property
    def model_name(self) -> str: ...

    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    def stream(self, request: LLMRequest) -> AsyncIterator[LLMEvent]: ...


class Stage(Protocol):
    """One pipeline step. Returns a new state; never mutates the one it received."""

    @property
    def name(self) -> str: ...

    async def run(self, state: PipelineState) -> PipelineState: ...
