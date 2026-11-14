"""The state that travels through the query pipeline."""

from collections import Counter
from typing import Annotated, Self

from pydantic import Field, model_validator

from open_rag_engine.domain.answer import Answer
from open_rag_engine.domain.base import DomainModel
from open_rag_engine.domain.query import Query, RequestContext
from open_rag_engine.domain.retrieval import ScoredChunk
from open_rag_engine.domain.types import NonBlankStr


class StageTiming(DomainModel):
    stage: NonBlankStr
    ms: Annotated[float, Field(ge=0)]


class PipelineState(DomainModel):
    """Everything known about one request so far.

    Each stage returns a new state via `evolve()` with its own fields filled in, so
    earlier snapshots stay intact for the debug response and eval traces.
    """

    query: Query
    context: RequestContext
    variants: tuple[Query, ...] = ()
    candidates: tuple[ScoredChunk, ...] = ()
    ranked: tuple[ScoredChunk, ...] = ()
    prompt: str | None = None
    answer: Answer | None = None
    degraded: tuple[NonBlankStr, ...] = ()
    timings: tuple[StageTiming, ...] = ()

    @model_validator(mode="after")
    def _check_timings(self) -> Self:
        counts = Counter(timing.stage for timing in self.timings)
        duplicates = sorted(stage for stage, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate timings for stages: {duplicates}")
        return self

    @property
    def timings_ms(self) -> dict[str, float]:
        return {timing.stage: timing.ms for timing in self.timings}
